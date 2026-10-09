"""报销规则管理接口（按工作区隔离）。"""

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.core.rules_engine import ReimbursementRule
from app.services.workspace import Workspace, get_workspace

router = APIRouter(prefix="/rules", tags=["rules"])


class RuleIn(BaseModel):
    category: str
    subcategory: str
    clause_id: str
    title: str
    content: str
    attachment: str = ""


class RuleUpdate(BaseModel):
    category: Optional[str] = None
    subcategory: Optional[str] = None
    clause_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    attachment: Optional[str] = None


@router.get("")
def list_rules(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    ws: Workspace = Depends(get_workspace),
) -> dict:
    engine = ws.rules
    if search:
        rules = engine.search_rules(search)
    elif category:
        rules = engine.get_rules_by_category(category)
    else:
        rules = engine.get_all_rules()
    return {"count": len(rules), "workspace": ws.id, "rules": [r.to_dict() for r in rules]}


@router.get("/categories")
def list_categories(ws: Workspace = Depends(get_workspace)) -> dict:
    return ws.rules.get_statistics()


@router.get("/stats")
def stats(ws: Workspace = Depends(get_workspace)) -> dict:
    return ws.rules.get_statistics()


@router.post("", status_code=201)
def create_rule(rule: RuleIn, ws: Workspace = Depends(get_workspace)) -> dict:
    obj = ReimbursementRule(**rule.model_dump())
    if not ws.rules.add_rule(obj):
        raise HTTPException(status_code=409, detail=f"规则已存在: {obj.rule_id}")
    ws.rules.save()
    return obj.to_dict()


@router.put("/{rule_id}")
def update_rule(rule_id: str, rule: RuleUpdate, ws: Workspace = Depends(get_workspace)) -> dict:
    payload = {k: v for k, v in rule.model_dump().items() if v is not None}
    if not ws.rules.update_rule(rule_id, **payload):
        raise HTTPException(status_code=404, detail=f"未找到规则: {rule_id}")
    ws.rules.save()
    return ws.rules.get_rule(rule_id).to_dict()


@router.delete("/{rule_id}")
def delete_rule(rule_id: str, ws: Workspace = Depends(get_workspace)) -> dict:
    if not ws.rules.delete_rule(rule_id):
        raise HTTPException(status_code=404, detail=f"未找到规则: {rule_id}")
    ws.rules.save()
    return {"deleted": rule_id}


@router.post("/import")
async def import_rules(
    file: UploadFile = File(...),
    replace: bool = Query(False),
    ws: Workspace = Depends(get_workspace),
) -> dict:
    text = (await file.read()).decode("utf-8", errors="ignore")
    if replace:
        count = ws.rules.replace_from_text(text)
    else:
        before = len(ws.rules.get_all_rules())
        ws.rules.parse_rules_from_text(text)
        count = len(ws.rules.get_all_rules()) - before
    ws.rules.save()
    return {"imported": count, "total": len(ws.rules.get_all_rules())}


@router.post("/reset")
def reset_rules(ws: Workspace = Depends(get_workspace)) -> dict:
    total = ws.reset_rules()
    return {"total": total}
