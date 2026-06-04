"""Unit tests for MockDataStore helper methods."""

import pytest

import sys
from pathlib import Path

# Add mock server root to path so we can import src.*
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.mock_store import MockDataStore


class TestSubstituteParameters:
    """Tests for _substitute_parameters — @param → literal value replacement."""

    def test_string_param_quoted(self):
        result = MockDataStore._substitute_parameters(
            "INSERT INTO t VALUES (@name)",
            {"@name": {"dataType": 5, "value": "Alice"}},
        )
        assert result == "INSERT INTO t VALUES ('Alice')"

    def test_int_param_unquoted(self):
        result = MockDataStore._substitute_parameters(
            "SELECT * FROM t WHERE id = @id",
            {"@id": {"dataType": 8, "value": 42}},
        )
        assert result == "SELECT * FROM t WHERE id = 42"

    def test_none_param_becomes_null(self):
        result = MockDataStore._substitute_parameters(
            "INSERT INTO t VALUES (@val)",
            {"@val": {"dataType": 5, "value": None}},
        )
        assert result == "INSERT INTO t VALUES (NULL)"

    def test_multiple_params(self):
        result = MockDataStore._substitute_parameters(
            "SELECT * FROM t WHERE a = @a AND b = @b",
            {
                "@a": {"dataType": 5, "value": "x"},
                "@b": {"dataType": 8, "value": 10},
            },
        )
        assert result == "SELECT * FROM t WHERE a = 'x' AND b = 10"

    def test_no_params_returns_query_unchanged(self):
        query = "SELECT 1"
        assert MockDataStore._substitute_parameters(query, None) == query
        assert MockDataStore._substitute_parameters(query, {}) == query

    def test_pydantic_model_param(self):
        """Should handle objects with a .value attribute (Pydantic models)."""

        class FakeParam:
            def __init__(self, value):
                self.value = value

        result = MockDataStore._substitute_parameters(
            "SELECT @x",
            {"@x": FakeParam("hello")},
        )
        assert result == "SELECT 'hello'"

    def test_special_chars_in_value(self):
        """Values with quotes should be included as-is (mock doesn't need escaping)."""
        result = MockDataStore._substitute_parameters(
            "INSERT INTO t VALUES (@name)",
            {"@name": {"dataType": 5, "value": "O'Reilly"}},
        )
        assert result == "INSERT INTO t VALUES ('O'Reilly')"


class TestExtractTableFromQuery:
    """Tests for two-part table name resolution fix."""

    def setup_method(self):
        # Create a minimal MockDataStore without loading real data
        self.store = MockDataStore.__new__(MockDataStore)

    def test_three_part_name(self):
        result = self.store._extract_table_from_query(
            "SELECT * FROM catalog.schema.table", None, None
        )
        assert result == "catalog.schema.table"

    def test_two_part_name_is_schema_table(self):
        """Two-part name should be treated as schema.table, not catalog.table."""
        result = self.store._extract_table_from_query(
            "SELECT * FROM public.users", None, None
        )
        # With no default_catalog, catalog portion is empty
        assert result == ".public.users"

    def test_two_part_name_with_default_catalog(self):
        """Two-part name with default_catalog should prepend catalog."""
        result = self.store._extract_table_from_query(
            "SELECT * FROM public.users", "MyCatalog", None
        )
        assert result == "MyCatalog.public.users"

    def test_two_part_name_does_not_duplicate_schema(self):
        """Regression: public.users must NOT become public.public.users."""
        result = self.store._extract_table_from_query(
            "SELECT * FROM public.users", None, None
        )
        assert "public.public" not in result

    def test_one_part_name_with_defaults(self):
        result = self.store._extract_table_from_query(
            "SELECT * FROM users", "MyCatalog", "public"
        )
        assert result == "MyCatalog.public.users"

    def test_bracketed_three_part_name(self):
        result = self.store._extract_table_from_query(
            "SELECT * FROM [Postgres].[public].[users]", None, None
        )
        assert result == "Postgres.public.users"


class TestExtractTableFromDml:
    """Tests for two-part table name resolution in DML statements."""

    def setup_method(self):
        self.store = MockDataStore.__new__(MockDataStore)

    def test_insert_two_part_name(self):
        result = self.store._extract_table_from_dml(
            "INSERT INTO public.users VALUES ('x')", None, None
        )
        assert result == ".public.users"

    def test_delete_two_part_name_with_catalog(self):
        result = self.store._extract_table_from_dml(
            "DELETE FROM public.users", "MyCatalog", None
        )
        assert result == "MyCatalog.public.users"

    def test_insert_two_part_does_not_duplicate(self):
        """Regression: schema.table must NOT become schema.schema.table."""
        result = self.store._extract_table_from_dml(
            "INSERT INTO public.booze VALUES ('x')", None, None
        )
        assert "public.public" not in result
