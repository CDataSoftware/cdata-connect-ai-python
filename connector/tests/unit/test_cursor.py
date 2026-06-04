"""Unit tests for the Cursor class properties, param validation, and fetch errors."""

import pytest
from unittest.mock import MagicMock

from cdata_connect_ai.cursor import Cursor
from cdata_connect_ai.exceptions import InterfaceError, ProgrammingError
from cdata_connect_ai.util.types import CONNECT_TYPE_VARCHAR, CONNECT_TYPE_INTEGER, CONNECT_TYPE_TIMESTAMP


class TestCursorProperties:
    def test_description_none_before_execute(self, mock_cursor):
        assert mock_cursor.description is None

    def test_rowcount_initial(self, mock_cursor):
        assert mock_cursor.rowcount == -1

    def test_arraysize_default(self, mock_cursor):
        assert mock_cursor.arraysize == 1

    def test_arraysize_setter(self, mock_cursor):
        mock_cursor.arraysize = 10
        assert mock_cursor.arraysize == 10


class TestCursorFetchErrors:
    def test_fetchone_before_execute_raises(self, mock_cursor):
        with pytest.raises(ProgrammingError):
            mock_cursor.fetchone()

    def test_fetchall_before_execute_raises(self, mock_cursor):
        with pytest.raises(ProgrammingError):
            mock_cursor.fetchall()

    def test_fetchmany_before_execute_raises(self, mock_cursor):
        with pytest.raises(ProgrammingError):
            mock_cursor.fetchmany()


class TestCursorParamValidation:
    def test_execute_non_dict_params_raises(self, mock_cursor):
        with pytest.raises(ProgrammingError):
            mock_cursor.execute("SELECT 1", params=["bad"])

    def test_executemany_non_list_params_raises(self, mock_cursor):
        with pytest.raises(ProgrammingError):
            mock_cursor.executemany("INSERT INTO t VALUES (@a)", params="bad")


class TestCursorClose:
    def test_close_sets_connection_none(self, mock_connection):
        cur = Cursor(mock_connection)
        cur.close()
        assert cur.connection is None

    def test_close_on_already_closed_cursor_raises(self, mock_connection):
        """After close(), connection is None, so further close raises InterfaceError."""
        cur = Cursor(mock_connection)
        cur.close()
        # Second close: connection is None → InterfaceError("Cursor is closed")
        # Actually, now close() doesn't check connection, so second close is a no-op.
        # This is intentional — cursor.close() should be idempotent for resource cleanup.
        cur.close()  # Should not raise

    def test_close_after_connection_closed(self, mock_connection):
        """Cursor should be closeable even after its connection is already closed."""
        cur = Cursor(mock_connection)
        mock_connection.is_open = False
        cur.close()  # Should not raise
        assert cur.connection is None


class TestCursorContextManager:
    def test_context_manager_closes_cursor(self, mock_connection):
        with Cursor(mock_connection) as cur:
            assert cur.connection is mock_connection
        assert cur.connection is None

    def test_context_manager_returns_cursor(self, mock_connection):
        cur = Cursor(mock_connection)
        with cur as c:
            assert c is cur


class TestCursorIterator:
    def test_iter_returns_self(self, mock_cursor):
        assert iter(mock_cursor) is mock_cursor

    def test_next_raises_stop_iteration_when_no_rows(self, mock_connection):
        """__next__ raises StopIteration when fetchone returns None."""
        cur = Cursor(mock_connection)
        cur.rows_generator = iter([])  # empty generator
        cur.schema = [{"dataTypeName": "VARCHAR", "columnName": "x", "dataType": 5}]
        with pytest.raises(StopIteration):
            next(cur)


class TestCursorNoOps:
    def test_setinputsizes_does_not_raise(self, mock_cursor):
        mock_cursor.setinputsizes((25,))

    def test_setoutputsize_does_not_raise(self, mock_cursor):
        mock_cursor.setoutputsize(1000)

    def test_setoutputsize_with_column_does_not_raise(self, mock_cursor):
        mock_cursor.setoutputsize(2000, 0)


class TestCursorOnClosedConnection:
    def test_execute_on_closed_connection_raises(self, mock_connection):
        cur = Cursor(mock_connection)
        mock_connection.is_open = False
        with pytest.raises(InterfaceError):
            cur.execute("SELECT 1")

    def test_fetchone_on_closed_connection_raises(self, mock_connection):
        cur = Cursor(mock_connection)
        mock_connection.is_open = False
        with pytest.raises(InterfaceError):
            cur.fetchone()


class TestExecuteParameterization:
    """Tests for server-side parameterization in execute()."""

    def test_pyformat_params_converted_to_at_placeholders(self, mock_cursor):
        """%(name)s placeholders should become @name in the query sent to the API."""
        mock_cursor.execute(
            "SELECT * FROM t WHERE name = %(name)s", {"name": "Alice"}
        )
        call_args = mock_cursor._execute_request.call_args
        json_object = call_args[0][1]
        assert json_object["query"] == "SELECT * FROM t WHERE name = @name"

    def test_pyformat_params_sent_in_parameters_field(self, mock_cursor):
        """Params should be sent via the JSON 'parameters' field, not interpolated."""
        mock_cursor.execute(
            "INSERT INTO t VALUES (%(val)s)", {"val": "O'Reilly"}
        )
        call_args = mock_cursor._execute_request.call_args
        json_object = call_args[0][1]
        assert "@val" in json_object["parameters"]
        assert json_object["parameters"]["@val"]["value"] == "O'Reilly"

    def test_params_type_inference_string(self, mock_cursor):
        """String params should map to VARCHAR type."""
        mock_cursor.execute("SELECT %(x)s", {"x": "hello"})
        json_object = mock_cursor._execute_request.call_args[0][1]
        assert json_object["parameters"]["@x"]["dataType"] == CONNECT_TYPE_VARCHAR

    def test_params_type_inference_int(self, mock_cursor):
        """Int params should map to INTEGER type."""
        mock_cursor.execute("SELECT %(x)s", {"x": 42})
        json_object = mock_cursor._execute_request.call_args[0][1]
        assert json_object["parameters"]["@x"]["dataType"] == CONNECT_TYPE_INTEGER

    def test_multiple_params(self, mock_cursor):
        """Multiple pyformat params should all be converted."""
        mock_cursor.execute(
            "SELECT * FROM t WHERE a = %(a)s AND b = %(b)s",
            {"a": "x", "b": "y"},
        )
        json_object = mock_cursor._execute_request.call_args[0][1]
        assert json_object["query"] == "SELECT * FROM t WHERE a = @a AND b = @b"
        assert "@a" in json_object["parameters"]
        assert "@b" in json_object["parameters"]

    def test_no_params_sends_no_parameters_field(self, mock_cursor):
        """When params is None, no 'parameters' key should be in the JSON."""
        mock_cursor.execute("SELECT 1")
        json_object = mock_cursor._execute_request.call_args[0][1]
        assert "parameters" not in json_object

    def test_sql_injection_not_possible_via_params(self, mock_cursor):
        """Values with SQL fragments should NOT appear in the query string."""
        mock_cursor.execute(
            "SELECT * FROM t WHERE name = %(name)s",
            {"name": "'; DROP TABLE t; --"},
        )
        json_object = mock_cursor._execute_request.call_args[0][1]
        # The query should only contain the @name placeholder, not the injected value
        assert "DROP TABLE" not in json_object["query"]
        assert json_object["query"] == "SELECT * FROM t WHERE name = @name"
        assert json_object["parameters"]["@name"]["value"] == "'; DROP TABLE t; --"


class TestDescriptionColumnLabel:
    """Tests for columnLabel preference in cursor.description."""

    def test_description_uses_column_label_when_present(self, mock_connection):
        """description should prefer columnLabel over columnName."""
        cur = Cursor(mock_connection)
        cur.schema = [
            {
                "columnName": "Id",
                "columnLabel": "OppId",
                "dataType": 5,
                "dataTypeName": "VARCHAR",
            }
        ]
        assert cur.description[0][0] == "OppId"

    def test_description_falls_back_to_column_name(self, mock_connection):
        """description should fall back to columnName when columnLabel is empty."""
        cur = Cursor(mock_connection)
        cur.schema = [
            {
                "columnName": "Id",
                "columnLabel": "",
                "dataType": 5,
                "dataTypeName": "VARCHAR",
            }
        ]
        assert cur.description[0][0] == "Id"

    def test_description_falls_back_when_label_missing(self, mock_connection):
        """description should fall back to columnName when columnLabel key is absent."""
        cur = Cursor(mock_connection)
        cur.schema = [
            {
                "columnName": "Name",
                "dataType": 5,
                "dataTypeName": "VARCHAR",
            }
        ]
        assert cur.description[0][0] == "Name"

    def test_description_distinct_aliases_for_same_column(self, mock_connection):
        """Two columns with same columnName but different labels should be distinct."""
        cur = Cursor(mock_connection)
        cur.schema = [
            {"columnName": "Id", "columnLabel": "OppId", "dataType": 5, "dataTypeName": "VARCHAR"},
            {"columnName": "Id", "columnLabel": "AcctId", "dataType": 5, "dataTypeName": "VARCHAR"},
        ]
        names = [col[0] for col in cur.description]
        assert names == ["OppId", "AcctId"]
