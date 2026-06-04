# ConnectAI Python Client — AI Context

## What This Is

A monorepo containing a Python DB-API 2.0 (PEP 249) connector for CData Connect AI and a companion mock server for testing. The connector is the installable package (`cdata-connect-ai`); the mock server is for development only.

## Repository Layout

```
connect-ai-python/
├── connector/                  # The installable Python package
│   ├── cdata_connect_ai/          # Source code
│   │   ├── __init__.py         # Module exports, connect() factory, PEP 249 attributes
│   │   ├── connection.py       # Connection class (auth, config, lifecycle)
│   │   ├── cursor.py           # Cursor class (execute, fetch, streaming via ijson)
│   │   ├── exceptions.py       # DB-API 2.0 exception hierarchy + ConfigurationError
│   │   ├── util/types.py       # Type mapping (Connect API ↔ Python) & Date/Time/Binary
│   │   ├── log.py              # Logger setup (NullHandler)
│   │   └── version.py          # __version__ = "1.0.0"
│   ├── tests/                  # Test suite (unit + integration)
│   │   ├── conftest.py         # Shared config helpers, marker registration
│   │   ├── unit/               # 140 tests, no server, ~0.1s
│   │   └── integration/        # 49 tests, needs mock server, ~1s
│   └── pyproject.toml          # Build config, deps, pytest settings
├── connect-ai-mock/            # FastAPI mock server
│   ├── run.py                  # Entry point
│   ├── src/routes/sql.py       # /api/query, /api/batch, /api/exec
│   ├── src/routes/metadata.py  # /api/catalogs, /api/tables, etc.
│   └── src/data/static/        # Scenario configs and test data
└── client_demo.py              # End-to-end demo script
```

## Key Technical Details

- **DB-API 2.0**: `apilevel="2.0"`, `threadsafety=1`, `paramstyle="pyformat"`
- **HTTP client**: Uses `requests` for HTTP, `ijson` for streaming JSON parsing
- **Auth**: Basic auth (username:password), also supports PyHOCON config files
- **API endpoints**: POST `/api/query` (SELECT), `/api/batch` (INSERT/UPDATE/DELETE), `/api/exec` (stored procs)
- **Retry**: Exponential backoff on 5xx errors, configurable `max_retries`/`retry_delay`
- **Thread-safe**: Uses `threading.local()` for connection state, `threading.Lock()` in cursor
- **Python**: >= 3.10

## Working with Tests

All commands run from `connector/` directory:

```bash
# Install
pip install -e ".[dev]"

# Unit tests (no server)
pytest tests/unit/ -v

# Integration tests (mock server auto-starts)
pytest tests/integration/ -v

# All tests
pytest tests/ -v
```

### Test structure
- **Unit tests** (`tests/unit/`): Use `mock_connection`/`mock_cursor` fixtures. No HTTP. Test class contracts, validation, types, exceptions.
- **Integration tests** (`tests/integration/`): Use `con`/`cursor` fixtures. Mock server auto-starts on localhost:8080.
- **Mock scenarios**: Controlled by PAT (password). `any_token` = default, `error_pat` = 401, `server_error_pat` = 500, `large_pat` = 100+ rows, `datatypes_pat` = SQL type variety. Full list in `connect-ai-mock/src/data/static/scenarios.json`.

## Code Conventions

- Type hints on public APIs
- Exceptions follow PEP 249 hierarchy exactly (see `exceptions.py`)
- The mock server returns errors as 200 with `{"error": {...}}` in JSON body (not HTTP status codes), except for real connection failures
- `cursor._execute_request()` handles retry logic — don't duplicate it
- Streaming: rows come through an `ijson` generator, not loaded into memory

## Common Tasks

**Adding a new unit test**: Add to the appropriate file in `tests/unit/`. Use `mock_cursor` or `mock_connection` fixture. No network calls.

**Adding a new integration test**: Add to `tests/integration/`. Use `con`/`cursor` fixtures. For scenario-specific tests, create a fixture that connects with the right PAT.

**Adding a new mock scenario**: Add to `connect-ai-mock/src/data/static/scenarios.json` with a credential mapping, and optionally create a data directory under `scenarios/`.

**Modifying the connector**: Source is in `connector/cdata_connect_ai/`. The `__init__.py` re-exports everything. Connection creates Cursors. Cursor does HTTP and streaming.
