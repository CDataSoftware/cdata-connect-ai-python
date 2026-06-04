"""
Performance test fixtures — scenario-specific connections and timing helpers.

All performance tests require the mock server (auto-started by the
session-scoped _mock_server_process fixture in tests/integration/conftest.py).

Marker registration and --run-soak option are in the root conftest.py.
"""

import time
from dataclasses import dataclass, field

import pytest

import cdata_connect_ai
from tests.conftest import _get_config

# Re-export the mock server fixtures so they're available when running
# pytest tests/performance/ directly (without tests/integration/ on the path).
from tests.integration.conftest import (  # noqa: F401
    _mock_server_process,
    _verify_connectivity,
)


# ---------------------------------------------------------------------------
# Timing helper
# ---------------------------------------------------------------------------

@dataclass
class PerfResult:
    """Captures timing and row counts for a performance test."""
    scenario: str = ""
    rows_expected: int = 0
    rows_received: int = 0
    elapsed_seconds: float = 0.0
    rows_per_second: float = 0.0
    peak_memory_kb: float = 0.0
    notes: str = ""
    per_fetch_times: list = field(default_factory=list)

    def summarize(self) -> str:
        lines = [
            f"Scenario:    {self.scenario}",
            f"Rows:        {self.rows_received}/{self.rows_expected}",
            f"Elapsed:     {self.elapsed_seconds:.3f}s",
            f"Throughput:  {self.rows_per_second:.1f} rows/sec",
        ]
        if self.peak_memory_kb:
            lines.append(f"Peak memory: {self.peak_memory_kb:.1f} KB")
        if self.notes:
            lines.append(f"Notes:       {self.notes}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Connection factory for perf scenarios
# ---------------------------------------------------------------------------

def _perf_connect(pat: str, timeout: int = 300, max_retries: int = 0):
    """Create a connection using a specific PAT (scenario selector)."""
    base_url, username, _, _ = _get_config()
    return cdata_connect_ai.connect(
        base_url=base_url,
        username=username,
        password=pat,
        timeout=timeout,
        max_retries=max_retries,
    )


@pytest.fixture
def perf_connect():
    """Factory fixture — call with a PAT to get a connection for that scenario."""
    connections = []

    def _factory(pat: str, timeout: int = 300, max_retries: int = 0):
        conn = _perf_connect(pat, timeout=timeout, max_retries=max_retries)
        connections.append(conn)
        return conn

    yield _factory

    for conn in connections:
        if conn.is_open:
            try:
                conn.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Convenience fixtures for common scenarios
# ---------------------------------------------------------------------------

@pytest.fixture
def conn_100(perf_connect):
    return perf_connect("perf_100_pat")


@pytest.fixture
def conn_1k(perf_connect):
    return perf_connect("perf_1k_pat")


@pytest.fixture
def conn_10k(perf_connect):
    return perf_connect("perf_10k_pat")


@pytest.fixture
def conn_50k(perf_connect):
    return perf_connect("perf_50k_pat")


@pytest.fixture
def conn_500k(perf_connect):
    return perf_connect("perf_500k_pat")


@pytest.fixture
def conn_mixed_types(perf_connect):
    return perf_connect("perf_types_pat")


@pytest.fixture
def conn_jittery(perf_connect):
    return perf_connect("perf_jittery_pat")


@pytest.fixture
def soak_progress_interval(request):
    """Progress report interval in seconds (from --soak-progress, default 30)."""
    return request.config.getoption("--soak-progress", default=30)
