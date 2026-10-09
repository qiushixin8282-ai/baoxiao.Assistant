"""报销台账导出接口（按工作区隔离）。"""

from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.core.ledger import to_csv, to_html, to_xlsx
from app.services.workspace import Workspace, get_workspace

router = APIRouter(prefix="/ledger", tags=["ledger"])


class ExportRequest(BaseModel):
    invoice_ids: Optional[List[str]] = None
    format: str = "csv"  # csv | xlsx | html
    title: str = "报销台账"


def _content_disposition(filename: str) -> str:
    return f"attachment; filename*=UTF-8''{quote(filename)}"


@router.post("/export")
def export(req: ExportRequest, ws: Workspace = Depends(get_workspace)) -> Response:
    records = ws.store.get_many(req.invoice_ids) if req.invoice_ids else ws.store.list()
    if not records:
        raise HTTPException(status_code=400, detail="没有可导出的发票")

    fmt = req.format.lower()
    if fmt == "csv":
        return Response(
            content=to_csv(records),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": _content_disposition(f"{req.title}.csv")},
        )
    if fmt == "xlsx":
        try:
            data = to_xlsx(records, title=req.title)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": _content_disposition(f"{req.title}.xlsx")},
        )
    if fmt == "html":
        return Response(
            content=to_html(records, title=req.title),
            media_type="text/html; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail=f"不支持的导出格式: {req.format}")
