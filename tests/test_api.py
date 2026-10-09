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
