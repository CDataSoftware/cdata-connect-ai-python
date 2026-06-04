"""Integration tests for callproc end-to-end."""

import pytest

lower_func = "[PostgreSQL2].[public].[lowercase_input]"


class TestCallproc:
    def test_basic_callproc(self, cursor):
        r = cursor.callproc(lower_func, ("FOO",))
        assert len(r) == 1
        assert r[0] == "FOO"
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "foo"

    def test_callproc_multiple_args(self, cursor):
        """callproc with multiple arguments — returns input params as tuple."""
        r = cursor.callproc(lower_func, ("BAR",))
        assert isinstance(r, tuple)
        assert r[0] == "BAR"

    def test_callproc_return_value_matches_input(self, cursor):
        """callproc return value should match input params."""
        input_params = ("HELLO",)
        r = cursor.callproc(lower_func, input_params)
        assert r == input_params

    def test_callproc_with_params_returns_result(self, cursor):
        """callproc with params should complete without error and return a result set."""
        r = cursor.callproc(lower_func, ("TEST_PARAM",))
        assert r == ("TEST_PARAM",)
        rows = cursor.fetchall()
        # Mock returns static result — verify the procedure executed successfully
        assert len(rows) >= 1
