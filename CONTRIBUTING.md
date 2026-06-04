# Contributing to ConnectAI Python Client

## Development Setup

```bash
# Clone the repo
git clone <repo-url>
cd connect-ai-python

# Install the connector in editable mode with dev dependencies
cd connector
pip install -e ".[dev]"
```

## Running Tests

The test suite is split into **unit** and **integration** tests.

### Unit Tests (fast, no server needed)

```bash
cd connector
pytest tests/unit/ -v
```

Unit tests use `unittest.mock` to mock HTTP calls. They run in milliseconds and verify class contracts, parameter validation, type conversion, and exception hierarchy.

### Integration Tests (requires mock server)

```bash
cd connector
pytest tests/integration/ -v
```

The mock server (`connect-ai-mock/`) auto-starts when tests target `localhost`. You can also start it manually:

```bash
cd connect-ai-mock
pip install -r requirements.txt
python run.py
```

### All Tests

```bash
cd connector
pytest tests/ -v
```

### Against a Live Endpoint

```bash
CDATA_BASE_URL=https://cloud.cdata.com/api \
CDATA_USERNAME=you@example.com \
CDATA_PASSWORD=<pat> \
SKIP_LIVE_TESTS=0 \
pytest tests/integration/ -v
```

## Adding New Tests

| Test type | Directory | When to use |
|-----------|-----------|-------------|
| Unit | `tests/unit/` | Testing class contracts, validation, type conversion — anything that doesn't need the server |
| Integration | `tests/integration/` | Testing end-to-end behavior against the mock (or live) server |

### Conventions

- Group related tests in classes (e.g., `TestConnectionLifecycle`)
- Use fixtures from the appropriate `conftest.py`
- Unit tests should never make network calls — mock all HTTP via `unittest.mock`
- Integration tests should use the `con` and `cursor` fixtures from `tests/integration/conftest.py`

## Code Style

- Python 3.10+
- Type hints on public APIs
- Follow existing patterns in the codebase
