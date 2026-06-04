from datetime import datetime, timedelta
import json
import logging
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from app.src.main.py.application.services import DemoService

logger = logging.getLogger(__name__)

class TextGenerator(Protocol):
    def generate_text(self, prompt: str) -> str: ...

ALLOWED_METRICS = [
    "general_summary",
    "users_count",
    "cards_count",
    "transactions_count",
    "users_with_transactions_count",
    "users_with_transactions",
    "total_amount",
    "average_amount",
    "min_transaction",
    "max_transaction",
    "transactions_by_date",
    "transactions_by_operation_type",
    "cards_by_type",
    "cards_total_balance",
    "cards_average_balance",
    "user_financial_summary",
    "user_total_charges",
    "user_total_payments",
    "user_net_movement",
    "ranking_users_by_spending",
    "ranking_users_by_payments",
    "ranking_cards_by_balance",
]

class AiAnalyticsService:
    def __init__(self, demo_service: DemoService, text_generator: TextGenerator) -> None:
        self.demo_service = demo_service
        self.text_generator = text_generator

    def ask(self, question: str) -> dict[str, Any]:
        logger.info("processing AI analytics question question=%s", question)
        plan = self._plan(question)
        metric = plan["metric"]
        filters = plan.get("filters") or {}
        logger.info("AI planned analytics query metric=%s filters=%s", metric, filters)
        analytics_result = self.demo_service.analytics_query(metric, filters)
        answer = self._answer(question, analytics_result)
        logger.info("AI analytics answer generated metric=%s filters=%s", metric, filters)
        return {
            "question": question,
            "metric": metric,
            "filters": filters,
            "result": analytics_result["result"],
            "answer": answer,
        }

    def _plan(self, question: str) -> dict[str, Any]:
        today = datetime.now(ZoneInfo("America/Santiago")).date()
        prompt = f"""
You are an API metric planner for a Demo analytics microservice.
Return only valid JSON, without Markdown.

Current date: {today.isoformat()}
Yesterday: {(today - timedelta(days=1)).isoformat()}

Allowed metrics:
{json.dumps(ALLOWED_METRICS, ensure_ascii=False)}

Allowed filters:
- date: YYYY-MM-DD
- from: YYYY-MM-DD
- to: YYYY-MM-DD
- operationType: output or input
- customer_id: integer
- type: credit or debit
- limit: integer

Rules:
- Never create SQL.
- Choose exactly one metric.
- For "transacciones" count questions, use transactions_count.
- For amount total questions, use total_amount.
- For "ayer", use the Yesterday value above.
- Return this shape: {{"metric": "transactions_count", "filters": {{"date": "YYYY-MM-DD"}}}}

User question:
{question}
"""
        raw = self.text_generator.generate_text(prompt)
        plan = self._parse_json(raw)
        metric = plan.get("metric")
        if metric not in ALLOWED_METRICS:
            logger.warning("AI planned unsupported metric metric=%s raw=%s", metric, raw)
            raise ValueError(f"Unsupported metric planned by AI: {metric}")
        filters = plan.get("filters")
        if filters is None:
            plan["filters"] = {}
        if not isinstance(plan["filters"], dict):
            logger.warning("AI returned invalid filters filters=%s", plan["filters"])
            raise ValueError("AI filters must be an object")
        return plan

    def _answer(self, question: str, analytics_result: dict[str, Any]) -> str:
        prompt = f"""
You answer Demo metric questions in Spanish.
Use only the provided API result. Do not invent data.
Be concise and mention filters when they matter.

Question:
{question}

API result:
{json.dumps(analytics_result, ensure_ascii=False)}
"""
        return self.text_generator.generate_text(prompt).strip()

    def _parse_json(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"AI did not return JSON: {text}")
        return json.loads(cleaned[start : end + 1])
