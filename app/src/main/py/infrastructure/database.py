import csv
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

EXPECTED_SCHEMA = {
    "Customers": [
        ("customer_id", "INTEGER"),
        ("full_name", "TEXT"),
        ("email", "TEXT"),
        ("customer_info", "TEXT"),
    ],
    "Cards": [
        ("card_id", "INTEGER"),
        ("customer_id", "INTEGER"),
        ("card_number", "TEXT"),
        ("card_type", "TEXT"),
        ("operation_ammount_actual", "REAL"),
    ],
    "Transactions": [
        ("transaction_id", "TEXT"),
        ("card_id", "INTEGER"),
        ("operation_date", "TEXT"),
        ("operation_type", "TEXT"),
        ("operation_ammount", "REAL"),
        ("operation_desc", "TEXT"),
    ],
}

DDL = """
CREATE TABLE IF NOT EXISTS Customers (
    customer_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    customer_info TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Cards (
    card_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    card_number TEXT NOT NULL,
    card_type TEXT NOT NULL,
    operation_ammount_actual REAL NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
);

CREATE TABLE IF NOT EXISTS Transactions (
    transaction_id TEXT PRIMARY KEY,
    card_id INTEGER NOT NULL,
    operation_date TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    operation_ammount REAL NOT NULL,
    operation_desc TEXT,
    FOREIGN KEY (card_id) REFERENCES Cards(card_id)
);

CREATE INDEX IF NOT EXISTS idx_cards_user_id ON Cards(customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_card_id ON Transactions(card_id);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON Transactions(operation_date);
CREATE INDEX IF NOT EXISTS idx_transactions_operation ON Transactions(operation_type);
"""

def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection

def initialize_database(database_path: Path, csv_data_path: Path) -> None:
    logger.info("initializing database path=%s csv_data_path=%s", database_path, csv_data_path)
    with connect(database_path) as connection:
        connection.executescript(DDL)
        if not _schema_matches(connection):
            logger.warning("schema mismatch detected, recreating database tables")
            for table_name in EXPECTED_SCHEMA:
                connection.execute(f"DROP TABLE IF EXISTS {table_name}")
            connection.executescript(DDL)
        if _table_count(connection, "Customers") == 0:
            _import_csv(connection, csv_data_path / "customers.csv", "Customers")
        if _table_count(connection, "Cards") == 0:
            _import_csv(connection, csv_data_path / "cards.csv", "Cards")
        if _table_count(connection, "Transactions") == 0:
            _import_csv(connection, csv_data_path / "transactions.csv", "Transactions")
    logger.info("database initialized path=%s", database_path)

def _table_count(connection: sqlite3.Connection, table_name: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])

def _schema_matches(connection: sqlite3.Connection) -> bool:
    for table_name, expected_schema in EXPECTED_SCHEMA.items():
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        if not rows:
            return False
        actual_schema = [(row[1], row[2].upper()) for row in rows]
        if actual_schema != expected_schema:
            return False
    return True


def _import_csv(connection: sqlite3.Connection, csv_path: Path, table_name: str) -> None:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames or []
        placeholders = ", ".join("?" for _ in columns)
        column_names = ", ".join(columns)
        query = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
        rows = [[row[column] for column in columns] for row in reader]
        connection.executemany(query, rows)
        logger.info("imported csv table=%s path=%s rows=%s", table_name, csv_path, len(rows))
