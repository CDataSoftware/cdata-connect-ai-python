"""Unit tests for the Connection class lifecycle and configuration."""

import warnings
from unittest.mock import patch, MagicMock

import pytest

from cdata_connect_ai.connection import Connection, DEFAULT_BASE_URL
from cdata_connect_ai.cursor import Cursor
from cdata_connect_ai.exceptions import (
    ConfigurationError,
    InterfaceError,
    Warning as CDataWarning,
    Error,
    DatabaseError,
    OperationalError,
    IntegrityError,
    InternalError,
    ProgrammingError,
    NotSupportedError,
)


class TestConnectionInit:
    def test_init_with_base_url_username_password(self):
        conn = Connection(
            base_url="http://localhost/api",
            username="user",
            password="pass",
        )
        assert conn.base_url == "http://localhost/api"
        assert conn.auth == ("user", "pass")
        assert conn.is_open is True

    def test_init_strips_trailing_slash(self):
        conn = Connection(
            base_url="http://localhost/api/",
            username="user",
            password="pass",
        )
        assert conn.base_url == "http://localhost/api"

    def test_init_default_base_url(self):
        conn = Connection(username="user", password="pass")
        assert conn.base_url == DEFAULT_BASE_URL

    def test_init_with_config_missing_base_url_uses_default(self):
        mock_config = MagicMock()
        mock_config.get_string.side_effect = lambda key: {
            "cdata_api_db.username": "config_user",
            "cdata_api_db.password": "config_pass",
        }[key]

        with patch("cdata_connect_ai.connection.ConfigFactory.parse_file", return_value=mock_config):
            conn = Connection(config_path="/fake/config.conf")
            assert conn.base_url == DEFAULT_BASE_URL
            assert conn.auth == ("config_user", "config_pass")

    def test_init_missing_params_raises_configuration_error(self):
        with pytest.raises(ConfigurationError):
            Connection()

    def test_init_missing_password_raises_configuration_error(self):
        with pytest.raises(ConfigurationError):
            Connection(base_url="http://localhost/api", username="user")

    def test_init_with_config_path(self):
        mock_config = MagicMock()
        mock_config.get_string.side_effect = lambda key: {
            "cdata_api_db.base_url": "http://config-server/api",
            "cdata_api_db.username": "config_user",
            "cdata_api_db.password": "config_pass",
        }[key]

        with patch("cdata_connect_ai.connection.ConfigFactory.parse_file", return_value=mock_config):
            conn = Connection(config_path="/fake/config.conf")
            assert conn.base_url == "http://config-server/api"
            assert conn.auth == ("config_user", "config_pass")

    def test_init_with_nonexistent_config_path_raises(self):
        with pytest.raises(ConfigurationError):
            Connection(config_path="/nonexistent/config.conf")

    def test_workspace_default_none(self):
        conn = Connection(
            base_url="http://localhost/api",
            username="user",
            password="pass",
        )
        assert conn.workspace_id is None
        assert conn.virtual_schema is None
        assert conn.workspace is None

    def test_timeout_default(self):
        conn = Connection(
            base_url="http://localhost/api",
            username="user",
            password="pass",
        )
        assert conn.timeout == 90

    def test_custom_retry_settings(self):
        conn = Connection(
            base_url="http://localhost/api",
            username="user",
            password="pass",
            max_retries=5,
            retry_delay=2.0,
        )
        assert conn.max_retries == 5
        assert conn.retry_delay == 2.0


class TestConnectionLifecycle:
    def test_close_sets_is_open_false(self):
        conn = Connection(
            base_url="http://localhost/api",
            username="user",
            password="pass",
        )
        conn.close()
        assert conn.is_open is False

    def test_close_twice_raises_interface_error(self):
        conn = Connection(
            base_url="http://localhost/api",
            username="user",
            password="pass",
        )
        conn.close()
        with pytest.raises(InterfaceError):
            conn.close()

    def test_commit_on_closed_connection_raises(self):
        conn = Connection(
            base_url="http://localhost/api",
            username="user",
            password="pass",
        )
        conn.close()
        with pytest.raises(InterfaceError):
            conn.commit()

    def test_commit_on_open_connection_succeeds(self):
        conn = Connection(
            base_url="http://localhost/api",
            username="user",
            password="pass",
        )
        conn.commit()  # No-op, should not raise

    def test_rollback_on_closed_connection_raises(self):
        conn = Connection(
            base_url="http://localhost/api",
            username="user",
            password="pass",
        )
        conn.close()
        with pytest.raises(InterfaceError):
            conn.rollback()

    def test_rollback_on_open_connection_succeeds(self):
        conn = Connection(
            base_url="http://localhost/api",
            username="user",
            password="pass",
        )
        conn.rollback()  # No-op, should not raise

    def test_cursor_returns_cursor_instance(self):
        conn = Connection(
            base_url="http://localhost/api",
            username="user",
            password="pass",
        )
        cur = conn.cursor()
        assert isinstance(cur, Cursor)

    def test_cursor_on_closed_connection_raises(self):
        conn = Connection(
            base_url="http://localhost/api",
            username="user",
            password="pass",
        )
        conn.close()
        with pytest.raises(InterfaceError):
            conn.cursor()


class TestConnectionContextManager:
    def test_context_manager_closes_on_exit(self):
        conn = Connection(
            base_url="http://localhost/api",
            username="user",
            password="pass",
        )
        with conn:
            assert conn.is_open is True
        assert conn.is_open is False

    def test_context_manager_returns_connection(self):
        conn = Connection(
            base_url="http://localhost/api",
            username="user",
            password="pass",
        )
        with conn as c:
            assert c is conn


class TestExceptionAttributes:
    """DB-API 2.0 optional extension: exceptions as Connection attributes."""

    @pytest.fixture
    def conn(self):
        c = Connection(
            base_url="http://localhost/api",
            username="user",
            password="pass",
        )
        yield c
        if c.is_open:
            c.close()

    def test_warning_attribute(self, conn):
        warnings.simplefilter("ignore")
        assert conn.Warning is CDataWarning
        warnings.resetwarnings()

    def test_error_attribute(self, conn):
        warnings.simplefilter("ignore")
        assert conn.Error is Error
        warnings.resetwarnings()

    def test_interface_error_attribute(self, conn):
        warnings.simplefilter("ignore")
        assert conn.InterfaceError is InterfaceError
        warnings.resetwarnings()

    def test_database_error_attribute(self, conn):
        warnings.simplefilter("ignore")
        assert conn.DatabaseError is DatabaseError
        warnings.resetwarnings()

    def test_operational_error_attribute(self, conn):
        warnings.simplefilter("ignore")
        assert conn.OperationalError is OperationalError
        warnings.resetwarnings()

    def test_integrity_error_attribute(self, conn):
        warnings.simplefilter("ignore")
        assert conn.IntegrityError is IntegrityError
        warnings.resetwarnings()

    def test_internal_error_attribute(self, conn):
        warnings.simplefilter("ignore")
        assert conn.InternalError is InternalError
        warnings.resetwarnings()

    def test_programming_error_attribute(self, conn):
        warnings.simplefilter("ignore")
        assert conn.ProgrammingError is ProgrammingError
        warnings.resetwarnings()

    def test_not_supported_error_attribute(self, conn):
        warnings.simplefilter("ignore")
        assert conn.NotSupportedError is NotSupportedError
        warnings.resetwarnings()


WORKSPACE_ID = "2f5ae96c-b558-4c7b-a3fb-92c9dd5a9d10"


def _conn(**kwargs):
    return Connection(base_url="http://localhost/api", username="user",
                      password="pass", **kwargs)


class TestWorkspaceId:
    def test_workspace_id_stored(self):
        assert _conn(workspaceId=WORKSPACE_ID).workspace_id == WORKSPACE_ID

    def test_workspace_id_normalized_to_canonical_form(self):
        conn = _conn(workspaceId="{2F5AE96C-B558-4C7B-A3FB-92C9DD5A9D10}")
        assert conn.workspace_id == WORKSPACE_ID

    @pytest.mark.parametrize("bad", ["Production", "", "2f5ae96c-b558", "not-a-guid"])
    def test_workspace_id_not_a_guid_raises(self, bad):
        with pytest.raises(ConfigurationError, match="workspaceId"):
            _conn(workspaceId=bad)


class TestVirtualSchema:
    def test_virtual_schema_stored(self):
        conn = _conn(virtualSchema="SalesData")
        assert conn.virtual_schema == "SalesData"
        assert conn.workspace == "SalesData"

    def test_virtual_schema_does_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _conn(virtualSchema="SalesData")

    def test_workspace_alias_sets_virtual_schema(self):
        with pytest.warns(DeprecationWarning, match="virtualSchema"):
            conn = _conn(workspace="ws1")
        assert conn.virtual_schema == "ws1"
        assert conn.workspace == "ws1"

    def test_workspace_and_virtual_schema_same_value_allowed(self):
        with pytest.warns(DeprecationWarning):
            conn = _conn(workspace="ws1", virtualSchema="ws1")
        assert conn.virtual_schema == "ws1"

    def test_workspace_and_virtual_schema_conflict_raises(self):
        with pytest.raises(ConfigurationError, match="Conflicting"):
            _conn(workspace="ws1", virtualSchema="ws2")

    def test_workspace_id_and_virtual_schema_together(self):
        conn = _conn(workspaceId=WORKSPACE_ID, virtualSchema="SalesData")
        assert conn.workspace_id == WORKSPACE_ID
        assert conn.virtual_schema == "SalesData"


def _config_conn(values, **kwargs):
    values = {"cdata_api_db.username": "u", "cdata_api_db.password": "p", **values}
    mock_config = MagicMock()
    mock_config.get_string.side_effect = lambda key: values[key]
    with patch("cdata_connect_ai.connection.ConfigFactory.parse_file",
               return_value=mock_config):
        return Connection(config_path="/fake/config.conf", **kwargs)


class TestWorkspaceConfigFile:
    def test_config_without_workspace_keys(self):
        conn = _config_conn({})
        assert conn.workspace_id is None
        assert conn.virtual_schema is None

    def test_config_workspace_id_and_virtual_schema(self):
        conn = _config_conn({
            "cdata_api_db.workspaceId": WORKSPACE_ID,
            "cdata_api_db.virtualSchema": "SalesData",
        })
        assert conn.workspace_id == WORKSPACE_ID
        assert conn.virtual_schema == "SalesData"

    def test_config_workspace_alias_warns(self):
        with pytest.warns(DeprecationWarning):
            conn = _config_conn({"cdata_api_db.workspace": "ws1"})
        assert conn.virtual_schema == "ws1"

    def test_config_workspace_conflict_raises(self):
        with pytest.raises(ConfigurationError, match="Conflicting"):
            _config_conn({
                "cdata_api_db.workspace": "ws1",
                "cdata_api_db.virtualSchema": "ws2",
            })

    def test_config_invalid_workspace_id_raises(self):
        with pytest.raises(ConfigurationError, match="workspaceId"):
            _config_conn({"cdata_api_db.workspaceId": "Production"})

    def test_arguments_override_config(self):
        other_id = "11111111-2222-3333-4444-555555555555"
        conn = _config_conn(
            {
                "cdata_api_db.workspaceId": WORKSPACE_ID,
                "cdata_api_db.workspace": "from_config",
            },
            workspaceId=other_id,
            virtualSchema="from_args",
        )
        assert conn.workspace_id == other_id
        assert conn.virtual_schema == "from_args"
