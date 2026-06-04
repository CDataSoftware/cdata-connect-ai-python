"""
client_demo.py — ConnectAI Python Connector demo against the mock server.

Demonstrates:
  1. Connecting to the mock API
  2. Fetching metadata (catalogs, tables)
  3. SELECT with fetchall / fetchone / fetchmany
  4. cursor.description (column metadata)
  5. Parameterized query (pyformat)
  6. Batch INSERT via executemany
  7. SELECT after INSERT (in-memory state)
  8. DELETE and verify empty result
  9. Stored procedure call
 10. Error handling
"""

import cdata_connect_ai

BASE_URL = "http://localhost:8080/api"
USERNAME = "test@example.com"
PASSWORD = "any_token"

SEP  = "=" * 60
SEP2 = "-" * 60


def section(title: str):
    print(f"\n{SEP}\n  {title}\n{SEP2}")


def connect():
    return cdata_connect_ai.connect(
        base_url=BASE_URL,
        username=USERNAME,
        password=PASSWORD,
    )


# ---------------------------------------------------------------------------
# 1. Basic SELECT — fetchall
# ---------------------------------------------------------------------------
section("1. Basic SELECT — fetchall")
conn = connect()
cur = conn.cursor()
cur.execute("SELECT * FROM Salesforce1.Salesforce.Contact")
rows = cur.fetchall()
print(f"Rows returned: {len(rows)}")
for row in rows[:3]:
    print(" ", row)
conn.close()


# ---------------------------------------------------------------------------
# 2. cursor.description — column metadata
# ---------------------------------------------------------------------------
section("2. cursor.description — column metadata")
conn = connect()
cur = conn.cursor()
cur.execute("SELECT * FROM Salesforce1.Salesforce.Contact")
print(f"{'Column':<20} {'Type':<10} {'Nullable'}")
print(SEP2)
for col in cur.description:
    name, type_obj, _, length, precision, scale, nullable = col
    print(f"{name:<20} {str(type_obj):<10} {nullable}")
conn.close()


# ---------------------------------------------------------------------------
# 3. fetchone / fetchmany
# ---------------------------------------------------------------------------
section("3. fetchone / fetchmany")
conn = connect()
cur = conn.cursor()
cur.execute("SELECT * FROM Salesforce1.Salesforce.Account")
first = cur.fetchone()
print(f"fetchone():  {first}")
batch = cur.fetchmany(2)
print(f"fetchmany(2): {batch}")
conn.close()


# ---------------------------------------------------------------------------
# 4. Parameterized query (pyformat)
# ---------------------------------------------------------------------------
section("4. Parameterized query (pyformat)")
conn = connect()
cur = conn.cursor()
cur.execute(
    "SELECT * FROM PostgreSQL_Prod.public.users WHERE id = %(id)s",
    {"id": 1},
)
rows = cur.fetchall()
print(f"Rows with id=1: {rows}")
conn.close()


# ---------------------------------------------------------------------------
# 5. Batch INSERT via executemany + SELECT to verify
# ---------------------------------------------------------------------------
section("5. Batch INSERT via executemany + SELECT to verify")
conn = connect()
cur = conn.cursor()

# Insert 3 beers — pass raw Python values, executemany wraps them with type info
cur.executemany(
    "INSERT INTO PostgreSQL2.public.dbapi20test_booze (beer) VALUES (@beer)",
    [
        {"@beer": "Coopers"},
        {"@beer": "Boags"},
        {"@beer": "Victoria Bitter"},
    ],
)
print("Inserted 3 rows via executemany")

cur.execute("SELECT * FROM PostgreSQL2.public.dbapi20test_booze")
rows = cur.fetchall()
print(f"SELECT after INSERT -> {len(rows)} rows:")
for row in rows:
    print(" ", row)
conn.close()


# ---------------------------------------------------------------------------
# 6. DELETE and verify empty
# ---------------------------------------------------------------------------
section("6. DELETE + verify empty")
conn = connect()
cur = conn.cursor()
cur.execute("DELETE FROM PostgreSQL2.public.dbapi20test_booze")
print("DELETE executed")
cur.execute("SELECT * FROM PostgreSQL2.public.dbapi20test_booze")
rows = cur.fetchall()
print(f"Rows after DELETE: {len(rows)}")
conn.close()


# ---------------------------------------------------------------------------
# 7. Stored procedure call
# ---------------------------------------------------------------------------
section("7. Stored procedure call")
conn = connect()
cur = conn.cursor()
cur.callproc("PostgreSQL2.public.lowercase_input", ("HELLO WORLD",))
rows = cur.fetchall()
print(f"callproc result: {rows}")
conn.close()


# ---------------------------------------------------------------------------
# 8. Error handling — connection error
# ---------------------------------------------------------------------------
section("8. Error handling")
try:
    bad_conn = cdata_connect_ai.connect(
        base_url="http://localhost:9999/api",
        username="x",
        password="y",
        max_retries=0,
    )
    cur = bad_conn.cursor()
    cur.execute("SELECT 1")
except cdata_connect_ai.OperationalError as e:
    print(f"OperationalError caught (expected): {type(e).__name__}")
except Exception as e:
    print(f"Other error: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# 9. Context info
# ---------------------------------------------------------------------------
section("9. Package info")
print(f"cdata_connect_ai version : {cdata_connect_ai.__version__}")
print(f"DB-API level          : {cdata_connect_ai.apilevel}")
print(f"Thread safety         : {cdata_connect_ai.threadsafety}")
print(f"Param style           : {cdata_connect_ai.paramstyle}")
print(f"Type objects          : STRING={cdata_connect_ai.STRING}, NUMBER={cdata_connect_ai.NUMBER}, "
      f"DATETIME={cdata_connect_ai.DATETIME}, BINARY={cdata_connect_ai.BINARY}")
print(f"\n{SEP}\nAll done.\n{SEP}")
