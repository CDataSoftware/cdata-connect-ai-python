import uuid
from typing import Optional

from pyhocon import ConfigFactory
from pyhocon.exceptions import ConfigException
from warnings import warn

from .cursor import Cursor
from .log import logger
from .exceptions import (
    ConfigurationError, InterfaceError, Warning, Error,
    DatabaseError, OperationalError, IntegrityError,
    InternalError, ProgrammingError, NotSupportedError,
)


DEFAULT_BASE_URL = "https://cloud.cdata.com/api"


def _normalize_workspace_id(workspace_id: Optional[str]) -> Optional[str]:
    """Validate a workspace GUID and return it in canonical form."""
    if workspace_id is None:
        return None
    try:
        return str(uuid.UUID(str(workspace_id)))
    except ValueError as e:
        raise ConfigurationError(
            f"workspaceId must be a workspace GUID, got: {workspace_id!r}"
        ) from e


def _resolve_virtual_schema(virtual_schema: Optional[str],
                            workspace: Optional[str]) -> Optional[str]:
    """Merge virtualSchema with its deprecated alias, workspace."""
    if workspace is None:
        return virtual_schema
    if virtual_schema is not None and virtual_schema != workspace:
        raise ConfigurationError(
            f"Conflicting virtual schema: virtualSchema={virtual_schema!r} "
            f"and workspace={workspace!r}. 'workspace' is a deprecated alias "
            f"for 'virtualSchema'; pass only virtualSchema."
        )
    warn("The 'workspace' option is deprecated and will be removed in a "
         "future release; use 'virtualSchema' instead.",
         DeprecationWarning, stacklevel=4)
    return workspace


def _get_optional_string(config, key: str) -> Optional[str]:
    try:
        return config.get_string(key)
    except (ConfigException, KeyError):
        return None


class Connection:
    """
    Create a connection to the CData Connect AI API.

    :param base_url: The base URL of the CData Connect AI API.
    :param username: The username for authentication.
    :param password: The password for authentication.
    :param config_path: Optional path to a config file in pyhocon format.
    :param workspaceId: Optional workspace GUID. Omitted = the account's default workspace.
    :param virtualSchema: Optional virtual schema name.
    :param workspace: Deprecated alias for virtualSchema.
    :param timeout: HTTP request timeout in seconds (per socket read). Default 90.
    :param max_retries: Number of retries on transient 5xx / connection errors. Default 3.
    :param retry_delay: Base delay in seconds between retries (exponential backoff). Default 1.0.
    """
    # DBAPI Extension: supply exceptions as attributes on the connection
    Warning = property(lambda self: self._getError(Warning))
    Error = property(lambda self: self._getError(Error))
    InterfaceError = property(lambda self: self._getError(InterfaceError))
    DatabaseError = property(lambda self: self._getError(DatabaseError))
    OperationalError = property(lambda self: self._getError(OperationalError))
    IntegrityError = property(lambda self: self._getError(IntegrityError))
    InternalError = property(lambda self: self._getError(InternalError))
    ProgrammingError = property(lambda self: self._getError(ProgrammingError))
    NotSupportedError = property(lambda self: self._getError(NotSupportedError))

    def _getError(self: "Connection", error):
        warn("DB-API extension connection.%s used" % error.__name__, stacklevel=3)
        return error

    def __init__(self, base_url: str = DEFAULT_BASE_URL, username: str = None,
                 password: str = None, config_path: str = None,
                 workspace: str = None, timeout: int = 90,
                 max_retries: int = 3, retry_delay: float = 1.0,
                 workspaceId: str = None, virtualSchema: str = None):

        self.is_open = True
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.workspace_id = _normalize_workspace_id(workspaceId)
        self.virtual_schema = _resolve_virtual_schema(virtualSchema, workspace)

        if config_path:
            logger.debug("Connection - Initialising Connection with config")
            try:
                config = ConfigFactory.parse_file(config_path)
            except (ConfigException, FileNotFoundError) as e:
                raise ConfigurationError(
                    f"Configuration file could not be loaded: {str(e)}"
                ) from e

            try:
                self.auth = (config.get_string('cdata_api_db.username'),
                             config.get_string('cdata_api_db.password'))
            except (ConfigException, KeyError) as e:
                raise ConfigurationError(
                    f"Missing required configuration in cdata_api_db block: {str(e)}"
                ) from e

            try:
                self.base_url = config.get_string('cdata_api_db.base_url').rstrip('/')
            except (ConfigException, KeyError):
                self.base_url = DEFAULT_BASE_URL

            # Explicit connect() arguments take precedence over the config file.
            if self.workspace_id is None:
                self.workspace_id = _normalize_workspace_id(
                    _get_optional_string(config, 'cdata_api_db.workspaceId'))
            if self.virtual_schema is None:
                self.virtual_schema = _resolve_virtual_schema(
                    _get_optional_string(config, 'cdata_api_db.virtualSchema'),
                    _get_optional_string(config, 'cdata_api_db.workspace'))

        else:
            logger.debug("Connection - Initialising Connection with "
                         "username and password")

            if username is None or password is None:
                raise ConfigurationError(
                    "Missing required parameters: username and password "
                    "must be provided."
                )

            self.base_url = base_url.rstrip('/')
            self.auth = (username, password)

    @property
    def workspace(self) -> Optional[str]:
        """Deprecated: the virtual schema name. Use ``virtual_schema``."""
        return self.virtual_schema

    # ------------------------------------------------------------------
    # Context manager (PEP 249 optional extension)
    # ------------------------------------------------------------------

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # ------------------------------------------------------------------
    # DB API 2.0 methods
    # ------------------------------------------------------------------

    def commit(self):
        """Commit any pending transaction. No-op — underlying API has no transactions."""
        if self.is_open is False:
            raise InterfaceError("Cannot commit because the connection is already closed.")

    def rollback(self):
        """Rollback any pending transaction. No-op — underlying API has no transactions."""
        if self.is_open is False:
            raise InterfaceError("Cannot rollback because the connection is already closed.")

    def close(self):
        if self.is_open is False:
            raise InterfaceError("The connection is already closed")
        self.is_open = False

    def cursor(self):
        if self.is_open is False:
            raise InterfaceError("Cannot create cursor: connection is closed")
        return Cursor(self)
