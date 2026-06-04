from functools import lru_cache
from pathlib import Path
import os
import re

class Settings:
    def __init__(
        self,
        database_path: Path,
        csv_data_path: Path,
        gemini_api_key: str | None,
        gemini_model: str,
        limits: dict[str, int],
        max_log_body_length: int,
    ) -> None:
        self.database_path = database_path
        self.csv_data_path = csv_data_path
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.limits = limits
        self.max_log_body_length = max_log_body_length

def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]

def _resource_path() -> Path:
    return Path(__file__).resolve().parents[1] / "resource" / "application.yml"

def _parse_scalar(value: str) -> int | str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if re.fullmatch(r"[0-9_]+", value):
        return int(value.replace("_", ""))
    return value

def _load_yaml(path: Path) -> dict[str, int | str | dict[str, int | str]]:
    result: dict[str, object] = {}
    parents: list[tuple[int, dict[str, object]]] = [(0, result)]
    with path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            key, sep, value = line.lstrip().partition(":")
            if sep != ":":
                continue
            key = key.strip()
            value = value.strip()
            while len(parents) > 1 and indent <= parents[-1][0]:
                parents.pop()
            parent = parents[-1][1]
            if value == "":
                node: dict[str, object] = {}
                parent[key] = node
                parents.append((indent, node))
            else:
                parent[key] = _parse_scalar(value)
    return result  # type: ignore[return-value]

@lru_cache
def get_settings() -> Settings:
    root = _project_root()
    resource_path = _resource_path()
    yml = _load_yaml(resource_path)
    limits = yml.get("limits", {}) if isinstance(yml, dict) else {}
    max_log_body_length_value = limits.get("MAX_LOG_BODY_LENGTH", 5000)
    if isinstance(max_log_body_length_value, str):
        max_log_body_length_value = int(max_log_body_length_value)
    return Settings(
        database_path=root / os.getenv("DATABASE_PATH", "database/database-demo.sqlite"),
        csv_data_path=root / os.getenv("CSV_DATA_PATH", "database/data/raw"),
        gemini_api_key=os.getenv("LLM_API_KEY"),
        gemini_model=os.getenv("LLM_MODEL", "gemini-flash-latest"),
        limits={
            key: int(value)
            for key, value in limits.items()
            if isinstance(value, (int, str)) and str(value).isdigit()
        },
        max_log_body_length=int(max_log_body_length_value),
    )
