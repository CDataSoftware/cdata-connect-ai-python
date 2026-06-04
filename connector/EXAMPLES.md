# cdata-connect-ai Usage Examples

## Installation

```bash
pip install cdata-connect-ai
```

## Basic Connection

```python
import cdata_connect_ai

conn = cdata_connect_ai.connect(
    username="you@example.com",
    password="<your_personal_access_token>",
)
```

## Using Context Managers (Recommended)

Connections and cursors support `with` statements for automatic cleanup:

```python
import cdata_connect_ai

with cdata_connect_ai.connect(
    username="you@example.com",
    password="<your_pat>",
) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM [Salesforce1].[Salesforce].[Account]")
        for row in cur:
            print(row)
# Connection and cursor are automatically closed here
```

## Querying Data

### Fetch All Rows

```python
with conn.cursor() as cur:
    cur.execute("SELECT Id, Name, Industry FROM [Salesforce1].[Salesforce].[Account]")
    rows = cur.fetchall()
    for row in rows:
        print(f"Id={row[0]}, Name={row[1]}, Industry={row[2]}")
```

### Fetch One Row at a Time

```python
with conn.cursor() as cur:
    cur.execute("SELECT * FROM [Salesforce1].[Salesforce].[Contact]")
    while True:
        row = cur.fetchone()
        if row is None:
            break
        print(row)
```

### Fetch in Batches

```python
with conn.cursor() as cur:
    cur.execute("SELECT * FROM [Salesforce1].[Salesforce].[Contact]")
    while True:
        batch = cur.fetchmany(100)  # 100 rows at a time
        if not batch:
            break
        for row in batch:
            process(row)
```

### Iterate Directly (PEP 249 Iterator Protocol)

```python
with conn.cursor() as cur:
    cur.execute("SELECT Name, Email FROM [Salesforce1].[Salesforce].[Contact]")
    for row in cur:
        print(f"{row[0]} — {row[1]}")
```

## Column Metadata

```python
with conn.cursor() as cur:
    cur.execute("SELECT Id, Name, AnnualRevenue FROM [Salesforce1].[Salesforce].[Account]")

    # cursor.description is a list of 7-tuples per PEP 249
    for col in cur.description:
        name, type_code, display_size, length, precision, scale, nullable = col
        print(f"Column: {name}, Type: {type_code}")

    rows = cur.fetchall()
```

## Parameterized Queries

The driver uses `pyformat` parameter style (`%(name)s` placeholders):

```python
with conn.cursor() as cur:
    cur.execute(
        "SELECT * FROM [DB].[public].[users] WHERE city = %(city)s AND age > %(min_age)s",
        {"city": "New York", "min_age": 25},
    )
    rows = cur.fetchall()
```

## Insert, Update, Delete

```python
with conn.cursor() as cur:
    # Insert
    cur.execute("INSERT INTO [DB].[public].[users] (name, email) VALUES ('Alice', 'alice@example.com')")

    # Update
    cur.execute("UPDATE [DB].[public].[users] SET email = 'alice@new.com' WHERE name = 'Alice'")

    # Delete
    cur.execute("DELETE FROM [DB].[public].[users] WHERE name = 'Alice'")
```

## Batch Insert (executemany)

```python
with conn.cursor() as cur:
    cur.executemany(
        "INSERT INTO [DB].[public].[cities] (city, id) VALUES (@city, @id)",
        [
            {"@city": {"dataType": 5, "value": "New York"}, "@id": {"dataType": 8, "value": 1}},
            {"@city": {"dataType": 5, "value": "London"},   "@id": {"dataType": 8, "value": 2}},
            {"@city": {"dataType": 5, "value": "Tokyo"},    "@id": {"dataType": 8, "value": 3}},
        ],
    )
```

## Stored Procedures

```python
with conn.cursor() as cur:
    result_args = cur.callproc("[DB].[public].[my_procedure]", ("arg1", "arg2"))
    rows = cur.fetchall()
    print(f"Input args returned: {result_args}")
    print(f"Result rows: {rows}")
```

## Configuration File

Keep credentials out of code using a [PyHOCON](https://github.com/chimpler/pyhocon) config file:

```hocon
# config.conf
cdata_api_db {
    username = "you@example.com"
    password = "<your_personal_access_token>"
}
```

```python
conn = cdata_connect_ai.connect(config_path="config.conf")
```

## Workspaces

Access a specific CData Connect AI workspace:

```python
conn = cdata_connect_ai.connect(
    username="you@example.com",
    password="<your_pat>",
    workspace="production",
)
```

## Connection Options

```python
conn = cdata_connect_ai.connect(
    username="you@example.com",
    password="<your_pat>",
    timeout=60,          # HTTP timeout in seconds (default: 60)
    max_retries=5,       # Retries on 5xx errors (default: 3)
    retry_delay=2.0,     # Base delay between retries in seconds (default: 1.0)
    # base_url="https://cloud.cdata.com/api",  # optional: override for non-production environments
)
```

## Error Handling

```python
import cdata_connect_ai
from cdata_connect_ai.exceptions import (
    InterfaceError,
    OperationalError,
    ProgrammingError,
    DatabaseError,
)

try:
    conn = cdata_connect_ai.connect(
        username="you@example.com",
        password="<your_pat>",
    )
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM [Salesforce1].[Salesforce].[Account]")
        rows = cur.fetchall()

except InterfaceError as e:
    print(f"Connection/interface problem: {e}")

except OperationalError as e:
    print(f"Server error, timeout, or connectivity issue: {e}")

except ProgrammingError as e:
    print(f"Query error or fetch before execute: {e}")

except DatabaseError as e:
    print(f"General database error: {e}")

finally:
    if conn.is_open:
        conn.close()
```

## Using with pandas

```bash
pip install "cdata-connect-ai[full]"
```

```python
import pandas as pd
import cdata_connect_ai

conn = cdata_connect_ai.connect(
    username="you@example.com",
    password="<your_pat>",
)

with conn.cursor() as cur:
    cur.execute("SELECT Id, Name, Industry, AnnualRevenue FROM [Salesforce1].[Salesforce].[Account]")
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

df = pd.DataFrame(rows, columns=columns)
print(df.head())
print(df.describe())

conn.close()
```

## Type Objects

PEP 249 type objects for use with `cursor.description`:

```python
import cdata_connect_ai

# Check column types from cursor.description
with conn.cursor() as cur:
    cur.execute("SELECT Id, Name, AnnualRevenue, CreatedDate FROM [Salesforce1].[Salesforce].[Account]")
    for col in cur.description:
        name, type_code = col[0], col[1]
        if type_code == cdata_connect_ai.STRING:
            print(f"{name} is a string")
        elif type_code == cdata_connect_ai.NUMBER:
            print(f"{name} is a number")
        elif type_code == cdata_connect_ai.DATETIME:
            print(f"{name} is a datetime")
        elif type_code == cdata_connect_ai.BINARY:
            print(f"{name} is binary")
```

## Date/Time Constructors

PEP 249 date/time helper constructors:

```python
import cdata_connect_ai

d = cdata_connect_ai.Date(2025, 3, 15)
t = cdata_connect_ai.Time(14, 30, 0)
ts = cdata_connect_ai.Timestamp(2025, 3, 15, 14, 30, 0)
b = cdata_connect_ai.Binary(b"raw bytes")

# From Unix timestamps
import time
d2 = cdata_connect_ai.DateFromTicks(time.time())
t2 = cdata_connect_ai.TimeFromTicks(time.time())
ts2 = cdata_connect_ai.TimestampFromTicks(time.time())
```

## Exception Hierarchy

```
cdata_connect_ai.Warning           — Important warnings (subclass of Exception)
cdata_connect_ai.Error             — Base error class
├── InterfaceError              — Connection/interface issues
├── ConfigurationError          — Bad config file or missing parameters
└── DatabaseError               — Database-related errors
    ├── DataError               — Data processing errors (bad JSON, etc.)
    ├── OperationalError        — Server errors, timeouts, connectivity
    ├── IntegrityError          — Constraint violations
    ├── InternalError           — Internal database errors
    ├── ProgrammingError        — Query errors, fetch before execute
    └── NotSupportedError       — Unsupported operations
```
