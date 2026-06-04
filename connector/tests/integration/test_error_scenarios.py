"""Integration tests for error handling via mock scenarios."""

import pytest

import cdata_connect_ai
from cdata_connect_ai.exceptions import OperationalError, ProgrammingError

from tests.conftest import _get_config


class TestAuthErrors:
    def test_bad_credentials_produce_no_rows(self):
        """Use error_pat to trigger auth error scenario from mock server.

        The mock returns 200 with an error body and empty results.
        The connector sees no schema/rows, so fetch raises ProgrammingError.
        """
        base_url, _, _, _ = _get_config()
        conn = cdata_connect_ai.connect(
            base_url=base_url,
            username="test@example.com",
            password="error_pat",
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        with pytest.raises(ProgrammingError):
            cur.fetchall()
        if conn.is_open:
            conn.close()


class TestServerErrors:
    def test_server_error_produces_no_rows(self):
        """Use server_error_pat to trigger server error scenario.

        The mock returns 200 with an error body and empty results.
        """
        base_url, _, _, _ = _get_config()
        conn = cdata_connect_ai.connect(
            base_url=base_url,
            username="test@example.com",
            password="server_error_pat",
            max_retries=0,
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        with pytest.raises(ProgrammingError):
            cur.fetchall()
        if conn.is_open:
            conn.close()


class TestConnectionErrors:
    def test_connection_refused_raises_operational_error(self):
        """Connecting to a non-existent port raises OperationalError."""
        conn = cdata_connect_ai.connect(
            base_url="http://localhost:19999/api",
            username="user",
            password="pass",
            max_retries=0,
            timeout=2,
        )
        cur = conn.cursor()
        with pytest.raises(OperationalError):
            cur.execute("SELECT 1")
        if conn.is_open:
            conn.close()
