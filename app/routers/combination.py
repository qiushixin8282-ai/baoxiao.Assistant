"""发票组合接口：按目标金额选择最优发票子集。"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.combination import invoice_amount, select_combination
from app.services.store import get_invoice_store

router = APIRouter(prefix="/combination", tags=["combination"])


class CombinationRequest(BaseModel):
    target: float
    tolerance: float = 0.0
    invoice_ids: Optional[List[str]] = None


@router.post("")
def combine(req: CombinationRequest) -> dict:
    store = get_invoice_store()
    records = store.get_many(req.invoice_ids) if req.invoice_ids else store.list()
    if not records:
        raise HTTPException(status_code=400, detail="没有可用于组合的发票")

    usable = [(rec, invoice_amount(rec)) for rec in records]
    usable = [(rec, amt) for rec, amt in usable if amt is not None]
    skipped = len(records) - len(usable)
    if not usable:
        raise HTTPException(status_code=400, detail="所选发票均无有效金额")

    result = select_combination([amt for _, amt in usable], req.target, req.tolerance)
    if result is None:
        raise HTTPException(status_code=400, detail="无法计算组合")

    chosen = [usable[i][0] for i in result["indices"]]
    return {
        "target": req.target,
        "tolerance": req.tolerance,
        "sum": result["sum"],
        "diff": result["diff"],
        "exact": result["exact"],
        "count": len(chosen),
        "skipped": skipped,
        "invoices": chosen,
    }
