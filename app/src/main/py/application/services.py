import logging
from typing import Any

from app.src.main.py.infrastructure.sqlite_repository import SqliteDemoRepository

logger = logging.getLogger(__name__)

class DemoService:
    def __init__(self, repository: SqliteDemoRepository) -> None:
        self.repository = repository

    def general_summary(self) -> dict[str, Any]:
        logger.info("building general summary")
        return {
            "totalUsers": self.repository.count_customers(),
            "totalCards": self.repository.count_cards(),
            "totalTransactions": self.repository.count_transactions({}),
            "totalCharges": self.repository.transaction_amount("SUM", {"operationType": "output"}),
            "totalPayments": self.repository.transaction_amount("SUM", {"operationType": "input"}),
            "totalCurrentBalance": self.repository.cards_balance("SUM"),
        }

    def user_net_movement(self, user_id: int, filters: dict[str, Any]) -> float:
        logger.info("calculating user net movement user_id=%s filters=%s", user_id, filters)
        payments = self.repository.user_transaction_amount(user_id, "input", filters)
        charges = self.repository.user_transaction_amount(user_id, "output", filters)
        return round(payments - charges, 2)

    def analytics_query(self, metric: str, filters: dict[str, Any]) -> dict[str, Any]:
        logger.info("executing analytics query metric=%s filters=%s", metric, filters)
        handlers = {
            "general_summary": lambda: self.general_summary(),
            "users_count": lambda: {"count": self.repository.count_customers()},
            "cards_count": lambda: {"count": self.repository.count_cards(filters.get("type"))},
            "transactions_count": lambda: {"count": self.repository.count_transactions(filters)},
            "users_with_transactions_count": lambda: {"count": self.repository.count_users_with_transactions(filters)},
            "users_with_transactions": lambda: self.repository.users_with_transactions(filters),
            "total_amount": lambda: {"amount": self.repository.transaction_amount("SUM", filters)},
            "average_amount": lambda: {"amount": self.repository.transaction_amount("AVG", filters)},
            "min_transaction": lambda: self.repository.transaction_extreme("ASC", filters.get("operationType")),
            "max_transaction": lambda: self.repository.transaction_extreme("DESC", filters.get("operationType")),
            "transactions_by_date": lambda: self.repository.transactions_by_date(filters),
            "transactions_by_operation_type": lambda: self.repository.transactions_by_operation_type(),
            "cards_by_type": lambda: self.repository.cards_by_type(),
            "cards_total_balance": lambda: {"amount": self.repository.cards_balance("SUM", filters.get("type"))},
            "cards_average_balance": lambda: {"amount": self.repository.cards_balance("AVG", filters.get("type"))},
            "user_financial_summary": lambda: self.repository.user_summary(int(filters["customer_id"])),
            "user_total_charges": lambda: {"amount": self.repository.user_transaction_amount(int(filters["customer_id"]), "output", filters)},
            "user_total_payments": lambda: {"amount": self.repository.user_transaction_amount(int(filters["customer_id"]), "input", filters)},
            "user_net_movement": lambda: {"amount": self.user_net_movement(int(filters["customer_id"]), filters)},
            "ranking_users_by_spending": lambda: self.repository.ranking_users("output", filters, int(filters.get("limit", 10))),
            "ranking_users_by_payments": lambda: self.repository.ranking_users("input", filters, int(filters.get("limit", 10))),
            "ranking_cards_by_balance": lambda: self.repository.ranking_cards_by_balance(filters.get("type"), int(filters.get("limit", 10))),
        }
        if metric not in handlers:
            logger.warning("unsupported analytics metric metric=%s filters=%s", metric, filters)
            raise ValueError(f"Unsupported metric: {metric}")
        result = handlers[metric]()
        logger.info("analytics query completed metric=%s filters=%s", metric, filters)
        return {"metric": metric, "filters": filters, "result": result}
