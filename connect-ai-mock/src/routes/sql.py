"""
SQL API routes with streaming support.
"""
import asyncio
import json
import random
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, AsyncGenerator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from src.data import get_store
from src.middleware import get_auth_credentials
from src.models import QueryResult, QueryRequest, BatchRequest, ExecRequest, ColumnInfo, ResultSet

router = APIRouter(prefix="/api", tags=["SQL API"])


def generate_template_value(template_str: str, index: int, variables: dict):
    """Generate a value from a template string."""
    if not isinstance(template_str, str):
        return template_str

    if template_str == "{{index}}":
        return index

    match = re.match(r'\{\{random_int:(\d+):(\d+)\}\}', template_str)
    if match:
        return random.randint(int(match.group(1)), int(match.group(2)))

    match = re.match(r'\{\{random_float:(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)\}\}', template_str)
    if match:
        return round(random.uniform(float(match.group(1)), float(match.group(2))), 2)

    if template_str == "{{random_bool}}":
        return random.choice([True, False])

    match = re.match(r'\{\{random_datetime:(\d{4}-\d{2}-\d{2}):(\d{4}-\d{2}-\d{2})\}\}', template_str)
    if match:
        start = datetime.strptime(match.group(1), "%Y-%m-%d")
        end = datetime.strptime(match.group(2), "%Y-%m-%d")
        delta = end - start
        random_days = random.randint(0, delta.days)
        random_date = start + timedelta(days=random_days,
                                        hours=random.randint(0, 23),
                                        minutes=random.randint(0, 59),
                                        seconds=random.randint(0, 59))
        return random_date.strftime("%Y-%m-%dT%H:%M:%S")

    match = re.match(r'\{\{random_date:(\d{4}-\d{2}-\d{2}):(\d{4}-\d{2}-\d{2})\}\}', template_str)
    if match:
        start = datetime.strptime(match.group(1), "%Y-%m-%d")
        end = datetime.strptime(match.group(2), "%Y-%m-%d")
        delta = end - start
        random_days = random.randint(0, delta.days)
        return (start + timedelta(days=random_days)).strftime("%Y-%m-%d")

    match = re.match(r'\{\{random_time\}\}', template_str)
    if match:
        return f"{random.randint(0,23):02}:{random.randint(0,59):02}:{random.randint(0,59):02}"

    if template_str == "{{uuid}}":
        import uuid
        return str(uuid.uuid4())

    result = template_str
    result = result.replace("{{index}}", str(index))

    for var_name, var_values in variables.items():
        placeholder = "{{" + var_name + "}}"
        if placeholder in result:
            result = result.replace(placeholder, random.choice(var_values))

    return result


def generate_row_from_template(row_template: list, index: int, variables: dict) -> list:
    """Generate a single row from template."""
    return [generate_template_value(col, index, variables) for col in row_template]


async def stream_query_response(
    table_info: dict,
    scenario,
    schema_list: list[ColumnInfo]
) -> AsyncGenerator[str, None]:
    """
    Stream JSON response with rows generated and sent progressively.
    Yields chunks of JSON as rows are generated.
    """
    template = table_info.get("template")
    row_template = template.get("row", []) if template else []
    variables = template.get("variables", {}) if template else {}

    row_count = scenario.row_count if scenario else 0
    pause_after_rows = scenario.pause_after_rows if scenario else row_count
    pause_pattern = scenario.pause_pattern_ms if scenario else []
    truncate_after = scenario.truncate_after_rows if scenario else None
    partial_error = scenario.partial_error if scenario else None

    # Build schema JSON
    schema_json = [col.model_dump(by_alias=True) for col in schema_list]

    # Start JSON response
    yield '{"results": [{"affectedRows": -1, "schema": '
    yield json.dumps(schema_json)
    yield ', "rows": ['

    pause_index = 0
    rows_sent = 0

    for i in range(1, row_count + 1):
        # Check truncation - stop abruptly mid-stream
        if truncate_after and i > truncate_after:
            # Yield partial row to simulate crash
            partial_row = generate_row_from_template(row_template, i, variables)
            partial_json = json.dumps(partial_row)
            # Cut it in the middle
            yield partial_json[:len(partial_json) // 2]
            return  # Stop streaming - incomplete JSON

        # Generate and yield row
        row = generate_row_from_template(row_template, i, variables)

        if i > 1:
            yield ", "
        yield json.dumps(row)
        rows_sent += 1

        # Apply pause after batch — send whitespace keepalives every 30s
        # during long pauses to prevent client socket read timeouts.
        if pause_pattern and pause_after_rows and i % pause_after_rows == 0 and i < row_count:
            pause_ms = pause_pattern[pause_index % len(pause_pattern)]
            pause_index += 1

            keepalive_interval_ms = 30_000  # send keepalive every 30s
            remaining_ms = pause_ms
            while remaining_ms > keepalive_interval_ms:
                await asyncio.sleep(keepalive_interval_ms / 1000.0)
                yield " "  # whitespace keepalive — valid JSON between array elements
                remaining_ms -= keepalive_interval_ms
            if remaining_ms > 0:
                await asyncio.sleep(remaining_ms / 1000.0)

    # Close rows array and result set
    yield "]}"

    # Close results array
    yield "]"

    # Add partial error if configured
    if partial_error:
        yield ', "error": '
        yield json.dumps(partial_error)
    else:
        yield ', "error": null'

    # Close response
    yield "}"


@router.post("/query", response_model=None)
async def execute_query(
    request: QueryRequest,
    workspace: Optional[str] = Query(None),
    credentials: Tuple[str, str] = Depends(get_auth_credentials)
):
    """Execute a SQL query (SELECT, INSERT, UPDATE, DELETE)."""
    store = get_store()
    scenario = store.get_scenario(credentials)

    # Check for error-only scenario (no data)
    if scenario and scenario.error and not scenario.partial_error:
        return QueryResult(
            results=[],
            error={"code": scenario.error["code"], "message": scenario.error["message"]}
        )

    if scenario and scenario.empty_results:
        return QueryResult(
            results=[ResultSet(schema=[], rows=[], affectedRows=-1)],
            error=None
        )

    # Check if this is a streaming scenario (template with rowCount)
    data = store.get_scenario_data(scenario)
    # Substitute parameters so table extraction and DML logic see literal values
    resolved_query = store._substitute_parameters(request.query, request.parameters)
    table_key = store._extract_table_from_query(resolved_query, request.defaultCatalog, request.defaultSchema)

    if table_key and table_key in data["table_data"]:
        table_info = data["table_data"][table_key]

        # Use streaming for template-based scenarios
        if table_info.get("template") and scenario and scenario.row_count:
            columns = table_info.get("columns", [])
            schema_list = [
                ColumnInfo(
                    catalogName=table_info.get("catalog", ""),
                    schemaName=table_info.get("schema", ""),
                    tableName=table_info.get("table", ""),
                    columnName=c.get("name", ""),
                    columnLabel=c.get("label", c.get("name", "")),
                    dataType=c.get("dataType", 1),
                    dataTypeName=c.get("dataTypeName", "STRING"),
                    length=c.get("length", 255),
                    nullable=c.get("nullable", True),
                    ordinal=i + 1
                )
                for i, c in enumerate(columns)
            ]

            return StreamingResponse(
                stream_query_response(table_info, scenario, schema_list),
                media_type="application/json"
            )

    # Non-streaming: return regular response
    return store.execute_query(
        query=request.query,
        default_catalog=request.defaultCatalog,
        default_schema=request.defaultSchema,
        schema_only=request.schemaOnly,
        parameters=request.parameters,
        credentials=credentials
    )


@router.post("/batch", response_model=QueryResult)
async def execute_batch(
    request: BatchRequest,
    workspace: Optional[str] = Query(None),
    credentials: Tuple[str, str] = Depends(get_auth_credentials)
) -> QueryResult:
    """Execute a batch SQL operation."""
    store = get_store()
    return store.execute_batch(
        query=request.query,
        parameters=request.parameters,
        default_catalog=request.defaultCatalog,
        default_schema=request.defaultSchema,
        credentials=credentials
    )


@router.post("/exec", response_model=QueryResult)
async def execute_procedure(
    request: ExecRequest,
    workspace: Optional[str] = Query(None),
    credentials: Tuple[str, str] = Depends(get_auth_credentials)
) -> QueryResult:
    """Execute a stored procedure."""
    store = get_store()
    return store.execute_procedure(
        procedure=request.procedure,
        parameters=request.parameters,
        default_catalog=request.defaultCatalog,
        default_schema=request.defaultSchema,
        credentials=credentials
    )
