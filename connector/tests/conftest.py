"""
Root conftest.py — shared configuration helpers and marker registration.

Environment variables:
  CDATA_BASE_URL    Base URL of the Connect API.
                    Defaults to http://localhost:8080/api
                    Set to https://cloud.cdata.com/api to use the live API.
  CDATA_USERNAME    Username for authentication. Defaults to test@example.com
  CDATA_PASSWORD    Password / PAT for authentication. Defaults to any_token

  MOCK_SERVER_DIR   Path to the connect-ai-mock project root.
                    Only used when CDATA_BASE_URL points to localhost and
                    the mock server is not already running. Defaults to
                    ../connect-ai-mock (relative to connector/).

  MOCK_PORT         Port for the mock server. Defaults to 8080.

  SKIP_LIVE_TESTS   If set to "1", "true", or "yes", tests marked
                    live_api are skipped. Defaults to "1" when targeting mock.

Test marks:
  unit              Pure unit tests — no server, no network.
  integration       Integration tests — require the mock (or live) server.
  live_api          Test requires true stateful DML (INSERT+SELECT round-trip).
                    Automatically skipped when running against mock.
"""

import os

import pytest

# ---------------------------------------------------------------------------
# Configuration helpers (shared by integration fixtures)
# ---------------------------------------------------------------------------

DEFAULT_MOCK_PORT = 8080
DEFAULT_BASE_URL = f"http://localhost:{DEFAULT_MOCK_PORT}/api"
DEFAULT_USERNAME = "test@example.com"
DEFAULT_PASSWORD = "any_token"

def _get_config():
    base_url = os.environ.get("CDATA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    username = os.environ.get("CDATA_USERNAME", DEFAULT_USERNAME)
    password = os.environ.get("CDATA_PASSWORD", DEFAULT_PASSWORD)
    mock_port = int(os.environ.get("MOCK_PORT", str(DEFAULT_MOCK_PORT)))
    return base_url, username, password, mock_port


def _is_localhost_url(base_url: str) -> bool:
    return "localhost" in base_url or "127.0.0.1" in base_url


def _is_skip_live_tests() -> bool:
    val = os.environ.get("SKIP_LIVE_TESTS", "").lower()
    return val in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Marker registration and skip logic
# ---------------------------------------------------------------------------

def pytest_addoption(parser):
    parser.addoption(
        "--skip-slow",
        action="store_true",
        default=False,
        help="Skip slow integration tests (delay/timeout/streaming scenarios)",
    )
    parser.addoption(
        "--run-soak",
        action="store_true",
        default=False,
        help="Run soak tests (long-running, 10+ minutes)",
    )
    parser.addoption(
        "--soak-progress",
        type=int,
        default=30,
        help="Soak test progress report interval in seconds (default: 30)",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "unit: marks pure unit tests (no server required)"
    )
    config.addinivalue_line(
        "markers",
        "integration: marks integration tests (require mock or live server)"
    )
    config.addinivalue_line(
        "markers",
        "slow_integration: marks slow integration tests (delay/timeout/streaming). "
        "Skipped by default — pass --run-slow to include."
    )
    config.addinivalue_line(
        "markers",
        "live_api: marks tests requiring a live stateful API "
        "(INSERT+SELECT round-trip). Skipped when running against mock."
    )
    config.addinivalue_line(
        "markers",
        "performance: marks performance / benchmark tests (require mock server)"
    )
    config.addinivalue_line(
        "markers",
        "soak: marks long-running soak tests (10+ minutes). "
        "Skipped by default — pass --run-soak to include."
    )


def pytest_collection_modifyitems(config, items):
    base_url, _, _, _ = _get_config()
    using_mock = _is_localhost_url(base_url)
    force_skip = _is_skip_live_tests()

    # --- Skip slow_integration when --skip-slow is passed ---
    if config.getoption("--skip-slow", default=False):
        skip_slow = pytest.mark.skip(
            reason="Slow integration test — skipped via --skip-slow"
        )
        for item in items:
            if item.get_closest_marker("slow_integration"):
                item.add_marker(skip_slow)

    # --- Skip soak when --run-soak is not passed ---
    if not config.getoption("--run-soak", default=False):
        skip_soak = pytest.mark.skip(
            reason="Soak test — pass --run-soak to run"
        )
        for item in items:
            if item.get_closest_marker("soak"):
                item.add_marker(skip_soak)

    # --- Skip live_api when targeting mock ---
    if not (using_mock or force_skip):
        return

    skip_reason = (
        "Requires live stateful API (INSERT+SELECT round-trip). "
        "Set CDATA_BASE_URL to the live API and SKIP_LIVE_TESTS=0 to enable."
    )
    skip_marker = pytest.mark.skip(reason=skip_reason)

    for item in items:
        if item.get_closest_marker("live_api"):
            item.add_marker(skip_marker)
