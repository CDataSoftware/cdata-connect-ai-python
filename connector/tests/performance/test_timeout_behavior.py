"""
Timeout behavior tests — validate how the driver handles timeouts
during initial connection vs mid-stream.

KEY BEHAVIORS (validated by these tests):
1. timeout= is a per-socket-read timeout, NOT a total query timeout
2. The mock server sends whitespace keepalives every 30s during long pauses,
   which resets the client's read timeout — so pauses >30s survive as long as
   the client timeout is >= ~35s
3. If client timeout < keepalive interval (30s), long pauses will timeout
4. A long-running stream with keepalives will never timeout regardless of
   total duration
5. Timeout exceptions are NOT retried (by design)
"""

import time

import pytest

from cdata_connect_ai.exceptions import OperationalError, DatabaseError
from tests.performance.conftest import PerfResult

pytestmark = pytest.mark.performance

QUERY = "SELECT * FROM [TestDB].[dbo].[Users]"
DEFAULT_QUERY = "SELECT * FROM [Salesforce1].[Salesforce].[Account]"


def _report(result: PerfResult):
    print(f"\n{'='*60}")
    print(result.summarize())
    print(f"{'='*60}")


class TestInitialConnectionTimeout:
    """Timeout behavior before streaming starts (first byte)."""

    def test_timeout_before_first_byte(self, perf_connect):
        """Server delays 5s before responding, timeout=2s — should raise OperationalError."""
        conn = perf_connect("very_slow_pat", timeout=2, max_retries=0)
        cur = conn.cursor()
        with pytest.raises(OperationalError, match="[Tt]imed out"):
            cur.execute(DEFAULT_QUERY)

    def test_no_timeout_when_within_limit(self, perf_connect):
        """Server delays 2s, timeout=10s — should succeed."""
        conn = perf_connect("slow_pat", timeout=10, max_retries=0)
        cur = conn.cursor()
        cur.execute(DEFAULT_QUERY)
        rows = cur.fetchall()
        assert len(rows) > 0
        cur.close()


class TestMidStreamWithKeepalive:
    """Mid-stream timeout behavior WITH whitespace keepalives.

    The mock server sends a whitespace keepalive every 30s during long
    pauses. This resets the client's per-read timeout, so pauses of any
    duration survive as long as timeout >= keepalive_interval (~35s to
    allow margin).
    """

    def test_long_pause_survives_with_keepalive(self, perf_connect):
        """35s gap between chunks, timeout=45s — keepalive at 30s keeps it alive."""
        conn = perf_connect("perf_chunk_gap_35s_pat", timeout=45, max_retries=0)
        cur = conn.cursor()

        t0 = time.perf_counter()
        cur.execute(QUERY)
        rows = cur.fetchall()
        elapsed = time.perf_counter() - t0
        cur.close()

        result = PerfResult(
            scenario="chunk_gap_35s / timeout=45s (keepalive saves it)",
            rows_expected=100, rows_received=len(rows),
            elapsed_seconds=elapsed,
            rows_per_second=len(rows) / elapsed if elapsed > 0 else 0,
            notes="35s gap, keepalive at 30s, timeout=45s — survives",
        )
        _report(result)
        assert len(rows) == 100

    def test_25s_gap_under_timeout_succeeds(self, perf_connect):
        """25s gap between chunks, 30s timeout — gap < timeout, no keepalive needed."""
        conn = perf_connect("perf_chunk_gap_25s_pat", timeout=30, max_retries=0)
        cur = conn.cursor()

        t0 = time.perf_counter()
        cur.execute(QUERY)
        rows = cur.fetchall()
        elapsed = time.perf_counter() - t0
        cur.close()

        result = PerfResult(
            scenario="chunk_gap_25s / timeout=30s (under limit)",
            rows_expected=100, rows_received=len(rows),
            elapsed_seconds=elapsed,
            rows_per_second=len(rows) / elapsed if elapsed > 0 else 0,
            notes="25s gap, 30s timeout — gap fits within timeout window",
        )
        _report(result)
        assert len(rows) == 100


class TestMidStreamTimeoutWithoutKeepalive:
    """When client timeout < keepalive interval (30s), long pauses WILL timeout.

    The keepalive fires at 30s into the pause. If the client's timeout is
    shorter (e.g. 5s), it times out before the keepalive arrives.
    """

    def test_short_timeout_on_long_gap_raises(self, perf_connect):
        """35s gap, 5s timeout — times out before keepalive arrives at 30s."""
        conn = perf_connect("perf_chunk_gap_35s_pat", timeout=5, max_retries=0)
        cur = conn.cursor()

        t0 = time.perf_counter()
        with pytest.raises(Exception) as exc_info:
            cur.execute(QUERY)
            cur.fetchall()
        elapsed = time.perf_counter() - t0

        exception_type = type(exc_info.value).__name__
        print(f"\nTimeout (5s) on 35s gap: failed in {elapsed:.1f}s")
        print(f"Exception: {exception_type}: {exc_info.value}")

        # Should fail in ~5s, not 30s (keepalive) or 35s (full gap)
        assert elapsed < 10, f"Took {elapsed:.1f}s — expected ~5s"

    def test_10s_timeout_on_35s_gap_raises(self, perf_connect):
        """35s gap, 10s timeout — still times out before 30s keepalive."""
        conn = perf_connect("perf_chunk_gap_35s_pat", timeout=10, max_retries=0)
        cur = conn.cursor()

        t0 = time.perf_counter()
        with pytest.raises(Exception):
            cur.execute(QUERY)
            cur.fetchall()
        elapsed = time.perf_counter() - t0

        print(f"\nTimeout (10s) on 35s gap: failed in {elapsed:.1f}s")
        assert elapsed < 15, f"Took {elapsed:.1f}s — expected ~10s"


class TestLongStreamNoTimeout:
    """Validate that long-running streams with small gaps DON'T timeout."""

    def test_long_stream_small_chunks(self, perf_connect):
        """100 rows with 100ms pauses every 25 rows, timeout=5s.

        Each gap (100ms) is far under timeout — completes fine.
        """
        conn = perf_connect("template_pat", timeout=5, max_retries=0)
        cur = conn.cursor()

        t0 = time.perf_counter()
        cur.execute(QUERY)
        rows = cur.fetchall()
        elapsed = time.perf_counter() - t0
        cur.close()

        result = PerfResult(
            scenario="template_stream / timeout=5s (small gaps)",
            rows_expected=100, rows_received=len(rows),
            elapsed_seconds=elapsed,
            rows_per_second=len(rows) / elapsed if elapsed > 0 else 0,
            notes="100ms gaps with 5s timeout — gaps never approach timeout",
        )
        _report(result)
        assert len(rows) == 100


class TestTimeoutWithRetries:
    """Verify timeout exceptions are NOT retried (by design)."""

    def test_timeout_not_retried(self, perf_connect):
        """Timeout should fail immediately even with max_retries=5."""
        conn = perf_connect("very_slow_pat", timeout=1, max_retries=5)
        cur = conn.cursor()

        t0 = time.perf_counter()
        with pytest.raises(OperationalError, match="[Tt]imed out"):
            cur.execute(DEFAULT_QUERY)
        elapsed = time.perf_counter() - t0

        assert elapsed < 5, (
            f"Timeout took {elapsed:.1f}s — retries may have fired "
            f"(expected immediate failure)"
        )
        print(f"\nTimeout (no retry) elapsed: {elapsed:.2f}s")
