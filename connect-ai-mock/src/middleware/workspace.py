"""
Workspace and virtual schema request validation, mirroring QueryRouter (CLOUD-26538).
"""
import uuid
from typing import Optional

from fastapi import HTTPException, Path, Query


def validate_workspace_id(workspaceId: str = Path(...)) -> str:
    """Reject a workspaces/{workspaceId} path segment that is not a GUID."""
    try:
        uuid.UUID(workspaceId)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_REQUEST",
                    "message": f"workspaceId must be a GUID: {workspaceId}"},
        )
    return workspaceId


def validate_virtual_schema(
    workspace: Optional[str] = Query(None),
    virtualSchema: Optional[str] = Query(None),
) -> Optional[str]:
    """?workspace= is the deprecated alias of ?virtualSchema=; reject conflicting values."""
    if workspace is not None and virtualSchema is not None and workspace != virtualSchema:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_REQUEST",
                    "message": "workspace and virtualSchema have different values"},
        )
    return virtualSchema if virtualSchema is not None else workspace
