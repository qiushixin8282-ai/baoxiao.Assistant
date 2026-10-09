"""API 冒烟测试（无需 LLM / OCR 依赖）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["rules_count"] > 0


def test_invoice_schema():
    res = client.get("/api/invoices/schema")
    assert res.status_code == 200
    assert "通用字段" in res.json()["fields"]


def test_rules_list_and_search():
    res = client.get("/api/rules")
    assert res.status_code == 200
    assert res.json()["count"] > 0

    res = client.get("/api/rules", params={"search": "住宿"})
    assert res.status_code == 200
    assert res.json()["count"] >= 1


def test_rule_crud():
    payload = {
        "category": "测试类别",
        "subcategory": "测试子类",
        "clause_id": "X1",
        "title": "测试条款",
        "content": "这是一条测试规则",
    }
    res = client.post("/api/rules", json=payload)
    assert res.status_code == 201
    rule_id = res.json()["rule_id"]

    res = client.put(f"/api/rules/{rule_id}", json={"content": "更新后的内容"})
    assert res.status_code == 200
    assert res.json()["content"] == "更新后的内容"

    res = client.delete(f"/api/rules/{rule_id}")
    assert res.status_code == 200


def test_audit_pass():
    fields = {
        "通用字段": {
            "发票号码": "12345678",
            "开票日期": "2026-10-01",
            "价税合计": "580",
        }
    }
    res = client.post(
        "/api/audit",
        json={"fields": fields, "context": {"city": "北京", "amount": "580", "nights": 1}},
    )
    assert res.status_code == 200
    summary = res.json()["summary"]
    assert summary["failed"] == 0


def test_audit_fail_hotel_limit():
    fields = {
        "通用字段": {
            "发票号码": "12345678",
            "开票日期": "2026-10-01",
            "价税合计": "900",
        }
    }
    res = client.post(
        "/api/audit",
        json={"fields": fields, "context": {"city": "北京", "amount": "900", "nights": 1}},
    )
    assert res.json()["summary"]["conclusion"] == "不通过"


def _sample(invoice_no, amount, code="044001", name="测试公司"):
    return {
        "通用字段": {
            "发票代码": code,
            "发票号码": invoice_no,
            "开票日期": "2026-10-01",
            "价税合计": str(amount),
        },
        "销售方信息": {"名称": name},
    }


def test_select_combination_exact():
    from app.core.combination import select_combination

    result = select_combination([300.0, 200.0, 150.0, 50.0], target=500.0)
    assert result is not None
    assert result["sum"] == 500.0
    assert result["exact"] is True


def test_combination_endpoint_and_ledger():
    client.delete("/api/invoices")
    from app.services.workspace import manager

    store = manager.get("default").store
    r1 = store.add(_sample("1001", 300))
    r2 = store.add(_sample("1002", 200))
    store.add(_sample("1003", 150))

    res = client.post("/api/combination", json={"target": 500, "tolerance": 0})
    assert res.status_code == 200
    body = res.json()
    assert body["sum"] == 500.0 and body["exact"] is True

    res = client.post(
        "/api/ledger/export",
        json={"invoice_ids": [r1["id"], r2["id"]], "format": "csv"},
    )
    assert res.status_code == 200
    assert "发票号码" in res.text

    res = client.post(
        "/api/ledger/export",
        json={"invoice_ids": [r1["id"], r2["id"]], "format": "html"},
    )
    assert res.status_code == 200
    assert "报销台账" in res.text

    res = client.post(
        "/api/ledger/export",
        json={"invoice_ids": [r1["id"], r2["id"]], "format": "xlsx"},
    )
    assert res.status_code in (200, 503)  # 未装 openpyxl 时优雅降级
    if res.status_code == 200:
        assert res.content[:2] == b"PK"  # xlsx 实为 zip

    client.delete("/api/invoices")


def test_duplicates():
    client.delete("/api/invoices")
    from app.services.workspace import manager

    store = manager.get("default").store
    store.add(_sample("2001", 100))
    store.add(_sample("2001", 100))
    res = client.get("/api/invoices/duplicates")
    assert res.status_code == 200
    assert res.json()["duplicate_groups"] >= 1
    client.delete("/api/invoices")


def test_workspace_isolation():
    client.delete("/api/workspaces/ws-test")
    client.post("/api/workspaces", json={"id": "ws-test"})

    base = client.get("/api/rules").json()["count"]
    payload = {
        "category": "隔离测试",
        "subcategory": "子类",
        "clause_id": "W1",
        "title": "仅工作区可见",
        "content": "内容",
    }
    res = client.post("/api/rules", json=payload, headers={"X-Workspace-Id": "ws-test"})
    assert res.status_code == 201

    ws_count = client.get("/api/rules", headers={"X-Workspace-Id": "ws-test"}).json()["count"]
    default_count = client.get("/api/rules").json()["count"]
    assert ws_count == base + 1
    assert default_count == base

    client.delete("/api/workspaces/ws-test")


def test_invalid_workspace_id():
    res = client.get("/api/rules", headers={"X-Workspace-Id": "../evil"})
    assert res.status_code == 400


def test_approval_config():
    res = client.get("/api/approval/config")
    assert res.status_code == 200
    assert "channels" in res.json()


def test_ocr_status():
    res = client.get("/api/system/ocr")
    assert res.status_code == 200
    assert "available" in res.json()
