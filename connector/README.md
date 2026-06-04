# ConnectAI Python Connector

CData Connect AI is a managed data layer providing live, governed access to 350+ enterprise data sources — Salesforce, SAP, Snowflake, Dynamics, and more. This PEP 249-compliant Python connector enables querying and writing via standard SQL through the Connect AI REST API. No ETL, no stale exports — just real-time data directly in your pipeline. Passthrough authentication inherits existing enterprise permissions.

A Python [DB-API 2.0 (PEP 249)](https://peps.python.org/pep-0249/) compliant connector for [CData Connect AI](https://www.cdata.com/connect/). Query any data source connected through Connect AI using the standard Python database interface.

## Installation

```bash
pip install cdata-connect-ai
```

For pandas integration:

```bash
pip install "cdata-connect-ai[full]"
```

## Quick Start

```python
import cdata_connect_ai

conn = cdata_connect_ai.connect(
    username="you@example.com",
    password="<your_personal_access_token>",
)

cursor = conn.cursor()
cursor.execute("SELECT * FROM [Salesforce1].[Salesforce].[Account]")
rows = cursor.fetchall()
for row in rows:
    print(row)

conn.close()
```

## Configuration File

Use a [PyHOCON](https://github.com/chimpler/pyhocon) config file to keep credentials out of code:

```hocon
# config.conf
cdata_api_db {
  username = "you@example.com"
  password = "<your_personal_access_token>"
}
```

```python
conn = cdata_connect_ai.connect(config_path="config.conf")
```

## Parameterized Queries

```python
cursor.execute(
    "SELECT * FROM [DB].[public].[users] WHERE city = %(city)s LIMIT %(limit)s",
    {"city": "New York", "limit": 10},
)
```

## Batch Operations

```python
cursor.executemany(
    "INSERT INTO [DB].[public].[cities] (city, id) VALUES (@city, @id)",
    [
		{"@city": {"dataType": 5, "value": "New York"}, "@id": {"dataType": 8, "value": 1}},
		{"@city": {"dataType": 5, "value": "London"},   "@id": {"dataType": 8, "value": 2}},
    ],
)
```

## Stored Procedures

```python
cursor.callproc("[DB].[public].[my_procedure]", ("arg1", "arg2"))
rows = cursor.fetchall()
```

## Connection Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `base_url` | Connect AI API base URL | `https://cloud.cdata.com/api` |
| `username` | Authentication username | — |
| `password` | Personal access token | — |
| `config_path` | Path to PyHOCON config file | — |
| `workspace` | Connect AI workspace name | — |
| `timeout` | HTTP request timeout (seconds) | `90` |
| `max_retries` | Retries on transient 5xx errors | `3` |
| `retry_delay` | Base delay between retries (seconds) | `1.0` |

## DB-API 2.0 Compliance

| Attribute | Value |
|-----------|-------|
| `apilevel` | `"2.0"` |
| `threadsafety` | `1` |
| `paramstyle` | `"pyformat"` |

**Supported methods:** `connect()`, `cursor()`, `execute()`, `executemany()`, `callproc()`, `fetchone()`, `fetchmany()`, `fetchall()`, `close()`, `commit()`, `rollback()`

## Exception Hierarchy

```
cdata_connect_ai.Error
├── InterfaceError
└── DatabaseError
    ├── DataError
    ├── OperationalError
    ├── IntegrityError
    ├── InternalError
    ├── ProgrammingError
    └── NotSupportedError
```

## Requirements

- Python >= 3.10
- `requests >= 2.28.0`
- `ijson >= 3.1.0`
- `pyhocon >= 0.3.60`

## Running Tests

Tests are split into **unit** (no server) and **integration** (mock server auto-starts).

```bash
pip install -e ".[dev]"

# Unit tests only — fast, no server needed
pytest tests/unit/ -v

# Integration tests — mock server auto-starts on localhost
pytest tests/integration/ -v

# All tests
pytest tests/ -v

# Run against a live Connect AI endpoint
CDATA_BASE_URL=https://cloud.cdata.com/api \
CDATA_USERNAME=you@example.com \
CDATA_PASSWORD=<pat> \
SKIP_LIVE_TESTS=0 \
pytest tests/integration/ -v
```

See `tests/README.md` for test organization details.

### Test Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CDATA_BASE_URL` | API endpoint | `http://localhost:8080/api` |
| `CDATA_USERNAME` | Auth username | `test@example.com` |
| `CDATA_PASSWORD` | Auth password / PAT | `any_token` |
| `MOCK_PORT` | Mock server port | `8080` |
| `MOCK_SERVER_DIR` | Path to mock server | `../connect-ai-mock` |
| `SKIP_LIVE_TESTS` | Skip live API tests | `1` |

## Building from Source

Install the build tool:

```bash
pip install build
```

Build both the wheel and source distribution from the `connector/` directory:

```bash
cd connector
python -m build
```

Artifacts are written to `connector/dist/`:

```
dist/
├── cdata_connect_ai-1.0.0-py3-none-any.whl   # Wheel (preferred for install)
└── cdata_connect_ai-1.0.0.tar.gz             # Source distribution
```

Install the locally built wheel:

```bash
pip install dist/cdata_connect_ai-1.0.0-py3-none-any.whl
```

### Publishing to PyPI

```bash
pip install twine

# Verify the package metadata before uploading
twine check dist/*

# Upload to PyPI
twine upload dist/*
```

Store your PyPI credentials in `~/.pypirc` or pass them as environment variables:

```ini
# ~/.pypirc
[pypi]
username = __token__
password = pypi-<your-api-token>
```

## Demo Client

A demo script at the repo root (`client_demo.py`) exercises the connector end-to-end against the mock server. It covers:

- `SELECT` with `fetchall`, `fetchone`, and `fetchmany`
- `cursor.description` (column metadata)
- Parameterized queries (`pyformat`)
- Batch `INSERT` via `executemany` and `SELECT` to verify
- `DELETE` and confirm empty result
- Stored procedure via `callproc`
- Error handling (`OperationalError` on bad host)

**Step 1 — Start the mock server** (in one terminal):

```bash
cd connect-ai-mock
pip install -r requirements.txt
python run.py
# Server ready at http://localhost:8080
```

**Step 2 — Install the connector and run the demo** (in another terminal):

```bash
# Install from PyPI
pip install cdata-connect-ai

# OR install the locally built wheel
pip install connector/dist/cdata_connect_ai-1.0.0-py3-none-any.whl

# Run
python client_demo.py
```

Expected output covers all 9 demo sections and ends with `All done.`

## License

MIT — see [LICENSE](LICENSE)
