"""intel 代理端点：/api/intel/docs、/api/intel/domains、/api/intel/reading/{id}。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

NOW = "2026-10-12T00:00:00+00:00"


@pytest.fixture()
def client(fresh_db, monkeypatch):
    from app import api
    return TestClient(api.app)


@pytest.fixture()
def fake_curator(monkeypatch):
    """替换 curator 模块函数，记录调用并返回固定数据。"""
    from app.services import curator

    calls: dict = {}

    def fake_list_docs(**kw):
        calls["list_docs"] = kw
        return {"total": 2, "docs": [{"id": 1, "title": "四星论文", "stars": 4},
                                     {"id": 2, "title": "未判定", "stars": None}]}

    def fake_domains(client=None):
        calls["domains"] = True
        return [{"id": 1, "name": "具身智能", "enabled": True}]

    def fake_set_reading(doc_id, *, is_read=None, is_favorite=None, client=None):
        calls["set_reading"] = {"doc_id": doc_id, "is_read": is_read,
                                "is_favorite": is_favorite}
        return {"ok": True}

    monkeypatch.setattr(curator, "list_docs", fake_list_docs)
    monkeypatch.setattr(curator, "domains", fake_domains)
    monkeypatch.setattr(curator, "set_reading", fake_set_reading)
    yield calls


def test_intel_docs_proxy(client, fake_curator):
    r = client.get("/api/intel/docs", params={
        "domain_id": 1, "kind": "paper", "min_stars": 4, "sort": "stars", "page": 2,
    })
    assert r.status_code == 200
    assert r.json()["total"] == 2
    call = fake_curator["list_docs"]
    assert call["domain_id"] == 1 and call["kind"] == "paper"
    assert call["min_stars"] == 4 and call["sort"] == "stars"
    assert call["page"] == 2


def test_intel_docs_kind_tag_passthrough(client, fake_curator):
    """文章子类（技术/商业）筛选参数原样透传 feed-curator。"""
    r = client.get("/api/intel/docs", params={"kind": "article", "kind_tag": "tech"})
    assert r.status_code == 200
    call = fake_curator["list_docs"]
    assert call["kind"] == "article" and call["kind_tag"] == "tech"
    # 不传时端点侧为 None（不发空参数由 curator 层 _clean 保证，见 test_curator.py）
    client.get("/api/intel/docs")
    assert fake_curator["list_docs"]["kind_tag"] is None


def test_intel_docs_invalid_min_stars_422(client):
    """越界门槛走 FastAPI 原生校验（与 feed-curator 侧同款 422）。"""
    assert client.get("/api/intel/docs", params={"min_stars": 9}).status_code == 422
    assert client.get("/api/intel/docs", params={"min_stars": 0}).status_code == 422


def test_intel_domains_proxy(client, fake_curator):
    r = client.get("/api/intel/domains")
    assert r.status_code == 200
    assert r.json()[0]["name"] == "具身智能"


def test_intel_reading_proxy(client, fake_curator):
    r = client.post("/api/intel/reading/7", json={"is_read": True})
    assert r.status_code == 200 and r.json()["ok"] is True
    assert fake_curator["set_reading"] == {"doc_id": 7, "is_read": True,
                                           "is_favorite": None}


def test_intel_unavailable_503_and_questions_unaffected(client, fresh_db, monkeypatch):
    """降级：图书馆闭馆 → 情报流 503；奏折（questions）完全不受影响。"""
    from app.services import curator

    def boom(**kw):
        raise curator.CuratorUnavailable("图书馆不可达：ConnectTimeout")

    monkeypatch.setattr(curator, "list_docs", boom)
    r = client.get("/api/intel/docs")
    assert r.status_code == 503
    assert "闭馆" in r.json()["detail"] or "不可达" in r.json()["detail"]
    # 奏折面无恙：问题列表照常可用
    r2 = client.post("/api/question/add", json={"title": "t", "prompt": "p"})
    assert r2.status_code == 200
