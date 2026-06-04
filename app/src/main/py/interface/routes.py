import json
from typing import Any
from urllib.parse import parse_qs

from app.src.main.py.application.ai_service import AiAnalyticsService
from app.src.main.py.application.services import DemoService

Response = tuple[int, dict[str, Any] | list[dict[str, Any]]]

def dispatch(
    method: str,
    path: str,
    raw_query: str,
    body: bytes,
    service: DemoService,
    ai_service: AiAnalyticsService | None = None,
) -> Response:
    query = _query_params(raw_query)
    segments = [segment for segment in path.strip("/").split("/") if segment]
    if not segments or segments[0] != "api":
        return _not_found()

    resource = segments[1:] if len(segments) > 1 else []

    if method == "GET" and resource == ["health"]:
        return 200, {"status": "ok"}

    if method == "GET" and resource == ["customers"]:
        return 200, service.repository.list_customers(_int(query, "limit", 50), _int(query, "offset", 0))
    if method == "GET" and resource == ["customers", "search"]:
        return 200, service.repository.search_customers(query.get("q", ""))
    if method == "GET" and len(resource) == 2 and resource[0] == "customers":
        return _required(service.repository.get_customer(int(resource[1])), "Customer not found")
    if method == "GET" and len(resource) == 3 and resource[0] == "customers" and resource[2] == "cards":
        return 200, service.repository.list_customer_cards(int(resource[1]))
    if method == "GET" and len(resource) == 3 and resource[0] == "customers" and resource[2] == "transactions":
        return 200, service.repository.list_customer_transactions(
            int(resource[1]), query.get("from"), query.get("to"), query.get("operationType"), _int(query, "limit", 50)
        )

    if method == "GET" and resource == ["cards"]:
        return 200, service.repository.list_cards(_first(query, "type"), _float(query, "minAmount"), _float(query, "maxAmount"))
    if method == "GET" and len(resource) == 2 and resource[0] == "cards":
        return _required(service.repository.get_card(int(resource[1])), "Card not found")
    if method == "GET" and len(resource) == 3 and resource[0] == "cards" and resource[2] == "transactions":
        return 200, service.repository.list_card_transactions(
            int(resource[1]), query.get("from"), query.get("to"), query.get("operationType")
        )

    if method == "GET" and resource == ["transactions"]:
        return 200, service.repository.list_transactions(_filters(query))
    if method == "GET" and len(resource) == 2 and resource[0] == "transactions":
        return _required(service.repository.get_transaction(int(resource[1])), "Transaction not found")

    if method == "GET" and resource == ["analytics", "summary"]:
        return 200, service.general_summary()
    if method == "GET" and resource == ["analytics", "users", "count"]:
        return 200, {"count": service.repository.count_customers()}
    if method == "GET" and resource == ["analytics", "cards", "count"]:
        return 200, {"count": service.repository.count_cards(query.get("type"))}
    if method == "GET" and resource == ["analytics", "transactions", "count"]:
        return 200, {"count": service.repository.count_transactions(_filters(query))}
    if method == "GET" and resource == ["analytics", "users-with-transactions", "count"]:
        return 200, {"count": service.repository.count_users_with_transactions(_filters(query))}
    if method == "GET" and resource == ["analytics", "users-with-transactions"]:
        return 200, service.repository.users_with_transactions(_filters(query))
    if method == "GET" and resource == ["analytics", "transactions", "total-amount"]:
        return 200, {"amount": service.repository.transaction_amount("SUM", _filters(query))}
    if method == "GET" and resource == ["analytics", "transactions", "average-amount"]:
        return 200, {"amount": service.repository.transaction_amount("AVG", _filters(query))}
    if method == "GET" and resource == ["analytics", "transactions", "min-amount"]:
        return _required(service.repository.transaction_extreme("ASC", query.get("operationType")), "Transaction not found")
    if method == "GET" and resource == ["analytics", "transactions", "max-amount"]:
        return _required(service.repository.transaction_extreme("DESC", query.get("operationType")), "Transaction not found")
    if method == "GET" and resource == ["analytics", "transactions", "by-date"]:
        return 200, service.repository.transactions_by_date(_filters(query))
    if method == "GET" and resource == ["analytics", "transactions", "by-operation-type"]:
        return 200, service.repository.transactions_by_operation_type()
    if method == "GET" and resource == ["analytics", "cards", "by-type"]:
        return 200, service.repository.cards_by_type()
    if method == "GET" and resource == ["analytics", "cards", "total-balance"]:
        return 200, {"amount": service.repository.cards_balance("SUM", query.get("type"))}
    if method == "GET" and resource == ["analytics", "cards", "average-balance"]:
        return 200, {"amount": service.repository.cards_balance("AVG", query.get("type"))}

    if method == "GET" and len(resource) == 4 and resource[:2] == ["analytics", "users"] and resource[3] == "summary":
        return _required(service.repository.user_summary(int(resource[2])), "Customer not found")
    if method == "GET" and len(resource) == 4 and resource[:2] == ["analytics", "users"] and resource[3] == "total-charges":
        return 200, {"amount": service.repository.user_transaction_amount(int(resource[2]), "output", _filters(query))}
    if method == "GET" and len(resource) == 4 and resource[:2] == ["analytics", "users"] and resource[3] == "total-payments":
        return 200, {"amount": service.repository.user_transaction_amount(int(resource[2]), "input", _filters(query))}
    if method == "GET" and len(resource) == 4 and resource[:2] == ["analytics", "users"] and resource[3] == "net-movement":
        return 200, {"amount": service.user_net_movement(int(resource[2]), _filters(query))}

    if method == "GET" and resource == ["analytics", "ranking", "users-by-spending"]:
        return 200, service.repository.ranking_users("output", _filters(query), _int(query, "limit", 10))
    if method == "GET" and resource == ["analytics", "ranking", "users-by-payments"]:
        return 200, service.repository.ranking_users("input", _filters(query), _int(query, "limit", 10))
    if method == "GET" and resource == ["analytics", "ranking", "cards-by-balance"]:
        return 200, service.repository.ranking_cards_by_balance(query.get("type"), _int(query, "limit", 10))

    if method == "POST" and resource == ["analytics", "query"]:
        payload = json.loads(body.decode("utf-8") or "{}")
        return 200, service.analytics_query(payload["metric"], payload.get("filters") or {})

    if method == "POST" and resource in (["ai", "query"], ["ai", "ask"]):
        if ai_service is None:
            return 503, {"detail": "AI service is not configured"}
        payload = json.loads(body.decode("utf-8") or "{}")
        question = str(payload.get("question") or "").strip()
        if not question:
            return 422, {"detail": "Missing field: question"}
        return 200, ai_service.ask(question)

    return _not_found()

def _query_params(raw_query: str) -> dict[str, str]:
    return {key: values[-1] for key, values in parse_qs(raw_query, keep_blank_values=False).items()}

def _filters(query: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("date", "from", "to", "operationType"):
        if key in query:
            result[key] = query[key]
    for key in ("minAmount", "maxAmount"):
        if key in query:
            result[key] = float(query[key])
    if "limit" in query:
        result["limit"] = int(query["limit"])
    return result

def _required(value: dict[str, Any] | None, message: str) -> Response:
    if value is None:
        return 404, {"detail": message}
    return 200, value

def _not_found() -> Response:
    return 404, {"detail": "Route not found"}

def _int(query: dict[str, str], key: str, default: int) -> int:
    return int(query.get(key) or default)

def _float(query: dict[str, str], key: str) -> float | None:
    return float(query[key]) if key in query else None

def _first(query: dict[str, str], key: str) -> str | None:
    return query[key] if key in query else None
