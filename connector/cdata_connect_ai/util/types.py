import base64
import datetime
import time
import types
import uuid
from collections import defaultdict
from decimal import Decimal
from typing import Any, DefaultDict, NamedTuple

DBAPI_TYPE_STRING = 0
DBAPI_TYPE_BINARY = 1
DBAPI_TYPE_NUMBER = 2
DBAPI_TYPE_TIMESTAMP = 3

type_codes: dict[type, int] = {
    str: DBAPI_TYPE_STRING,
    bool: DBAPI_TYPE_NUMBER,
    int: DBAPI_TYPE_NUMBER,
    float: DBAPI_TYPE_NUMBER,
    Decimal: DBAPI_TYPE_NUMBER,
    datetime.datetime: DBAPI_TYPE_TIMESTAMP,
    datetime.date: DBAPI_TYPE_TIMESTAMP,
    datetime.time: DBAPI_TYPE_TIMESTAMP,
    bytes: DBAPI_TYPE_BINARY,
    bytearray: DBAPI_TYPE_BINARY,
    types.NoneType: 9,  # For NoneType
}


def _register_wrapper_types() -> None:
    """Register DB-API wrapper types after their classes are defined (below)."""
    type_codes[Date] = DBAPI_TYPE_TIMESTAMP
    type_codes[Time] = DBAPI_TYPE_TIMESTAMP
    type_codes[Timestamp] = DBAPI_TYPE_TIMESTAMP
    type_codes[Binary] = DBAPI_TYPE_BINARY

CONNECT_TYPE_BINARY = 1
CONNECT_TYPE_VARCHAR = 5
CONNECT_TYPE_TINYINT = 6
CONNECT_TYPE_SMALLINT = 7
CONNECT_TYPE_INTEGER = 8
CONNECT_TYPE_BIGINT = 9
CONNECT_TYPE_FLOAT = 10
CONNECT_TYPE_DOUBLE = 11
CONNECT_TYPE_DECIMAL = 12
CONNECT_TYPE_NUMERIC = 13
CONNECT_TYPE_BOOLEAN = 14
CONNECT_TYPE_DATE = 15
CONNECT_TYPE_TIME = 16
CONNECT_TYPE_TIMESTAMP = 17
CONNECT_TYPE_UUID = 18


class FieldType(NamedTuple):
    connect_type: int
    dbapi_type: int


def convert_to_python_type(value, data_type):
    if data_type in ('TINYINT', 'SMALLINT', 'INTEGER', 'BIGINT', 'INT'):
        return value if value is None or isinstance(value, int) else int(str(value))
    elif data_type in ('FLOAT', 'DOUBLE', 'REAL'):
        return value if value is None or isinstance(value, float) else float(str(value))
    elif data_type in ('DECIMAL', 'NUMERIC'):
        return value if value is None or isinstance(value, Decimal) else Decimal(str(value))
    elif data_type in ('BOOLEAN', 'BOOL'):
        return value if value is None or isinstance(value, bool) else str(value).lower() in ('true', '1')
    elif data_type == 'DATE':
        return value if value is None or isinstance(value, datetime.date) else datetime.datetime.strptime(value, '%Y-%m-%d').date()
    elif data_type == 'TIME':
        return value if value is None or isinstance(value, datetime.time) else datetime.datetime.strptime(value, '%H:%M:%S').time()
    elif data_type in ('TIMESTAMP', 'DATETIME'):
        if value is None or isinstance(value, datetime.datetime):
            return value
        for fmt in ('%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d %H:%M:%S.%f',
                    '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'):
            try:
                return datetime.datetime.strptime(value, fmt)
            except ValueError:
                continue
        return value
    elif data_type == 'UUID':
        return value if value is None else uuid.UUID(value)
    elif data_type in ('BINARY', 'VARBINARY', 'LONGVARBINARY', 'BLOB'):
        if value is None:
            return None
        if isinstance(value, (bytes, bytearray)):
            return bytearray(value)
        if isinstance(value, str):
            return bytearray(base64.b64decode(value))
        return bytearray(value)
    elif data_type in ('VARCHAR', 'STRING', 'TEXT', 'CHAR', 'NVARCHAR', 'NCHAR'):
        return value if value is None or isinstance(value, str) else str(value)
    elif data_type == 'NULL':
        return None
    else:
        # Unknown type — return value as-is rather than crashing
        return value


FIELD_TYPES: tuple[FieldType, ...] = (
    FieldType(
        connect_type=CONNECT_TYPE_BINARY, dbapi_type=DBAPI_TYPE_BINARY
    ),
    FieldType(
        connect_type=CONNECT_TYPE_VARCHAR, dbapi_type=DBAPI_TYPE_STRING
    ),
    FieldType(
        connect_type=CONNECT_TYPE_TINYINT, dbapi_type=DBAPI_TYPE_NUMBER
    ),
    FieldType(
        connect_type=CONNECT_TYPE_SMALLINT, dbapi_type=DBAPI_TYPE_NUMBER
    ),
    FieldType(
        connect_type=CONNECT_TYPE_INTEGER, dbapi_type=DBAPI_TYPE_NUMBER
    ),
    FieldType(
        connect_type=CONNECT_TYPE_BIGINT, dbapi_type=DBAPI_TYPE_NUMBER
    ),
    FieldType(
        connect_type=CONNECT_TYPE_FLOAT, dbapi_type=DBAPI_TYPE_NUMBER
    ),
    FieldType(
        connect_type=CONNECT_TYPE_DOUBLE, dbapi_type=DBAPI_TYPE_NUMBER
    ),
    FieldType(
        connect_type=CONNECT_TYPE_DECIMAL, dbapi_type=DBAPI_TYPE_NUMBER
    ),
    FieldType(
        connect_type=CONNECT_TYPE_NUMERIC, dbapi_type=DBAPI_TYPE_NUMBER
    ),
    FieldType(
        connect_type=CONNECT_TYPE_BOOLEAN, dbapi_type=DBAPI_TYPE_NUMBER
    ),
    FieldType(
        connect_type=CONNECT_TYPE_DATE, dbapi_type=DBAPI_TYPE_TIMESTAMP
    ),
    FieldType(
        connect_type=CONNECT_TYPE_TIME, dbapi_type=DBAPI_TYPE_TIMESTAMP
    ),
    FieldType(
        connect_type=CONNECT_TYPE_TIMESTAMP, dbapi_type=DBAPI_TYPE_TIMESTAMP
    ),
    FieldType(
         connect_type=CONNECT_TYPE_UUID, dbapi_type=DBAPI_TYPE_STRING
    )
)

TYPE_CONNECT_TO_PYTHON: DefaultDict[Any, int] = defaultdict(int)
TYPE_PYTHON_TO_CONNECT: DefaultDict[int, str] = defaultdict(str)

for idx, field_type in enumerate(FIELD_TYPES):
    TYPE_CONNECT_TO_PYTHON[field_type.connect_type] = field_type.dbapi_type

TYPE_PYTHON_TO_CONNECT[DBAPI_TYPE_STRING] = CONNECT_TYPE_VARCHAR
TYPE_PYTHON_TO_CONNECT[DBAPI_TYPE_NUMBER] = CONNECT_TYPE_INTEGER
TYPE_PYTHON_TO_CONNECT[DBAPI_TYPE_TIMESTAMP] = CONNECT_TYPE_TIMESTAMP
TYPE_PYTHON_TO_CONNECT[DBAPI_TYPE_BINARY] = CONNECT_TYPE_BINARY


class Date:
    def __init__(self, year, month, day):
        self.year = year
        self.month = month
        self.day = day

    def __str__(self):
        return f"{self.year:04}-{self.month:02}-{self.day:02}"

    @classmethod
    def fromtimestamp(cls, timestamp):
        dt = datetime.date.fromtimestamp(timestamp)
        return cls(dt.year, dt.month, dt.day)


class Time:
    def __init__(self, hour, minute, second):
        self.hour = hour
        self.minute = minute
        self.second = second

    def __str__(self):
        return f"{self.hour:02}:{self.minute:02}:{self.second:02}"

    @classmethod
    def fromtimestamp(cls, timestamp):
        t = datetime.datetime.fromtimestamp(timestamp)
        return cls(t.hour, t.minute, t.second)


class Timestamp:
    def __init__(self, year, month, day, hour, minute, second):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second

    def __str__(self):
        return f"{self.year:04}-{self.month:02}-{self.day:02} {self.hour:02}:{self.minute:02}:{self.second:02}"

    @classmethod
    def fromtimestamp(cls, timestamp):
        dt = datetime.datetime.fromtimestamp(timestamp)
        return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


def DateFromTicks(ticks):
    return Date.fromtimestamp(ticks)


def TimeFromTicks(ticks):
    return Time.fromtimestamp(ticks)


def TimestampFromTicks(ticks):
    return Timestamp.fromtimestamp(ticks)


class Binary:
    def __init__(self, data):
        self.data = data


# Now that all wrapper classes are defined, register them in type_codes
_register_wrapper_types()
