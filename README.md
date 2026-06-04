# Demo Analytics API

AI-powered API for querying financial data through natural language interfaces.

## Overview

This project implements a RESTful analytics API with integrated natural language processing capabilities. Users can query financial datasets using conversational prompts; the system interprets intent through Gemini API, executes appropriate analytics queries, and returns structured responses with natural language explanations.

**Design Pattern:** Hexagonal architecture with clear separation between domain, application, and infrastructure layers.

**Stack:** Python 3.10+, SQLite3, Gemini API, stdlib HTTP server.

## Features

- **RESTful Analytics API** – Endpoints for Customers, Cards, Transactions with pagination, filtering, and aggregation support
- **Natural Language Query Interface** – Process questions in Spanish/English via `/api/ai/ask` and `/api/ai/query` endpoints
- **Query Constraint Model** – AI restricted to 21 predefined metrics; no arbitrary SQL execution
- **Automatic Schema Management** – SQLite3 database with schema validation and auto-recovery on mismatch
- **OpenAPI 3.0.3 Specification** – Full contract documentation in `app/ api-contract.yml`

## Quick Start

### Prerequisites

- Python 3.10 or higher
- 50 MB disk space for database and CSV data
- Gemini API key (optional; required for `/api/ai/*` endpoints)

### Installation

```bash
cd /path/to/duoc-workshop-app

# Create isolated Python environment
python -m venv .duoc-api-llm-demo.venv
source .duoc-api-llm-demo.venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install optional dependencies
pip install -r requirements.txt

# Configure API key (optional)
export LLM_API_KEY="your-gemini-api-key"

# Start server
python run.py
```

The server binds to `http://localhost:8080/api` by default.

### Health Check

```bash
curl http://localhost:8080/api/health
```

Response:
```json
{"status": "ok"}
```

## API Endpoints

### Customers Resource

```bash
# List customers with pagination
curl "http://localhost:8080/api/customers?limit=10&offset=0"

# Retrieve single customer
curl http://localhost:8080/api/customers/1

# Search customers by name
curl "http://localhost:8080/api/customers/search?q=Carlos"

# List cards for customer
curl http://localhost:8080/api/customers/1/cards

# List transactions for customer in date range
curl "http://localhost:8080/api/customers/1/transactions?from=2026-05-01&to=2026-05-31"
```

### Analytics Resource

```bash
# Aggregated financial summary
curl http://localhost:8080/api/analytics/summary

# Count metrics
curl http://localhost:8080/api/analytics/users/count
curl http://localhost:8080/api/analytics/cards/count
curl http://localhost:8080/api/analytics/transactions/count

# Ranking queries
curl "http://localhost:8080/api/analytics/ranking/users-by-spending?limit=5"
curl "http://localhost:8080/api/analytics/ranking/users-by-payments?limit=5"
curl "http://localhost:8080/api/analytics/ranking/cards-by-balance?limit=5"
```

### Natural Language Query Endpoints

Process arbitrary questions through AI planning and metric execution.

**Endpoint:** `POST /api/ai/ask` or `POST /api/ai/query` (both accepted)

**Request:**
```bash
curl -X POST http://localhost:8080/api/ai/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuántas transacciones se hicieron el 26 de mayo?"
  }'
```

**Response Structure:**
```json
{
  "question": "¿Cuántas transacciones se hicieron el 26 de mayo?",
  "metric": "transactions_count",
  "filters": {
    "date": "2026-05-26"
  },
  "result": {
    "count": 5
  },
  "answer": "Se registraron 5 transacciones el 26 de mayo."
}
```

**Processing Flow:**
1. AI service receives natural language question
2. Gemini API analyzes intent and generates JSON plan: `{metric, filters}`
3. System validates metric against whitelist of 21 allowed metrics
4. Query executes against SQLite database
5. Gemini API generates natural language response based on result
6. Response returned with all execution steps for transparency

**Allowed Metrics** (subset): `general_summary`, `users_count`, `transactions_count`, `cards_count`, `users_with_transactions_count`, `ranking_users_by_spending`, `ranking_cards_by_balance`, etc.

### Direct Metric Query

For programmatic clients, invoke metrics directly without AI planning:

```bash
curl -X POST http://localhost:8080/api/analytics/query \
  -H "Content-Type: application/json" \
  -d '{
    "metric": "transactions_count",
    "filters": {"date": "2026-05-26"}
  }'
```

## Configuration

Environment variables configure application behavior. Set before executing `python run.py`:

```bash
# Server Network Configuration
export HOST="0.0.0.0"                           # Binding address (default: 0.0.0.0)
export PORT="8080"                              # HTTP port (default: 8080)

# Database Configuration
export DATABASE_PATH="database/database-demo.sqlite"
export CSV_DATA_PATH="database/data/raw"        # CSV source directory

# Gemini API Configuration (required for /api/ai/* endpoints)
export LLM_API_KEY="AIzaSy..."                  # Google Gemini API key
export LLM_MODEL="gemini-flash-latest"          # Model identifier (default: gemini-flash-latest)
```

### Obtaining Gemini API Key

1. Navigate to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Create API key" or select existing project
3. Copy the generated API key
4. Export to environment:
   ```bash
   export LLM_API_KEY="AIzaSy..."
   ```
5. Restart application to apply configuration

See [Gemini API Documentation](https://ai.google.dev/gemini-api/docs/quickstart) for quota limits and billing information.

## Project Structure

```
duoc-workshop-app/
├── app/
│   └── src/main/py/
│       ├── api/
│       │   └── routes.py                   # HTTP request dispatcher
│       ├── application/
│       │   ├── ai_service.py               # Gemini API orchestration and metric planning
│       │   └── services.py                 # Business logic and analytics query execution
│       ├── domain/
│       │   └── repositories.py             # Repository interface contracts (hexagonal)
│       ├── infrastructure/
│       │   ├── database.py                 # SQLite3 initialization and schema management
│       │   ├── llm_client.py               # Gemini HTTP client wrapper
│       │   └── sqlite_repository.py        # SQL execution and data access layer
│       ├── config.py                       # YAML configuration parser
│       ├── main.py                         # HTTP server setup and initialization
│       ├── __init__.py
│       ├── logging_config.py               # Structured logging configuration
│       └── logging_config.py
├── database/
│   ├── data/raw/
│   │   ├── customers.csv                   # Customer records (customer_id, name, email, phone)
│   │   ├── cards.csv                       # Card records (card_id, customer_id, card_type, balance)
│   │   └── transactions.csv                # Transaction records (transaction_id, card_id, amount, date)
│   └── database-demo.sqlite                # SQLite3 database (auto-created on first run)
├── logs/
│   └── banking_api.log                     # Application log file
├── app/ api-contract.yml                   # OpenAPI 3.0.3 specification
├── requirements.txt                        # Optional dependencies
├── Dockerfile                              # Container image definition
├── run.py                                  # Entry point
└── README.md
```

## Database

### Initialization Process

On first startup, the application:

1. **Creates database file** – `database/database-demo.sqlite` in SQLite 3.x format
2. **Defines schema** – Executes DDL for `Customers`, `Cards`, `Transactions` tables
3. **Imports data** – Loads CSV files from `database/data/raw/` using Python csv module
4. **Validates schema** – Subsequent startups compare current schema to expected structure
5. **Auto-recovery** – If mismatch detected, drops and recreates affected tables

### Schema Definition

```sql
CREATE TABLE Customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT
);

CREATE TABLE Cards (
    card_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    card_type TEXT,
    balance REAL DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
);

CREATE TABLE Transactions (
    transaction_id TEXT PRIMARY KEY,
    card_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    date TEXT,
    description TEXT,
    FOREIGN KEY (card_id) REFERENCES Cards(card_id)
);
```

### Recovery

To reset database to initial state:
```bash
rm database/database-demo.sqlite
python run.py
```

*rm database/database-demo.sqlite*

The application will reinitialize the database from CSV files on next startup.

## API Documentation

Full OpenAPI 3.0.3 specification: [app/ api-contract.yml](app/ api-contract.yml)

Specification includes:
- Complete endpoint definitions with request/response schemas
- Example request and response payloads
- HTTP status codes and error responses
- Request parameter validation rules

For visualization, upload the YAML to [Swagger UI Editor](https://editor.swagger.io/) or use local tooling.

## Deployment

### Docker

Build container image:
```bash
docker build -t duoc-demo-api .
```

Run container locally:
```bash
docker run -p 8080:8080 \
  -e LLM_API_KEY="AIzaSy..." \
  -e LLM_MODEL="gemini-flash-latest" \
  duoc-demo-api
```

### Azure Container Apps

Create resource group and container registry:
```bash
az group create --name rg-duoc-demo --location eastus
az acr create --resource-group rg-duoc-demo --name duocRegistryName --sku Basic
```

Build and push image:
```bash
az acr build --registry duocRegistryName --image duoc-demo-api:1.0 .
```

Create container app environment:
```bash
az containerapp env create \
  --name duoc-demo-env \
  --resource-group rg-duoc-demo \
  --location eastus
```

Deploy container app with configuration:
```bash
az containerapp create \
  --name duoc-demo-api \
  --resource-group rg-duoc-demo \
  --environment duoc-demo-env \
  --image duocRegistryName.azurecr.io/duoc-demo-api:1.0 \
  --target-port 8080 \
  --ingress external \
  --secrets gemini-api-key="AIzaSy..." \
  --env-vars \
    LLM_MODEL="gemini-flash-latest" \
    PORT="8080" \
    LLM_API_KEY="secretref:gemini-api-key"
```

## Troubleshooting

### AI Endpoint Returns 503: "AI service is not configured"

**Cause:** `LLM_API_KEY` environment variable not set at startup.

**Solution:**
```bash
export LLM_API_KEY="your-api-key"
python run.py
```

Restart the application for configuration to take effect.

### Database: "sqlite3.OperationalError: no such column"

**Cause:** Schema mismatch between code and persisted database (occurs after code updates).

**Solution:**
```bash
rm database/database-demo.sqlite
python run.py
```

Application automatically recreates schema and reimports CSV data.

### Port 8080 Already in Use

**Cause:** Another process bound to port 8080.

**Solution - Option A (custom port):**
```bash
export PORT="8081"
python run.py
```

**Solution - Option B (kill conflicting process):**
```bash
lsof -i :8080
kill <PID>
```

### Slow Initial Startup (5-10 seconds)

**Expected behavior:** First startup imports 100+ customer records and 1000+ transaction records from CSV files. Subsequent startups load existing database in ~1 second.

**To monitor:** Check `logs/banking_api.log` for initialization progress.

### Gemini API Rate Limits

**Symptom:** `/api/ai/*` endpoints return 429 or timeout.

**Cause:** Exceeded Gemini API quota or rate limit.

**Resolution:**
1. Check [Google Cloud Console](https://console.cloud.google.com/) for quota usage
2. Increase quota limits in project settings
3. Consider implementing request queueing for high throughput

## Architecture

### Hexagonal Pattern

```
Domain Layer (repository interfaces)
    ↓
Application Layer (business logic)
    ↓
Infrastructure Layer (implementations)
```

### HTTP Server

- **Framework:** Python 3.10+ `http.server.ThreadingHTTPServer`
- **Request Handling:** Thread-per-request model
- **No External Dependencies:** Does not require Flask, FastAPI, or Django
- **Payload Parsing:** Manual JSON parsing via `json` module

### Data Access

- **ORM:** None; direct SQLite3 queries with parameter binding
- **SQL Injection Protection:** All queries use parameterized statements
- **Connection Pooling:** Not used; new connection per query

### Request/Response Flow

1. **HTTP Server** receives request and dispatches to request handler
2. **Router** (`routes.py`) parses path and selects appropriate service method
3. **Application Service** executes business logic and queries data layer
4. **Infrastructure (SQLite Repository)** executes parameterized SQL queries
5. **Response** serialized as JSON and returned to client

### Logging

Structured logging to `logs/banking_api.log` with configurable verbosity:
- `DEBUG` – Request/response bodies, query timing
- `INFO` – Request arrival, response status
- `ERROR` – Exceptions, database errors

## Development

### Running Tests (Future)

```bash
pytest tests/
```

### Code Structure Notes

- **No external web framework** – Uses stdlib `http.server` only
- **Stateless design** – No session storage or request correlation
- **Configuration-driven** – All settings via environment variables or YAML
- **Type hints** – Optional but recommended for IDE support
- **Logging-first** – All significant operations logged for observability

## License

Educational demonstration project. Use freely for learning and development purposes.
