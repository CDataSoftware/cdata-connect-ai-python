# Mock Server — AI Context

FastAPI-based mock server simulating CData Connect AI Query APIs. Used for local development and testing.

## Layout

```
connect-ai-mock/
├── run.py                          # Entry point (uvicorn)
├── src/
│   ├── main.py                     # FastAPI app, /health endpoint
│   ├── routes/
│   │   ├── sql.py                  # POST /api/query, /api/batch, /api/exec
│   │   └── metadata.py            # GET /api/catalogs, /api/tables, etc.
│   ├── middleware/auth.py          # Basic auth extraction
│   ├── data/
│   │   ├── mock_store.py          # Scenario routing, template generation, DML state
│   │   └── static/
│   │       ├── scenarios.json     # Scenario definitions + credential→scenario mapping
│   │       ├── tables/            # Default table data (JSON files per catalog)
│   │       └── scenarios/         # Scenario-specific data directories
│   │           ├── large/         # Large dataset scenario (100-200 rows)
│   │           ├── datatypes/     # SQL data type testing
│   │           └── template/      # Template-based row generation
│   └── models/schemas.py          # Pydantic models (QueryRequest, QueryResult, etc.)
```

## How Scenarios Work

1. Client sends Basic auth header (`username:password`)
2. `scenarios.json` `credentials` section maps `username:password` → scenario name
3. Scenario config determines behavior: error response, delay, data directory, template generation, etc.

## Key Scenarios

| PAT (password) | Scenario | Behavior |
|----------------|----------|----------|
| `any_token` | default | Standard mock data (Salesforce, PostgreSQL tables) |
| `error_pat` | error_auth | 200 response with `{"error": {"code": 401, ...}}` |
| `server_error_pat` | error_server | 200 response with `{"error": {"code": 500, ...}}` |
| `large_pat` | large_dataset | 100-200 rows per table |
| `datatypes_pat` | datatypes | Various SQL types (INT, DECIMAL, DATE, etc.) |
| `template_pat` | template_stream | Generated rows with pauses (streaming test) |
| `partial_error_pat` | template_partial_error | 50 rows then error |

**Important**: Error scenarios return HTTP 200 with error in JSON body, not HTTP error status codes.

## DML State

The mock server tracks in-memory DML state per table:
- `DELETE FROM table` → clears rows
- `INSERT INTO table VALUES (...)` → appends row
- `SELECT FROM table` → returns current in-memory state

This enables the DB-API 2.0 compliance tests to do INSERT+SELECT round-trips.

## Running

```bash
pip install -r requirements.txt
python run.py                     # Starts on port 8080
MOCK_PORT=9090 python run.py      # Custom port
```
