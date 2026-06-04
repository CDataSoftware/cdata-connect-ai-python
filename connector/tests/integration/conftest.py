"""
Integration test fixtures — mock server lifecycle, connection, and cursor.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

import cdata_connect_ai

from tests.conftest import _get_config, _is_localhost_url


# ---------------------------------------------------------------------------
# Server helpers
# ---------------------------------------------------------------------------

def _port_is_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _wait_for_server(host: str, port: int, health_url: str,
                     timeout_seconds: int = 30) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _port_is_open(host, port):
            try:
                resp = requests.get(health_url, timeout=2)
                if resp.status_code == 200:
                    return True
            except requests.RequestException:
                pass
        time.sleep(0.5)
    return False


# ---------------------------------------------------------------------------
# Mock server lifecycle (session-scoped)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _mock_server_process():
    """
    Start the mock server if targeting localhost and it's not already running.
    Yields the subprocess (or None). Stops it on teardown.
    """
    base_url, _, _, mock_port = _get_config()

    if not _is_localhost_url(base_url):
        yield None
        return

    if _port_is_open("localhost", mock_port):
        print(f"\n[conftest] Mock server already running on port {mock_port}")
        yield None
        return

    tests_dir = Path(__file__).parent.parent
    default_mock_dir = tests_dir.parent.parent / "connect-ai-mock"
    mock_dir = Path(os.environ.get("MOCK_SERVER_DIR", str(default_mock_dir)))

    if not mock_dir.exists():
        pytest.fail(
            f"Mock server directory not found at {mock_dir}. "
            f"Set MOCK_SERVER_DIR to the connect-ai-mock project path, "
            f"or start the mock server manually on port {mock_port}."
        )

    run_py = mock_dir / "run.py"
    if not run_py.exists():
        pytest.fail(f"Mock server entry point not found: {run_py}")

    # Ensure mock server dependencies are available in the current Python environment.
    # Only install if fastapi is missing — avoids overhead on repeated runs.
    try:
        import importlib
        importlib.import_module("fastapi")
    except ImportError:
        req_file = mock_dir / "requirements.txt"
        if req_file.exists():
            print(f"\n[conftest] Installing mock server dependencies from {req_file}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                pytest.fail(
                    f"Failed to install mock server dependencies:\n{result.stderr}"
                )
        else:
            pytest.fail(
                f"fastapi is not installed and no requirements.txt found at {mock_dir}. "
                f"Run: pip install fastapi uvicorn pydantic"
            )

    print(f"\n[conftest] Starting mock server on port {mock_port}...")

    env = os.environ.copy()
    env["MOCK_PORT"] = str(mock_port)

    process = subprocess.Popen(
        [sys.executable, str(run_py)],
        cwd=str(mock_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    health_url = f"http://localhost:{mock_port}/health"
    ready = _wait_for_server("localhost", mock_port, health_url, timeout_seconds=30)

    if not ready:
        process.terminate()
        stdout = process.stdout.read().decode(errors="replace") if process.stdout else ""
        stderr = process.stderr.read().decode(errors="replace") if process.stderr else ""
        pytest.fail(
            f"Mock server failed to start within 30 seconds.\n"
            f"stdout: {stdout}\nstderr: {stderr}"
        )

    print(f"[conftest] Mock server ready at http://localhost:{mock_port}")
    yield process

    print("\n[conftest] Stopping mock server...")
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


# ---------------------------------------------------------------------------
# Connectivity check (session-scoped, autouse)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _verify_connectivity(_mock_server_process):
    """Fail fast with a clear message if the target API is unreachable."""
    base_url, _, _, _ = _get_config()
    try:
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not _port_is_open(host, port):
            pytest.fail(
                f"Cannot connect to API at {base_url}. "
                f"Host {host}:{port} is not reachable."
            )
    except Exception as e:
        pytest.fail(f"Connectivity check failed: {e}")


# ---------------------------------------------------------------------------
# Connection fixture (function-scoped)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def con(_mock_server_process):
    """Function-scoped DB API 2.0 Connection driven by environment variables."""
    base_url, username, password, _ = _get_config()

    connection = cdata_connect_ai.connect(
        base_url=base_url,
        username=username,
        password=password,
    )

    yield connection

    if connection.is_open:
        try:
            connection.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Cursor fixture (function-scoped)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def cursor(con):
    """Function-scoped cursor from the session connection."""
    cur = con.cursor()
    yield cur
    try:
        cur.close()
    except Exception:
        pass
