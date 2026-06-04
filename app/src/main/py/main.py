from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import time
from urllib.parse import urlparse
from uuid import uuid4

from app.src.main.py.application.ai_service import AiAnalyticsService
from app.src.main.py.application.services import DemoService
from app.src.main.py.config import get_settings
from app.src.main.py.infrastructure.database import initialize_database
from app.src.main.py.infrastructure.llm_client import GeminiClient
from app.src.main.py.infrastructure.sqlite_repository import SqliteDemoRepository
from app.src.main.py.interface.routes import dispatch
from app.src.main.py.logging_config import configure_logging

logger = logging.getLogger(__name__)
settings = get_settings()

class DemoRequestHandler(BaseHTTPRequestHandler):
    service: DemoService
    ai_service: AiAnalyticsService | None

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def do_OPTIONS(self) -> None:
        logger.info("request method=OPTIONS path=%s", self.path)
        self.send_response(204)
        self._send_headers()
        self.end_headers()
        logger.info("response method=OPTIONS path=%s status=204", self.path)

    def _handle(self) -> None:
        request_id = uuid4().hex[:12]
        started_at = time.perf_counter()
        parsed_url = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length else b""
        logger.info(
            "request id=%s method=%s path=%s query=%s remote=%s body=%s",
            request_id,
            self.command,
            parsed_url.path,
            parsed_url.query or "-",
            self.client_address[0],
            _format_body_for_log(body),
        )
        try:
            status, payload = dispatch(
                self.command,
                parsed_url.path,
                parsed_url.query,
                body,
                self.service,
                self.ai_service,
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            status, payload = 422, {"detail": str(exc)}
        except RuntimeError as exc:
            status, payload = 503, {"detail": str(exc)}
        except Exception as exc:
            logger.exception("unexpected error id=%s method=%s path=%s", request_id, self.command, parsed_url.path)
            status, payload = 500, {"detail": "Internal server error", "error": str(exc)}

        response = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._send_headers()
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "response id=%s method=%s path=%s status=%s elapsed_ms=%.2f body=%s",
            request_id,
            self.command,
            parsed_url.path,
            status,
            elapsed_ms,
            _format_body_for_log(response),
        )

    def _send_headers(self) -> None:
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format: str, *args: object) -> None:
        logger.info("http_server " + format, *args)

def _format_body_for_log(body: bytes) -> str:
    if not body:
        return "-"
    text = body.decode("utf-8", errors="replace")
    max_length = settings.max_log_body_length
    if len(text) > max_length:
        return f"{text[:max_length]}...<truncated {len(text) - max_length} chars>"
    return text

def create_server(host: str = "0.0.0.0", port: int = 8080) -> ThreadingHTTPServer:
    configure_logging(Path(__file__).resolve().parents[2])
    logger.info("starting Demo API host=%s port=%s database=%s csv_data=%s", host, port, settings.database_path, settings.csv_data_path)
    initialize_database(settings.database_path, settings.csv_data_path)
    demo_service = DemoService(SqliteDemoRepository(settings.database_path))
    gemini_client = GeminiClient(settings.gemini_api_key, settings.gemini_model)
    DemoRequestHandler.service = demo_service
    if settings.gemini_api_key:
        DemoRequestHandler.ai_service = AiAnalyticsService(demo_service, gemini_client)
    else:
        DemoRequestHandler.ai_service = None
    logger.info("services initialized ai_configured=%s gemini_model=%s", bool(settings.gemini_api_key), settings.gemini_model)
    return ThreadingHTTPServer((host, port), DemoRequestHandler)

def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    server = create_server(host, port)
    try:
        print(f"Demo API running at http://{host}:{port}/api")
    except OSError:
        pass
    server.serve_forever()

if __name__ == "__main__":
    main()
