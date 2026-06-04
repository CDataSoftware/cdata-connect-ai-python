# ConnectAI Mock API Server

A FastAPI-based mock server that simulates the [CData Connect AI](https://www.cdata.com/connect/) Query APIs. Used for local development and running the connector's test suite without a live endpoint.

## Quick Start

```bash
cd connect-ai-mock
pip install -r requirements.txt
python run.py
```

Server runs at `http://localhost:8080`.

## Configuration

| Environment Variable | Description | Default |
|----------------------|-------------|---------|
| `MOCK_PORT` | Server port | `8080` |
| `MOCK_DATA_DIR` | Custom data directory | `src/data/static` |
| `MOCK_GLOBAL_DELAY_MS` | Global response delay (ms) | `0` |

## Test Scenarios

Use `test@example.com` as the username and the PAT token below to trigger different behaviors.

### Basic

| PAT Token | Description |
|-----------|-------------|
| `any_token` | Default — standard mock data (3 catalogs) |
| `empty_pat` | Empty result sets |

### Error Scenarios

| PAT Token | Description |
|-----------|-------------|
| `error_pat` | 401 Invalid credentials |
| `notfound_pat` | 404 Resource not found |
| `server_error_pat` | 500 Internal server error |

### Delay Scenarios

| PAT Token | Description |
|-----------|-------------|
| `slow_pat` | 2 second delay |
| `very_slow_pat` | 5 second delay |

### Data Scenarios

| PAT Token | Description |
|-----------|-------------|
| `large_pat` | 150 contacts, 100 accounts, 200 orders |
| `datatypes_pat` | Various SQL types (numeric, date/time, text, binary, JSON, XML) |

### Streaming (Template-based)

| PAT Token | Description |
|-----------|-------------|
| `template_pat` | 100 rows, pause [100ms, 500ms, 100ms] every 25 rows |
| `template_slow_pat` | 50 rows, pause [1s, 2s, 1s] every 10 rows |
| `template_large_pat` | 1,000 rows |
| `million_pat` | 1,000,000 rows, 20ms pause every 1,000 rows |

### Partial Error / Crash Scenarios

| PAT Token | Description |
|-----------|-------------|
| `partial_error_pat` | 50 rows then connection timeout error |
| `partial_500_pat` | 100 rows then server error |
| `all_features_pat` | 100 rows + pauses [200ms, 500ms] + gateway timeout |
| `truncate_pat` | Malformed JSON after 10 rows (simulates server crash) |
| `crash_pat` | Truncates mid-stream after 50 rows |

## API Endpoints

### SQL API
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/query` | Execute a SQL query |
| `POST` | `/api/batch` | Execute a batch operation |
| `POST` | `/api/exec` | Execute a stored procedure |

### Metadata API
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/catalogs` | List catalogs |
| `GET` | `/api/schemas` | List schemas |
| `GET` | `/api/tables` | List tables |
| `GET` | `/api/columns` | List columns |
| `GET` | `/api/primaryKeys` | List primary keys |
| `GET` | `/api/procedures` | List stored procedures |
| `GET` | `/api/procedureParameters` | List procedure parameters |
| `GET` | `/api/exportedKeys` | List exported keys |
| `GET` | `/api/importedKeys` | List imported keys |

### Utility
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Server info |
| `GET` | `/health` | Health check |

## Usage Examples

```bash
# Health check
curl http://localhost:8080/health

# List catalogs (default scenario)
curl -u "test@example.com:any_token" http://localhost:8080/api/catalogs

# Execute a query
curl -u "test@example.com:any_token" \
  -X POST http://localhost:8080/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM Salesforce1.Salesforce.Contact"}'

# Trigger auth error
curl -u "test@example.com:error_pat" http://localhost:8080/api/catalogs

# Streaming with pauses
curl -N -u "test@example.com:template_pat" \
  -X POST http://localhost:8080/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM TestDB.dbo.Users"}'
```

## Template Variables

Template-based scenarios support these placeholders in row data:

| Placeholder | Description |
|-------------|-------------|
| `{{index}}` | Row number (1-based) |
| `{{random_int:min:max}}` | Random integer in range |
| `{{random_float:min:max}}` | Random float (2 decimal places) |
| `{{random_bool}}` | `true` or `false` |
| `{{random_datetime:YYYY-MM-DD:YYYY-MM-DD}}` | Random datetime in range |
| `{{uuid}}` | Random UUID v4 |
| `{{variable_name}}` | Random value from a named variable list |

## Custom Scenarios

Add scenarios to `src/data/static/scenarios.json`:

```json
{
  "credentials": {
    "test@example.com:my_token": "my_scenario"
  },
  "scenarios": {
    "my_scenario": {
      "description": "My custom scenario",
      "delayMs": 500,
      "rowCount": 50,
      "pauseAfterRows": 10,
      "pausePattern": ["100ms", "500ms"]
    }
  }
}
```

### Scenario Options

| Option | Type | Description |
|--------|------|-------------|
| `delayMs` | int | Delay before first response (ms) |
| `error` | object | Return an error `{"code": 401, "message": "..."}` |
| `emptyResults` | bool | Return empty result sets |
| `dataDir` | string | Custom data directory for this scenario |
| `rowCount` | int | Rows to generate (enables template mode) |
| `pauseAfterRows` | int | Insert a pause every N rows |
| `pausePattern` | array | Pause durations `["100ms", "500ms", "1s"]` |
| `partialError` | object | Append error after rows `{"code": 500, "message": "..."}` |
| `truncateAfterRows` | int | Cut the response after N rows (crash simulation) |

## Project Structure

```
connect-ai-mock/
├── run.py                        # Server entry point
├── requirements.txt
├── test_scenarios.sh             # Shell script for quick scenario testing
└── src/
    ├── main.py                   # FastAPI app, middleware, lifespan
    ├── middleware/
    │   └── auth.py               # Basic Auth extraction
    ├── models/
    │   └── schemas.py            # Pydantic request/response models
    ├── routes/
    │   ├── sql.py                # /api/query, /api/batch, /api/exec
    │   └── metadata.py           # /api/catalogs, /api/tables, etc.
    └── data/
        ├── mock_store.py         # Data loading, scenario routing, DML state
        └── static/
            ├── scenarios.json
            ├── catalogs.json
            ├── schemas.json
            ├── tables.json
            ├── columns.json
            ├── tables/           # Per-table row data
            └── scenarios/        # Scenario-specific data dirs
```

## Requirements

- Python >= 3.10
- `fastapi >= 0.109.0`
- `uvicorn[standard] >= 0.27.0`
- `pydantic >= 2.5.0`
