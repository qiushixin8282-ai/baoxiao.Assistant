"""报销规则管理接口。"""

from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.core.rules_engine import ReimbursementRule, get_rules_engine

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
) -> dict:
    engine = get_rules_engine()
    if search:
        rules = engine.search_rules(search)
    elif category:
        rules = engine.get_rules_by_category(category)
    else:
        rules = engine.get_all_rules()
    return {"count": len(rules), "rules": [r.to_dict() for r in rules]}


@router.get("/categories")
def list_categories() -> dict:
    engine = get_rules_engine()
    return engine.get_statistics()


@router.get("/stats")
def stats() -> dict:
    return get_rules_engine().get_statistics()


@router.post("", status_code=201)
def create_rule(rule: RuleIn) -> dict:
    engine = get_rules_engine()
    obj = ReimbursementRule(**rule.model_dump())
    if not engine.add_rule(obj):
        raise HTTPException(status_code=409, detail=f"规则已存在: {obj.rule_id}")
    return obj.to_dict()


@router.put("/{rule_id}")
def update_rule(rule_id: str, rule: RuleUpdate) -> dict:
    engine = get_rules_engine()
    payload = {k: v for k, v in rule.model_dump().items() if v is not None}
    if not engine.update_rule(rule_id, **payload):
        raise HTTPException(status_code=404, detail=f"未找到规则: {rule_id}")
    return engine.get_rule(rule_id).to_dict()


@router.delete("/{rule_id}")
def delete_rule(rule_id: str) -> dict:
    if not get_rules_engine().delete_rule(rule_id):
        raise HTTPException(status_code=404, detail=f"未找到规则: {rule_id}")
    return {"deleted": rule_id}


@router.post("/import")
async def import_rules(file: UploadFile = File(...), replace: bool = Query(False)) -> dict:
    engine = get_rules_engine()
    text = (await file.read()).decode("utf-8", errors="ignore")
    if replace:
        count = engine.replace_from_text(text)
    else:
        before = len(engine.get_all_rules())
        engine.parse_rules_from_text(text)
        count = len(engine.get_all_rules()) - before
    return {"imported": count, "total": len(engine.get_all_rules())}


@router.post("/reset")
def reset_rules() -> dict:
    from app.config import DEFAULT_RULES_FILE

    engine = get_rules_engine()
    engine.rules = []
    engine.categories = {}
    engine.load_from_file(DEFAULT_RULES_FILE)
    return {"total": len(engine.get_all_rules())}
