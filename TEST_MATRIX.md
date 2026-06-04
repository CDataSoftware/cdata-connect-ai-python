# TEST_MATRIX.md — CData Connect AI Python Connector

> **How to keep this file current**: re-run the count commands in the
> [Maintenance Rules](#2-maintenance-rules) section whenever you add, rename,
> or delete a test file.  Update the tables below to match.

---

## 1. Summary

| Metric | Count |
|---|---|
| **Total unit tests** | **167** |
| **Total integration tests — mock server** | **73** |
| **Total integration tests — live API** | **99** |
| **Source modules** | **8** |
| **Mock scenarios** | **36** |

---

### 1a. Source Modules (`connector/cdata_connect_ai/`)

| Module | Role |
|---|---|
| `__init__.py` | Public API surface — `connect()` factory, PEP 249 module attributes, re-exports |
| `connection.py` | `Connection` class — auth, config, lifecycle, cursor factory |
| `cursor.py` | `Cursor` class — `execute`, `fetch*`, streaming via `ijson`, retry logic |
| `exceptions.py` | DB-API 2.0 exception hierarchy + `ConfigurationError` |
| `util/types.py` | Type mapping (Connect API ↔ Python), `Date`/`Time`/`Timestamp`/`Binary` wrappers |
| `log.py` | Logger setup (`NullHandler`) |
| `version.py` | `__version__` constant |
| `util/__init__.py` | Package marker |

---

### 1b. Unit Tests (`connector/tests/unit/`)

No server required.  Run with `pytest tests/unit/ -v`.

| File | Tests | Source module(s) covered |
|---|---|---|
| `test_connection.py` | 29 | `connection.py` |
| `test_cursor.py` | 32 | `cursor.py` |
| `test_exceptions.py` | 15 | `exceptions.py` |
| `test_module.py` | 13 | `__init__.py` |
| `test_types.py` | 78 | `util/types.py` |
| **Total** | **167** | |

**What these tests cover**: pure logic (type conversion, parameter formatting, placeholder substitution), state machine (connection/cursor lifecycle, `close` idempotency), guard clauses (bad argument types, missing config fields), and PEP 249 module-level attributes — none of which require a network call.

---

### 1c. Integration Tests — Mock Server (`connector/tests/integration/`)

Mock server auto-starts on `localhost:8080`.  Run with `pytest tests/integration/ -v`.

| File | Tests | Area |
|---|---|---|
| `test_dbapi20_compliance.py` | 33 | PEP 249 compliance (one assertion per spec requirement) |
| `test_timeout_and_delays.py` | 14 | Timeouts, streaming pauses, partial errors, truncated streams |
| `test_query_operations.py` | 13 | CRUD — SELECT, INSERT, DELETE, parameterised queries, column aliases |
| `test_stored_procedures.py` | 4 | `callproc()` with varying argument counts |
| `test_favicon.py` | 3 | HTTP routing (`/favicon.ico`, Apple touch icons) |
| `test_error_scenarios.py` | 3 | Error paths — bad auth, 5xx, connection refused |
| `test_streaming.py` | 3 | Large dataset streaming, SQL type variety |
| **Total** | **73** | |

**What these tests cover**: wire format (exact JSON bodies and HTTP responses), scenario-driven behaviour (auth errors, server errors, streaming with pauses, partial errors, truncated streams), fetch semantics end-to-end (`fetchone`/`fetchmany`/`fetchall` exhaustion, `cursor.description`, `rowcount` after DML), and retry logic (exponential backoff on 5xx).

**Key distinction from unit tests**: these tests require an actual HTTP round-trip to the mock server.  They do not require live CData Connect AI credentials.

---

### 1d. Integration Tests — Live API (`connector/tests/integration_live/`)

Requires live CData Connect AI credentials.  Run with `pytest tests/integration_live/ -v`.
Marked `@pytest.mark.live_api`.

| File | Tests | Area |
|---|---|---|
| `test_select.py` | 23 | SELECT — full scans, filtering, sorting, aggregation, joins, CTEs, NULLs |
| `test_auth.py` | 12 | Authentication — valid/invalid credentials, config files, workspace param, context manager |
| `test_edge_cases.py` | 12 | Edge cases — special chars, unicode, fetch boundary conditions, no-op methods |
| `test_large_dataset.py` | 9 | Large data — COUNT ≥ 1M rows, fetchmany batches, streaming traversal, aggregates |
| `test_stored_procedures.py` | 8 | Stored procedures — all 8 live procs (create, update, activate, transfer, refresh) |
| `test_derivedviews.py` | 8 | Derived views — SELECT, WHERE, ORDER BY, COUNT, LIMIT, column projection |
| `test_datatypes.py` | 7 | Data types — INT, FLOAT, BOOLEAN, TIMESTAMP variations, BINARY, NULL, type codes |
| `test_workspace.py` | 5 | Workspace — URL construction, scoped queries, context manager |
| `test_delete.py` | 4 | DELETE — targeted row, WHERE condition, multi-row, post-DELETE fetch guard |
| `test_insert.py` | 4 | INSERT — single row, multiple rows, default field values, `executemany` batch |
| `test_update.py` | 4 | UPDATE — single field, multiple fields, BOOLEAN toggle, row isolation |
| `test_concurrency.py` | 3 | Concurrency — 2 threads, 10 threads, interleaved cursor fetch on same connection |
| **Total** | **99** | |

**What these tests cover**: end-to-end correctness against a real CData Connect AI instance — SQL semantics (joins, CTEs, GROUP BY/HAVING, DISTINCT, IS NULL), DML round-trips (INSERT → SELECT verify, UPDATE → SELECT verify, DELETE → empty SELECT), live stored procedure execution, derived view queries, large dataset streaming, concurrent connection safety, and workspace URL routing.

**Key distinction from mock integration tests**: these tests exercise the real server's SQL engine and data.  They can catch regressions that the mock cannot simulate (e.g. unexpected server-side type coercions, stored procedure contract changes, query planner behaviour).

---

### 1e. Mock Scenarios (`connect-ai-mock/src/data/static/scenarios.json`)

36 scenarios are defined.  Each PAT (password) selects exactly one scenario.

| # | Scenario key | PAT | Behaviour |
|---|---|---|---|
| 1 | `default` | *(any unmapped token)* | Standard Salesforce/PostgreSQL mock data |
| 2 | `happy_path` | `happy_pat` | Success with full data |
| 3 | `error_auth` | `error_pat` | 200 + `{"error":{"code":401}}` |
| 4 | `error_not_found` | `notfound_pat` | 200 + `{"error":{"code":404}}` |
| 5 | `error_server` | `server_error_pat` | 200 + `{"error":{"code":500}}` |
| 6 | `slow_response` | `slow_pat` | 2 s delay before first byte |
| 7 | `very_slow` | `very_slow_pat` | 5 s delay before first byte |
| 8 | `empty_data` | `empty_pat` | Empty result sets |
| 9 | `large_dataset` | `large_pat` | 100–200 rows per table |
| 10 | `datatypes` | `datatypes_pat` | Variety of SQL column types |
| 11 | `template_stream` | `template_pat` | 100 rows, pauses every 25 rows |
| 12 | `template_large` | `template_large_pat` | 1 000 rows, pauses every 200 rows |
| 13 | `template_slow` | `template_slow_pat` | 50 rows, 1–2 s pauses |
| 14 | `template_million` | `million_pat` | 1 000 000 rows, 20 ms pause/page |
| 15 | `template_partial_error` | `partial_error_pat` | 50 rows then 504 error mid-stream |
| 16 | `template_partial_500` | `partial_500_pat` | 100 rows then 500 error mid-stream |
| 17 | `template_all_features` | `all_features_pat` | Rows + pauses + partial error |
| 18 | `truncated_response` | `truncate_pat` | Truncated JSON after 10 rows |
| 19 | `truncated_mid_stream` | `crash_pat` | Truncated JSON after 50 rows with pauses |
| 20 | `perf_100` | `perf_100_pat` | 100 rows, no pauses |
| 21 | `perf_1k` | `perf_1k_pat` | 1 000 rows, no pauses |
| 22 | `perf_10k` | `perf_10k_pat` | 10 000 rows, no pauses |
| 23 | `perf_50k` | `perf_50k_pat` | 50 000 rows, no pauses |
| 24 | `perf_mixed_types` | `perf_types_pat` | 1 000 rows, all column types |
| 25 | `perf_long_stream` | `perf_long_pat` | 600 rows, 1 s pause/row (~10 min) |
| 26 | `perf_jittery` | `perf_jittery_pat` | 1 000 rows, randomised jitter pauses |
| 27 | `perf_500k` | `perf_500k_pat` | 500 000 rows, no pauses |
| 28 | `perf_soak_slow_server` | `perf_soak_slow_pat` | 5 000 rows, 500 ms/row (~42 min) |
| 29 | `perf_soak_medium` | `perf_soak_medium_pat` | 10 000 rows, 100 ms every 10 rows (~17 min) |
| 30 | `perf_chunk_gap_35s` | `perf_chunk_gap_35s_pat` | 100 rows, 35 s mid-stream gap (exceeds 30 s timeout) |
| 31 | `perf_chunk_gap_25s` | `perf_chunk_gap_25s_pat` | 100 rows, 25 s mid-stream gap (under 30 s timeout) |
| 32 | `perf_soak_1h_drip` | `perf_soak_1h_drip_pat` | 3 600 rows, 1 row/s — 1 hour drip |
| 33 | `perf_soak_1h_burst` | `perf_soak_1h_burst_pat` | 36 000 rows, bursts + 10 s pauses — 1 hour burst |
| 34 | `perf_soak_1h_mixed` | `perf_soak_1h_mixed_pat` | 3 600 mixed-type rows, 1 row/s — 1 hour type-load |
| 35 | `perf_soak_1h_firehose` | `perf_soak_1h_firehose_pat` | 360 000 rows, 10 ms/row — 1 hour firehose |
| 36 | `perf_soak_1h_firehose_mixed` | `perf_soak_1h_firehose_mixed_pat` | 360 000 mixed-type rows, 10 ms/row |

---

## 2. Maintenance Rules

### Decision tree: which suite does a new test belong in?

```
New behaviour to test?
│
├─ No network call needed (pure logic, validation, state)?
│   └─► unit/
│
├─ Needs HTTP but NOT live credentials?
│   ├─ Scenario already exists in scenarios.json?  ──► integration/  (use existing PAT)
│   └─ New scenario needed?  ──────────────────────► add to scenarios.json, then integration/
│
└─ Must run against a real CData Connect AI instance?
    ├─ SQL semantics, DML round-trips, live stored procs, type coercions?  ──► integration_live/
    └─ Already covered by mock?  ────────────────────────────────────────►  skip (mock is enough)
```

### When a unit test is sufficient

Write a unit test when the behaviour is:

- **Pure logic**: type conversion, parameter formatting, placeholder substitution, exception hierarchy, module attributes, default values.
- **State machine**: connection/cursor lifecycle, `close` idempotency, `is_open` flag.
- **Guard clauses**: bad argument types (`non-dict params`, `non-list executemany`), missing config fields.
- **No I/O dependency**: exercisable with `unittest.mock.patch` or a fixture that never touches the network.

### When to add a mock integration test

Add a test in `integration/` when you need to verify:

- **Wire format**: exact JSON body sent over HTTP, or parsing of a real HTTP response.
- **Scenario behaviour**: auth errors, server errors, streaming with pauses, partial errors, truncated streams.
- **Fetch semantics end-to-end**: `fetchone`/`fetchmany`/`fetchall` exhaustion, `cursor.description`, `rowcount` after DML.
- **Retry logic**: exponential backoff on 5xx.
- **A new mock scenario**: every new `scenarios.json` entry needs ≥ 1 integration test.

### When to add a live integration test

Add a test in `integration_live/` when you need to verify:

- **Real SQL engine behaviour**: JOINs, CTEs, GROUP BY/HAVING, DISTINCT, IS NULL — semantics the mock cannot replicate.
- **DML correctness on live data**: INSERT → SELECT verify, UPDATE → SELECT verify, DELETE → empty result.
- **Live stored procedures**: actual procedure signatures, return shapes, and side effects.
- **Server-side type coercions**: unexpected type narrowing or precision loss from the real server.
- **Concurrency with real connections**: thread safety under actual TCP connections.
- **Workspace routing**: URL construction validated against a real multi-workspace environment.

> Do **not** duplicate mock integration tests in `integration_live/`.  If the mock already verifies
> the connector's side of a behaviour (e.g. retry count), a live test adds no value and is slower.

---

### Target test counts per area

Minimum targets — not ceilings.

| Area | Suite | File | Current | Target |
|---|---|---|---|---|
| PEP 249 compliance | mock | `test_dbapi20_compliance.py` | 33 | ≥ 33 (one per spec requirement) |
| Timeouts / resilience | mock | `test_timeout_and_delays.py` | 14 | ≥ 1 per timeout scenario |
| CRUD (mock) | mock | `test_query_operations.py` | 13 | ≥ 13 |
| Error paths | mock | `test_error_scenarios.py` | 3 | ≥ 1 per error scenario in `scenarios.json` |
| Streaming (mock) | mock | `test_streaming.py` | 3 | ≥ 1 per streaming scenario |
| Stored procs (mock) | mock | `test_stored_procedures.py` | 4 | ≥ 1 per `callproc` argument pattern |
| SELECT (live) | live | `test_select.py` | 23 | ≥ 1 per SQL clause type |
| Auth (live) | live | `test_auth.py` | 12 | ≥ 1 per credential/config variant |
| Edge cases (live) | live | `test_edge_cases.py` | 12 | ≥ 1 per boundary condition |
| Large datasets (live) | live | `test_large_dataset.py` | 9 | ≥ 1 per fetch method on large data |
| Stored procs (live) | live | `test_stored_procedures.py` | 8 | ≥ 1 per live stored procedure |
| Derived views (live) | live | `test_derivedviews.py` | 8 | ≥ 1 per SQL feature on views |
| Data types (live) | live | `test_datatypes.py` | 7 | ≥ 1 per Connect API type code |
| Workspace (live) | live | `test_workspace.py` | 5 | ≥ 1 per workspace routing variant |
| DML — delete (live) | live | `test_delete.py` | 4 | ≥ 1 per DELETE pattern |
| DML — insert (live) | live | `test_insert.py` | 4 | ≥ 1 per INSERT pattern |
| DML — update (live) | live | `test_update.py` | 4 | ≥ 1 per UPDATE pattern |
| Concurrency (live) | live | `test_concurrency.py` | 3 | ≥ 1 per threading pattern |
| Type conversion | unit | `test_types.py` | 78 | ≥ 1 per Connect API type code |
| Connection lifecycle | unit | `test_connection.py` | 29 | ≥ 1 per public `Connection` method |
| Cursor contract | unit | `test_cursor.py` | 32 | ≥ 1 per public `Cursor` method/property |

---

### How to keep this file up to date

Run from the repo root after any test change:

```bash
# Unit tests
for f in connector/tests/unit/test_*.py; do
  printf "%-45s %s\n" "$f" "$(grep -c '^\s*def test_' "$f")"
done

# Integration tests — mock server
for f in connector/tests/integration/test_*.py; do
  printf "%-55s %s\n" "$f" "$(grep -c '^\s*def test_' "$f")"
done

# Integration tests — live API
for f in connector/tests/integration_live/test_*.py; do
  printf "%-60s %s\n" "$f" "$(grep -c '^\s*def test_' "$f")"
done

# Mock scenario count
python -c "import json; d=json.load(open('connect-ai-mock/src/data/static/scenarios.json')); print(len(d['scenarios']), 'scenarios')"
```

**When adding a new source module**:
1. Add a row to §1a (Source Modules).
2. Add `test_<module>.py` in `connector/tests/unit/`.
3. Add integration coverage in the most relevant existing file, or create a new one.

**When adding a new mock scenario**:
1. Add a row to §1e (Mock Scenarios) with scenario key, PAT, and behaviour.
2. Add ≥ 1 integration test in `integration/` that uses the new PAT.
3. Re-run the count commands above and update §1c totals.

**When adding a new live test file**:
1. Add a row to §1d (Integration Live) with the file name, test count, and area.
2. Update the §1d total and the §1 summary table.
