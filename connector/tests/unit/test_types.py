"""Unit tests for type conversion, Date/Time/Timestamp/Binary constructors."""

import base64
import datetime
import time
import uuid
from decimal import Decimal

import pytest

from cdata_connect_ai.util.types import (
    convert_to_python_type,
    Date,
    Time,
    Timestamp,
    Binary,
    DateFromTicks,
    TimeFromTicks,
    TimestampFromTicks,
    TYPE_CONNECT_TO_PYTHON,
    TYPE_PYTHON_TO_CONNECT,
    DBAPI_TYPE_STRING,
    DBAPI_TYPE_BINARY,
    DBAPI_TYPE_NUMBER,
    DBAPI_TYPE_TIMESTAMP,
    CONNECT_TYPE_VARCHAR,
    CONNECT_TYPE_INTEGER,
    CONNECT_TYPE_TIMESTAMP,
    CONNECT_TYPE_BINARY,
    CONNECT_TYPE_FLOAT,
    CONNECT_TYPE_DOUBLE,
    CONNECT_TYPE_DECIMAL,
    CONNECT_TYPE_BOOLEAN,
    CONNECT_TYPE_DATE,
    CONNECT_TYPE_TIME,
    CONNECT_TYPE_UUID,
    CONNECT_TYPE_TINYINT,
    CONNECT_TYPE_SMALLINT,
    CONNECT_TYPE_BIGINT,
    CONNECT_TYPE_NUMERIC,
)


class TestConvertToPythonType:
    # --- Integer types ---
    def test_int_from_string(self):
        assert convert_to_python_type("42", "INT") == 42

    def test_tinyint(self):
        assert convert_to_python_type("1", "TINYINT") == 1

    def test_smallint(self):
        assert convert_to_python_type("100", "SMALLINT") == 100

    def test_integer(self):
        assert convert_to_python_type("999", "INTEGER") == 999

    def test_bigint(self):
        assert convert_to_python_type("9999999999", "BIGINT") == 9999999999

    def test_int_none_passthrough(self):
        assert convert_to_python_type(None, "INT") is None

    def test_int_already_int(self):
        assert convert_to_python_type(42, "INT") == 42

    # --- Float types ---
    def test_float_from_string(self):
        assert convert_to_python_type("3.14", "FLOAT") == pytest.approx(3.14)

    def test_double(self):
        assert convert_to_python_type("2.718", "DOUBLE") == pytest.approx(2.718)

    def test_real(self):
        assert convert_to_python_type("1.5", "REAL") == pytest.approx(1.5)

    def test_float_none_passthrough(self):
        assert convert_to_python_type(None, "FLOAT") is None

    # --- Decimal types ---
    def test_decimal_from_string(self):
        result = convert_to_python_type("123.45", "DECIMAL")
        assert result == Decimal("123.45")
        assert isinstance(result, Decimal)

    def test_numeric(self):
        result = convert_to_python_type("99.99", "NUMERIC")
        assert result == Decimal("99.99")

    def test_decimal_none_passthrough(self):
        assert convert_to_python_type(None, "DECIMAL") is None

    # --- Boolean types ---
    def test_boolean_true(self):
        assert convert_to_python_type("true", "BOOLEAN") is True

    def test_boolean_false(self):
        assert convert_to_python_type("false", "BOOLEAN") is False

    def test_bool_1(self):
        assert convert_to_python_type("1", "BOOL") is True

    def test_boolean_none_passthrough(self):
        assert convert_to_python_type(None, "BOOLEAN") is None

    # --- Date type ---
    def test_date_from_string(self):
        result = convert_to_python_type("2023-01-15", "DATE")
        assert result == datetime.date(2023, 1, 15)

    def test_date_none_passthrough(self):
        assert convert_to_python_type(None, "DATE") is None

    # --- Time type ---
    def test_time_from_string(self):
        result = convert_to_python_type("13:45:30", "TIME")
        assert result == datetime.time(13, 45, 30)

    def test_time_none_passthrough(self):
        assert convert_to_python_type(None, "TIME") is None

    # --- Timestamp types ---
    def test_timestamp_iso_z(self):
        result = convert_to_python_type("2023-01-15T13:45:30Z", "TIMESTAMP")
        assert result == datetime.datetime(2023, 1, 15, 13, 45, 30)

    def test_timestamp_iso_no_z(self):
        result = convert_to_python_type("2023-01-15T13:45:30", "TIMESTAMP")
        assert result == datetime.datetime(2023, 1, 15, 13, 45, 30)

    def test_timestamp_space_separator(self):
        result = convert_to_python_type("2023-01-15 13:45:30", "DATETIME")
        assert result == datetime.datetime(2023, 1, 15, 13, 45, 30)

    def test_timestamp_none_passthrough(self):
        assert convert_to_python_type(None, "TIMESTAMP") is None

    def test_timestamp_unparseable_returns_as_is(self):
        result = convert_to_python_type("not-a-date", "TIMESTAMP")
        assert result == "not-a-date"

    def test_timestamp_iso_z_microseconds(self):
        result = convert_to_python_type("2026-03-11T10:46:49.349039Z", "TIMESTAMP")
        assert result == datetime.datetime(2026, 3, 11, 10, 46, 49, 349039)

    def test_timestamp_iso_no_z_microseconds(self):
        result = convert_to_python_type("2026-03-11T10:46:49.349039", "TIMESTAMP")
        assert result.microsecond == 349039

    def test_timestamp_space_microseconds(self):
        result = convert_to_python_type("2026-03-11 10:46:49.123456", "TIMESTAMP")
        assert result.microsecond == 123456

    def test_timestamp_one_digit_fraction(self):
        result = convert_to_python_type("2026-03-11T10:46:49.1Z", "TIMESTAMP")
        assert result.microsecond == 100000

    def test_timestamp_three_digit_fraction(self):
        result = convert_to_python_type("2026-03-11T10:46:49.123Z", "TIMESTAMP")
        assert result.microsecond == 123000

    def test_timestamp_datetime_alias_microseconds(self):
        result = convert_to_python_type("2026-03-11T10:46:49.349039Z", "DATETIME")
        assert isinstance(result, datetime.datetime)

    # --- UUID type ---
    def test_uuid(self):
        val = "12345678-1234-5678-1234-567812345678"
        result = convert_to_python_type(val, "UUID")
        assert result == uuid.UUID(val)

    def test_uuid_none_passthrough(self):
        assert convert_to_python_type(None, "UUID") is None

    # --- Binary type ---
    def test_binary(self):
        result = convert_to_python_type(b"hello", "BINARY")
        assert result == bytearray(b"hello")

    def test_binary_from_base64_string(self):
        encoded = base64.b64encode(b"hello").decode("ascii")
        result = convert_to_python_type(encoded, "BINARY")
        assert result == bytearray(b"hello")

    def test_binary_none_passthrough(self):
        assert convert_to_python_type(None, "BINARY") is None

    def test_binary_bytearray_passthrough(self):
        result = convert_to_python_type(bytearray(b"\x01\x02"), "BINARY")
        assert result == bytearray(b"\x01\x02")

    def test_varbinary_from_base64(self):
        b64_value = base64.b64encode(b"\x00\x01\x02\x03").decode("ascii")
        result = convert_to_python_type(b64_value, "VARBINARY")
        assert result == bytearray(b"\x00\x01\x02\x03")

    def test_longvarbinary_from_base64(self):
        b64_value = base64.b64encode(b"hello binary").decode("ascii")
        result = convert_to_python_type(b64_value, "LONGVARBINARY")
        assert result == bytearray(b"hello binary")

    def test_blob_from_base64(self):
        b64_value = base64.b64encode(b"\xff\xfe").decode("ascii")
        result = convert_to_python_type(b64_value, "BLOB")
        assert isinstance(result, bytearray)

    def test_varbinary_none_passthrough(self):
        assert convert_to_python_type(None, "VARBINARY") is None

    def test_binary_empty_string(self):
        result = convert_to_python_type("", "BINARY")
        assert isinstance(result, bytearray)
        assert len(result) == 0

    # --- String types ---
    def test_varchar(self):
        assert convert_to_python_type("hello", "VARCHAR") == "hello"

    def test_text(self):
        assert convert_to_python_type("hello", "TEXT") == "hello"

    def test_char(self):
        assert convert_to_python_type("h", "CHAR") == "h"

    def test_nvarchar(self):
        assert convert_to_python_type("hello", "NVARCHAR") == "hello"

    def test_string_none_passthrough(self):
        assert convert_to_python_type(None, "VARCHAR") is None

    # --- NULL type ---
    def test_null_type(self):
        assert convert_to_python_type("anything", "NULL") is None

    # --- Unknown type ---
    def test_unknown_type_returns_as_is(self):
        assert convert_to_python_type("value", "UNKNOWN_TYPE") == "value"


class TestDateClass:
    def test_constructor(self):
        d = Date(2023, 1, 15)
        assert d.year == 2023
        assert d.month == 1
        assert d.day == 15

    def test_str(self):
        d = Date(2023, 1, 5)
        assert str(d) == "2023-01-05"

    def test_fromtimestamp(self):
        ts = time.mktime((2023, 1, 15, 0, 0, 0, 0, 0, 0))
        result = Date.fromtimestamp(ts)
        assert isinstance(result, Date)
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 15


class TestTimeClass:
    def test_constructor(self):
        t = Time(13, 45, 30)
        assert t.hour == 13
        assert t.minute == 45
        assert t.second == 30

    def test_str(self):
        t = Time(9, 5, 3)
        assert str(t) == "09:05:03"

    def test_fromtimestamp(self):
        ts = time.mktime((2023, 1, 1, 13, 45, 30, 0, 0, 0))
        result = Time.fromtimestamp(ts)
        assert isinstance(result, Time)
        assert result.hour == 13
        assert result.minute == 45
        assert result.second == 30


class TestTimestampClass:
    def test_constructor(self):
        ts = Timestamp(2023, 1, 15, 13, 45, 30)
        assert ts.year == 2023
        assert ts.hour == 13

    def test_str(self):
        ts = Timestamp(2023, 1, 15, 13, 45, 30)
        assert str(ts) == "2023-01-15 13:45:30"

    def test_fromtimestamp(self):
        ticks = time.mktime((2023, 1, 15, 13, 45, 30, 0, 0, 0))
        result = Timestamp.fromtimestamp(ticks)
        assert isinstance(result, Timestamp)
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 13
        assert result.minute == 45
        assert result.second == 30


class TestBinaryClass:
    def test_constructor(self):
        b = Binary(b"hello")
        assert b.data == b"hello"

    def test_empty_binary(self):
        b = Binary(b"")
        assert b.data == b""


class TestFromTicks:
    def test_date_from_ticks(self):
        ticks = time.mktime((2023, 1, 15, 0, 0, 0, 0, 0, 0))
        result = DateFromTicks(ticks)
        assert isinstance(result, Date)
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 15

    def test_time_from_ticks(self):
        ticks = time.mktime((2023, 1, 1, 13, 45, 30, 0, 0, 0))
        result = TimeFromTicks(ticks)
        assert isinstance(result, Time)
        assert result.hour == 13
        assert result.minute == 45
        assert result.second == 30

    def test_timestamp_from_ticks(self):
        ticks = time.mktime((2023, 1, 15, 13, 45, 30, 0, 0, 0))
        result = TimestampFromTicks(ticks)
        assert isinstance(result, Timestamp)
        assert result.year == 2023
        assert result.hour == 13


class TestWrapperTypeCodes:
    """DB-API wrapper types (Date, Time, Timestamp, Binary) must be in type_codes."""

    def test_date_in_type_codes(self):
        from cdata_connect_ai.util.types import type_codes
        assert type_codes[Date] == DBAPI_TYPE_TIMESTAMP

    def test_time_in_type_codes(self):
        from cdata_connect_ai.util.types import type_codes
        assert type_codes[Time] == DBAPI_TYPE_TIMESTAMP

    def test_timestamp_in_type_codes(self):
        from cdata_connect_ai.util.types import type_codes
        assert type_codes[Timestamp] == DBAPI_TYPE_TIMESTAMP

    def test_binary_in_type_codes(self):
        from cdata_connect_ai.util.types import type_codes
        assert type_codes[Binary] == DBAPI_TYPE_BINARY

    def test_date_maps_to_timestamp_connect_type(self):
        """Date wrapper should map through to CONNECT_TYPE_TIMESTAMP via type_codes."""
        from cdata_connect_ai.util.types import type_codes
        code = type_codes[Date]
        assert TYPE_PYTHON_TO_CONNECT[code] == CONNECT_TYPE_TIMESTAMP

    def test_binary_maps_to_binary_connect_type(self):
        """Binary wrapper should map through to CONNECT_TYPE_BINARY via type_codes."""
        from cdata_connect_ai.util.types import type_codes
        code = type_codes[Binary]
        assert TYPE_PYTHON_TO_CONNECT[code] == CONNECT_TYPE_BINARY


class TestTypeMappings:
    def test_connect_to_python_varchar(self):
        assert TYPE_CONNECT_TO_PYTHON[CONNECT_TYPE_VARCHAR] == DBAPI_TYPE_STRING

    def test_connect_to_python_integer(self):
        assert TYPE_CONNECT_TO_PYTHON[CONNECT_TYPE_INTEGER] == DBAPI_TYPE_NUMBER

    def test_connect_to_python_float(self):
        assert TYPE_CONNECT_TO_PYTHON[CONNECT_TYPE_FLOAT] == DBAPI_TYPE_NUMBER

    def test_connect_to_python_double(self):
        assert TYPE_CONNECT_TO_PYTHON[CONNECT_TYPE_DOUBLE] == DBAPI_TYPE_NUMBER

    def test_connect_to_python_decimal(self):
        assert TYPE_CONNECT_TO_PYTHON[CONNECT_TYPE_DECIMAL] == DBAPI_TYPE_NUMBER

    def test_connect_to_python_boolean(self):
        assert TYPE_CONNECT_TO_PYTHON[CONNECT_TYPE_BOOLEAN] == DBAPI_TYPE_NUMBER

    def test_connect_to_python_date(self):
        assert TYPE_CONNECT_TO_PYTHON[CONNECT_TYPE_DATE] == DBAPI_TYPE_TIMESTAMP

    def test_connect_to_python_time(self):
        assert TYPE_CONNECT_TO_PYTHON[CONNECT_TYPE_TIME] == DBAPI_TYPE_TIMESTAMP

    def test_connect_to_python_timestamp(self):
        assert TYPE_CONNECT_TO_PYTHON[CONNECT_TYPE_TIMESTAMP] == DBAPI_TYPE_TIMESTAMP

    def test_connect_to_python_binary(self):
        assert TYPE_CONNECT_TO_PYTHON[CONNECT_TYPE_BINARY] == DBAPI_TYPE_BINARY

    def test_connect_to_python_uuid(self):
        assert TYPE_CONNECT_TO_PYTHON[CONNECT_TYPE_UUID] == DBAPI_TYPE_STRING

    def test_connect_to_python_tinyint(self):
        assert TYPE_CONNECT_TO_PYTHON[CONNECT_TYPE_TINYINT] == DBAPI_TYPE_NUMBER

    def test_connect_to_python_smallint(self):
        assert TYPE_CONNECT_TO_PYTHON[CONNECT_TYPE_SMALLINT] == DBAPI_TYPE_NUMBER

    def test_connect_to_python_bigint(self):
        assert TYPE_CONNECT_TO_PYTHON[CONNECT_TYPE_BIGINT] == DBAPI_TYPE_NUMBER

    def test_connect_to_python_numeric(self):
        assert TYPE_CONNECT_TO_PYTHON[CONNECT_TYPE_NUMERIC] == DBAPI_TYPE_NUMBER

    def test_python_to_connect_string(self):
        assert TYPE_PYTHON_TO_CONNECT[DBAPI_TYPE_STRING] == CONNECT_TYPE_VARCHAR

    def test_python_to_connect_number(self):
        assert TYPE_PYTHON_TO_CONNECT[DBAPI_TYPE_NUMBER] == CONNECT_TYPE_INTEGER

    def test_python_to_connect_timestamp(self):
        assert TYPE_PYTHON_TO_CONNECT[DBAPI_TYPE_TIMESTAMP] == CONNECT_TYPE_TIMESTAMP

    def test_python_to_connect_binary(self):
        assert TYPE_PYTHON_TO_CONNECT[DBAPI_TYPE_BINARY] == CONNECT_TYPE_BINARY
