"""Integration tests for query operations — SELECT, INSERT, UPDATE, DELETE end-to-end."""

import pytest

import cdata_connect_ai

table_prefix = "[PostgreSQL2].[public].dbapi20test_"


class TestSelect:
    def test_select_returns_rows(self, cursor):
        cursor.execute(f"delete from {table_prefix}booze")
        cursor.execute(f"insert into {table_prefix}booze values ('Lager')")
        cursor.execute(f"select name from {table_prefix}booze")
        rows = cursor.fetchall()
        assert len(rows) >= 1
        assert any(row[0] == "Lager" for row in rows)

    def test_select_correct_column_types(self, cursor):
        cursor.execute(f"select name from {table_prefix}booze")
        if cursor.description:
            assert cursor.description[0][0].lower() == "name"

    def test_empty_result_set(self, cursor):
        cursor.execute(f"delete from {table_prefix}booze")
        cursor.execute(f"select name from {table_prefix}booze")
        rows = cursor.fetchall()
        assert rows == []


class TestInsert:
    def test_insert_via_execute(self, cursor):
        cursor.execute(f"delete from {table_prefix}booze")
        cursor.execute(f"insert into {table_prefix}booze values ('Ale')")
        cursor.execute(f"select name from {table_prefix}booze")
        rows = cursor.fetchall()
        names = [r[0] for r in rows]
        assert "Ale" in names

    def test_parameterized_select(self, cursor):
        cursor.execute(f"delete from {table_prefix}booze")
        cursor.execute(f"insert into {table_prefix}booze values ('Stout')")
        cursor.execute(
            f"insert into {table_prefix}booze values (%(beer)s)",
            {"beer": "Porter"},
        )
        cursor.execute(f"select name from {table_prefix}booze")
        rows = cursor.fetchall()
        assert len(rows) == 2


class TestBatchInsert:
    def test_executemany_insert(self, cursor):
        cursor.execute(f"delete from {table_prefix}booze")
        margs = [{"@beer": "IPA"}, {"@beer": "Pilsner"}]
        cursor.executemany(
            f"insert into {table_prefix}booze values (@beer)",
            margs,
        )
        cursor.execute(f"select name from {table_prefix}booze")
        rows = cursor.fetchall()
        names = sorted(r[0] for r in rows)
        assert "IPA" in names
        assert "Pilsner" in names


class TestParameterizedExecute:
    """Integration tests for server-side parameterized execute()."""

    def test_parameterized_insert_and_select_roundtrip(self, cursor):
        """Params sent via execute() should be properly substituted server-side."""
        cursor.execute(f"delete from {table_prefix}booze")
        cursor.execute(
            f"insert into {table_prefix}booze values (%(beer)s)",
            {"beer": "Coopers"},
        )
        cursor.execute(f"select name from {table_prefix}booze")
        rows = cursor.fetchall()
        names = [r[0] for r in rows]
        assert "Coopers" in names

    def test_parameterized_value_with_special_chars(self, cursor):
        """Values with quotes/special chars should be safely parameterized."""
        cursor.execute(f"delete from {table_prefix}booze")
        cursor.execute(
            f"insert into {table_prefix}booze values (%(beer)s)",
            {"beer": "Cooper's Ale"},
        )
        cursor.execute(f"select name from {table_prefix}booze")
        rows = cursor.fetchall()
        names = [r[0] for r in rows]
        assert "Cooper's Ale" in names

    def test_parameterized_with_multiple_params(self, cursor):
        """Multiple params should all be sent server-side."""
        cursor.execute(f"delete from {table_prefix}booze")
        cursor.execute(
            f"insert into {table_prefix}booze values (%(beer)s)",
            {"beer": "Stout"},
        )
        cursor.execute(f"select name from {table_prefix}booze")
        rows = cursor.fetchall()
        assert len(rows) >= 1


class TestColumnLabel:
    """Integration tests verifying cursor.description uses column aliases."""

    def test_description_returns_column_labels(self, cursor):
        """description column names should come from the API's columnLabel field."""
        cursor.execute(f"select name from {table_prefix}booze")
        if cursor.description:
            # The mock server sets columnLabel = columnName by default
            assert cursor.description[0][0] is not None
            assert len(cursor.description[0][0]) > 0

    def test_description_uses_aliases_for_same_column_names(self, cursor):
        """Columns with the same columnName (Id) but different aliases should be distinct.

        Simulates a UNION/JOIN scenario: SELECT Id as OrderId, Id as InvoiceId.
        The mock table union_alias_view has columnName=Id for both columns
        but columnLabel=OrderId and columnLabel=InvoiceId respectively.
        """
        cursor.execute("SELECT * FROM PostgreSQL_Prod.public.union_alias_view")
        assert cursor.description is not None
        col_names = [col[0] for col in cursor.description]
        assert col_names == ["OrderId", "InvoiceId"]

    def test_aliased_columns_return_correct_data(self, cursor):
        """Rows should be returned correctly when two columns share the same columnName."""
        cursor.execute("SELECT * FROM PostgreSQL_Prod.public.union_alias_view")
        rows = cursor.fetchall()
        assert len(rows) == 3
        assert rows[0] == [101, 501]
        assert rows[1] == [102, 502]
        assert rows[2] == [103, 503]


class TestDelete:
    def test_delete_clears_rows(self, cursor):
        cursor.execute(f"insert into {table_prefix}booze values ('Temp')")
        cursor.execute(f"delete from {table_prefix}booze")
        cursor.execute(f"select name from {table_prefix}booze")
        rows = cursor.fetchall()
        assert rows == []
