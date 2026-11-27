"""Unit tests for module-level attributes and the connect() factory."""

import pytest

import cdata_connect_ai


class TestModuleAttributes:
    def test_apilevel(self):
        assert cdata_connect_ai.apilevel == "2.0"

    def test_threadsafety(self):
        assert cdata_connect_ai.threadsafety == 1

    def test_paramstyle(self):
        assert cdata_connect_ai.paramstyle == "pyformat"

    def test_string_type_exists(self):
        assert hasattr(cdata_connect_ai, "STRING")

    def test_binary_type_exists(self):
        assert hasattr(cdata_connect_ai, "BINARY")

    def test_number_type_exists(self):
        assert hasattr(cdata_connect_ai, "NUMBER")

    def test_datetime_type_exists(self):
        assert hasattr(cdata_connect_ai, "DATETIME")

    def test_rowid_type_exists(self):
        assert hasattr(cdata_connect_ai, "ROWID")


class TestConnect:
    def test_connect_with_valid_params(self):
        conn = cdata_connect_ai.connect(
            base_url="http://localhost/api",
            username="user",
            password="pass",
        )
        assert conn is not None
        assert conn.is_open is True
        conn.close()

    def test_connect_missing_params_raises(self):
        with pytest.raises(cdata_connect_ai.InterfaceError):
            cdata_connect_ai.connect()

    def test_connect_missing_password_raises(self):
        with pytest.raises(cdata_connect_ai.InterfaceError):
            cdata_connect_ai.connect(base_url="http://localhost/api", username="user")

    def test_connect_with_workspace(self):
        with pytest.warns(DeprecationWarning):
            conn = cdata_connect_ai.connect(
                base_url="http://localhost/api",
                username="user",
                password="pass",
                workspace="my_workspace",
            )
        assert conn.workspace == "my_workspace"
        assert conn.virtual_schema == "my_workspace"
        conn.close()

    def test_connect_with_workspace_id_and_virtual_schema(self):
        conn = cdata_connect_ai.connect(
            base_url="http://localhost/api",
            username="user",
            password="pass",
            workspaceId="2f5ae96c-b558-4c7b-a3fb-92c9dd5a9d10",
            virtualSchema="SalesData",
        )
        assert conn.workspace_id == "2f5ae96c-b558-4c7b-a3fb-92c9dd5a9d10"
        assert conn.virtual_schema == "SalesData"
        conn.close()

    def test_connect_workspace_alias_warning_points_at_caller(self):
        with pytest.warns(DeprecationWarning) as record:
            cdata_connect_ai.connect(
                base_url="http://localhost/api",
                username="user",
                password="pass",
                workspace="my_workspace",
            )
        assert record[0].filename == __file__

    def test_connect_with_config_path_missing_file(self):
        from cdata_connect_ai.exceptions import ConfigurationError
        with pytest.raises(ConfigurationError):
            cdata_connect_ai.connect(config_path="/nonexistent/config.conf")
