"""
Unit test fixtures — no server, no network. Uses unittest.mock for HTTP mocking.
"""

import pytest
from unittest.mock import MagicMock, patch

from cdata_connect_ai.connection import Connection
from cdata_connect_ai.cursor import Cursor


@pytest.fixture
def mock_connection():
    """A Connection object with mocked internals — no real HTTP calls."""
    with patch.object(Connection, "__init__", lambda self, **kw: None):
        conn = Connection.__new__(Connection)

    conn.is_open = True
    conn.base_url = "http://mock-server/api"
    conn.auth = ("user", "pass")
    conn.workspace = None
    conn.timeout = 30
    conn.max_retries = 3
    conn.retry_delay = 1.0
    return conn


@pytest.fixture
def mock_cursor(mock_connection):
    """A Cursor with a mocked _execute_request — no real HTTP calls."""
    cur = Cursor(mock_connection)
    cur._execute_request = MagicMock()
    return cur
