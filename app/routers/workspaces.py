"""工作区管理接口（多用户隔离）。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.workspace import manager

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceIn(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)


@router.get("")
def list_workspaces() -> dict:
    return {"workspaces": manager.list()}


@router.post("", status_code=201)
def create_workspace(body: WorkspaceIn) -> dict:
    try:
        ws = manager.get(body.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": ws.id, "rules_count": len(ws.rules.get_all_rules())}


@router.delete("/{workspace_id}")
def delete_workspace(workspace_id: str) -> dict:
    if not manager.delete(workspace_id):
        raise HTTPException(status_code=404, detail=f"未找到工作区: {workspace_id}")
    return {"deleted": workspace_id}
