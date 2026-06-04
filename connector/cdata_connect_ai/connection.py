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


class Connection:
    """
    Create a connection to the CData Connect AI API.

    :param base_url: The base URL of the CData Connect AI API.
    :param username: The username for authentication.
    :param password: The password for authentication.
    :param config_path: Optional path to a config file in pyhocon format.
    :param workspace: Optional arg to access a specific CData workspace.
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
                 max_retries: int = 3, retry_delay: float = 1.0):

        self.is_open = True
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.workspace = workspace

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
