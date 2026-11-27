"""Integration tests for workspace (workspaceId) and virtual schema routing."""

import pytest

import cdata_connect_ai

from tests.conftest import _get_config

table_prefix = "[PostgreSQL2].[public].dbapi20test_"
lower_func = "[PostgreSQL2].[public].[lowercase_input]"
WORKSPACE_ID = "2f5ae96c-b558-4c7b-a3fb-92c9dd5a9d10"


@pytest.fixture
def connect(_mock_server_process):
    """Open connections against the configured server; close them on teardown."""
    base_url, username, password, _ = _get_config()
    opened = []

    def _connect(**kwargs):
        conn = cdata_connect_ai.connect(
            base_url=base_url, username=username, password=password, **kwargs
        )
        opened.append(conn)
        return conn

    yield _connect

    for conn in opened:
        if conn.is_open:
            conn.close()


class TestWorkspaceRouting:
    def test_execute_with_workspace_id(self, connect):
        cur = connect(workspaceId=WORKSPACE_ID).cursor()
        cur.execute(f"delete from {table_prefix}booze")
        cur.execute(f"insert into {table_prefix}booze values ('Stout')")
        cur.execute(f"select name from {table_prefix}booze")
        assert [r[0] for r in cur.fetchall()] == ["Stout"]

    def test_executemany_with_workspace_id(self, connect):
        cur = connect(workspaceId=WORKSPACE_ID).cursor()
        cur.execute(f"delete from {table_prefix}booze")
        cur.executemany(
            f"insert into {table_prefix}booze values (@beer)",
            [{"@beer": "IPA"}, {"@beer": "Pilsner"}],
        )
        cur.execute(f"select name from {table_prefix}booze")
        assert sorted(r[0] for r in cur.fetchall()) == ["IPA", "Pilsner"]

    def test_callproc_with_workspace_id(self, connect):
        cur = connect(workspaceId=WORKSPACE_ID).cursor()
        assert cur.callproc(lower_func, ("FOO",)) == ("FOO",)

    def test_workspace_id_and_virtual_schema(self, connect):
        cur = connect(workspaceId=WORKSPACE_ID, virtualSchema="SalesData").cursor()
        cur.execute(f"select name from {table_prefix}booze")
        cur.fetchall()

    def test_virtual_schema_without_workspace_id(self, connect):
        cur = connect(virtualSchema="SalesData").cursor()
        cur.execute(f"select name from {table_prefix}booze")
        cur.fetchall()

    def test_deprecated_workspace_alias_still_works(self, connect):
        with pytest.warns(DeprecationWarning):
            conn = connect(workspace="SalesData")
        cur = conn.cursor()
        cur.execute(f"select name from {table_prefix}booze")
        cur.fetchall()
