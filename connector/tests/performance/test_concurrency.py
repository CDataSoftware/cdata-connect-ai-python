"""
Concurrency tests — multiple threads and connections running in parallel.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from tests.performance.conftest import PerfResult, _perf_connect

pytestmark = pytest.mark.performance

QUERY = "SELECT * FROM [TestDB].[dbo].[Users]"


def _report(result: PerfResult):
    print(f"\n{'='*60}")
    print(result.summarize())
    print(f"{'='*60}")


def _worker_fetchall(pat, query=QUERY):
    """Worker: open connection, execute, fetchall, close. Return row count + time."""
    conn = _perf_connect(pat)
    cur = conn.cursor()
    t0 = time.perf_counter()
    cur.execute(query)
    rows = cur.fetchall()
    elapsed = time.perf_counter() - t0
    cur.close()
    conn.close()
    return len(rows), elapsed


class TestConcurrentConnections:
    """Multiple independent connections querying in parallel."""

    @pytest.mark.parametrize("n_workers", [2, 5, 10])
    def test_concurrent_fetchall_1k(self, n_workers):
        """N workers each fetch 1k rows on separate connections."""
        t0 = time.perf_counter()

        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = [
                pool.submit(_worker_fetchall, "perf_1k_pat")
                for _ in range(n_workers)
            ]
            results = []
            for f in as_completed(futures):
                row_count, worker_time = f.result()
                results.append((row_count, worker_time))

        total_elapsed = time.perf_counter() - t0
        total_rows = sum(r[0] for r in results)
        worker_times = [r[1] for r in results]

        result = PerfResult(
            scenario=f"concurrent {n_workers}x perf_1k / fetchall",
            rows_expected=1000 * n_workers,
            rows_received=total_rows,
            elapsed_seconds=total_elapsed,
            rows_per_second=total_rows / total_elapsed if total_elapsed > 0 else 0,
            notes=(
                f"Workers: {n_workers}, "
                f"per-worker: min={min(worker_times):.3f}s "
                f"max={max(worker_times):.3f}s "
                f"avg={sum(worker_times)/len(worker_times):.3f}s"
            ),
        )
        _report(result)

        for row_count, _ in results:
            assert row_count == 1000

    def test_concurrent_mixed_sizes(self):
        """Workers with different result set sizes running simultaneously."""
        tasks = [
            ("perf_100_pat", 100),
            ("perf_1k_pat", 1000),
            ("perf_1k_pat", 1000),
            ("perf_100_pat", 100),
            ("perf_10k_pat", 10000),
        ]

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {
                pool.submit(_worker_fetchall, pat): expected
                for pat, expected in tasks
            }
            for f in as_completed(futures):
                expected = futures[f]
                row_count, worker_time = f.result()
                assert row_count == expected, (
                    f"Expected {expected} rows, got {row_count}"
                )

        total_elapsed = time.perf_counter() - t0
        total_rows = sum(expected for _, expected in tasks)

        result = PerfResult(
            scenario="concurrent mixed sizes (100+1k+1k+100+10k)",
            rows_expected=total_rows,
            rows_received=total_rows,
            elapsed_seconds=total_elapsed,
            rows_per_second=total_rows / total_elapsed if total_elapsed > 0 else 0,
        )
        _report(result)


class TestConcurrentCursorsOnConnection:
    """Multiple cursors from the same connection (sequential — DB-API 2.0
    doesn't mandate concurrent cursor support on same connection)."""

    def test_sequential_cursors_same_connection(self, perf_connect):
        """Open cursor, fetch, close, repeat — measures cursor reuse overhead."""
        conn = perf_connect("perf_100_pat")

        times = []
        for i in range(10):
            cur = conn.cursor()
            t0 = time.perf_counter()
            cur.execute(QUERY)
            rows = cur.fetchall()
            elapsed = time.perf_counter() - t0
            cur.close()
            times.append(elapsed)
            assert len(rows) == 100

        result = PerfResult(
            scenario="10x sequential cursors on same connection (100 rows each)",
            rows_expected=1000,
            rows_received=1000,
            elapsed_seconds=sum(times),
            rows_per_second=1000 / sum(times) if sum(times) > 0 else 0,
            notes=(
                f"Per-cursor: min={min(times)*1000:.1f}ms "
                f"max={max(times)*1000:.1f}ms "
                f"avg={sum(times)/len(times)*1000:.1f}ms"
            ),
        )
        _report(result)


class TestConnectionLifecycle:
    """Measure connection and cursor creation overhead."""

    def test_connection_create_close_cycle(self):
        """Measure connect() + close() cycle time — no query."""
        times = []
        for _ in range(50):
            t0 = time.perf_counter()
            conn = _perf_connect("perf_100_pat")
            conn.close()
            elapsed = time.perf_counter() - t0
            times.append(elapsed)

        avg_ms = sum(times) / len(times) * 1000
        print(f"\nConnection create/close cycle (50 iterations):")
        print(f"  avg={avg_ms:.2f}ms  min={min(times)*1000:.2f}ms  max={max(times)*1000:.2f}ms")
        # Should be sub-millisecond — no network call on connect()
        assert avg_ms < 10, f"Connection lifecycle too slow: {avg_ms:.2f}ms avg"

    def test_rapid_query_reuse(self, perf_connect):
        """Execute 100 queries back-to-back on the same cursor."""
        conn = perf_connect("perf_100_pat")
        cur = conn.cursor()

        times = []
        for _ in range(100):
            t0 = time.perf_counter()
            cur.execute(QUERY)
            rows = cur.fetchall()
            elapsed = time.perf_counter() - t0
            times.append(elapsed)
            assert len(rows) == 100

        cur.close()

        total = sum(times)
        result = PerfResult(
            scenario="100x rapid queries on same cursor (100 rows each)",
            rows_expected=10000,
            rows_received=10000,
            elapsed_seconds=total,
            rows_per_second=10000 / total if total > 0 else 0,
            notes=(
                f"Per-query: min={min(times)*1000:.1f}ms "
                f"max={max(times)*1000:.1f}ms "
                f"avg={sum(times)/len(times)*1000:.1f}ms"
            ),
        )
        _report(result)
