# ConnectAI Python Client

This repository contains the Python client library for [CData Connect AI](https://www.cdata.com/connect/) and the companion mock server used for development and testing.

## Repository Structure

```
connect-ai-python/
├── connector/          # Python DB-API 2.0 connector (the installable package)
├── connect-ai-mock/    # Mock API server for local development and testing
└── .gitignore
```

## Projects

### `connector/` — Python Connector

A Python [DB-API 2.0 (PEP 249)](https://peps.python.org/pep-0249/) compliant connector for CData Connect AI. Install it, point it at a Connect AI endpoint, and query any connected data source using standard Python database idioms.

See [`connector/README.md`](connector/README.md) for full documentation.

```bash
pip install cdata-connect-ai
```

### `connect-ai-mock/` — Mock API Server

A FastAPI-based mock server that simulates the Connect AI Query APIs. Used for:

- Running the connector's test suite locally without a live endpoint
- Developing and testing against edge cases (errors, timeouts, large datasets, streaming)

See [`connect-ai-mock/README.md`](connect-ai-mock/README.md) for full documentation.

```bash
cd connect-ai-mock
pip install -r requirements.txt
python run.py
```

## Building the Package

From the `connector/` directory:

```bash
pip install build
python -m build
```

This produces two artifacts in `connector/dist/`:

| File | Purpose |
|------|---------|
| `cdata_connect_ai-1.0.0-py3-none-any.whl` | Wheel — install with `pip install` |
| `cdata_connect_ai-1.0.0.tar.gz` | Source distribution — for PyPI upload |

Install the wheel locally:

```bash
pip install connector/dist/cdata_connect_ai-1.0.0-py3-none-any.whl
```

Publish to PyPI:

```bash
pip install twine
twine check connector/dist/*          # verify metadata
twine upload connector/dist/*         # upload (requires PyPI token)
```

See [`connector/README.md`](connector/README.md) for full build and publish details.

## Running the Demo Client

`client_demo.py` (at the repo root) exercises the connector end-to-end against the mock server — SELECT, INSERT, DELETE, stored procedures, error handling, and more.

**Step 1 — Start the mock server:**

```bash
cd connect-ai-mock
pip install -r requirements.txt
python run.py
```

**Step 2 — Run the demo** (from the repo root, in a second terminal):

```bash
pip install cdata-connect-ai          # from PyPI
# or: pip install connector/dist/cdata_connect_ai-1.0.0-py3-none-any.whl

python client_demo.py
```

## Running Tests

From the `connector/` directory:

```bash
pip install -e ".[dev]"

# Unit tests only — fast, no server needed
pytest tests/unit/ -v

# Integration tests — mock server auto-starts on localhost
pytest tests/integration/ -v

# All tests
pytest tests/ -v
```

See [`connector/tests/README.md`](connector/tests/README.md) for full test organization details.

## Requirements

- Python >= 3.10
