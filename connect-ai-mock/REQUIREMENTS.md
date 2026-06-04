# Connect AI Query APIs - Mock API Requirements

## 1. Overview

### 1.1 Purpose
Create a mock API server that simulates the CData Connect AI Query APIs for integration testing purposes. The mock should provide predictable, configurable responses that match the production API contract.

### 1.2 Scope
The mock API will implement:
- **SQL API**: Query execution, batch operations, and stored procedure execution
- **Metadata API**: Catalog, schema, table, column, and procedure metadata retrieval

### 1.3 Base URL
- **Production**: `https://cloud.cdata.com/api`
- **Mock**: `http://localhost:8080/api` (configurable)

### 1.4 Operating Modes

The mock server supports two operating modes to balance simplicity and flexibility:

#### Static Mode (Default)
For quick start, CI/CD pipelines, and simple integration tests.

| Feature | Behavior |
|---------|----------|
| Setup | Zero configuration - just start the server |
| Data | Pre-bundled static JSON files |
| Users | Any valid `email:PAT` accepted, returns same data |
| Admin API | Disabled |
| Changes | Requires restart to update data |
| Best for | Unit tests, smoke tests, local development, CI/CD |

**Start command**:
```bash
./mock-server
# or
docker run -p 8080:8080 connect-ai-mock
```

#### Configurable Mode
For complex integration testing, multi-team testing, and scenario-based testing.

| Feature | Behavior |
|---------|----------|
| Setup | Enable via `--mode=configurable` flag |
| Data | Admin API + file-based configuration |
| Users | Different `email:PAT` → different data/behavior |
| Admin API | Enabled (requires `--admin-key`) |
| Changes | Runtime updates without restart |
| Best for | E2E tests, performance testing, chaos testing |

**Start command**:
```bash
./mock-server --mode=configurable --admin-key=your-secret-key
# or
docker run -p 8080:8080 -e MOCK_MODE=configurable -e ADMIN_KEY=secret connect-ai-mock
```

#### Mode Comparison

| Capability | Static Mode | Configurable Mode |
|------------|-------------|-------------------|
| Quick start | Yes | Requires setup |
| Pre-bundled data | Yes | Yes |
| Custom data files | Yes (on startup) | Yes (runtime) |
| Admin API | No | Yes |
| Per-user data | No | Yes |
| Per-user delays | No | Yes |
| Named scenarios | No | Yes |
| Request matching rules | No | Yes |
| Sequence responses | No | Yes |
| CI/CD friendly | Very | Moderate |

---

## 2. Authentication

### 2.1 Authentication Type
HTTP Basic Authentication

### 2.2 Credentials
| Field | Description |
|-------|-------------|
| Username | User email or username |
| Password | Personal Access Token (PAT) |

### 2.3 Authorization Header Format
```
Authorization: Basic {base64(username:PAT)}
```

### 2.4 Mock Behavior
- Accept any valid Basic Auth header format
- Optionally validate against configured test credentials
- Return `401 Unauthorized` for missing/malformed auth headers

---

## 3. Common Response Schema

### 3.1 QueryResult
All endpoints return a `QueryResult` object:

```json
{
  "results": [ResultSet],
  "error": ErrorDetail | null
}
```

### 3.2 ResultSet
```json
{
  "affectedRows": integer,
  "schema": [ColumnInfo],
  "rows": [[any]]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `affectedRows` | integer | Number of rows affected by the operation. `-1` if not applicable (e.g., SELECT queries) |
| `schema` | array | Array of `ColumnInfo` objects describing result columns |
| `rows` | array | Array of arrays containing row data |

### 3.3 ColumnInfo
```json
{
  "catalogName": "string",
  "columnLabel": "string",
  "columnName": "string",
  "dataType": integer,
  "dataTypeName": "string",
  "length": integer,
  "nullable": boolean,
  "ordinal": integer,
  "precision": integer,
  "scale": integer,
  "schemaName": "string",
  "tableName": "string"
}
```

### 3.4 ErrorDetail
```json
{
  "code": integer,
  "message": "string"
}
```

### 3.5 Data Types
| Value | Type Name |
|-------|-----------|
| 1 | STRING |
| 2 | INT |
| 3 | DOUBLE |
| 4 | DATETIME |
| 5 | BOOLEAN |
| 6 | DECIMAL |
| 7 | BINARY |
| 8 | DATE |
| 9 | TIME |
| 10 | BIGINT |
| 11 | SMALLINT |
| 12 | TINYINT |
| 13 | FLOAT |
| 14 | GUID |
| 15 | XML |
| 16 | JSON |
| 17 | CLOB |
| 18 | BLOB |

---

## 4. SQL API Endpoints

### 4.1 Execute Query

**Endpoint**: `POST /api/query`

**Description**: Execute a SQL query (SELECT, INSERT, UPDATE, DELETE statements)

#### Request

**Headers**:
| Header | Value | Required |
|--------|-------|----------|
| `Content-Type` | `application/json` | Yes |
| `Authorization` | `Basic {credentials}` | Yes |

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace` | string | No | Workspace identifier (required if query references a workspace) |

**Request Body** (`QueryRequest`):
```json
{
  "query": "string",
  "defaultCatalog": "string | null",
  "defaultSchema": "string | null",
  "parameters": {
    "paramName": {
      "dataType": integer,
      "value": any
    }
  },
  "schemaOnly": boolean,
  "timeout": integer
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | SQL query to execute (min 1 character) |
| `defaultCatalog` | string | No | Default catalog context for unqualified table names |
| `defaultSchema` | string | No | Default schema context for unqualified table names |
| `parameters` | object | No | Named parameters for parameterized queries |
| `schemaOnly` | boolean | No | If `true`, return only schema without data rows (default: `false`) |
| `timeout` | integer | No | Query timeout in seconds (1-300) |

#### Response

**Status**: `200 OK`

**Body**: `QueryResult`

#### Example

**Request**:
```json
{
  "query": "SELECT Id, Name, Email FROM Salesforce1.Contact LIMIT 10",
  "defaultCatalog": "Salesforce1",
  "timeout": 30
}
```

**Response**:
```json
{
  "results": [
    {
      "affectedRows": -1,
      "schema": [
        {
          "catalogName": "Salesforce1",
          "columnLabel": "Id",
          "columnName": "Id",
          "dataType": 1,
          "dataTypeName": "STRING",
          "length": 18,
          "nullable": false,
          "ordinal": 1,
          "precision": 0,
          "scale": 0,
          "schemaName": "Salesforce",
          "tableName": "Contact"
        },
        {
          "catalogName": "Salesforce1",
          "columnLabel": "Name",
          "columnName": "Name",
          "dataType": 1,
          "dataTypeName": "STRING",
          "length": 255,
          "nullable": true,
          "ordinal": 2,
          "precision": 0,
          "scale": 0,
          "schemaName": "Salesforce",
          "tableName": "Contact"
        },
        {
          "catalogName": "Salesforce1",
          "columnLabel": "Email",
          "columnName": "Email",
          "dataType": 1,
          "dataTypeName": "STRING",
          "length": 255,
          "nullable": true,
          "ordinal": 3,
          "precision": 0,
          "scale": 0,
          "schemaName": "Salesforce",
          "tableName": "Contact"
        }
      ],
      "rows": [
        ["003xx000004TmiUAAS", "John Doe", "john.doe@example.com"],
        ["003xx000004TmiVAAS", "Jane Smith", "jane.smith@example.com"]
      ]
    }
  ],
  "error": null
}
```

---

### 4.2 Execute Batch Query

**Endpoint**: `POST /api/batch`

**Description**: Execute batch SQL operations (typically INSERT, UPDATE, DELETE)

#### Request

**Headers**:
| Header | Value | Required |
|--------|-------|----------|
| `Content-Type` | `application/json` | Yes |
| `Authorization` | `Basic {credentials}` | Yes |

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace` | string | No | Workspace identifier |

**Request Body** (`BatchRequest`):
```json
{
  "query": "string",
  "defaultCatalog": "string | null",
  "defaultSchema": "string | null",
  "parameters": [
    {
      "dataType": integer,
      "value": any
    }
  ],
  "timeout": integer
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | SQL statement to execute (min 1 character) |
| `defaultCatalog` | string | No | Default catalog context |
| `defaultSchema` | string | No | Default schema context |
| `parameters` | array | No | Array of parameter objects with `dataType` and `value` |
| `timeout` | integer | No | Query timeout in seconds (1-300) |

#### Response

**Status**: `200 OK`

**Body**: `QueryResult`

#### Example

**Request**:
```json
{
  "query": "INSERT INTO Salesforce1.Contact (Name, Email) VALUES (?, ?)",
  "parameters": [
    {"dataType": 1, "value": "New Contact"},
    {"dataType": 1, "value": "new@example.com"}
  ],
  "timeout": 60
}
```

**Response**:
```json
{
  "results": [
    {
      "affectedRows": 1,
      "schema": [],
      "rows": []
    }
  ],
  "error": null
}
```

---

### 4.3 Execute Procedure

**Endpoint**: `POST /api/exec`

**Description**: Execute a stored procedure

#### Request

**Headers**:
| Header | Value | Required |
|--------|-------|----------|
| `Content-Type` | `application/json` | Yes |
| `Authorization` | `Basic {credentials}` | Yes |

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace` | string | No | Workspace identifier |

**Request Body** (`ExecRequest`):
```json
{
  "procedure": "string",
  "defaultCatalog": "string | null",
  "defaultSchema": "string | null",
  "parameters": {
    "paramName": {
      "direction": integer,
      "dataType": integer,
      "value": any
    }
  },
  "timeout": integer
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `procedure` | string | Yes | Procedure name to execute (min 1 character) |
| `defaultCatalog` | string | No | Default catalog context |
| `defaultSchema` | string | No | Default schema context |
| `parameters` | object | No | Named parameters with direction, dataType, and value |
| `timeout` | integer | No | Execution timeout in seconds (1-300) |

**Parameter Direction Values**:
| Value | Direction |
|-------|-----------|
| 1 | IN |
| 2 | OUT |
| 4 | IN_OUT |
| 5 | RETURN |

#### Response

**Status**: `200 OK`

**Body**: `QueryResult`

#### Example

**Request**:
```json
{
  "procedure": "GetContactsByAccount",
  "defaultCatalog": "Salesforce1",
  "parameters": {
    "AccountId": {
      "direction": 1,
      "dataType": 1,
      "value": "001xx000003GYf5AAG"
    }
  },
  "timeout": 30
}
```

**Response**:
```json
{
  "results": [
    {
      "affectedRows": -1,
      "schema": [
        {
          "catalogName": "Salesforce1",
          "columnLabel": "ContactId",
          "columnName": "ContactId",
          "dataType": 1,
          "dataTypeName": "STRING",
          "length": 18,
          "nullable": false,
          "ordinal": 1,
          "precision": 0,
          "scale": 0,
          "schemaName": "Salesforce",
          "tableName": ""
        }
      ],
      "rows": [
        ["003xx000004TmiUAAS"],
        ["003xx000004TmiVAAS"]
      ]
    }
  ],
  "error": null
}
```

---

## 5. Metadata API Endpoints

### 5.1 List Catalogs

**Endpoint**: `GET /api/catalogs`

**Description**: Retrieve available catalogs (data sources/connections)

#### Request

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace` | string | No | Restricts results to the specified workspace |

#### Response

**Status**: `200 OK`

**Body**: `QueryResult`

**Result Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `TABLE_CAT` | STRING | Catalog name |

#### Example Response
```json
{
  "results": [
    {
      "affectedRows": -1,
      "schema": [
        {
          "columnName": "TABLE_CAT",
          "dataType": 1,
          "dataTypeName": "STRING",
          "ordinal": 1
        }
      ],
      "rows": [
        ["Salesforce1"],
        ["PostgreSQL_Prod"],
        ["MySQL_Analytics"]
      ]
    }
  ],
  "error": null
}
```

---

### 5.2 List Schemas

**Endpoint**: `GET /api/schemas`

**Description**: Retrieve schemas within a catalog

#### Request

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace` | string | No | Restricts results to the specified workspace |
| `catalogName` | string | No | Restricts results to the specified catalog |
| `schemaName` | string | No | Restricts results to the specified schema |

#### Response

**Status**: `200 OK`

**Body**: `QueryResult`

**Result Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `TABLE_SCHEM` | STRING | Schema name |
| `TABLE_CATALOG` | STRING | Catalog name |

#### Example Response
```json
{
  "results": [
    {
      "affectedRows": -1,
      "schema": [
        {"columnName": "TABLE_SCHEM", "dataType": 1, "ordinal": 1},
        {"columnName": "TABLE_CATALOG", "dataType": 1, "ordinal": 2}
      ],
      "rows": [
        ["Salesforce", "Salesforce1"],
        ["public", "PostgreSQL_Prod"]
      ]
    }
  ],
  "error": null
}
```

---

### 5.3 List Tables

**Endpoint**: `GET /api/tables`

**Description**: Retrieve tables within a schema

#### Request

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace` | string | No | Restricts results to the specified workspace |
| `catalogName` | string | No | Restricts results to the specified catalog |
| `schemaName` | string | No | Restricts results to the specified schema |
| `tableName` | string | No | Restricts results to the specified table |
| `tableType` | string | No | Restricts results to the specified table type(s) |

#### Response

**Status**: `200 OK`

**Body**: `QueryResult`

**Result Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `TABLE_CAT` | STRING | Catalog name |
| `TABLE_SCHEM` | STRING | Schema name |
| `TABLE_NAME` | STRING | Table name |
| `TABLE_TYPE` | STRING | Table type (TABLE, VIEW, SYSTEM TABLE) |
| `REMARKS` | STRING | Table description/comments |

#### Example Response
```json
{
  "results": [
    {
      "affectedRows": -1,
      "schema": [
        {"columnName": "TABLE_CAT", "dataType": 1, "ordinal": 1},
        {"columnName": "TABLE_SCHEM", "dataType": 1, "ordinal": 2},
        {"columnName": "TABLE_NAME", "dataType": 1, "ordinal": 3},
        {"columnName": "TABLE_TYPE", "dataType": 1, "ordinal": 4},
        {"columnName": "REMARKS", "dataType": 1, "ordinal": 5}
      ],
      "rows": [
        ["Salesforce1", "Salesforce", "Account", "TABLE", "Salesforce Account object"],
        ["Salesforce1", "Salesforce", "Contact", "TABLE", "Salesforce Contact object"],
        ["Salesforce1", "Salesforce", "Lead", "TABLE", "Salesforce Lead object"]
      ]
    }
  ],
  "error": null
}
```

---

### 5.4 List Columns

**Endpoint**: `GET /api/columns`

**Description**: Retrieve column metadata for a table

#### Request

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace` | string | No | Restricts results to the specified workspace |
| `catalogName` | string | No | Restricts results to the specified catalog |
| `schemaName` | string | No | Restricts results to the specified schema |
| `tableName` | string | No | Restricts results to the specified table |
| `columnName` | string | No | Restricts results to the specified column |

#### Response

**Status**: `200 OK`

**Body**: `QueryResult`

**Result Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `TABLE_CAT` | STRING | Catalog name |
| `TABLE_SCHEM` | STRING | Schema name |
| `TABLE_NAME` | STRING | Table name |
| `COLUMN_NAME` | STRING | Column name |
| `DATA_TYPE` | INT | SQL data type code |
| `TYPE_NAME` | STRING | Data type name |
| `COLUMN_SIZE` | INT | Column size/length |
| `NULLABLE` | INT | Nullable (0=No, 1=Yes, 2=Unknown) |
| `REMARKS` | STRING | Column description |
| `COLUMN_DEF` | STRING | Default value |
| `ORDINAL_POSITION` | INT | Column position (1-based) |
| `IS_NULLABLE` | STRING | "YES" or "NO" |

#### Example Response
```json
{
  "results": [
    {
      "affectedRows": -1,
      "schema": [
        {"columnName": "TABLE_CAT", "dataType": 1, "ordinal": 1},
        {"columnName": "TABLE_SCHEM", "dataType": 1, "ordinal": 2},
        {"columnName": "TABLE_NAME", "dataType": 1, "ordinal": 3},
        {"columnName": "COLUMN_NAME", "dataType": 1, "ordinal": 4},
        {"columnName": "DATA_TYPE", "dataType": 2, "ordinal": 5},
        {"columnName": "TYPE_NAME", "dataType": 1, "ordinal": 6},
        {"columnName": "COLUMN_SIZE", "dataType": 2, "ordinal": 7},
        {"columnName": "NULLABLE", "dataType": 2, "ordinal": 8},
        {"columnName": "ORDINAL_POSITION", "dataType": 2, "ordinal": 9}
      ],
      "rows": [
        ["Salesforce1", "Salesforce", "Contact", "Id", 1, "STRING", 18, 0, 1],
        ["Salesforce1", "Salesforce", "Contact", "Name", 1, "STRING", 255, 1, 2],
        ["Salesforce1", "Salesforce", "Contact", "Email", 1, "STRING", 255, 1, 3],
        ["Salesforce1", "Salesforce", "Contact", "Phone", 1, "STRING", 40, 1, 4],
        ["Salesforce1", "Salesforce", "Contact", "AccountId", 1, "STRING", 18, 1, 5]
      ]
    }
  ],
  "error": null
}
```

---

### 5.5 List Primary Keys

**Endpoint**: `GET /api/primaryKeys`

**Description**: Retrieve primary key information for a table

#### Request

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace` | string | No | Restricts results to the specified workspace |
| `catalogName` | string | No | Restricts results to the specified catalog |
| `schemaName` | string | No | Restricts results to the specified schema |
| `tableName` | string | No | Restricts results to the specified table |

#### Response

**Status**: `200 OK`

**Body**: `QueryResult`

**Result Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `TABLE_CAT` | STRING | Catalog name |
| `TABLE_SCHEM` | STRING | Schema name |
| `TABLE_NAME` | STRING | Table name |
| `COLUMN_NAME` | STRING | Primary key column name |
| `KEY_SEQ` | INT | Sequence number within primary key (1-based) |
| `PK_NAME` | STRING | Primary key constraint name |

#### Example Response
```json
{
  "results": [
    {
      "affectedRows": -1,
      "schema": [
        {"columnName": "TABLE_CAT", "dataType": 1, "ordinal": 1},
        {"columnName": "TABLE_SCHEM", "dataType": 1, "ordinal": 2},
        {"columnName": "TABLE_NAME", "dataType": 1, "ordinal": 3},
        {"columnName": "COLUMN_NAME", "dataType": 1, "ordinal": 4},
        {"columnName": "KEY_SEQ", "dataType": 2, "ordinal": 5},
        {"columnName": "PK_NAME", "dataType": 1, "ordinal": 6}
      ],
      "rows": [
        ["Salesforce1", "Salesforce", "Contact", "Id", 1, "PK_Contact"]
      ]
    }
  ],
  "error": null
}
```

---

### 5.6 List Procedures

**Endpoint**: `GET /api/procedures`

**Description**: Retrieve available stored procedures

#### Request

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace` | string | No | Restricts results to the specified workspace |
| `catalogName` | string | No | Restricts results to the specified catalog |
| `schemaName` | string | No | Restricts results to the specified schema |
| `procedureName` | string | No | Restricts results to the specified procedure |

#### Response

**Status**: `200 OK`

**Body**: `QueryResult`

**Result Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `PROCEDURE_CAT` | STRING | Catalog name |
| `PROCEDURE_SCHEM` | STRING | Schema name |
| `PROCEDURE_NAME` | STRING | Procedure name |
| `REMARKS` | STRING | Procedure description |
| `PROCEDURE_TYPE` | INT | Procedure type (1=No result, 2=Returns result) |

#### Example Response
```json
{
  "results": [
    {
      "affectedRows": -1,
      "schema": [
        {"columnName": "PROCEDURE_CAT", "dataType": 1, "ordinal": 1},
        {"columnName": "PROCEDURE_SCHEM", "dataType": 1, "ordinal": 2},
        {"columnName": "PROCEDURE_NAME", "dataType": 1, "ordinal": 3},
        {"columnName": "REMARKS", "dataType": 1, "ordinal": 4},
        {"columnName": "PROCEDURE_TYPE", "dataType": 2, "ordinal": 5}
      ],
      "rows": [
        ["Salesforce1", "Salesforce", "GetContactsByAccount", "Retrieves contacts for an account", 2],
        ["Salesforce1", "Salesforce", "CreateLead", "Creates a new lead record", 1]
      ]
    }
  ],
  "error": null
}
```

---

### 5.7 List Procedure Parameters

**Endpoint**: `GET /api/procedureParameters`

**Description**: Retrieve parameters for a stored procedure

#### Request

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace` | string | No | Restricts results to the specified workspace |
| `catalogName` | string | No | Restricts results to the specified catalog |
| `schemaName` | string | No | Restricts results to the specified schema |
| `procedureName` | string | No | Restricts results to the specified procedure |
| `paramName` | string | No | Restricts results to the specified parameter |

#### Response

**Status**: `200 OK`

**Body**: `QueryResult`

**Result Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `PROCEDURE_CAT` | STRING | Catalog name |
| `PROCEDURE_SCHEM` | STRING | Schema name |
| `PROCEDURE_NAME` | STRING | Procedure name |
| `COLUMN_NAME` | STRING | Parameter name |
| `COLUMN_TYPE` | INT | Parameter type (1=IN, 2=OUT, 4=IN_OUT, 5=RETURN) |
| `DATA_TYPE` | INT | SQL data type code |
| `TYPE_NAME` | STRING | Data type name |
| `NULLABLE` | INT | Nullable (0=No, 1=Yes) |

#### Example Response
```json
{
  "results": [
    {
      "affectedRows": -1,
      "schema": [
        {"columnName": "PROCEDURE_CAT", "dataType": 1, "ordinal": 1},
        {"columnName": "PROCEDURE_SCHEM", "dataType": 1, "ordinal": 2},
        {"columnName": "PROCEDURE_NAME", "dataType": 1, "ordinal": 3},
        {"columnName": "COLUMN_NAME", "dataType": 1, "ordinal": 4},
        {"columnName": "COLUMN_TYPE", "dataType": 2, "ordinal": 5},
        {"columnName": "DATA_TYPE", "dataType": 2, "ordinal": 6},
        {"columnName": "TYPE_NAME", "dataType": 1, "ordinal": 7}
      ],
      "rows": [
        ["Salesforce1", "Salesforce", "GetContactsByAccount", "AccountId", 1, 1, "STRING"],
        ["Salesforce1", "Salesforce", "GetContactsByAccount", "Limit", 1, 2, "INT"]
      ]
    }
  ],
  "error": null
}
```

---

### 5.8 List Exported Keys

**Endpoint**: `GET /api/exportedKeys`

**Description**: Retrieve foreign key relationships where the specified table is the parent

#### Request

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace` | string | No | Restricts results to the specified workspace |
| `catalogName` | string | No | Restricts results to the specified catalog |
| `schemaName` | string | No | Restricts results to the specified schema |
| `tableName` | string | No | Restricts results to the specified table |

#### Response

**Status**: `200 OK`

**Body**: `QueryResult`

**Result Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `PKTABLE_CAT` | STRING | Primary key table catalog |
| `PKTABLE_SCHEM` | STRING | Primary key table schema |
| `PKTABLE_NAME` | STRING | Primary key table name |
| `PKCOLUMN_NAME` | STRING | Primary key column name |
| `FKTABLE_CAT` | STRING | Foreign key table catalog |
| `FKTABLE_SCHEM` | STRING | Foreign key table schema |
| `FKTABLE_NAME` | STRING | Foreign key table name |
| `FKCOLUMN_NAME` | STRING | Foreign key column name |
| `KEY_SEQ` | INT | Sequence number |
| `FK_NAME` | STRING | Foreign key name |
| `PK_NAME` | STRING | Primary key name |

---

### 5.9 List Imported Keys

**Endpoint**: `GET /api/importedKeys`

**Description**: Retrieve foreign key relationships where the specified table is the child

#### Request

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace` | string | No | Restricts results to the specified workspace |
| `catalogName` | string | No | Restricts results to the specified catalog |
| `schemaName` | string | No | Restricts results to the specified schema |
| `tableName` | string | No | Restricts results to the specified table |

#### Response

**Status**: `200 OK`

**Body**: `QueryResult`

**Result Columns**: Same as List Exported Keys

---

## 6. Error Handling

### 6.1 HTTP Status Codes

| Status | Description |
|--------|-------------|
| `200` | Success |
| `400` | Bad Request - Invalid request body or parameters |
| `401` | Unauthorized - Missing or invalid authentication |
| `403` | Forbidden - Insufficient permissions |
| `404` | Not Found - Resource does not exist |
| `408` | Request Timeout - Query exceeded timeout |
| `500` | Internal Server Error |

### 6.2 Error Response Format

All errors return a `QueryResult` with the `error` field populated:

```json
{
  "results": [],
  "error": {
    "code": 400,
    "message": "Invalid SQL syntax: unexpected token at position 15"
  }
}
```

### 6.3 Common Error Codes

| Code | Description |
|------|-------------|
| `400` | Invalid request/query syntax |
| `401` | Authentication failed |
| `403` | Permission denied |
| `404` | Catalog/Schema/Table not found |
| `408` | Query timeout |
| `500` | Internal server error |

---

## 7. Mock API Features

### 7.0 Feature Availability by Mode

| Feature | Static Mode | Configurable Mode |
|---------|:-----------:|:-----------------:|
| Pre-bundled mock data | Yes | Yes |
| Load data from JSON/YAML files | Yes (startup only) | Yes (runtime) |
| Any `email:PAT` accepted | Yes | Yes |
| User-specific mock data | No | Yes |
| User-specific delays | No | Yes |
| Named scenarios | No | Yes |
| Per-request headers (`X-Mock-*`) | No | Yes |
| Sequence-based responses | No | Yes |
| Request matching rules | No | Yes |
| Admin API | No | Yes |

---

### 7.1 User Identity & Session Management

> **Mode**: Configurable Mode only

The **username:PAT** combination from the Basic Auth header is the primary key for determining mock behavior. Each unique combination can have:
- Its own mock data set (catalogs, schemas, tables, rows)
- Its own scenario configuration
- Its own delay settings
- Its own error behavior

**Example**:
- `user1@test.com:token_abc` → Returns Salesforce data, no delay
- `user2@test.com:token_xyz` → Returns PostgreSQL data, 2s delay
- `error@test.com:token_err` → Always returns errors

> **Static Mode**: Any valid `email:PAT` combination is accepted and returns the same default mock data.

---

### 7.2 Mock Data Configuration

#### 7.2.1 Configuration Methods

| Method | Description | Static Mode | Configurable Mode |
|--------|-------------|:-----------:|:-----------------:|
| JSON Files | Load from JSON files at startup | Yes | Yes |
| YAML Files | Load from YAML files at startup | Yes | Yes |
| Admin API | Configure dynamically via REST | No | Yes |

#### 7.2.2 JSON File Structure

```
mock-data/
├── default/                    # Default data (fallback)
│   ├── catalogs.json
│   ├── schemas.json
│   ├── tables.json
│   └── data/
│       └── Salesforce1.Contact.json
│
└── users/                      # User-specific data
    ├── user1@test.com_token123/
    │   ├── config.json         # User settings
    │   ├── catalogs.json
    │   └── data/
    │       └── Salesforce1.Contact.json
    │
    └── user2@test.com_token456/
        ├── config.json
        └── ...
```

**User `config.json`**:
```json
{
  "name": "Test User 1",
  "description": "Standard test user with Salesforce access",
  "scenario": "happy-path",
  "delay": {
    "global": 0,
    "endpoints": {},
    "random": null
  },
  "errorRate": 0.0
}
```

**Example `catalogs.json`**:
```json
{
  "catalogs": [
    {"name": "Salesforce1", "description": "Salesforce CRM"},
    {"name": "PostgreSQL_Prod", "description": "Production Database"}
  ]
}
```

**Example `data/Salesforce1.Contact.json`**:
```json
{
  "catalog": "Salesforce1",
  "schema": "Salesforce",
  "table": "Contact",
  "columns": [
    {"name": "Id", "dataType": 1, "dataTypeName": "STRING", "length": 18, "nullable": false},
    {"name": "Name", "dataType": 1, "dataTypeName": "STRING", "length": 255, "nullable": true},
    {"name": "Email", "dataType": 1, "dataTypeName": "STRING", "length": 255, "nullable": true}
  ],
  "rows": [
    ["003xx000001", "John Doe", "john@example.com"],
    ["003xx000002", "Jane Smith", "jane@example.com"]
  ]
}
```

#### 7.2.3 YAML File Configuration

**Example `mock-config.yaml`**:
```yaml
users:
  "user1@test.com:token123":
    name: Test User 1
    scenario: happy-path
    delay: 0
    catalogs:
      - name: Salesforce1
        schemas:
          - name: Salesforce
            tables:
              - name: Contact
                columns:
                  - {name: Id, type: STRING, primaryKey: true}
                  - {name: Name, type: STRING}
                  - {name: Email, type: STRING, nullable: true}
                data:
                  - ["003xx000001", "John Doe", "john@example.com"]
                  - ["003xx000002", "Jane Smith", "jane@example.com"]

  "slowuser@test.com:token456":
    name: Slow Response User
    scenario: happy-path
    delay:
      min: 1000
      max: 3000
    catalogs:
      - name: Salesforce1
        # inherits default data

  "erroruser@test.com:token789":
    name: Error User
    scenario: error-state
    errorRate: 1.0
```

---

### 7.3 Request Matching

> **Mode**: Configurable Mode only

Priority-based matching to determine which response to return.

#### 7.3.1 Matching Priority (Highest to Lowest)

1. **User-specific matches** (based on username:PAT)
2. **Exact match rules**
3. **Pattern/regex match rules**
4. **Rule-based conditional matches**
5. **Default mock data**

#### 7.3.2 Exact Match

Match specific query strings or request bodies exactly.

```json
{
  "matches": [
    {
      "type": "exact",
      "user": "user1@test.com:token123",
      "request": {
        "endpoint": "/api/query",
        "body": {
          "query": "SELECT * FROM Salesforce1.Contact WHERE Id = '003xx000001'"
        }
      },
      "response": {
        "status": 200,
        "body": {
          "results": [{"affectedRows": -1, "schema": [...], "rows": [["003xx000001", "John Doe", "john@example.com"]]}],
          "error": null
        }
      }
    }
  ]
}
```

#### 7.3.3 Pattern/Regex Match

Match using regular expressions.

```json
{
  "matches": [
    {
      "type": "pattern",
      "user": "*",
      "request": {
        "endpoint": "/api/query",
        "bodyPatterns": {
          "query": "SELECT.*FROM\\s+Salesforce1\\.Contact.*"
        }
      },
      "response": {
        "useTableData": "Salesforce1.Salesforce.Contact"
      }
    }
  ]
}
```

**Pattern Locations**:
| Location | Description |
|----------|-------------|
| `endpoint` | URL path pattern |
| `queryParams` | Query parameter patterns |
| `bodyPatterns` | Request body field patterns |

#### 7.3.4 Rule-Based Matching

Conditional rules with multiple criteria.

```json
{
  "matches": [
    {
      "type": "rule",
      "name": "Block DELETE for limited users",
      "conditions": [
        {"field": "user", "operator": "equals", "value": "limited@test.com:token000"},
        {"field": "body.query", "operator": "matches", "value": "^DELETE.*"}
      ],
      "response": {
        "status": 200,
        "body": {
          "results": [],
          "error": {"code": 403, "message": "DELETE operations not permitted"}
        }
      }
    }
  ]
}
```

**Supported Operators**:
| Operator | Description |
|----------|-------------|
| `equals` | Exact match |
| `notEquals` | Not equal |
| `contains` | Contains substring |
| `startsWith` | Starts with |
| `endsWith` | Ends with |
| `matches` | Regex match |
| `in` | Value in array |

---

### 7.4 Scenario Support

> **Mode**: Configurable Mode only

#### 7.4.1 Named Scenarios

Predefined configurations that can be assigned to users.

```json
{
  "scenarios": {
    "happy-path": {
      "description": "All requests succeed with normal data",
      "errorRate": 0.0,
      "delay": 0
    },
    "error-state": {
      "description": "All requests return errors",
      "errorRate": 1.0,
      "errorResponse": {
        "code": 500,
        "message": "Database connection failed"
      }
    },
    "slow-response": {
      "description": "Simulate slow database",
      "delay": {"min": 2000, "max": 5000}
    },
    "empty-results": {
      "description": "All queries return empty",
      "forceEmptyResults": true
    },
    "partial-failure": {
      "description": "50% of requests fail",
      "errorRate": 0.5
    },
    "timeout": {
      "description": "Requests timeout",
      "delay": 310000
    }
  }
}
```

#### 7.4.2 Per-Request Scenario Control

Override scenario via request headers.

| Header | Description | Example |
|--------|-------------|---------|
| `X-Mock-Scenario` | Use scenario for this request | `error-state` |
| `X-Mock-Delay` | Add delay (ms) | `2000` |
| `X-Mock-Error` | Force error response | `{"code":500,"message":"Forced"}` |

#### 7.4.3 Sequence-Based Responses

Return different responses on successive calls.

```json
{
  "matches": [
    {
      "type": "sequence",
      "user": "sequence@test.com:token",
      "request": {"endpoint": "/api/query"},
      "responses": [
        {"body": {"results": [{"rows": [["First"]]}], "error": null}},
        {"body": {"results": [{"rows": [["Second"]]}], "error": null}},
        {"body": {"results": [], "error": {"code": 429, "message": "Rate limited"}}}
      ],
      "afterLast": "cycle"
    }
  ]
}
```

| `afterLast` | Behavior |
|-------------|----------|
| `cycle` | Repeat from first |
| `repeat` | Keep returning last |
| `error` | Return 500 error |

---

### 7.5 Delay Simulation

#### 7.5.1 Global Delay

> **Mode**: Both modes (Static via environment variable, Configurable via Admin API)

Apply to all responses.

```json
{
  "delay": {
    "global": 500
  }
}
```

#### 7.5.2 Per-Endpoint Delay

Different delays per endpoint.

```json
{
  "delay": {
    "endpoints": {
      "/api/query": 1000,
      "/api/batch": 2000,
      "/api/exec": 1500,
      "/api/catalogs": 100
    }
  }
}
```

#### 7.5.3 Random Range Delay

Random delay within min-max range.

```json
{
  "delay": {
    "random": {
      "enabled": true,
      "min": 100,
      "max": 2000
    }
  }
}
```

#### 7.5.4 Per-User Delay

Configured per username:PAT combination.

```json
{
  "users": {
    "fast@test.com:token1": {
      "delay": 0
    },
    "slow@test.com:token2": {
      "delay": 3000
    },
    "variable@test.com:token3": {
      "delay": {"min": 500, "max": 2000}
    }
  }
}
```

#### 7.5.5 Delay Feature Availability

| Delay Type | Static Mode | Configurable Mode |
|------------|:-----------:|:-----------------:|
| Global delay | Yes (env var) | Yes |
| Per-endpoint delay | Yes (config file) | Yes |
| Random range delay | Yes (config file) | Yes |
| Per-user delay | No | Yes |
| Per-request header | No | Yes |

#### 7.5.6 Delay Priority (Configurable Mode)

1. Per-request header (`X-Mock-Delay`)
2. User-specific delay (username:PAT config)
3. Scenario delay
4. Per-endpoint delay
5. Random range (added to above)
6. Global delay

#### 7.5.7 Static Mode Delay Configuration

In Static Mode, delays are configured via environment variables or config file at startup:

```bash
# Environment variables
MOCK_GLOBAL_DELAY_MS=500
MOCK_RANDOM_DELAY_MIN=100
MOCK_RANDOM_DELAY_MAX=1000

# Or via config file (mock-config.json)
{
  "delay": {
    "global": 500,
    "random": {"min": 100, "max": 1000},
    "endpoints": {
      "/api/query": 1000
    }
  }
}
```

---

### 7.6 Mock Admin API

> **Mode**: Configurable Mode only

REST API for runtime configuration. Not available in Static Mode.

**Base URL**: `http://localhost:8080/mock-admin`

**Authentication**: `X-Admin-Key` header (set via `--admin-key` flag or `ADMIN_KEY` env var)

**Enable**: Start server with `--mode=configurable --admin-key=your-secret`

---

#### 7.6.1 User Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/users` | List all configured users |
| `GET` | `/users/{email}:{pat}` | Get user configuration |
| `PUT` | `/users/{email}:{pat}` | Create/update user |
| `DELETE` | `/users/{email}:{pat}` | Delete user |
| `PATCH` | `/users/{email}:{pat}/delay` | Update user delay |
| `PATCH` | `/users/{email}:{pat}/scenario` | Update user scenario |
| `PUT` | `/users/{email}:{pat}/data` | Upload user's mock data |

**Create User Example**:
```bash
curl -X PUT "http://localhost:8080/mock-admin/users/test@example.com:mytoken" \
  -H "X-Admin-Key: admin123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "scenario": "happy-path",
    "delay": 500,
    "catalogs": ["Salesforce1"]
  }'
```

**Set User Delay**:
```bash
curl -X PATCH "http://localhost:8080/mock-admin/users/test@example.com:mytoken/delay" \
  -H "X-Admin-Key: admin123" \
  -H "Content-Type: application/json" \
  -d '{"delay": 2000}'
```

---

#### 7.6.2 Mock Data Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/data/catalogs` | List all catalogs |
| `PUT` | `/data/catalogs/{name}` | Create/update catalog |
| `DELETE` | `/data/catalogs/{name}` | Delete catalog |
| `PUT` | `/data/{catalog}/{schema}/{table}` | Set table data |
| `GET` | `/data/{catalog}/{schema}/{table}` | Get table data |
| `DELETE` | `/data/{catalog}/{schema}/{table}` | Delete table data |
| `PUT` | `/users/{email}:{pat}/data/{catalog}/{schema}/{table}` | Set user-specific table data |

**Set Table Data Example**:
```bash
curl -X PUT "http://localhost:8080/mock-admin/data/Salesforce1/Salesforce/Contact" \
  -H "X-Admin-Key: admin123" \
  -H "Content-Type: application/json" \
  -d '{
    "columns": [
      {"name": "Id", "dataType": 1, "dataTypeName": "STRING"},
      {"name": "Name", "dataType": 1, "dataTypeName": "STRING"}
    ],
    "rows": [
      ["001", "John Doe"],
      ["002", "Jane Smith"]
    ]
  }'
```

**Set User-Specific Data**:
```bash
curl -X PUT "http://localhost:8080/mock-admin/users/test@example.com:mytoken/data/Salesforce1/Salesforce/Contact" \
  -H "X-Admin-Key: admin123" \
  -H "Content-Type: application/json" \
  -d '{
    "columns": [...],
    "rows": [["custom_001", "Custom Contact"]]
  }'
```

---

#### 7.6.3 Scenario Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/scenarios` | List all scenarios |
| `GET` | `/scenarios/{name}` | Get scenario details |
| `PUT` | `/scenarios/{name}` | Create/update scenario |
| `DELETE` | `/scenarios/{name}` | Delete scenario |

---

#### 7.6.4 Delay Configuration

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/delay` | Get delay configuration |
| `PUT` | `/delay/global` | Set global delay |
| `PUT` | `/delay/endpoints` | Set per-endpoint delays |
| `PUT` | `/delay/random` | Set random delay range |

---

#### 7.6.5 Request Matching Rules

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/matches` | List all matching rules |
| `POST` | `/matches` | Add matching rule |
| `DELETE` | `/matches/{ruleId}` | Delete rule |
| `DELETE` | `/matches` | Clear all rules |

---

#### 7.6.6 Server Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/reset` | Reset all configuration to defaults |
| `POST` | `/reload` | Reload configuration from files |

---

## 8. Non-Functional Requirements

### 8.1 Performance
- Response time < 100ms for mock responses (excluding configured delays)
- Support for concurrent requests

### 8.2 Portability
- Docker container support
- Cross-platform (Windows, macOS, Linux)

### 8.3 Startup Configuration

#### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--port` | Server port | `8080` |
| `--mode` | Operating mode (`static` or `configurable`) | `static` |
| `--admin-key` | Admin API key (required for configurable mode) | - |
| `--data-dir` | Directory for mock data files | `./mock-data` |
| `--config` | Path to configuration file | `./mock-config.json` |

#### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MOCK_PORT` | Server port | `8080` |
| `MOCK_MODE` | Operating mode | `static` |
| `ADMIN_KEY` | Admin API key | - |
| `MOCK_DATA_DIR` | Mock data directory | `./mock-data` |
| `MOCK_CONFIG_FILE` | Configuration file path | `./mock-config.json` |
| `MOCK_GLOBAL_DELAY_MS` | Global delay in milliseconds | `0` |
| `MOCK_RANDOM_DELAY_MIN` | Minimum random delay | `0` |
| `MOCK_RANDOM_DELAY_MAX` | Maximum random delay | `0` |

### 8.4 Docker Support

**Static Mode**:
```bash
docker run -p 8080:8080 connect-ai-mock
```

**Configurable Mode**:
```bash
docker run -p 8080:8080 \
  -e MOCK_MODE=configurable \
  -e ADMIN_KEY=your-secret-key \
  -v ./my-data:/app/mock-data \
  connect-ai-mock
```

**With custom data volume**:
```bash
docker run -p 8080:8080 \
  -v ./my-mock-data:/app/mock-data \
  connect-ai-mock
```

---

## 9. Test Data Requirements

### 9.1 Default Mock Data Set
The mock should include a default data set with:

- **Catalogs**: Salesforce1, PostgreSQL_Prod, MySQL_Analytics
- **Schemas**: Per catalog (e.g., Salesforce, public)
- **Tables**: Common business objects (Account, Contact, Lead, Order, Product)
- **Columns**: Realistic column definitions per table
- **Sample Data**: 10-50 rows per table

### 9.2 Custom Data Sets
Support for loading custom data sets for specific test scenarios.

---

## 10. Appendix

### 10.1 Quick Start Examples

#### Static Mode (Default)

```bash
# Start server
./mock-server

# Test - any credentials work
curl -X GET "http://localhost:8080/api/catalogs" \
  -H "Authorization: Basic $(echo -n 'anyuser@test.com:anytoken' | base64)"

# Execute query
curl -X POST "http://localhost:8080/api/query" \
  -H "Authorization: Basic $(echo -n 'anyuser@test.com:anytoken' | base64)" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM Salesforce1.Contact LIMIT 5"}'
```

#### Configurable Mode

```bash
# Start server in configurable mode
./mock-server --mode=configurable --admin-key=admin123

# Create a test user with specific configuration
curl -X PUT "http://localhost:8080/mock-admin/users/testuser@example.com:token123" \
  -H "X-Admin-Key: admin123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "scenario": "happy-path",
    "delay": 0
  }'

# Set user-specific data
curl -X PUT "http://localhost:8080/mock-admin/users/testuser@example.com:token123/data/Salesforce1/Salesforce/Contact" \
  -H "X-Admin-Key: admin123" \
  -H "Content-Type: application/json" \
  -d '{
    "columns": [
      {"name": "Id", "dataType": 1, "dataTypeName": "STRING"},
      {"name": "Name", "dataType": 1, "dataTypeName": "STRING"}
    ],
    "rows": [
      ["custom_001", "Custom Contact for Test User"]
    ]
  }'

# Now query as that user - gets custom data
curl -X POST "http://localhost:8080/api/query" \
  -H "Authorization: Basic $(echo -n 'testuser@example.com:token123' | base64)" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM Salesforce1.Contact"}'

# Create an error user
curl -X PUT "http://localhost:8080/mock-admin/users/erroruser@example.com:errortoken" \
  -H "X-Admin-Key: admin123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Error User",
    "scenario": "error-state"
  }'

# Query as error user - gets errors
curl -X POST "http://localhost:8080/api/query" \
  -H "Authorization: Basic $(echo -n 'erroruser@example.com:errortoken' | base64)" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM Salesforce1.Contact"}'

# Create a slow user
curl -X PUT "http://localhost:8080/mock-admin/users/slowuser@example.com:slowtoken" \
  -H "X-Admin-Key: admin123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Slow User",
    "scenario": "happy-path",
    "delay": {"min": 2000, "max": 5000}
  }'
```

### 10.2 API Examples (Both Modes)

**List Catalogs**:
```bash
curl -X GET "http://localhost:8080/api/catalogs" \
  -H "Authorization: Basic $(echo -n 'user@test.com:token' | base64)"
```

**Execute Query**:
```bash
curl -X POST "http://localhost:8080/api/query" \
  -H "Authorization: Basic $(echo -n 'user@test.com:token' | base64)" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM Salesforce1.Contact LIMIT 5"}'
```

**List Tables**:
```bash
curl -X GET "http://localhost:8080/api/tables?catalogName=Salesforce1&schemaName=Salesforce" \
  -H "Authorization: Basic $(echo -n 'user@test.com:token' | base64)"
```

**Execute with Parameters**:
```bash
curl -X POST "http://localhost:8080/api/query" \
  -H "Authorization: Basic $(echo -n 'user@test.com:token' | base64)" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM Salesforce1.Contact WHERE Id = @id",
    "parameters": {
      "id": {"dataType": 1, "value": "003xx000001"}
    }
  }'
```

### 10.3 Per-Request Override (Configurable Mode Only)

```bash
# Force a specific scenario for one request
curl -X POST "http://localhost:8080/api/query" \
  -H "Authorization: Basic $(echo -n 'user@test.com:token' | base64)" \
  -H "Content-Type: application/json" \
  -H "X-Mock-Scenario: error-state" \
  -d '{"query": "SELECT * FROM Salesforce1.Contact"}'

# Force a delay for one request
curl -X POST "http://localhost:8080/api/query" \
  -H "Authorization: Basic $(echo -n 'user@test.com:token' | base64)" \
  -H "Content-Type: application/json" \
  -H "X-Mock-Delay: 3000" \
  -d '{"query": "SELECT * FROM Salesforce1.Contact"}'

# Force an error for one request
curl -X POST "http://localhost:8080/api/query" \
  -H "Authorization: Basic $(echo -n 'user@test.com:token' | base64)" \
  -H "Content-Type: application/json" \
  -H "X-Mock-Error: {\"code\": 500, \"message\": \"Forced error\"}" \
  -d '{"query": "SELECT * FROM Salesforce1.Contact"}'
```
