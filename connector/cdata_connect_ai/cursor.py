import re
import time
import typing
from urllib.parse import quote

import ijson
import requests

from .log import logger
from .exceptions import (
    InterfaceError, OperationalError, DataError, DatabaseError,
    ProgrammingError,
)
from .util.types import (
    TYPE_CONNECT_TO_PYTHON, TYPE_PYTHON_TO_CONNECT,
    type_codes, convert_to_python_type,
)

_PYFORMAT_RE = re.compile(r'%\(([^)]+)\)s')


class Cursor:
    """
    DB API 2.0 (PEP 249) cursor initialized by the Connection class.

    :param connection: The parent Connection instance.
    """

    def __init__(self, connection):
        self.connection = connection
        self.schema = None
        self.rows_generator = None
        self.response = None
        self.json_reader = None
        self.current_row = 0
        self._rowcount = -1

    # ------------------------------------------------------------------
    # Context manager & iterator protocol (PEP 249 optional extensions)
    # ------------------------------------------------------------------

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __iter__(self):
        return self

    def __next__(self):
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_connection(self):
        if self.connection is None:
            raise InterfaceError("Cursor is closed")
        if not self.connection.is_open:
            raise InterfaceError("Operation on closed connection is not allowed")

    def _execute_request(self, url: str, json_object: dict) -> None:
        """Send an HTTP POST to the Connect API with timeout and retry."""
        self._check_connection()

        max_retries = self.connection.max_retries
        retry_delay = self.connection.retry_delay
        timeout = self.connection.timeout

        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                # Close any previous response before retrying to avoid resource leaks
                self._close_response()

                logger.debug(
                    f"Cursor - Sending API request to {url} (attempt {attempt + 1})"
                )
                self.response = requests.post(
                    url,
                    auth=self.connection.auth,
                    json=json_object,
                    stream=True,
                    timeout=timeout,
                )

                if self.response.status_code == 200:
                    self.json_reader = ijson.parse(
                        self.response.raw, buf_size=256
                    )
                    self._process_schema()
                    self._prepare_rows_reader()
                    self._rowcount = -1
                    return

                # Transient server errors — eligible for retry
                if self.response.status_code in (500, 502, 503, 504):
                    if attempt < max_retries:
                        wait = retry_delay * (2 ** attempt)
                        logger.warning(
                            f"Cursor - Transient server error "
                            f"{self.response.status_code}, retrying in "
                            f"{wait:.1f}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait)
                        continue

                # Non-retryable error (4xx, or exhausted retries on 5xx)
                error_string = (
                    f"Cursor - API request failed with status code "
                    f"{self.response.status_code}: {self.response.text}"
                )
                logger.error(error_string)
                raise OperationalError(error_string)

            except requests.exceptions.Timeout as e:
                raise OperationalError(f"Request timed out: {str(e)}") from e

            except requests.exceptions.ConnectionError as e:
                last_exception = e
                if attempt < max_retries:
                    wait = retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Cursor - Connection error, retrying in {wait:.1f}s: {e}"
                    )
                    time.sleep(wait)
                    continue
                break

            except requests.exceptions.RequestException as e:
                raise OperationalError(f"Error executing query: {str(e)}") from e

            except ijson.JSONError as e:
                raise DataError(f"Error parsing JSON response: {str(e)}") from e

            except (OperationalError, InterfaceError, ProgrammingError, DataError,
                    DatabaseError):
                raise  # re-raise our own exceptions without wrapping

            except Exception as e:
                raise DatabaseError(f"Unexpected error occurred: {str(e)}") from e

        raise OperationalError(
            f"Request failed after {max_retries} retries: {str(last_exception)}"
        )

    def _process_schema(self) -> None:
        self.schema = []
        key = ''
        for prefix, event, value in self.json_reader:
            if (prefix, event) == ('results.item.schema.item', 'start_map'):
                key = ''
                current_schema_item = {}
            elif (prefix, event) == ('results.item.schema.item', 'end_map'):
                self.schema.append(current_schema_item)
            elif (prefix, event) == ('results.item.schema.item', 'map_key'):
                key = value
            elif prefix == 'results.item.schema.item.%s' % key:
                current_schema_item[key] = value
            elif prefix == 'results.item.rows':
                break

    def _prepare_rows_reader(self) -> None:
        if not self.schema:
            # Non-row-returning statement (e.g. DELETE, INSERT, CREATE).
            # Leave rows_generator as None so fetch calls raise ProgrammingError.
            self.rows_generator = None
            return
        self.rows_generator = ijson.items(self.json_reader,
                                          'results.item.rows.item')

    def _convert_row(self, row: list) -> list:
        data_type_names = [schema_item['dataTypeName'] for schema_item in self.schema]
        return [
            convert_to_python_type(value, data_type_name)
            for data_type_name, value in zip(data_type_names, row)
        ]

    def _build_url(self, endpoint: str) -> str:
        """Build API URL with optional workspace query parameter."""
        url = f"{self.connection.base_url}/{endpoint}"
        if self.connection.workspace:
            url += f"?workspace={quote(self.connection.workspace)}"
        return url

    # ------------------------------------------------------------------
    # DB API 2.0 properties
    # ------------------------------------------------------------------

    @property
    def description(self) -> typing.Optional[typing.List[typing.Tuple]]:
        if not self.schema:
            return None
        columns = []
        for column in self.schema:
            col_name = column.get("columnLabel") or column["columnName"]
            columns.append((
                col_name,
                TYPE_CONNECT_TO_PYTHON[column["dataType"]],
                None,            # display_size (not used)
                column.get("length"),
                column.get("precision"),
                column.get("scale"),
                column.get("nullable"),
            ))
        return columns

    @property
    def rowcount(self) -> int:
        return self._rowcount

    @property
    def arraysize(self) -> int:
        return getattr(self, '_arraysize', 1)

    @arraysize.setter
    def arraysize(self, value: int) -> None:
        self._arraysize = value

    # ------------------------------------------------------------------
    # DB API 2.0 methods
    # ------------------------------------------------------------------

    def _close_response(self) -> None:
        """Drain and close the current HTTP streaming response, if any."""
        if self.response is not None:
            try:
                self.response.close()
            except Exception:
                pass
            self.response = None
        # Drop the ijson reader so it releases the socket reference too.
        self.json_reader = None

    def execute(self, query: str, params: typing.Optional[dict] = None) -> None:
        self._check_connection()
        self._rowcount = -1
        self._close_response()
        self.rows_generator = None
        self.schema = None

        json_object: dict[str, typing.Any] = {"query": query}

        if params is not None:
            if not isinstance(params, dict):
                raise ProgrammingError("params must be a dictionary")
            # Convert pyformat %(name)s placeholders to @name server-side parameters
            json_object["query"] = _PYFORMAT_RE.sub(r'@\1', query)
            parameters: dict[str, dict] = {}
            for key, value in params.items():
                data_type = type(value)
                data_type_code = type_codes.get(data_type, 9)
                data_type_connect = TYPE_PYTHON_TO_CONNECT[data_type_code]
                parameters[f"@{key}"] = {
                    "dataType": data_type_connect,
                    "value": value,
                }
            json_object["parameters"] = parameters

        self._execute_request(self._build_url("query"), json_object)

    def executemany(self, query: str,
                    params: typing.Optional[list] = None) -> None:
        self._check_connection()
        self._close_response()
        self.rows_generator = None
        self.schema = None

        json_object = {"query": query}

        if params is not None:
            if not isinstance(params, list):
                raise ProgrammingError("params must be a list of dictionaries")

            parameter_list = []
            for param_dict in params:
                parameter_item = {}
                for key, value in param_dict.items():
                    data_type = type(value)
                    data_type_code = type_codes.get(data_type, 9)
                    data_type_connect = TYPE_PYTHON_TO_CONNECT[data_type_code]
                    parameter_item[key] = {
                        "dataType": data_type_connect,
                        "value": value,
                    }
                parameter_list.append(parameter_item)

            json_object["parameters"] = parameter_list

        self._execute_request(self._build_url("batch"), json_object)

    def callproc(self, procedure: str,
                 params: typing.Optional[tuple] = None) -> tuple:
        self._check_connection()
        self._rowcount = -1
        self._close_response()
        self.rows_generator = None
        self.schema = None

        if params is None:
            args = []
        elif isinstance(params, tuple):
            args = list(params)
        else:
            args = [params]

        json_object = {
            "procedure": procedure,
            "parameters": {},
        }

        for key, value in enumerate(args, start=1):
            data_type = type(value)
            data_type_code = type_codes.get(data_type, 9)
            data_type_connect = TYPE_PYTHON_TO_CONNECT[data_type_code]
            json_object["parameters"][f"@{key}"] = {
                "dataType": data_type_connect,
                "value": value,
            }

        self._execute_request(self._build_url("exec"), json_object)
        return tuple(args)

    def close(self) -> None:
        # Allow closing even if the connection is already closed —
        # the cursor should still be able to release its own resources.
        self._close_response()
        self.rows_generator = None
        self.connection = None

    def fetchone(self) -> typing.Optional[list]:
        self._check_connection()
        if self.rows_generator is None:
            raise ProgrammingError(
                "fetchone() called before execute() or on a non-row-returning statement"
            )
        try:
            current_row = next(self.rows_generator)
            return self._convert_row(current_row)
        except StopIteration:
            return None

    def fetchall(self) -> list:
        self._check_connection()
        if self.rows_generator is None:
            raise ProgrammingError(
                "fetchall() called before execute() or on a non-row-returning statement"
            )
        processed_rows = []
        for row in self.rows_generator:
            processed_rows.append(self._convert_row(row))
        return processed_rows

    def fetchmany(self, size: typing.Optional[int] = None) -> list:
        self._check_connection()
        if self.rows_generator is None:
            raise ProgrammingError(
                "fetchmany() called before execute() or on a non-row-returning statement"
            )
        if size is None:
            size = self.arraysize
        rows = []
        for _ in range(size):
            row = self.fetchone()
            if row is None:
                break
            rows.append(row)
        return rows

    def setinputsizes(self, sizes) -> None:
        """DB API 2.0 optional method — no-op for this driver."""

    def setoutputsize(self, size, column=None) -> None:
        """DB API 2.0 optional method — no-op for this driver."""
