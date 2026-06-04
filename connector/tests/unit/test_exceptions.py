"""Unit tests for the DB-API 2.0 exception hierarchy compliance."""

from cdata_connect_ai.exceptions import (
    Warning,
    Error,
    InterfaceError,
    DatabaseError,
    DataError,
    OperationalError,
    IntegrityError,
    InternalError,
    ProgrammingError,
    NotSupportedError,
    ConfigurationError,
)


class TestExceptionHierarchy:
    def test_warning_is_exception(self):
        assert issubclass(Warning, Exception)

    def test_error_is_exception(self):
        assert issubclass(Error, Exception)

    def test_interface_error_is_error(self):
        assert issubclass(InterfaceError, Error)

    def test_database_error_is_error(self):
        assert issubclass(DatabaseError, Error)

    def test_data_error_is_database_error(self):
        assert issubclass(DataError, DatabaseError)

    def test_operational_error_is_database_error(self):
        assert issubclass(OperationalError, DatabaseError)

    def test_integrity_error_is_database_error(self):
        assert issubclass(IntegrityError, DatabaseError)

    def test_internal_error_is_database_error(self):
        assert issubclass(InternalError, DatabaseError)

    def test_programming_error_is_database_error(self):
        assert issubclass(ProgrammingError, DatabaseError)

    def test_not_supported_error_is_database_error(self):
        assert issubclass(NotSupportedError, DatabaseError)

    def test_configuration_error_is_error(self):
        assert issubclass(ConfigurationError, Error)


class TestExceptionInstantiation:
    def test_warning_can_be_raised(self):
        with __import__("pytest").raises(Warning):
            raise Warning("test warning")

    def test_error_can_be_raised(self):
        with __import__("pytest").raises(Error):
            raise Error("test error")

    def test_operational_error_message(self):
        err = OperationalError("connection failed")
        assert str(err) == "connection failed"

    def test_programming_error_message(self):
        err = ProgrammingError("bad query")
        assert str(err) == "bad query"
