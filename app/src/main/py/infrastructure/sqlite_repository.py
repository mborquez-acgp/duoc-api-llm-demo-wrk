import sqlite3
from pathlib import Path
from typing import Any

from app.src.main.py.infrastructure.database import connect

class SqliteDemoRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def list_customers(self, limit: int, offset: int) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT customer_id, full_name AS nombreCompleto, email
            FROM Customers
            ORDER BY customer_id
            LIMIT ? OFFSET ?
            """,
            [limit, offset],
        )

    def get_customer(self, user_id: int) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            SELECT customer_id, full_name AS nombreCompleto, email
            FROM Customers
            WHERE customer_id = ?
            """,
            [user_id],
        )

    def search_customers(self, query: str) -> list[dict[str, Any]]:
        term = f"%{query}%"
        return self._fetch_all(
            """
            SELECT customer_id, full_name AS nombreCompleto, email
            FROM Customers
            WHERE full_name LIKE ? OR email LIKE ?
            ORDER BY customer_id
            """,
            [term, term],
        )

    def list_cards(
        self,
        card_type: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._card_filters(card_type, min_amount, max_amount)
        return self._fetch_all(
            f"""
            SELECT card_id, customer_id, {self._masked_card_sql()} AS numeroTarjetaMasked,
                   card_type AS tipoTarjeta, ROUND(operation_ammount_actual, 2) AS operation_ammountActual
            FROM Cards
            {where}
            ORDER BY card_id
            """,
            params,
        )

    def get_card(self, card_id: int) -> dict[str, Any] | None:
        return self._fetch_one(
            f"""
            SELECT card_id, customer_id, {self._masked_card_sql()} AS numeroTarjetaMasked,
                   card_type AS tipoTarjeta, ROUND(operation_ammount_actual, 2) AS operation_ammountActual
            FROM Cards
            WHERE card_id = ?
            """,
            [card_id],
        )

    def list_customer_cards(self, user_id: int) -> list[dict[str, Any]]:
        return self._fetch_all(
            f"""
            SELECT card_id, customer_id, {self._masked_card_sql()} AS numeroTarjetaMasked,
                   card_type AS tipoTarjeta, ROUND(operation_ammount_actual, 2) AS operation_ammountActual
            FROM Cards
            WHERE customer_id = ?
            ORDER BY card_id
            """,
            [user_id],
        )

    def list_card_transactions(
        self,
        card_id: int,
        date_from: str | None = None,
        date_to: str | None = None,
        operation_type: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        filters = {"from": date_from, "to": date_to, "operationType": operation_type}
        where, params = self._transaction_filters(filters, prefix="t")
        params.insert(0, card_id)
        limit_sql = "LIMIT ?" if limit else ""
        if limit:
            params.append(limit)
        return self._fetch_all(
            f"""
            SELECT t.transaction_id, t.card_id, t.operation_date AS fechaTransaccion,
                   t.operation_type AS tipoOperacion, ROUND(t.operation_ammount, 2) AS operation_ammount, t.operation_desc
            FROM Transactions t
            WHERE t.card_id = ?
            {where.replace("WHERE", "AND", 1)}
            ORDER BY t.operation_date DESC, t.transaction_id DESC
            {limit_sql}
            """,
            params,
        )

    def list_customer_transactions(
        self,
        user_id: int,
        date_from: str | None = None,
        date_to: str | None = None,
        operation_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        filters = {"from": date_from, "to": date_to, "operationType": operation_type}
        where, params = self._transaction_filters(filters, prefix="t")
        params.insert(0, user_id)
        params.append(limit)
        return self._fetch_all(
            f"""
            {self._transaction_detail_select()}
            WHERE c.customer_id = ?
            {where.replace("WHERE", "AND", 1)}
            ORDER BY t.operation_date DESC, t.transaction_id DESC
            LIMIT ?
            """,
            params,
        )

    def list_transactions(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        where, params = self._transaction_filters(filters, prefix="t", include_amount=True)
        limit = min(int(filters.get("limit") or 50), 500)
        params.append(limit)
        return self._fetch_all(
            f"""
            {self._transaction_detail_select()}
            {where}
            ORDER BY t.operation_date DESC, t.transaction_id DESC
            LIMIT ?
            """,
            params,
        )

    def get_transaction(self, transaction_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            f"""
            {self._transaction_detail_select()}
            WHERE t.transaction_id = ?
            """,
            [transaction_id],
        )

    def count_customers(self) -> int:
        return self._scalar("SELECT COUNT(*) FROM Customers")

    def count_cards(self, card_type: str | None = None) -> int:
        where, params = self._card_filters(card_type)
        return self._scalar(f"SELECT COUNT(*) FROM Cards {where}", params)

    def count_transactions(self, filters: dict[str, Any]) -> int:
        where, params = self._transaction_filters(filters, prefix="t")
        return self._scalar(f"SELECT COUNT(*) FROM Transactions t {where}", params)

    def count_users_with_transactions(self, filters: dict[str, Any]) -> int:
        where, params = self._transaction_filters(filters, prefix="t")
        return self._scalar(
            f"""
            SELECT COUNT(DISTINCT c.customer_id)
            FROM Customers c
            JOIN Cards ca ON ca.customer_id = c.customer_id
            JOIN Transactions t ON t.card_id = ca.card_id
            {where}
            """,
            params,
        )

    def users_with_transactions(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        where, params = self._transaction_filters(filters, prefix="t")
        return self._fetch_all(
            f"""
            SELECT c.customer_id, c.full_name AS nombreCompleto,
                   COUNT(t.transaction_id) AS transactionsCount,
                   ROUND(COALESCE(SUM(t.operation_ammount), 0), 2) AS totalAmount
            FROM Customers c
            JOIN Cards ca ON ca.customer_id = c.customer_id
            JOIN Transactions t ON t.card_id = ca.card_id
            {where}
            GROUP BY c.customer_id, c.full_name
            ORDER BY transactionsCount DESC, c.customer_id
            """,
            params,
        )

    def transaction_amount(self, aggregate: str, filters: dict[str, Any]) -> float:
        where, params = self._transaction_filters(filters, prefix="t")
        return self._scalar_float(f"SELECT COALESCE({aggregate}(t.operation_ammount), 0) FROM Transactions t {where}", params)

    def transaction_extreme(self, direction: str, operation_type: str | None = None) -> dict[str, Any] | None:
        filters = {"operationType": operation_type}
        where, params = self._transaction_filters(filters, prefix="t")
        return self._fetch_one(
            f"""
            {self._transaction_detail_select()}
            {where}
            ORDER BY t.operation_ammount {direction}, t.transaction_id
            LIMIT 1
            """,
            params,
        )

    def transactions_by_date(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        where, params = self._transaction_filters(filters, prefix="t")
        return self._fetch_all(
            f"""
            SELECT t.operation_date AS date, COUNT(*) AS transactionsCount,
                   ROUND(COALESCE(SUM(t.operation_ammount), 0), 2) AS totalAmount
            FROM Transactions t
            {where}
            GROUP BY t.operation_date
            ORDER BY t.operation_date
            """,
            params,
        )

    def transactions_by_operation_type(self) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT operation_type AS operationType, COUNT(*) AS transactionsCount,
                   ROUND(COALESCE(SUM(operation_ammount), 0), 2) AS totalAmount
            FROM Transactions
            GROUP BY operation_type
            ORDER BY operation_type
            """
        )

    def cards_by_type(self) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT card_type AS cardType, COUNT(*) AS cardsCount,
                   ROUND(COALESCE(SUM(operation_ammount_actual), 0), 2) AS totalBalance
            FROM Cards
            GROUP BY card_type
            ORDER BY card_type
            """
        )

    def cards_balance(self, aggregate: str, card_type: str | None = None) -> float:
        where, params = self._card_filters(card_type)
        return self._scalar_float(f"SELECT COALESCE({aggregate}(operation_ammount_actual), 0) FROM Cards {where}", params)

    def user_summary(self, user_id: int) -> dict[str, Any] | None:
        customer = self.get_customer(user_id)
        if not customer:
            return None
        total_charges = self.user_transaction_amount(user_id, "output", {})
        total_payments = self.user_transaction_amount(user_id, "input", {})
        totals = self._fetch_one(
            """
            SELECT
                (SELECT COUNT(*) FROM Cards WHERE customer_id = ?) AS totalCards,
                (SELECT COUNT(*)
                 FROM Transactions t
                 JOIN Cards ca ON ca.card_id = t.card_id
                 WHERE ca.customer_id = ?) AS totalTransactions,
                (SELECT ROUND(COALESCE(SUM(operation_ammount_actual), 0), 2)
                 FROM Cards
                 WHERE customer_id = ?) AS totalCurrentBalance
            """,
            [user_id, user_id, user_id],
        ) or {}
        return {
            "customer_id": customer["customer_id"],
            "nombreCompleto": customer["nombreCompleto"],
            "totalCards": totals.get("totalCards", 0),
            "totalTransactions": totals.get("totalTransactions", 0),
            "totalCharges": total_charges,
            "totalPayments": total_payments,
            "netMovement": round(total_payments - total_charges, 2),
            "totalCurrentBalance": totals.get("totalCurrentBalance", 0),
        }

    def user_transaction_amount(self, user_id: int, operation_type: str, filters: dict[str, Any]) -> float:
        scoped_filters = dict(filters)
        scoped_filters["operationType"] = operation_type
        where, params = self._transaction_filters(scoped_filters, prefix="t")
        params.insert(0, user_id)
        return self._scalar_float(
            f"""
            SELECT COALESCE(SUM(t.operation_ammount), 0)
            FROM Cards ca
            JOIN Transactions t ON t.card_id = ca.card_id
            WHERE ca.customer_id = ?
            {where.replace("WHERE", "AND", 1)}
            """,
            params,
        )

    def ranking_users(self, operation_type: str, filters: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        scoped_filters = dict(filters)
        scoped_filters["operationType"] = operation_type
        where, params = self._transaction_filters(scoped_filters, prefix="t")
        params.append(limit)
        rows = self._fetch_all(
            f"""
            SELECT c.customer_id, c.full_name AS nombreCompleto,
                   ROUND(COALESCE(SUM(t.operation_ammount), 0), 2) AS amount
            FROM Customers c
            JOIN Cards ca ON ca.customer_id = c.customer_id
            JOIN Transactions t ON t.card_id = ca.card_id
            {where}
            GROUP BY c.customer_id, c.full_name
            ORDER BY amount DESC, c.customer_id
            LIMIT ?
            """,
            params,
        )
        return self._with_position(rows)

    def ranking_cards_by_balance(self, card_type: str | None, limit: int) -> list[dict[str, Any]]:
        where, params = self._card_filters(card_type, prefix="ca")
        params.append(limit)
        rows = self._fetch_all(
            f"""
            SELECT ca.card_id, ca.customer_id, c.full_name AS nombreCompleto,
                   ca.card_type AS tipoTarjeta, ROUND(ca.operation_ammount_actual, 2) AS operation_ammountActual
            FROM Cards ca
            JOIN Customers c ON c.customer_id = ca.customer_id
            {where}
            ORDER BY ca.operation_ammount_actual DESC, ca.card_id
            LIMIT ?
            """,
            params,
        )
        return self._with_position(rows)

    def _transaction_detail_select(self) -> str:
        return f"""
        SELECT t.transaction_id, c.customer_id, c.full_name AS nombreCompleto,
               ca.card_id, {self._masked_card_sql("ca")} AS numeroTarjetaMasked,
               ca.card_type AS tipoTarjeta, t.operation_date AS fechaTransaccion,
               t.operation_type AS tipoOperacion, ROUND(t.operation_ammount, 2) AS operation_ammount, t.operation_desc
        FROM Transactions t
        JOIN Cards ca ON ca.card_id = t.card_id
        JOIN Customers c ON c.customer_id = ca.customer_id
        """

    def _transaction_filters(
        self,
        filters: dict[str, Any],
        prefix: str = "t",
        include_amount: bool = False,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        date = filters.get("date")
        date_from = filters.get("from")
        date_to = filters.get("to")
        operation_type = filters.get("operationType")
        if date:
            clauses.append(f"{prefix}.operation_date = ?")
            params.append(date)
        if date_from:
            clauses.append(f"{prefix}.operation_date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append(f"{prefix}.operation_date <= ?")
            params.append(date_to)
        if operation_type:
            clauses.append(f"{prefix}.operation_type = ?")
            params.append(operation_type)
        if include_amount and filters.get("minAmount") is not None:
            clauses.append(f"{prefix}.operation_ammount >= ?")
            params.append(filters["minAmount"])
        if include_amount and filters.get("maxAmount") is not None:
            clauses.append(f"{prefix}.operation_ammount <= ?")
            params.append(filters["maxAmount"])
        if not clauses:
            return "", params
        return "WHERE " + " AND ".join(clauses), params

    def _card_filters(
        self,
        card_type: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        prefix: str | None = None,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        column_prefix = f"{prefix}." if prefix else ""
        if card_type:
            clauses.append(f"{column_prefix}card_type = ?")
            params.append(card_type)
        if min_amount is not None:
            clauses.append(f"{column_prefix}operation_ammount_actual >= ?")
            params.append(min_amount)
        if max_amount is not None:
            clauses.append(f"{column_prefix}operation_ammount_actual <= ?")
            params.append(max_amount)
        if not clauses:
            return "", params
        return "WHERE " + " AND ".join(clauses), params

    def _fetch_all(self, query: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        with connect(self.database_path) as connection:
            return [dict(row) for row in connection.execute(query, params or []).fetchall()]

    def _fetch_one(self, query: str, params: list[Any] | None = None) -> dict[str, Any] | None:
        with connect(self.database_path) as connection:
            row = connection.execute(query, params or []).fetchone()
            return dict(row) if row else None

    def _scalar(self, query: str, params: list[Any] | None = None) -> int:
        with connect(self.database_path) as connection:
            return int(connection.execute(query, params or []).fetchone()[0])

    def _scalar_float(self, query: str, params: list[Any] | None = None) -> float:
        with connect(self.database_path) as connection:
            return round(float(connection.execute(query, params or []).fetchone()[0] or 0), 2)

    def _with_position(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"position": index, **row} for index, row in enumerate(rows, start=1)]

    def _masked_card_sql(self, alias: str | None = None) -> str:
        column = f"{alias}.card_number" if alias else "card_number"
        return f"'****-****-****-' || substr({column}, -4)"
