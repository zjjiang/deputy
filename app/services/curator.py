"""curator 客户端 —— deputy 对 feed-curator 的唯一集成出口。

约定（见 add-intel-stream design D1 / CLAUDE.md 章程）：
  - 全仓对 feed-curator 的 HTTP 访问只允许经本模块，禁止第二处散落调用；
  - 目标限本机 localhost（默认 127.0.0.1:9003，CURATOR_BASE_URL 可配）；
  - 任何不可达/非 2xx 统一抛 CuratorUnavailable，由 API 层映射 503 降级；
  - 只做转发与透传，不缓存、不落库（状态跟着实体走，阅读状态存 feed-curator）。
"""
from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:9003"
TIMEOUT = 2.0


class CuratorUnavailable(RuntimeError):
    """feed-curator 不可达或响应异常（API 层映射 503 降级）。"""


def _base_url() -> str:
    return os.environ.get("CURATOR_BASE_URL", DEFAULT_BASE_URL)


def _request(
    client: httpx.Client | None,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any]:
    own = client is None
    http = client or httpx.Client(base_url=_base_url(), timeout=TIMEOUT)
    try:
        resp = http.request(method, path, params=params, json=json_body)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:  # 连接错误/超时/非 2xx 一律降级
        raise CuratorUnavailable(f"图书馆不可达：{type(e).__name__}") from e
    finally:
        if own:
            http.close()


def _clean(params: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in params.items() if v is not None}


def list_docs(
    *,
    domain_id: int | None = None,
    kind: str | None = None,
    kind_tag: str | None = None,
    min_stars: int | None = None,
    sort: str | None = None,
    page: int = 1,
    per_page: int = 30,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """拉文档流（feed-curator GET /api/docs），page 从 1 起。"""
    return _request(
        client,
        "GET",
        "/api/docs",
        params=_clean({
            "domain_id": domain_id,
            "kind": kind,
            "kind_tag": kind_tag,
            "min_stars": min_stars,
            "sort": sort,
            "limit": per_page,
            "offset": (page - 1) * per_page,
        }),
    )


def domains(client: httpx.Client | None = None) -> list[dict[str, Any]]:
    """领域列表（GET /api/domains），供情报流筛选下拉。"""
    result = _request(client, "GET", "/api/domains")
    assert isinstance(result, list)
    return result


def set_reading(
    doc_id: int,
    *,
    is_read: bool | None = None,
    is_favorite: bool | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """阅读状态代理写回（POST /api/docs/{id}/reading），deputy 不落库。"""
    body = _clean({"is_read": is_read, "is_favorite": is_favorite})
    result = _request(client, "POST", f"/api/docs/{doc_id}/reading", json_body=body)
    assert isinstance(result, dict)
    return result
