"""
Metadata API routes.
"""
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, Query

from src.data import get_store
from src.middleware import get_auth_credentials
from src.models import QueryResult

router = APIRouter(prefix="/api", tags=["Metadata API"])


@router.get("/catalogs", response_model=QueryResult)
async def list_catalogs(
    workspace: Optional[str] = Query(None),
    credentials: Tuple[str, str] = Depends(get_auth_credentials)
) -> QueryResult:
    """List available catalogs (data sources)."""
    store = get_store()
    return store.get_catalogs(workspace=workspace, credentials=credentials)


@router.get("/schemas", response_model=QueryResult)
async def list_schemas(
    workspace: Optional[str] = Query(None),
    catalogName: Optional[str] = Query(None),
    schemaName: Optional[str] = Query(None),
    credentials: Tuple[str, str] = Depends(get_auth_credentials)
) -> QueryResult:
    """List schemas within a catalog."""
    store = get_store()
    return store.get_schemas(
        catalog_name=catalogName,
        schema_name=schemaName,
        credentials=credentials
    )


@router.get("/tables", response_model=QueryResult)
async def list_tables(
    workspace: Optional[str] = Query(None),
    catalogName: Optional[str] = Query(None),
    schemaName: Optional[str] = Query(None),
    tableName: Optional[str] = Query(None),
    tableType: Optional[str] = Query(None),
    credentials: Tuple[str, str] = Depends(get_auth_credentials)
) -> QueryResult:
    """List tables within a schema."""
    store = get_store()
    return store.get_tables(
        catalog_name=catalogName,
        schema_name=schemaName,
        table_name=tableName,
        table_type=tableType,
        credentials=credentials
    )


@router.get("/columns", response_model=QueryResult)
async def list_columns(
    workspace: Optional[str] = Query(None),
    catalogName: Optional[str] = Query(None),
    schemaName: Optional[str] = Query(None),
    tableName: Optional[str] = Query(None),
    columnName: Optional[str] = Query(None),
    credentials: Tuple[str, str] = Depends(get_auth_credentials)
) -> QueryResult:
    """List columns for a table."""
    store = get_store()
    return store.get_columns(
        catalog_name=catalogName,
        schema_name=schemaName,
        table_name=tableName,
        column_name=columnName,
        credentials=credentials
    )


@router.get("/primaryKeys", response_model=QueryResult)
async def list_primary_keys(
    workspace: Optional[str] = Query(None),
    catalogName: Optional[str] = Query(None),
    schemaName: Optional[str] = Query(None),
    tableName: Optional[str] = Query(None),
    credentials: Tuple[str, str] = Depends(get_auth_credentials)
) -> QueryResult:
    """List primary keys for a table."""
    store = get_store()
    return store.get_primary_keys(
        catalog_name=catalogName,
        schema_name=schemaName,
        table_name=tableName,
        credentials=credentials
    )


@router.get("/procedures", response_model=QueryResult)
async def list_procedures(
    workspace: Optional[str] = Query(None),
    catalogName: Optional[str] = Query(None),
    schemaName: Optional[str] = Query(None),
    procedureName: Optional[str] = Query(None),
    credentials: Tuple[str, str] = Depends(get_auth_credentials)
) -> QueryResult:
    """List stored procedures."""
    store = get_store()
    return store.get_procedures(
        catalog_name=catalogName,
        schema_name=schemaName,
        procedure_name=procedureName,
        credentials=credentials
    )


@router.get("/procedureParameters", response_model=QueryResult)
async def list_procedure_parameters(
    workspace: Optional[str] = Query(None),
    catalogName: Optional[str] = Query(None),
    schemaName: Optional[str] = Query(None),
    procedureName: Optional[str] = Query(None),
    paramName: Optional[str] = Query(None),
    credentials: Tuple[str, str] = Depends(get_auth_credentials)
) -> QueryResult:
    """List parameters for a stored procedure."""
    store = get_store()
    return store.get_procedure_parameters(
        catalog_name=catalogName,
        schema_name=schemaName,
        procedure_name=procedureName,
        param_name=paramName,
        credentials=credentials
    )


@router.get("/exportedKeys", response_model=QueryResult)
async def list_exported_keys(
    workspace: Optional[str] = Query(None),
    catalogName: Optional[str] = Query(None),
    schemaName: Optional[str] = Query(None),
    tableName: Optional[str] = Query(None),
    credentials: Tuple[str, str] = Depends(get_auth_credentials)
) -> QueryResult:
    """List foreign keys where the specified table is the parent."""
    store = get_store()
    return store.get_exported_keys(
        catalog_name=catalogName,
        schema_name=schemaName,
        table_name=tableName,
        credentials=credentials
    )


@router.get("/importedKeys", response_model=QueryResult)
async def list_imported_keys(
    workspace: Optional[str] = Query(None),
    catalogName: Optional[str] = Query(None),
    schemaName: Optional[str] = Query(None),
    tableName: Optional[str] = Query(None),
    credentials: Tuple[str, str] = Depends(get_auth_credentials)
) -> QueryResult:
    """List foreign keys where the specified table is the child."""
    store = get_store()
    return store.get_imported_keys(
        catalog_name=catalogName,
        schema_name=schemaName,
        table_name=tableName,
        credentials=credentials
    )
