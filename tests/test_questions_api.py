"""questions API 端到端：建题/编辑/到期聚合/回答操作，全走 HTTP。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

NOW = "2026-07-23T00:00:00+00:00"


@pytest.fixture()
def client(fresh_db):
    from app import api
    return TestClient(api.app)


def _add(client, **kw):
    body = {"title": "测试题", "prompt": "本周动向?"}
    body.update(kw)
    return client.post("/api/question/add", json=body)


def test_question_crud_over_http(client):
    r = _add(client)
    assert r.status_code == 200
    q = r.json()
    assert q["id"] == "q1" and q["cadence"] == "daily"

    r = client.post("/api/question/q1/edit", json={"title": "改名", "cadence": "weekly"})
    assert r.status_code == 200
    assert r.json()["title"] == "改名" and r.json()["cadence"] == "weekly"

    assert len(client.get("/api/questions").json()) == 1

    r = client.post("/api/question/q1/remove")
    assert r.status_code == 200
    assert client.get("/api/questions").json() == []


def test_question_add_illegal_cadence_400(client):
    assert _add(client, cadence="hourly").status_code == 400


def test_question_edit_missing_404(client):
    assert client.post("/api/question/q9/edit", json={"title": "x"}).status_code == 404


def test_question_remove_missing_404(client):
    assert client.post("/api/question/q9/remove").status_code == 404


def test_question_active_endpoint(client):
    _add(client)
    r = client.post("/api/question/q1/active", json={"active": False})
    assert r.status_code == 200 and r.json()["active"] is False
    r = client.post("/api/question/q1/active", json={"active": True})
    assert r.status_code == 200 and r.json()["active"] is True
    assert client.post("/api/question/q9/active", json={"active": True}).status_code == 404


def test_questions_overview_aggregates_and_run(client):
    """列表聚合：due/到期原因；「跑一次」打标落库。"""
    from app.store import questions

    _add(client)
    r = client.post("/api/question/q1/run")
    assert r.status_code == 200
    data = {x["id"]: x for x in client.get("/api/questions").json()}
    assert data["q1"]["due"] is True and data["q1"]["due_reason"] == "manual-request"
    # run 生效落库：store 里 requested_at 已打标
    assert questions.get_question("q1")["requested_at"] is not None


def test_answers_flow_over_http(client):
    """v2 提交后：列表只数最新版未读、预览是 v2、标已读归零、删除只剩 v1。"""
    from app.store import questions

    _add(client)
    questions.submit_answer("q1", "v1 正文", run_date="2026-07-23", now=NOW)
    questions.submit_answer("q1", "v2 正文", run_date="2026-07-23",
                            now="2026-07-23T12:00:00+00:00")

    r = client.get("/api/question/q1/answers")
    assert r.status_code == 200 and len(r.json()) == 2
    assert r.json()[0]["body_md"] == "v2 正文"  # 新版本在前

    data = client.get("/api/questions").json()[0]
    assert data["unread_count"] == 1  # 只有最新版计未读
    assert data["preview"].startswith("v2 正文")
    assert data["last_answer_at"] == "2026-07-23T12:00:00+00:00"

    aid = r.json()[0]["id"]
    assert client.post(f"/api/answer/{aid}/read").status_code == 200
    assert client.get("/api/questions").json()[0]["unread_count"] == 0

    assert client.post(f"/api/answer/{aid}/delete").status_code == 200
    assert len(client.get("/api/question/q1/answers").json()) == 1


def test_answers_limit(client):
    from app.store import questions

    _add(client)
    questions.submit_answer("q1", "d1v1", run_date="2026-07-23", now=NOW)
    questions.submit_answer("q1", "d1v2", run_date="2026-07-23",
                            now="2026-07-23T12:00:00+00:00")
    questions.submit_answer("q1", "d2v1", run_date="2026-07-24",
                            now="2026-07-24T01:00:00+00:00")
    r = client.get("/api/question/q1/answers?limit=2")
    assert [a["body_md"] for a in r.json()] == ["d2v1", "d1v2"]


def test_answers_missing_question_404(client):
    assert client.get("/api/question/q9/answers").status_code == 404


def test_answer_read_delete_missing_404(client):
    assert client.post("/api/answer/999/read").status_code == 404
    assert client.post("/api/answer/999/delete").status_code == 404
