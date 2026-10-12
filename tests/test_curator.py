"""curator 客户端（唯一集成出口）：参数转发、响应透传、三态降级。MockTransport 注入。"""
from __future__ import annotations

import json

import httpx
import pytest

from app.services import curator


def _mk(handler) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:9003"
    )


def test_list_docs_forwards_params_and_passthrough():
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        return httpx.Response(200, json={"total": 1, "docs": [{"id": 1, "title": "t"}]})

    body = curator.list_docs(
        domain_id=3, kind="paper", min_stars=4, sort="stars",
        page=2, per_page=30, client=_mk(handler),
    )
    assert body["docs"][0]["id"] == 1
    url = captured["url"]
    for fragment in ("domain_id=3", "kind=paper", "min_stars=4",
                     "sort=stars", "offset=30", "limit=30"):
        assert fragment in url, fragment


def test_list_docs_omits_none_params():
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        return httpx.Response(200, json={"total": 0, "docs": []})

    curator.list_docs(client=_mk(handler))
    url = captured["url"]
    assert "domain_id" not in url and "min_stars" not in url
    assert "kind_tag" not in url
    assert "offset=0" in url and "limit=30" in url


def test_list_docs_forwards_kind_tag():
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        return httpx.Response(200, json={"total": 0, "docs": []})

    curator.list_docs(kind="article", kind_tag="tech", client=_mk(handler))
    assert "kind=article" in captured["url"] and "kind_tag=tech" in captured["url"]


def test_domains_passthrough():
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/api/domains"
        return httpx.Response(200, json=[{"id": 1, "name": "具身智能", "enabled": True}])

    body = curator.domains(client=_mk(handler))
    assert body[0]["name"] == "具身智能"


def test_set_reading_posts_body():
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["path"] = req.url.path
        captured["body"] = json.loads(req.content)
        return httpx.Response(200, json={"ok": True})

    body = curator.set_reading(7, is_read=True, client=_mk(handler))
    assert body["ok"] is True
    assert captured["path"] == "/api/docs/7/reading"
    assert captured["body"] == {"is_read": True}


def test_timeout_and_connect_error_raise_unavailable():
    def timeout_handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout")

    def connect_handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    with pytest.raises(curator.CuratorUnavailable):
        curator.list_docs(client=_mk(timeout_handler))
    with pytest.raises(curator.CuratorUnavailable):
        curator.set_reading(7, is_read=True, client=_mk(connect_handler))


def test_http_500_raises_unavailable():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    with pytest.raises(curator.CuratorUnavailable):
        curator.list_docs(client=_mk(handler))


def test_default_base_url_env(monkeypatch):
    monkeypatch.setenv("CURATOR_BASE_URL", "http://127.0.0.1:9999")
    assert curator._base_url() == "http://127.0.0.1:9999"
    monkeypatch.delenv("CURATOR_BASE_URL")
    assert curator._base_url() == "http://127.0.0.1:9003"
