from typing import Optional

from .connection import Connection, DEFAULT_BASE_URL
from .exceptions import (
    ConfigurationError,
    DatabaseError,
    DataError,
    Error,
    IntegrityError,
    InterfaceError,
    InternalError,
    NotSupportedError,
    OperationalError,
    ProgrammingError,
    Warning,
)
from .util.types import (
    DBAPI_TYPE_STRING,
    DBAPI_TYPE_BINARY,
    DBAPI_TYPE_NUMBER,
    DBAPI_TYPE_TIMESTAMP,
    Date,
    Time,
    Timestamp,
    Binary,
    DateFromTicks,
    TimeFromTicks,
    TimestampFromTicks,
)
from .version import __version__

# PEP 249 mandatory module-level type objects
STRING = DBAPI_TYPE_STRING       # 0
BINARY = DBAPI_TYPE_BINARY       # 1
NUMBER = DBAPI_TYPE_NUMBER       # 2
DATETIME = DBAPI_TYPE_TIMESTAMP  # 3
ROWID = DBAPI_TYPE_STRING        # No dedicated ROWID type; STRING is the standard fallback

# DB API 2.0 module attributes
apilevel = "2.0"
threadsafety = 1
paramstyle = "pyformat"


def connect(
    config_path: Optional[str] = None,
    base_url: str = DEFAULT_BASE_URL,
    username: Optional[str] = None,
    password: Optional[str] = None,
    workspace: Optional[str] = None,
    timeout: int = 90,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> Connection:
    """
    Create a connection to the CData Connect AI API.

    :param base_url: The base URL of the CData Connect AI API.
    :param username: The username for authentication.
    :param password: The password for authentication.
    :param config_path: Optional path to a pyhocon config file.
    :param workspace: Optional workspace name to append as a query parameter.
    :param timeout: HTTP request timeout in seconds (per socket read). Default 90.
    :param max_retries: Retry count for transient 5xx errors. Default 3.
    :param retry_delay: Base seconds between retries (exponential backoff). Default 1.0.
    :return: A Connection object.
    """
    if not config_path and not (username and password):
        raise InterfaceError(
            "Either config_path or username and password must be provided."
        )

    return Connection(
        config_path=config_path,
        base_url=base_url,
        username=username,
        password=password,
        workspace=workspace,
        timeout=timeout,
        max_retries=max_retries,
        retry_delay=retry_delay,
    )
