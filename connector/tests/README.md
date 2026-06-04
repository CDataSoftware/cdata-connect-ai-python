# Test Suite

## Organization

```
tests/
├── conftest.py                        # Root: shared config helpers, marker registration
├── unit/                              # Pure unit tests — no server, no network
│   ├── conftest.py                    # Mock connection & cursor fixtures
│   ├── test_module.py                 # Module-level attributes & connect() factory
│   ├── test_connection.py             # Connection lifecycle & config
│   ├── test_cursor.py                 # Cursor properties, param validation, fetch errors
│   ├── test_exceptions.py            # Exception hierarchy compliance
│   └── test_types.py                  # Type conversion, Date/Time/Timestamp/Binary
├── integration/                       # Requires mock server (or live endpoint)
│   ├── conftest.py                    # Mock server lifecycle, connection & cursor fixtures
│   ├── test_dbapi20_compliance.py     # 33 DB-API 2.0 compliance tests (Stuart Bishop suite)
│   ├── test_query_operations.py       # SELECT, INSERT, DELETE end-to-end
│   ├── test_error_scenarios.py        # Auth errors, server errors, connection refused
│   ├── test_streaming.py             # Large datasets, streaming, data type scenarios
│   └── test_stored_procedures.py     # callproc end-to-end
└── integration_live/                  # Requires live CData Connect AI cloud environment
    ├── conftest.py                    # Skip guard (RUN_LIVE_TESTS), credentials, fixtures
    ├── helpers.py                     # Shared constants, data helpers, cleanup
    ├── test_select.py                 # SELECT — fetch, description, filter, order, count
    ├── test_insert.py                 # INSERT — single row, batch, default values
    ├── test_update.py                 # UPDATE — single field, multi-field, boolean
    ├── test_delete.py                 # DELETE — single row, conditional, multi-row
    └── test_stored_procedures.py      # All 8 stored procedures end-to-end
```

## Running Tests

### Unit tests only (fast, no server)

```bash
pytest tests/unit/ -v
```

### Integration tests only (mock server auto-starts)

```bash
pytest tests/integration/ -v
```

### Live environment tests (requires CData Connect AI cloud access)

```bash
RUN_LIVE_TESTS=1 \
CDATA_BASE_URL=https://cloud.cdata.com/api \
CDATA_USERNAME=<username> \
CDATA_PASSWORD=<pat> \
pytest tests/integration_live/ -v
```

Skipped by default. Set `RUN_LIVE_TESTS=1` plus the three `CDATA_*` variables to enable.
In CI/CD pipelines, supply these as secrets/environment variables — no credentials are stored in the repo.

### Everything (unit + mock integration; live tests skipped unless RUN_LIVE_TESTS=1)

```bash
pytest tests/ -v
```

## Adding New Tests

- **Unit tests** go in `tests/unit/`. Use the `mock_connection` and `mock_cursor` fixtures from `tests/unit/conftest.py`. Never make real HTTP calls.
- **Integration tests** go in `tests/integration/`. Use the `con` and `cursor` fixtures from `tests/integration/conftest.py`. The mock server starts automatically.
- **Live integration tests** go in `tests/integration_live/`. Use the `cur` fixture from `tests/integration_live/conftest.py`. Import helpers from `tests/integration_live/helpers.py`. Always clean up test data in a `finally` block.

## Mock Scenarios

The mock server supports test scenarios based on PAT (password) credentials.
All scenarios use `test@example.com` as the username.

| PAT (password) | Scenario | Behavior |
|----------------|----------|----------|
| `any_token` | default | Standard mock data |
| `happy_pat` | happy_path | Same as default |
| `error_pat` | error_auth | Returns 401 error in response body |
| `notfound_pat` | error_not_found | Returns 404 error in response body |
| `server_error_pat` | error_server | Returns 500 error in response body |
| `empty_pat` | empty_data | Returns empty result sets |
| `large_pat` | large_dataset | Large datasets (100-200 rows) |
| `datatypes_pat` | datatypes | Various SQL data types |
| `template_pat` | template_stream | Template-based streaming (100 rows) |
| `slow_pat` | slow_response | 2-second delay |
| `partial_error_pat` | template_partial_error | 50 rows then connection timeout |

See `connect-ai-mock/src/data/static/scenarios.json` for the full list.

## Environment Variables

### Mock / general

| Variable | Description | Default |
|----------|-------------|---------|
| `CDATA_BASE_URL` | API endpoint | `http://localhost:8080/api` |
| `CDATA_USERNAME` | Auth username | `test@example.com` |
| `CDATA_PASSWORD` | Auth password / PAT | `any_token` |
| `MOCK_PORT` | Mock server port | `8080` |
| `MOCK_SERVER_DIR` | Path to mock server | `../connect-ai-mock` |
| `SKIP_LIVE_TESTS` | Skip live API tests | `1` |

### Live environment (`tests/integration_live/`)

| Variable | Description | Required |
|----------|-------------|---------|
| `RUN_LIVE_TESTS` | Set to `1` to enable live tests | Yes |
| `CDATA_BASE_URL` | Connect AI base URL | Yes |
| `CDATA_USERNAME` | Account username | Yes |
| `CDATA_PASSWORD` | Account password / PAT | Yes |
