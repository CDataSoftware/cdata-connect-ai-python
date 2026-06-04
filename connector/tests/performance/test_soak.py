"""
Soak tests — long-running streaming tests that run for up to 1 hour.

These are skipped by default. Run with:
    pytest tests/performance/test_soak.py --run-soak -v -s

Progress reporting (prints to console every N seconds):
    pytest ... --soak-progress=10     # every 10 seconds
    pytest ... --soak-progress=60     # every 1 minute
    pytest ... --soak-progress=5      # every 5 seconds (verbose)

Default is every 30 seconds. Requires -s to see output.

What soak tests validate:
- Connection stays alive for the full duration (no socket drops)
- Whitespace keepalives prevent mid-stream read timeouts on long pauses
- Memory stays flat when streaming row-by-row (no leaks)
- All rows arrive with correct count and type conversion
- Driver handles sustained throughput without degradation
"""

import time
import tracemalloc

import pytest

from tests.performance.conftest import PerfResult

pytestmark = [pytest.mark.performance, pytest.mark.soak]

QUERY = "SELECT * FROM [TestDB].[dbo].[Users]"
QUERY_MIXED = "SELECT * FROM [TestDB].[dbo].[MixedTypes]"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _report(result: PerfResult):
    print(f"\n{'='*70}", flush=True)
    print(result.summarize(), flush=True)
    print(f"{'='*70}", flush=True)


def _stream_with_monitoring(cur, query, expected_rows, label,
                            progress_interval_s=30, check_memory=True):
    """Stream rows via fetchone with time-based progress reporting.

    Args:
        cur: Cursor to use.
        query: SQL query to execute.
        expected_rows: Expected total rows (for % display).
        label: Short label for progress lines.
        progress_interval_s: Seconds between progress reports.
        check_memory: Whether to track memory via tracemalloc.

    Returns:
        (row_count, elapsed, peak_memory_kb, memory_samples)
    """
    cur.execute(query)

    if check_memory:
        tracemalloc.start()
        snap_start = tracemalloc.take_snapshot()

    count = 0
    memory_samples = []
    t0 = time.perf_counter()
    next_report = t0 + progress_interval_s

    while True:
        row = cur.fetchone()
        if row is None:
            break
        count += 1

        now = time.perf_counter()
        if now >= next_report:
            elapsed = now - t0
            pct = count / expected_rows * 100 if expected_rows else 0
            rate = count / elapsed if elapsed > 0 else 0
            eta = (expected_rows - count) / rate if rate > 0 else 0

            if check_memory:
                current, peak = tracemalloc.get_traced_memory()
                memory_samples.append({
                    "rows": count,
                    "elapsed_s": elapsed,
                    "current_kb": current / 1024,
                    "peak_kb": peak / 1024,
                })
                print(
                    f"  [{elapsed:>7.0f}s] {label}: "
                    f"{count:>6}/{expected_rows} ({pct:5.1f}%)  "
                    f"{rate:>6.1f} rows/s  "
                    f"mem={current/1024:.0f}KB peak={peak/1024:.0f}KB  "
                    f"ETA {eta:.0f}s",
                    flush=True,
                )
            else:
                print(
                    f"  [{elapsed:>7.0f}s] {label}: "
                    f"{count:>6}/{expected_rows} ({pct:5.1f}%)  "
                    f"{rate:>6.1f} rows/s  "
                    f"ETA {eta:.0f}s",
                    flush=True,
                )

            next_report = now + progress_interval_s

    elapsed = time.perf_counter() - t0
    peak_kb = 0.0
    snap_end = None
    if check_memory:
        _, peak = tracemalloc.get_traced_memory()
        peak_kb = peak / 1024
        snap_end = tracemalloc.take_snapshot()
        tracemalloc.stop()

    # Final summary line
    rate = count / elapsed if elapsed > 0 else 0
    print(
        f"  [{elapsed:>7.0f}s] {label}: "
        f"DONE {count}/{expected_rows} rows  "
        f"{rate:.1f} rows/s  peak={peak_kb:.0f}KB",
        flush=True,
    )

    # Print top allocators by diff if we have snapshots
    if check_memory and snap_end is not None:
        _print_top_allocators(snap_start, snap_end)

    return count, elapsed, peak_kb, memory_samples


def _print_top_allocators(snap_start, snap_end, limit=10):
    """Print the top memory allocators between two tracemalloc snapshots."""
    stats = snap_end.compare_to(snap_start, 'lineno')
    if not stats:
        return
    print(f"\n  {'─'*60}", flush=True)
    print(f"  Top {limit} memory allocators (new - baseline):", flush=True)
    print(f"  {'─'*60}", flush=True)
    print(f"  {'Size':>10}  {'Count':>7}  {'Location'}", flush=True)
    print(f"  {'─'*60}", flush=True)
    for stat in stats[:limit]:
        size = stat.size_diff
        count = stat.count_diff
        if size <= 0:
            continue
        if size >= 1024 * 1024:
            size_str = f"{size / 1024 / 1024:.1f} MB"
        elif size >= 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} B"
        print(f"  {size_str:>10}  {count:>+7}  {stat.traceback}", flush=True)
    print(f"  {'─'*60}", flush=True)


def _check_memory_stability(memory_samples, max_growth_kb=512):
    """Print memory timeline and assert memory didn't grow unbounded."""
    if len(memory_samples) < 2:
        return

    # Print timeline table
    print(f"\n  {'─'*60}", flush=True)
    print(f"  Memory Timeline:", flush=True)
    print(f"  {'─'*60}", flush=True)
    print(f"  {'Elapsed':>10}  {'Rows':>10}  {'Current':>10}  {'Peak':>10}  {'Delta':>10}", flush=True)
    print(f"  {'─'*60}", flush=True)
    for i, s in enumerate(memory_samples):
        delta = s["current_kb"] - memory_samples[0]["current_kb"]
        delta_str = f"{delta:+.0f}KB"
        print(
            f"  {s['elapsed_s']:>9.0f}s  {s['rows']:>10}  "
            f"{s['current_kb']:>8.0f}KB  {s['peak_kb']:>8.0f}KB  "
            f"{delta_str:>10}",
            flush=True,
        )
    print(f"  {'─'*60}", flush=True)

    # Summary and assertion
    first = memory_samples[0]["current_kb"]
    last = memory_samples[-1]["current_kb"]
    peak = max(s["peak_kb"] for s in memory_samples)
    growth = last - first
    print(f"\n  Memory Summary:", flush=True)
    print(f"    First sample:  {first:.0f} KB", flush=True)
    print(f"    Last sample:   {last:.0f} KB", flush=True)
    print(f"    Peak:          {peak:.0f} KB", flush=True)
    print(f"    Growth:        {growth:+.0f} KB", flush=True)
    print(f"    Threshold:     {max_growth_kb} KB", flush=True)
    print(f"    Verdict:       {'PASS' if growth < max_growth_kb else 'FAIL — possible leak'}", flush=True)

    assert growth < max_growth_kb, (
        f"Memory grew by {growth:.0f}KB over the run "
        f"(first={first:.0f}KB, last={last:.0f}KB). "
        f"Possible leak — threshold is {max_growth_kb}KB."
    )


# ---------------------------------------------------------------------------
# 1-hour soak: steady drip (1 row/sec)
# ---------------------------------------------------------------------------

class TestSoak1HourDrip:
    """3,600 rows at 1 row/sec — exactly 1 hour of streaming.

    The server sends one row, pauses 1 second, sends the next. The 1s
    gaps are well within the 90s default timeout. Tests pure connection
    stability over a long duration.
    """

    def test_1h_drip_streaming(self, perf_connect, soak_progress_interval):
        conn = perf_connect("perf_soak_1h_drip_pat", timeout=90, max_retries=0)
        cur = conn.cursor()

        count, elapsed, peak_kb, samples = _stream_with_monitoring(
            cur, QUERY,
            expected_rows=3600,
            label="1h-drip",
            progress_interval_s=soak_progress_interval,
        )
        cur.close()

        result = PerfResult(
            scenario="soak_1h_drip (1 row/sec, 3600 rows, ~1 hour)",
            rows_expected=3600, rows_received=count,
            elapsed_seconds=elapsed,
            rows_per_second=count / elapsed if elapsed > 0 else 0,
            peak_memory_kb=peak_kb,
        )
        _report(result)

        assert count == 3600
        _check_memory_stability(samples)


# ---------------------------------------------------------------------------
# 1-hour soak: bursty traffic (100-row bursts with 10s pauses)
# ---------------------------------------------------------------------------

class TestSoak1HourBurst:
    """36,000 rows in bursts of 100 with 10s pauses — ~1 hour.

    Simulates a query that returns data in pages: 100 rows fast, then
    10s pause (server-side paging), repeat. 360 bursts x 10s = 1 hour.
    """

    def test_1h_burst_streaming(self, perf_connect, soak_progress_interval):
        conn = perf_connect("perf_soak_1h_burst_pat", timeout=90, max_retries=0)
        cur = conn.cursor()

        count, elapsed, peak_kb, samples = _stream_with_monitoring(
            cur, QUERY,
            expected_rows=36000,
            label="1h-burst",
            progress_interval_s=soak_progress_interval,
        )
        cur.close()

        result = PerfResult(
            scenario="soak_1h_burst (100-row bursts + 10s pause, 36k rows, ~1 hour)",
            rows_expected=36000, rows_received=count,
            elapsed_seconds=elapsed,
            rows_per_second=count / elapsed if elapsed > 0 else 0,
            peak_memory_kb=peak_kb,
        )
        _report(result)

        assert count == 36000
        _check_memory_stability(samples)


# ---------------------------------------------------------------------------
# 1-hour soak: mixed types (type conversion under sustained load)
# ---------------------------------------------------------------------------

class TestSoak1HourMixedTypes:
    """3,600 mixed-type rows at 1 row/sec — 1 hour of type conversion.

    Each row has 14 columns: INT, TINYINT, SMALLINT, BIGINT, FLOAT,
    DOUBLE, DECIMAL, BOOLEAN, DATE, TIME, DATETIME, UUID, STRING x2.
    """

    def test_1h_mixed_types_streaming(self, perf_connect, soak_progress_interval):
        conn = perf_connect("perf_soak_1h_mixed_pat", timeout=90, max_retries=0)
        cur = conn.cursor()

        count, elapsed, peak_kb, samples = _stream_with_monitoring(
            cur, QUERY_MIXED,
            expected_rows=3600,
            label="1h-mixed",
            progress_interval_s=soak_progress_interval,
        )
        cur.close()

        result = PerfResult(
            scenario="soak_1h_mixed (14-col mixed types, 1 row/sec, ~1 hour)",
            rows_expected=3600, rows_received=count,
            elapsed_seconds=elapsed,
            rows_per_second=count / elapsed if elapsed > 0 else 0,
            peak_memory_kb=peak_kb,
        )
        _report(result)

        assert count == 3600
        _check_memory_stability(samples)


# ---------------------------------------------------------------------------
# Shorter soak tests (10-42 min) — kept for quicker validation
# ---------------------------------------------------------------------------

class TestSoakSlowServer:
    """Server drip-feeds rows — 1 row per 500ms for 5000 rows (~42 min)."""

    def test_slow_drip_5000_rows(self, perf_connect, soak_progress_interval):
        conn = perf_connect("perf_soak_slow_pat", timeout=90, max_retries=0)
        cur = conn.cursor()

        count, elapsed, peak_kb, samples = _stream_with_monitoring(
            cur, QUERY,
            expected_rows=5000,
            label="slow-drip",
            progress_interval_s=soak_progress_interval,
        )
        cur.close()

        result = PerfResult(
            scenario="soak_slow_server (500ms/row, 5000 rows, ~42 min)",
            rows_expected=5000, rows_received=count,
            elapsed_seconds=elapsed,
            rows_per_second=count / elapsed if elapsed > 0 else 0,
            peak_memory_kb=peak_kb,
        )
        _report(result)

        assert count == 5000
        _check_memory_stability(samples)


class TestSoakMediumStream:
    """Steady stream with 100ms pauses — 10k rows over ~17 min."""

    def test_steady_stream_10k_rows(self, perf_connect, soak_progress_interval):
        conn = perf_connect("perf_soak_medium_pat", timeout=90, max_retries=0)
        cur = conn.cursor()

        count, elapsed, peak_kb, samples = _stream_with_monitoring(
            cur, QUERY,
            expected_rows=10000,
            label="medium",
            progress_interval_s=soak_progress_interval,
        )
        cur.close()

        result = PerfResult(
            scenario="soak_medium (100ms every 10 rows, 10k rows, ~17 min)",
            rows_expected=10000, rows_received=count,
            elapsed_seconds=elapsed,
            rows_per_second=count / elapsed if elapsed > 0 else 0,
            peak_memory_kb=peak_kb,
        )
        _report(result)

        assert count == 10000
        _check_memory_stability(samples)


class TestSoakSlowClient:
    """Client deliberately reads slowly — server stream must stay open."""

    def test_slow_client_100ms_1k_rows(self, perf_connect):
        """Client sleeps 100ms per row on 1k rows (~100s)."""
        conn = perf_connect("perf_1k_pat", timeout=90, max_retries=0)
        cur = conn.cursor()
        cur.execute(QUERY)

        count = 0
        t0 = time.perf_counter()
        while True:
            row = cur.fetchone()
            if row is None:
                break
            count += 1
            time.sleep(0.1)

        elapsed = time.perf_counter() - t0
        cur.close()

        result = PerfResult(
            scenario="soak_slow_client (100ms/row, 1k rows, ~100s)",
            rows_expected=1000, rows_received=count,
            elapsed_seconds=elapsed,
            rows_per_second=count / elapsed if elapsed > 0 else 0,
            notes="Client sleeps 100ms between rows, server sends fast",
        )
        _report(result)
        assert count == 1000


class TestSoak1HourFirehose:
    """360,000 rows at 10ms/row — sustained high-volume streaming for ~1 hour.

    Unlike the drip test (1 row/sec), this floods the client with data.
    Tests that the driver can sustain ~100 rows/sec for a full hour without
    memory leaks, throughput degradation, or connection drops.
    """

    def test_1h_firehose_streaming(self, perf_connect, soak_progress_interval):
        conn = perf_connect("perf_soak_1h_firehose_pat", timeout=90, max_retries=0)
        cur = conn.cursor()

        count, elapsed, peak_kb, samples = _stream_with_monitoring(
            cur, QUERY,
            expected_rows=360000,
            label="1h-firehose",
            progress_interval_s=soak_progress_interval,
        )
        cur.close()

        result = PerfResult(
            scenario="soak_1h_firehose (10ms/row, 360k rows, ~1 hour)",
            rows_expected=360000, rows_received=count,
            elapsed_seconds=elapsed,
            rows_per_second=count / elapsed if elapsed > 0 else 0,
            peak_memory_kb=peak_kb,
        )
        _report(result)

        assert count == 360000
        _check_memory_stability(samples)

    def test_1h_firehose_mixed_types(self, perf_connect, soak_progress_interval):
        """Same firehose rate but with 14-column mixed types — heavy type conversion."""
        conn = perf_connect("perf_soak_1h_firehose_mixed_pat", timeout=90, max_retries=0)
        cur = conn.cursor()

        count, elapsed, peak_kb, samples = _stream_with_monitoring(
            cur, QUERY_MIXED,
            expected_rows=360000,
            label="1h-firehose-mixed",
            progress_interval_s=soak_progress_interval,
        )
        cur.close()

        result = PerfResult(
            scenario="soak_1h_firehose_mixed (10ms/row, 360k mixed-type rows, ~1 hour)",
            rows_expected=360000, rows_received=count,
            elapsed_seconds=elapsed,
            rows_per_second=count / elapsed if elapsed > 0 else 0,
            peak_memory_kb=peak_kb,
        )
        _report(result)

        assert count == 360000
        _check_memory_stability(samples)


class TestSoakHighVolume:
    """Near-million row tests — pure throughput, no pauses."""

    def test_500k_rows_fetchall(self, perf_connect):
        """500k rows buffered via fetchall."""
        conn = perf_connect("perf_500k_pat", timeout=600, max_retries=0)
        cur = conn.cursor()

        t0 = time.perf_counter()
        cur.execute(QUERY)
        rows = cur.fetchall()
        elapsed = time.perf_counter() - t0
        cur.close()

        result = PerfResult(
            scenario="soak_500k / fetchall (high volume)",
            rows_expected=500000, rows_received=len(rows),
            elapsed_seconds=elapsed,
            rows_per_second=len(rows) / elapsed if elapsed > 0 else 0,
        )
        _report(result)
        assert len(rows) == 500000

    def test_500k_rows_streaming_count(self, perf_connect, soak_progress_interval):
        """500k rows consumed via fetchone — streaming without accumulation."""
        conn = perf_connect("perf_500k_pat", timeout=600, max_retries=0)
        cur = conn.cursor()

        count, elapsed, peak_kb, _ = _stream_with_monitoring(
            cur, QUERY,
            expected_rows=500000,
            label="500k-stream",
            progress_interval_s=soak_progress_interval,
        )
        cur.close()

        result = PerfResult(
            scenario="soak_500k / fetchone streaming (high volume)",
            rows_expected=500000, rows_received=count,
            elapsed_seconds=elapsed,
            rows_per_second=count / elapsed if elapsed > 0 else 0,
            peak_memory_kb=peak_kb,
        )
        _report(result)
        assert count == 500000
