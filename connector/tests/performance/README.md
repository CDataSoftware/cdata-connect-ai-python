# Performance & Soak Test Suite

Performance and long-running soak tests for the `cdata-connect-ai` Python connector. All tests run against the mock server (auto-started).

## Quick Reference

```bash
# All quick performance tests (~5s)
pytest tests/performance/ -v --ignore=tests/performance/test_soak.py

# Throughput benchmarks only
pytest tests/performance/test_throughput.py -v

# Streaming & memory profiling
pytest tests/performance/test_streaming.py -v

# Timeout & keepalive behavior
pytest tests/performance/test_timeout_behavior.py -v

# Soak tests (long-running, 10 min to 1 hour)
pytest tests/performance/test_soak.py --run-soak -v -s

# Soak with custom progress interval (every 10 seconds)
pytest tests/performance/test_soak.py --run-soak --soak-progress=10 -v -s
```

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--run-soak` | off | Enable soak tests (skipped by default) |
| `--soak-progress=N` | `30` | Console progress report interval in seconds |
| `--skip-slow` | off | Skip slow integration tests |
| `-s` | off | Required to see soak progress output |

## Test Files

### `test_throughput.py` — Baseline Throughput (10 tests)

Measures raw rows/sec at different scales using `fetchall`.

| Test | Rows | What it measures |
|------|------|------------------|
| `test_fetchall_100_rows` | 100 | Baseline small query |
| `test_fetchall_1k_rows` | 1,000 | Medium query |
| `test_fetchall_10k_rows` | 10,000 | Large query |
| `test_fetchall_50k_rows` | 50,000 | Stress query |
| `test_fetchall_vs_fetchone_1k` | 1,000 | fetchall vs fetchone overhead |
| `test_fetchmany_100_vs_fetchone` | 1,000 | fetchmany(100) vs fetchone |
| `test_fetchmany_10_vs_fetchone` | 1,000 | fetchmany(10) vs fetchone |
| `test_fetchall_1k_rows_comparison` | 1,000 | All fetch methods side-by-side |
| `test_simple_types_1k` | 1,000 | 6-column simple types throughput |
| `test_mixed_types_1k` | 1,000 | 14-column mixed types throughput |

### `test_streaming.py` — Memory & Streaming (8 tests)

Validates that streaming (`fetchone`) uses bounded memory vs buffered (`fetchall`).

| Test | Rows | What it measures |
|------|------|------------------|
| `test_fetchall_memory_10k` | 10,000 | Peak memory for buffered fetch |
| `test_fetchone_memory_10k` | 10,000 | Peak memory for streaming fetch |
| `test_streaming_uses_less_memory` | 10,000 | Asserts streaming < buffered |
| `test_jittery_stream_fetchall` | 1,000 | Throughput under network jitter |
| `test_jittery_per_fetch_latency` | 1,000 | p50/p95/p99/max latency distribution |
| `test_slow_client_10ms` | 1,000 | Client reads at 10ms/row |
| `test_slow_client_50ms` | 1,000 | Client reads at 50ms/row |
| `test_slow_client_fetchmany_200ms` | 1,000 | fetchmany(50) with 200ms processing |

### `test_timeout_behavior.py` — Timeout & Keepalive (8 tests)

Documents how `requests` per-socket-read timeouts interact with streaming and the mock server's whitespace keepalive mechanism.

| Test | Gap | Timeout | Expected | Why |
|------|-----|---------|----------|-----|
| `test_timeout_before_first_byte` | 5s delay | 2s | Fail | Server hasn't responded in time |
| `test_no_timeout_when_within_limit` | 2s delay | 10s | Pass | Response arrives before timeout |
| `test_35s_gap_with_45s_timeout` | 35s | 45s | Pass | Keepalive at 30s resets timer |
| `test_25s_gap_with_30s_timeout` | 25s | 30s | Pass | Gap < timeout, no keepalive needed |
| `test_35s_gap_5s_client_timeout` | 35s | 5s | Fail | Timeout fires before 30s keepalive |
| `test_35s_gap_10s_client_timeout` | 35s | 10s | Fail | Timeout fires before 30s keepalive |
| `test_short_gaps_with_tight_timeout` | 100ms | 5s | Pass | Frequent data keeps socket alive |
| `test_timeout_not_retried` | 35s | 5s | Fail | Timeouts bypass retry logic |

**Key finding**: The `timeout` parameter in `requests.post(..., timeout=N, stream=True)` applies to each individual `socket.read()` call, not the total query duration. This means a 90-second timeout allows indefinitely long queries as long as *some* data (or a keepalive whitespace byte) arrives within every 90-second window.

### `test_soak.py` — Long-Running Soak Tests (10 tests)

All soak tests are **skipped by default**. Pass `--run-soak` to enable. Use `-s` to see progress output.

```bash
# All soak tests
pytest tests/performance/test_soak.py --run-soak -v -s --soak-progress=10

# Just drip tests (slow, 1 row/sec)
pytest tests/performance/test_soak.py::TestSoak1HourDrip --run-soak -v -s --soak-progress=10

# Just firehose tests (fast, 100 rows/sec)
pytest tests/performance/test_soak.py::TestSoak1HourFirehose --run-soak -v -s --soak-progress=10

# Single specific test
pytest tests/performance/test_soak.py::TestSoak1HourFirehose::test_1h_firehose_streaming --run-soak -v -s --soak-progress=10
```

| Test | Duration | Rows | Pattern |
|------|----------|------|---------|
| `test_1h_drip_streaming` | ~1 hour | 3,600 | 1 row/sec steady drip |
| `test_1h_burst_streaming` | ~1 hour | 36,000 | 100-row bursts + 10s pause |
| `test_1h_mixed_types_streaming` | ~1 hour | 3,600 | 14-col mixed types, 1 row/sec |
| `test_1h_firehose_streaming` | ~1 hour | 360,000 | 100 rows/sec (10ms/row) sustained flood |
| `test_1h_firehose_mixed_types` | ~1 hour | 360,000 | 100 rows/sec, 14-col mixed types |
| `test_slow_drip_5000_rows` | ~42 min | 5,000 | 1 row per 500ms |
| `test_steady_stream_10k_rows` | ~17 min | 10,000 | 100ms pause every 10 rows |
| `test_slow_client_100ms_1k_rows` | ~100s | 1,000 | Client sleeps 100ms/row |
| `test_500k_rows_fetchall` | varies | 500,000 | Buffered high-volume |
| `test_500k_rows_streaming_count` | varies | 500,000 | Streaming high-volume |

The tests cover two extremes of 1-hour streaming:
- **Drip tests**: minimal data, maximum idle time — validates connection stability and keepalives
- **Firehose tests**: maximum data, minimal idle time — validates sustained throughput and memory stability

#### What soak tests validate

- Connection stays alive for the full duration (no socket drops)
- Whitespace keepalives prevent mid-stream read timeouts on long pauses
- Memory stays flat when streaming row-by-row (no leaks)
- All rows arrive with correct count and type conversion
- Driver handles sustained throughput without degradation

#### Memory stability check

Soak tests with `_stream_with_monitoring()` collect `tracemalloc` samples at each progress interval. The `_check_memory_stability()` helper asserts that memory growth between the first and last sample stays under 512KB — a simple leak detector for long-running streams.

#### Console progress output

With `--soak-progress=10 -s`, output looks like:

```
  [    10s] 1h-drip:     10/3600 ( 0.3%)    1.0 rows/s  mem=45KB peak=52KB  ETA 3590s
  [    20s] 1h-drip:     20/3600 ( 0.6%)    1.0 rows/s  mem=46KB peak=52KB  ETA 3580s
  ...
  [  3600s] 1h-drip: DONE 3600/3600 rows  1.0 rows/s  peak=53KB
```

Each line shows: elapsed time, label, row count, percentage, throughput, current/peak memory, and ETA.

## Mock Server Scenarios

All performance scenarios are defined in `connect-ai-mock/src/data/static/scenarios.json`. The mock server routes requests by PAT (password) to determine which scenario to use.

### Scenario → PAT Mapping

| PAT | Scenario | Rows | Pause Pattern |
|-----|----------|------|---------------|
| `perf_100_pat` | `perf_100` | 100 | none |
| `perf_1k_pat` | `perf_1k` | 1,000 | none |
| `perf_10k_pat` | `perf_10k` | 10,000 | none |
| `perf_50k_pat` | `perf_50k` | 50,000 | none |
| `perf_500k_pat` | `perf_500k` | 500,000 | none |
| `perf_types_pat` | `perf_mixed_types` | 1,000 | none (14 columns) |
| `perf_long_pat` | `perf_long_stream` | 600 | 1s per row (~10 min) |
| `perf_jittery_pat` | `perf_jittery` | 1,000 | 50ms/200ms/1s/50ms every 50 rows |
| `perf_soak_slow_pat` | `perf_soak_slow_server` | 5,000 | 500ms per row |
| `perf_soak_medium_pat` | `perf_soak_medium` | 10,000 | 100ms every 10 rows |
| `perf_soak_1h_drip_pat` | `perf_soak_1h_drip` | 3,600 | 1s per row |
| `perf_soak_1h_burst_pat` | `perf_soak_1h_burst` | 36,000 | 10s every 100 rows |
| `perf_soak_1h_mixed_pat` | `perf_soak_1h_mixed` | 3,600 | 1s per row (mixed types) |
| `perf_soak_1h_firehose_pat` | `perf_soak_1h_firehose` | 360,000 | 10ms per row |
| `perf_soak_1h_firehose_mixed_pat` | `perf_soak_1h_firehose_mixed` | 360,000 | 10ms per row (mixed types) |
| `perf_chunk_gap_35s_pat` | `perf_chunk_gap_35s` | 100 | 35s every 10 rows |
| `perf_chunk_gap_25s_pat` | `perf_chunk_gap_25s` | 100 | 25s every 10 rows |

### Whitespace Keepalive Mechanism

For scenarios with pauses longer than 30 seconds (e.g., `perf_chunk_gap_35s`), the mock server sends a whitespace byte (`" "`) every 30 seconds during the pause. This is valid JSON whitespace between array elements and resets the client's per-socket-read timeout. The `ijson` parser handles it transparently.

This allows connections with a 90-second timeout to survive arbitrarily long server-side pauses, as long as the keepalive interval (30s) is shorter than the client timeout.

## Streaming Buffer Size (`buf_size`)

The connector uses `ijson.parse(response.raw, buf_size=256)` to parse streamed JSON. The `buf_size` controls how many bytes ijson reads per `read()` call from the HTTP socket.

The default `buf_size=65536` (64KB) blocks until 64KB of data arrives — at 1 row/sec (~80 bytes/row), that means **no rows for ~13 minutes**. We benchmarked 8 values (2 to 65536) across 100–50k rows:

| buf_size | Wall throughput | CPU usage | Streaming latency (1 row/sec) |
|----------|----------------|-----------|-------------------------------|
| 2 | same | **95% (6.7x more)** | per-row |
| 256 | same | 16% (1.1x) | per-row |
| 1024 | same | 15% (1.1x) | ~8s batches |
| 65536 | same | 14% (baseline) | blocked 13+ min |

**`buf_size=256`** is the sweet spot: each ~80-byte row fits within a single read, giving per-row streaming latency with only ~1% more CPU than the 64KB default. Wall clock throughput is identical because the OS TCP buffer absorbs network data regardless of application read size.

## Fixtures

Defined in `tests/performance/conftest.py`:

| Fixture | Description |
|---------|-------------|
| `perf_connect(pat, timeout, max_retries)` | Factory — creates a connection for a specific scenario |
| `conn_100` / `conn_1k` / `conn_10k` / `conn_50k` / `conn_500k` | Pre-configured connections |
| `conn_mixed_types` | Connection for 14-column mixed type scenario |
| `conn_jittery` | Connection for jitter scenario |
| `soak_progress_interval` | Returns `--soak-progress` value (default 30) |

`PerfResult` is a dataclass that captures scenario name, row counts, elapsed time, throughput, peak memory, and optional notes. Its `summarize()` method formats a human-readable report printed at the end of each test.
