# Connector — AI Context

This is the installable `cdata-connect-ai` Python package — a DB-API 2.0 (PEP 249) connector for CData Connect AI.

## Source Layout

```
cdata_connect_ai/
├── __init__.py         # Module exports, connect() factory, apilevel/threadsafety/paramstyle
├── connection.py       # Connection class — auth, config, lifecycle, cursor creation
├── cursor.py           # Cursor class — execute, fetch, streaming (ijson), retry logic
├── exceptions.py       # PEP 249 exception hierarchy + ConfigurationError
├── util/types.py       # Type mapping (Connect API ↔ Python), Date/Time/Timestamp/Binary
├── log.py              # Logger (NullHandler)
└── version.py          # __version__
```

## Architecture

1. `connect()` → creates a `Connection` (validates params or reads PyHOCON config)
2. `Connection.cursor()` → creates a `Cursor` (holds reference to Connection for auth/base_url)
3. `Cursor.execute(query)` → `_execute_request()` → HTTP POST to `/api/query` with retry
4. Response is streamed: `ijson.parse()` extracts schema, then `ijson.items()` yields rows lazily
5. `fetchone()`/`fetchall()`/`fetchmany()` consume from the row generator

## Key Patterns

- **Retry logic** lives in `Cursor._execute_request()` — exponential backoff on 5xx/ConnectionError
- **Type conversion**: `util/types.py:convert_to_python_type()` maps API type names → Python types
- **Thread safety**: Connection uses `threading.local()`, Cursor uses `threading.Lock()`
- **No-ops**: `commit()`, `rollback()`, `setinputsizes()`, `setoutputsize()` are intentional no-ops
- **Exception hierarchy**: Must match PEP 249 exactly. `ConfigurationError` extends `Error` (custom addition)

## Tests

```bash
pip install -e ".[dev]"
pytest tests/unit/ -v        # 140 tests, no server, ~0.1s
pytest tests/integration/ -v # 49 tests, mock server auto-starts, ~1s
```

- **Unit**: `tests/unit/` — fixtures `mock_connection`/`mock_cursor` (mocked HTTP). Never hit network.
- **Integration**: `tests/integration/` — fixtures `con`/`cursor` (real HTTP to mock server).
- **Mock scenarios**: PAT-based. `any_token`=default, `error_pat`=401, `large_pat`=100+ rows. See `../connect-ai-mock/src/data/static/scenarios.json`.

## Build

```bash
pip install build && python -m build
# Produces dist/cdata_connect_ai-1.0.0-py3-none-any.whl
```
