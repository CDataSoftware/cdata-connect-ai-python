"""Integration tests for streaming and large dataset scenarios."""

import pytest

import cdata_connect_ai

from tests.conftest import _get_config


class TestLargeDataset:
    @pytest.fixture
    def large_cursor(self):
        """Connection using large_pat for the large dataset scenario."""
        base_url, _, _, _ = _get_config()
        conn = cdata_connect_ai.connect(
            base_url=base_url,
            username="test@example.com",
            password="large_pat",
        )
        cur = conn.cursor()
        yield cur
        if conn.is_open:
            conn.close()

    def test_fetch_large_dataset(self, large_cursor):
        """Fetch a large dataset scenario — the mock returns 100+ rows."""
        large_cursor.execute(
            "select * from [Salesforce1].[Salesforce].[Contact]"
        )
        rows = large_cursor.fetchall()
        assert len(rows) >= 100, (
            f"Expected at least 100 rows for large dataset, got {len(rows)}"
        )

    def test_streaming_fetchmany(self, large_cursor):
        """Streaming with fetchmany in batches."""
        large_cursor.execute(
            "select * from [Salesforce1].[Salesforce].[Contact]"
        )
        all_rows = []
        while True:
            batch = large_cursor.fetchmany(20)
            if not batch:
                break
            all_rows.extend(batch)
        assert len(all_rows) >= 100


class TestDataTypes:
    @pytest.fixture
    def datatypes_cursor(self):
        """Connection using datatypes_pat for the datatypes scenario."""
        base_url, _, _, _ = _get_config()
        conn = cdata_connect_ai.connect(
            base_url=base_url,
            username="test@example.com",
            password="datatypes_pat",
        )
        cur = conn.cursor()
        yield cur
        if conn.is_open:
            conn.close()

    def test_various_sql_types(self, datatypes_cursor):
        """Verify data type conversion with the datatypes scenario."""
        datatypes_cursor.execute(
            "select * from [TestDB].[dbo].[Products]"
        )
        rows = datatypes_cursor.fetchall()
        assert len(rows) >= 1
        assert datatypes_cursor.description is not None
        assert len(datatypes_cursor.description) > 0
