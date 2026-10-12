"""learning API 端到端：track CRUD/大纲/自评/小结，全走 HTTP。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

NOW = "2026-10-12T00:00:00+00:00"


@pytest.fixture()
def client(fresh_db):
    from app import api
    return TestClient(api.app)


def _add_track(client, **kw):
    body = {"title": "具身智能", "goal": "能看懂前沿论文"}
    body.update(kw)
    return client.post("/api/learning/track/add", json=body)


def test_track_crud_over_http(client):
    r = _add_track(client)
    assert r.status_code == 200
    t = r.json()
    assert t["id"] == "l1" and t["status"] == "active"

    r = client.post("/api/learning/track/l1/edit", json={"title": "改名", "goal": "新目标"})
    assert r.status_code == 200 and r.json()["title"] == "改名"

    r = client.post("/api/learning/track/l1/status", json={"status": "paused"})
    assert r.status_code == 200 and r.json()["status"] == "paused"
    assert client.post("/api/learning/track/l1/status", json={"status": "bad"}).status_code == 400

    assert len(client.get("/api/learning").json()) == 1
    assert client.post("/api/learning/track/l1/remove").status_code == 200
    assert client.get("/api/learning").json() == []


def test_track_add_empty_goal_400(client):
    assert _add_track(client, goal="  ").status_code == 400


def test_track_edit_missing_404(client):
    assert client.post("/api/learning/track/l9/edit", json={"title": "x"}).status_code == 404
    assert client.post("/api/learning/track/l9/remove").status_code == 404


def test_curriculum_and_self_assessment_flow(client):
    """建题→HTTP 直设大纲→自评→概览进度与下一课。"""
    from app.store import learning

    _add_track(client)
    r = client.post(
        "/api/learning/track/l1/curriculum",
        json={"points": [{"title": "A", "summary": "s"}, {"title": "B"}]},
    )
    assert r.status_code == 200
    assert [p["title"] for p in r.json()["points"]] == ["A", "B"]

    kid = r.json()["points"][0]["id"]
    r = client.post(f"/api/learning/point/{kid}/status", json={"status": "learned"})
    assert r.status_code == 200 and r.json()["status"] == "learned"

    overview = client.get("/api/learning").json()[0]
    assert overview["progress"] == {"total": 2, "learned": 1, "todo": 1, "revisit": 0}
    assert overview["next_point"]["title"] == "B"

    # 非法路径
    assert client.post(
        "/api/learning/track/l1/curriculum", json={"points": []}
    ).status_code == 400
    assert client.post(
        "/api/learning/point/k999/status", json={"status": "learned"}
    ).status_code == 404
    assert client.post(
        "/api/learning/point/kid/status", json={"status": "learned"}
    ).status_code == 404


def test_track_detail_with_notes(client):
    from app.store import learning

    _add_track(client)
    learning.submit_lesson_note("l1", "A", "第一课小结", now=NOW)
    learning.submit_lesson_note("l1", "A", "回炉小结", now=NOW)

    r = client.get("/api/learning/l1")
    assert r.status_code == 200
    body = r.json()
    assert body["progress"]["total"] >= 0 and "next_point" in body
    assert len(body["notes"]) == 2 and body["notes"][0]["body_md"] == "回炉小结"

    r = client.get("/api/learning/l1/notes?limit=1")
    assert r.status_code == 200 and len(r.json()) == 1
    assert client.get("/api/learning/l9").status_code == 404
