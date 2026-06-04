"""
Throughput benchmarks — measure rows/sec for different result set sizes
and fetch methods (fetchall, fetchone, fetchmany).
"""

import time

import pytest

from tests.performance.conftest import PerfResult

pytestmark = pytest.mark.performance

QUERY = "SELECT * FROM [TestDB].[dbo].[Users]"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _timed_fetchall(conn, query=QUERY):
    cur = conn.cursor()
    cur.execute(query)
    t0 = time.perf_counter()
    rows = cur.fetchall()
    elapsed = time.perf_counter() - t0
    cur.close()
    return rows, elapsed


def _timed_fetchone(conn, query=QUERY):
    cur = conn.cursor()
    cur.execute(query)
    rows = []
    t0 = time.perf_counter()
    while True:
        row = cur.fetchone()
        if row is None:
            break
        rows.append(row)
    elapsed = time.perf_counter() - t0
    cur.close()
    return rows, elapsed


def _timed_fetchmany(conn, batch_size, query=QUERY):
    cur = conn.cursor()
    cur.execute(query)
    rows = []
    t0 = time.perf_counter()
    while True:
        batch = cur.fetchmany(batch_size)
        if not batch:
            break
        rows.extend(batch)
    elapsed = time.perf_counter() - t0
    cur.close()
    return rows, elapsed


def _report(result: PerfResult):
    print(f"\n{'='*60}")
    print(result.summarize())
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Throughput by result set size — fetchall
# ---------------------------------------------------------------------------

class TestFetchallThroughput:
    """Measure fetchall throughput at different result set sizes."""

    def test_fetchall_100_rows(self, conn_100):
        rows, elapsed = _timed_fetchall(conn_100)
        result = PerfResult(
            scenario="perf_100 / fetchall",
            rows_expected=100, rows_received=len(rows),
            elapsed_seconds=elapsed,
            rows_per_second=len(rows) / elapsed if elapsed > 0 else 0,
        )
        _report(result)
        assert len(rows) == 100

    def test_fetchall_1k_rows(self, conn_1k):
        rows, elapsed = _timed_fetchall(conn_1k)
        result = PerfResult(
            scenario="perf_1k / fetchall",
            rows_expected=1000, rows_received=len(rows),
            elapsed_seconds=elapsed,
            rows_per_second=len(rows) / elapsed if elapsed > 0 else 0,
        )
        _report(result)
        assert len(rows) == 1000

    def test_fetchall_10k_rows(self, conn_10k):
        rows, elapsed = _timed_fetchall(conn_10k)
        result = PerfResult(
            scenario="perf_10k / fetchall",
            rows_expected=10000, rows_received=len(rows),
            elapsed_seconds=elapsed,
            rows_per_second=len(rows) / elapsed if elapsed > 0 else 0,
        )
        _report(result)
        assert len(rows) == 10000

    def test_fetchall_50k_rows(self, conn_50k):
        rows, elapsed = _timed_fetchall(conn_50k)
        result = PerfResult(
            scenario="perf_50k / fetchall",
            rows_expected=50000, rows_received=len(rows),
            elapsed_seconds=elapsed,
            rows_per_second=len(rows) / elapsed if elapsed > 0 else 0,
        )
        _report(result)
        assert len(rows) == 50000


# ---------------------------------------------------------------------------
# Fetch method comparison at 1k rows
# ---------------------------------------------------------------------------

class TestFetchMethodComparison:
    """Compare fetchall vs fetchone vs fetchmany on 1k rows."""

    def test_fetchall_1k(self, conn_1k):
        rows, elapsed = _timed_fetchall(conn_1k)
        result = PerfResult(
            scenario="perf_1k / fetchall",
            rows_expected=1000, rows_received=len(rows),
            elapsed_seconds=elapsed,
            rows_per_second=len(rows) / elapsed if elapsed > 0 else 0,
        )
        _report(result)
        assert len(rows) == 1000

    def test_fetchone_1k(self, conn_1k):
        rows, elapsed = _timed_fetchone(conn_1k)
        result = PerfResult(
            scenario="perf_1k / fetchone (row-by-row)",
            rows_expected=1000, rows_received=len(rows),
            elapsed_seconds=elapsed,
            rows_per_second=len(rows) / elapsed if elapsed > 0 else 0,
        )
        _report(result)
        assert len(rows) == 1000

    def test_fetchmany_100_batch_1k(self, conn_1k):
        rows, elapsed = _timed_fetchmany(conn_1k, batch_size=100)
        result = PerfResult(
            scenario="perf_1k / fetchmany(100)",
            rows_expected=1000, rows_received=len(rows),
            elapsed_seconds=elapsed,
            rows_per_second=len(rows) / elapsed if elapsed > 0 else 0,
        )
        _report(result)
        assert len(rows) == 1000

    def test_fetchmany_10_batch_1k(self, conn_1k):
        rows, elapsed = _timed_fetchmany(conn_1k, batch_size=10)
        result = PerfResult(
            scenario="perf_1k / fetchmany(10)",
            rows_expected=1000, rows_received=len(rows),
            elapsed_seconds=elapsed,
            rows_per_second=len(rows) / elapsed if elapsed > 0 else 0,
        )
        _report(result)
        assert len(rows) == 1000


# ---------------------------------------------------------------------------
# Type conversion overhead
# ---------------------------------------------------------------------------

class TestTypeConversionOverhead:
    """Compare throughput: simple 6-col template vs 14-col mixed-types template."""

    def test_simple_types_1k(self, conn_1k):
        """6 columns: INT, STRING, STRING, DECIMAL, BOOLEAN, DATETIME."""
        rows, elapsed = _timed_fetchall(conn_1k)
        result = PerfResult(
            scenario="perf_1k / simple types (6 cols)",
            rows_expected=1000, rows_received=len(rows),
            elapsed_seconds=elapsed,
            rows_per_second=len(rows) / elapsed if elapsed > 0 else 0,
        )
        _report(result)
        assert len(rows) == 1000

    def test_mixed_types_1k(self, conn_mixed_types):
        """14 columns: INT, STRING, TINYINT, SMALLINT, BIGINT, FLOAT, DOUBLE,
        DECIMAL, BOOLEAN, DATE, TIME, DATETIME, UUID, STRING."""
        query = "SELECT * FROM [TestDB].[dbo].[MixedTypes]"
        rows, elapsed = _timed_fetchall(conn_mixed_types, query=query)
        result = PerfResult(
            scenario="perf_1k / mixed types (14 cols)",
            rows_expected=1000, rows_received=len(rows),
            elapsed_seconds=elapsed,
            rows_per_second=len(rows) / elapsed if elapsed > 0 else 0,
        )
        _report(result)
        assert len(rows) == 1000
