"""
Slow integration tests — delay, timeout, and streaming-pause scenarios.

These tests exercise the mock server's delay/pause infrastructure and verify
that the connector handles slow responses, client-side timeouts, mid-stream
pauses, and truncated connections correctly.

Run by default.  Skip with:
    pytest tests/integration/ --skip-slow -v
"""

import pytest

import cdata_connect_ai
from cdata_connect_ai.exceptions import DataError, OperationalError

from tests.conftest import _get_config

pytestmark = pytest.mark.slow_integration

USERNAME = "test@example.com"


def _base_url():
    base_url, _, _, _ = _get_config()
    return base_url


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _connect(password, **overrides):
    """Create a connection to the mock server with a specific scenario PAT."""
    return cdata_connect_ai.connect(
        base_url=_base_url(),
        username=USERNAME,
        password=password,
        **overrides,
    )


# -----------------------------------------------------------------------
# 1. Delayed responses — server adds latency before first byte
# -----------------------------------------------------------------------

class TestDelayedResponses:
    """Use slow_pat (2 s) and very_slow_pat (5 s) delay scenarios."""

    def test_slow_response_succeeds_within_default_timeout(self):
        """2 s server delay should complete fine under 30 s default timeout."""
        conn = _connect("slow_pat")
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM [Salesforce1].[Salesforce].[Account]")
            rows = cur.fetchall()
            assert len(rows) > 0, "Expected rows from slow_pat scenario"
        finally:
            conn.close()

    def test_very_slow_response_succeeds_with_generous_timeout(self):
        """5 s server delay should complete with a 10 s client timeout."""
        conn = _connect("very_slow_pat", timeout=10)
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM [Salesforce1].[Salesforce].[Account]")
            rows = cur.fetchall()
            assert len(rows) > 0, "Expected rows from very_slow_pat scenario"
        finally:
            conn.close()

    def test_slow_response_times_out_with_short_timeout(self):
        """2 s server delay should trigger OperationalError with 1 s client timeout."""
        conn = _connect("slow_pat", timeout=1, max_retries=0)
        try:
            cur = conn.cursor()
            with pytest.raises(OperationalError, match="timed out"):
                cur.execute("SELECT * FROM [Salesforce1].[Salesforce].[Account]")
        finally:
            conn.close()

    def test_very_slow_times_out_with_short_timeout(self):
        """5 s server delay should trigger OperationalError with 2 s client timeout."""
        conn = _connect("very_slow_pat", timeout=2, max_retries=0)
        try:
            cur = conn.cursor()
            with pytest.raises(OperationalError, match="timed out"):
                cur.execute("SELECT * FROM [Salesforce1].[Salesforce].[Account]")
        finally:
            conn.close()


# -----------------------------------------------------------------------
# 2. Streaming with mid-stream pauses
# -----------------------------------------------------------------------

class TestStreamingPauses:
    """
    template_pat:      100 rows, pause [100ms, 500ms, 100ms] every 25 rows
    template_slow_pat: 50 rows, pause [1s, 2s, 1s] every 10 rows (~5 s total)
    """

    def test_template_streaming_with_pauses(self):
        """100 rows with short pauses should complete successfully."""
        conn = _connect("template_pat")
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM [TestDB].[dbo].[Users]")
            rows = cur.fetchall()
            assert len(rows) == 100
        finally:
            conn.close()

    def test_template_streaming_fetchone_iteration(self):
        """Fetch rows one at a time from a paused stream."""
        conn = _connect("template_pat")
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM [TestDB].[dbo].[Users]")
            count = 0
            while cur.fetchone() is not None:
                count += 1
            assert count == 100
        finally:
            conn.close()

    def test_template_streaming_fetchmany_batches(self):
        """Fetch in small batches across pause boundaries."""
        conn = _connect("template_pat")
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM [TestDB].[dbo].[Users]")
            total = 0
            while True:
                batch = cur.fetchmany(15)
                if not batch:
                    break
                total += len(batch)
            assert total == 100
        finally:
            conn.close()

    def test_slow_streaming_completes(self):
        """50 rows with ~5 s of pauses should complete within default timeout."""
        conn = _connect("template_slow_pat")
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM [TestDB].[dbo].[Users]")
            rows = cur.fetchall()
            assert len(rows) == 50
        finally:
            conn.close()


# -----------------------------------------------------------------------
# 3. Partial errors — rows then error mid-stream
# -----------------------------------------------------------------------

class TestPartialErrors:
    """
    partial_error_pat: 50 rows then error {"code": 504, "message": "Connection timeout after 50 rows"}
    partial_500_pat:   100 rows then error {"code": 500, "message": "...interrupted"}
    all_features_pat:  100 rows + pauses [200ms, 500ms] + error
    """

    def test_partial_error_returns_rows_before_error(self):
        """50 rows are returned; the trailing error is in JSON body not HTTP status."""
        conn = _connect("partial_error_pat")
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM [TestDB].[dbo].[Users]")
            rows = cur.fetchall()
            # Mock embeds error after rows; connector may get all 50 rows
            assert len(rows) >= 1, "Should receive at least some rows before error"
        finally:
            conn.close()

    def test_partial_500_returns_rows_before_error(self):
        """100 rows followed by an in-body server error."""
        conn = _connect("partial_500_pat")
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM [TestDB].[dbo].[Users]")
            rows = cur.fetchall()
            assert len(rows) >= 1
        finally:
            conn.close()

    def test_all_features_scenario(self):
        """100 rows + pauses + trailing error — rows should still be accessible."""
        conn = _connect("all_features_pat")
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM [TestDB].[dbo].[Users]")
            rows = cur.fetchall()
            assert len(rows) >= 1
        finally:
            conn.close()


# -----------------------------------------------------------------------
# 4. Truncated / crashed streams
# -----------------------------------------------------------------------

class TestTruncatedStream:
    """
    truncate_pat: server truncates JSON after 10 rows (malformed response)
    crash_pat:    server crashes mid-stream after 50 rows with pauses
    """

    def test_truncated_response_raises_error(self):
        """Malformed JSON from truncation should raise DataError or similar."""
        conn = _connect("truncate_pat")
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM [TestDB].[dbo].[Users]")
            # The stream is truncated mid-JSON, so iterating should eventually fail
            with pytest.raises((DataError, Exception)):
                cur.fetchall()
        finally:
            conn.close()

    def test_crash_mid_stream_raises_error(self):
        """Server crash after 50 rows should raise an error during fetch."""
        conn = _connect("crash_pat")
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM [TestDB].[dbo].[Users]")
            with pytest.raises((DataError, Exception)):
                cur.fetchall()
        finally:
            conn.close()


# -----------------------------------------------------------------------
# 5. Large template dataset
# -----------------------------------------------------------------------

class TestLargeTemplate:
    """template_large_pat: 1000 rows with small pauses every 200 rows."""

    def test_large_template_fetchall(self):
        """1000 rows with periodic pauses should stream correctly."""
        conn = _connect("template_large_pat")
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM [TestDB].[dbo].[Users]")
            rows = cur.fetchall()
            assert len(rows) == 1000
        finally:
            conn.close()
