"""
Streaming performance tests — memory profiling, jittery networks,
and client-side slow consumption.
"""

import time
import tracemalloc

import pytest

from tests.performance.conftest import PerfResult

pytestmark = pytest.mark.performance

QUERY = "SELECT * FROM [TestDB].[dbo].[Users]"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _report(result: PerfResult):
    print(f"\n{'='*60}")
    print(result.summarize())
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Memory: streaming (fetchone) vs buffered (fetchall)
# ---------------------------------------------------------------------------

class TestMemoryProfile:
    """Verify streaming keeps memory flat vs fetchall loading everything."""

    def test_fetchall_memory_10k(self, conn_10k):
        """fetchall loads all rows into memory — measure peak."""
        cur = conn_10k.cursor()
        cur.execute(QUERY)

        tracemalloc.start()
        rows = cur.fetchall()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        cur.close()

        peak_kb = peak / 1024
        result = PerfResult(
            scenario="perf_10k / fetchall memory",
            rows_expected=10000, rows_received=len(rows),
            peak_memory_kb=peak_kb,
            notes=f"All {len(rows)} rows buffered in memory",
        )
        _report(result)
        assert len(rows) == 10000

    def test_fetchone_memory_10k(self, conn_10k):
        """fetchone streams row-by-row — peak memory should be much lower."""
        cur = conn_10k.cursor()
        cur.execute(QUERY)

        tracemalloc.start()
        count = 0
        while True:
            row = cur.fetchone()
            if row is None:
                break
            count += 1
            # Don't accumulate rows — just count them
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        cur.close()

        peak_kb = peak / 1024
        result = PerfResult(
            scenario="perf_10k / fetchone memory (streaming)",
            rows_expected=10000, rows_received=count,
            peak_memory_kb=peak_kb,
            notes="Rows consumed one-at-a-time, not accumulated",
        )
        _report(result)
        assert count == 10000

    def test_streaming_memory_lower_than_buffered(self, perf_connect):
        """Streaming should use significantly less peak memory than fetchall."""
        # --- fetchall (buffered) ---
        conn1 = perf_connect("perf_10k_pat")
        cur1 = conn1.cursor()
        cur1.execute(QUERY)

        tracemalloc.start()
        rows = cur1.fetchall()
        _, peak_buffered = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        cur1.close()

        # --- fetchone (streaming) ---
        conn2 = perf_connect("perf_10k_pat")
        cur2 = conn2.cursor()
        cur2.execute(QUERY)

        tracemalloc.start()
        count = 0
        while True:
            row = cur2.fetchone()
            if row is None:
                break
            count += 1
        _, peak_streaming = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        cur2.close()

        print(f"\nBuffered peak: {peak_buffered/1024:.1f} KB")
        print(f"Streaming peak: {peak_streaming/1024:.1f} KB")
        print(f"Ratio: {peak_buffered/peak_streaming:.1f}x")

        assert len(rows) == count == 10000
        # Streaming should use less memory than buffered
        assert peak_streaming < peak_buffered, (
            f"Streaming ({peak_streaming/1024:.0f} KB) should use less "
            f"memory than buffered ({peak_buffered/1024:.0f} KB)"
        )


# ---------------------------------------------------------------------------
# Jittery network simulation
# ---------------------------------------------------------------------------

class TestJitteryStream:
    """Measure throughput with simulated network jitter."""

    def test_jittery_fetchall(self, conn_jittery):
        """1000 rows with [50ms, 200ms, 1s, 50ms] pauses every 50 rows."""
        cur = conn_jittery.cursor()
        t0 = time.perf_counter()
        cur.execute(QUERY)
        rows = cur.fetchall()
        elapsed = time.perf_counter() - t0
        cur.close()

        result = PerfResult(
            scenario="perf_jittery / fetchall (network jitter)",
            rows_expected=1000, rows_received=len(rows),
            elapsed_seconds=elapsed,
            rows_per_second=len(rows) / elapsed if elapsed > 0 else 0,
            notes="Pauses: [50ms,200ms,1s,50ms] every 50 rows = ~26s total pause",
        )
        _report(result)
        assert len(rows) == 1000

    def test_jittery_fetchone_timing(self, conn_jittery):
        """Measure per-fetch latency distribution under jitter."""
        cur = conn_jittery.cursor()
        cur.execute(QUERY)

        fetch_times = []
        rows = 0
        while True:
            t0 = time.perf_counter()
            row = cur.fetchone()
            elapsed = time.perf_counter() - t0
            if row is None:
                break
            fetch_times.append(elapsed)
            rows += 1
        cur.close()

        fetch_times.sort()
        p50 = fetch_times[len(fetch_times) // 2]
        p95 = fetch_times[int(len(fetch_times) * 0.95)]
        p99 = fetch_times[int(len(fetch_times) * 0.99)]
        max_t = fetch_times[-1]

        result = PerfResult(
            scenario="perf_jittery / fetchone latency distribution",
            rows_expected=1000, rows_received=rows,
            elapsed_seconds=sum(fetch_times),
            rows_per_second=rows / sum(fetch_times) if sum(fetch_times) > 0 else 0,
            notes=f"p50={p50*1000:.1f}ms  p95={p95*1000:.1f}ms  p99={p99*1000:.1f}ms  max={max_t*1000:.1f}ms",
        )
        _report(result)
        assert rows == 1000


# ---------------------------------------------------------------------------
# Slow client consumption — client reads slowly, server stream stays open
# ---------------------------------------------------------------------------

class TestSlowClientPull:
    """Simulate a slow client that deliberately pauses between fetches.

    This tests that the server-side stream stays open and doesn't timeout
    or drop the connection while the client is processing slowly.
    """

    def test_slow_client_10ms_per_row(self, conn_1k):
        """Client sleeps 10ms between fetchone calls — ~10s for 1k rows."""
        cur = conn_1k.cursor()
        cur.execute(QUERY)

        rows = 0
        t0 = time.perf_counter()
        while True:
            row = cur.fetchone()
            if row is None:
                break
            rows += 1
            time.sleep(0.01)  # 10ms client processing time
        elapsed = time.perf_counter() - t0
        cur.close()

        result = PerfResult(
            scenario="perf_1k / slow client (10ms/row)",
            rows_expected=1000, rows_received=rows,
            elapsed_seconds=elapsed,
            rows_per_second=rows / elapsed if elapsed > 0 else 0,
            notes="Client sleeps 10ms between each fetchone",
        )
        _report(result)
        assert rows == 1000

    def test_slow_client_50ms_per_row(self, conn_100):
        """Client sleeps 50ms between fetchone calls — ~5s for 100 rows."""
        cur = conn_100.cursor()
        cur.execute(QUERY)

        rows = 0
        t0 = time.perf_counter()
        while True:
            row = cur.fetchone()
            if row is None:
                break
            rows += 1
            time.sleep(0.05)  # 50ms client processing time
        elapsed = time.perf_counter() - t0
        cur.close()

        result = PerfResult(
            scenario="perf_100 / slow client (50ms/row)",
            rows_expected=100, rows_received=rows,
            elapsed_seconds=elapsed,
            rows_per_second=rows / elapsed if elapsed > 0 else 0,
            notes="Client sleeps 50ms between each fetchone",
        )
        _report(result)
        assert rows == 100

    def test_slow_client_fetchmany_with_processing(self, conn_1k):
        """Client fetches in batches of 50, then 'processes' for 200ms."""
        cur = conn_1k.cursor()
        cur.execute(QUERY)

        rows = 0
        batches = 0
        t0 = time.perf_counter()
        while True:
            batch = cur.fetchmany(50)
            if not batch:
                break
            rows += len(batch)
            batches += 1
            time.sleep(0.2)  # 200ms batch processing
        elapsed = time.perf_counter() - t0
        cur.close()

        result = PerfResult(
            scenario="perf_1k / slow client fetchmany(50) + 200ms process",
            rows_expected=1000, rows_received=rows,
            elapsed_seconds=elapsed,
            rows_per_second=rows / elapsed if elapsed > 0 else 0,
            notes=f"{batches} batches, 200ms processing per batch",
        )
        _report(result)
        assert rows == 1000
