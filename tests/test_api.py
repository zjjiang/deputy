"""API 层端到端：HTTP 门禁流程 + 你直接操作真源。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

NOW = "2026-07-23T00:00:00+00:00"


@pytest.fixture()
def client(fresh_db):
    from app import api
    return TestClient(api.app)


def test_state_endpoint(client):
    r = client.get("/api/state")
    assert r.status_code == 200
    assert any(p["id"] == "p1" for p in r.json()["projects"])


def test_gate_flow_over_http(client, fresh_db):
    """分身提议（直接入库）→ API 查到 → 批准 → 真源改变。"""
    from app.store import proposals

    prop = proposals.propose("add_todo", {"project_id": "p1", "text": "HTTP门禁"},
                             reason="端到端", now=NOW)
    # 待批列表能查到
    r = client.get("/api/proposals")
    assert r.status_code == 200 and len(r.json()) == 1
    # 批准前无 todo
    assert client.get("/api/project/p1").json()["todos"] == []
    # 批准
    r = client.post(f"/api/proposals/{prop['id']}/approve")
    assert r.status_code == 200
    # 批准后真源已变
    todos = client.get("/api/project/p1").json()["todos"]
    assert len(todos) == 1 and todos[0]["text"] == "HTTP门禁"


def test_proposals_status_empty_means_all(client, fresh_db):
    """回归测试：?status= 空串应返回全部（含历史），而非 WHERE status=''。"""
    from app.store import proposals

    p1 = proposals.propose("add_to_backlog", {"text": "a"}, reason="r", now=NOW)
    client.post(f"/api/proposals/{p1['id']}/approve")
    proposals.propose("add_to_backlog", {"text": "b"}, reason="r", now=NOW)

    assert len(client.get("/api/proposals?status=").json()) == 2   # 全部
    assert len(client.get("/api/proposals").json()) == 1           # 默认 pending


def test_illegal_stage_returns_400(client):
    r = client.post("/api/project/stage", json={"project_id": "p1", "stage": "operate"})
    assert r.status_code == 400


def test_missing_project_returns_404(client):
    r = client.get("/api/project/nope")
    assert r.status_code == 404


def test_user_direct_edit_bypasses_gate(client):
    """你在看板直接加 todo（你自己拍板）不进提议队列，直接落地。"""
    r = client.post("/api/todo/add", json={"project_id": "p1", "text": "我自己加的"})
    assert r.status_code == 200
    assert client.get("/api/proposals").json() == []  # 没产生提议
    assert len(client.get("/api/project/p1").json()["todos"]) == 1
