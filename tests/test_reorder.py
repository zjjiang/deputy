"""项目排序：reorder_project 单测 —— 全局 ord 重新编号，桶概念不下沉到 store 层。"""
from __future__ import annotations

import pytest

NOW = "2026-07-23T00:00:00+00:00"


def _seed(fresh_db, *rows):
    """在 p1 之外追加项目，rows: (id, name, stage, ord)。"""
    with fresh_db.transaction() as conn:
        for pid, name, stage, ordv in rows:
            conn.execute(
                "INSERT INTO projects (id, name, stage, drive, kind, trigger, ord) "
                "VALUES (?, ?, ?, 'self', 'biz', '', ?)",
                (pid, name, stage, ordv),
            )


def _ord_sequence(fresh_db) -> list[str]:
    from app.store.db import get_conn

    with get_conn() as conn:
        rows = conn.execute("SELECT id FROM projects ORDER BY ord, id").fetchall()
    return [r["id"] for r in rows]


def test_reorder_before(fresh_db):
    from app.store import projects

    _seed(fresh_db, ("p2", "b", "probe", 1), ("p3", "c", "probe", 2))
    assert _ord_sequence(fresh_db) == ["p1", "p2", "p3"]

    projects.reorder_project("p3", "p2", "before")
    assert _ord_sequence(fresh_db) == ["p1", "p3", "p2"]


def test_reorder_after(fresh_db):
    from app.store import projects

    _seed(fresh_db, ("p2", "b", "probe", 1), ("p3", "c", "probe", 2))
    assert _ord_sequence(fresh_db) == ["p1", "p2", "p3"]

    projects.reorder_project("p1", "p2", "after")
    assert _ord_sequence(fresh_db) == ["p2", "p1", "p3"]


def test_reorder_renumbers_contiguously(fresh_db):
    from app.store.db import get_conn
    from app.store import projects

    _seed(fresh_db, ("p2", "b", "probe", 5), ("p3", "c", "probe", 9))
    projects.reorder_project("p3", "p1", "before")
    with get_conn() as conn:
        rows = conn.execute("SELECT id, ord FROM projects ORDER BY ord").fetchall()
    assert [r["ord"] for r in rows] == [0, 1, 2]
    assert [r["id"] for r in rows] == ["p3", "p1", "p2"]


def test_reorder_noop_when_target_is_self(fresh_db):
    from app.store import projects

    _seed(fresh_db, ("p2", "b", "probe", 1))
    before = _ord_sequence(fresh_db)
    result = projects.reorder_project("p1", "p1", "before")
    assert result["id"] == "p1"
    assert _ord_sequence(fresh_db) == before


def test_reorder_missing_project_id_raises(fresh_db):
    from app.store import projects

    _seed(fresh_db, ("p2", "b", "probe", 1))
    with pytest.raises(KeyError):
        projects.reorder_project("ghost", "p2", "before")


def test_reorder_missing_target_id_raises(fresh_db):
    from app.store import projects

    with pytest.raises(KeyError):
        projects.reorder_project("p1", "ghost", "before")


def test_reorder_illegal_position_raises(fresh_db):
    from app.store import projects
    from app import domain

    _seed(fresh_db, ("p2", "b", "probe", 1))
    with pytest.raises(domain.DomainError):
        projects.reorder_project("p1", "p2", "sideways")


def test_add_project_after_delete_does_not_collide_ord(fresh_db):
    """COUNT(*) 算 ord 在删除后会撞号：p1(ord0) p2(ord1)，删 p1 剩 count=1，
    新项目若用 COUNT(*) 又拿到 ord=1，和 p2 撞号。改为 max(ord)+1 应避免。"""
    from app.store.db import get_conn
    from app.store import projects

    _seed(fresh_db, ("p2", "b", "probe", 1))
    projects.delete_project("p1")
    new = projects.add_project("新项目")
    with get_conn() as conn:
        rows = {r["id"]: r["ord"] for r in conn.execute("SELECT id, ord FROM projects")}
    assert rows[new["id"]] != rows["p2"]


def test_reorder_via_gate_does_not_mutate_until_approved(fresh_db):
    from app.store import projects, proposals

    _seed(fresh_db, ("p2", "b", "probe", 1))
    prop = proposals.propose(
        "reorder_project", {"project_id": "p2", "target_id": "p1", "position": "before"},
        reason="测试", now=NOW,
    )
    assert _ord_sequence(fresh_db) == ["p1", "p2"]
    proposals.approve(prop["id"], now=NOW)
    assert _ord_sequence(fresh_db) == ["p2", "p1"]
