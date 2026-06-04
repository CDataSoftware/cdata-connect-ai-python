"""
Pydantic models for Connect AI Query API request/response schemas.
"""
from typing import Any, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Common Response Models
# ============================================================================

class ColumnInfo(BaseModel):
    """Column metadata information."""
    catalogName: str = ""
    columnLabel: str = ""
    columnName: str = ""
    dataType: int = 1
    dataTypeName: str = "STRING"
    length: int = 0
    nullable: bool = True
    ordinal: int = 1
    precision: int = 0
    scale: int = 0
    schemaName: str = ""
    tableName: str = ""


class ErrorDetail(BaseModel):
    """Error information."""
    code: int
    message: str


class ResultSet(BaseModel):
    """Result set containing query results."""
    affectedRows: int = -1
    schema_: list[ColumnInfo] = Field(default_factory=list, alias="schema")
    rows: list[list[Any]] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class QueryResult(BaseModel):
    """Standard response for all API endpoints."""
    results: list[ResultSet] = Field(default_factory=list)
    error: Optional[ErrorDetail] = None


# ============================================================================
# SQL API Request Models
# ============================================================================

class QueryParameter(BaseModel):
    """Parameter for parameterized queries."""
    dataType: int
    value: Any


class QueryRequest(BaseModel):
    """Request body for /api/query endpoint."""
    query: str = Field(..., min_length=1)
    defaultCatalog: Optional[str] = None
    defaultSchema: Optional[str] = None
    parameters: Optional[dict[str, QueryParameter]] = None
    schemaOnly: bool = False
    timeout: Optional[int] = Field(None, ge=1, le=300)


class BatchParameter(BaseModel):
    """Parameter for batch operations."""
    dataType: int
    value: Any


class BatchRequest(BaseModel):
    """Request body for /api/batch endpoint."""
    query: str = Field(..., min_length=1)
    defaultCatalog: Optional[str] = None
    defaultSchema: Optional[str] = None
    # Each element maps "@param_name" -> {"dataType": int, "value": any}
    parameters: Optional[list[dict[str, Any]]] = None
    timeout: Optional[int] = Field(None, ge=1, le=300)


class ProcedureParameter(BaseModel):
    """Parameter for stored procedure execution."""
    direction: int = 1  # 1=IN, 2=OUT, 4=IN_OUT, 5=RETURN
    dataType: int
    value: Any = None


class ExecRequest(BaseModel):
    """Request body for /api/exec endpoint."""
    procedure: str = Field(..., min_length=1)
    defaultCatalog: Optional[str] = None
    defaultSchema: Optional[str] = None
    parameters: Optional[dict[str, ProcedureParameter]] = None
    timeout: Optional[int] = Field(None, ge=1, le=300)
