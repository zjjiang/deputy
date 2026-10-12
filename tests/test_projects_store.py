"""项目真源规则测试：归档时间戳 archived_at 的写入/清空/迁移（见 filter-archived-by-time）。"""
from __future__ import annotations

import sqlite3

from app.store import db as db_mod
from app.store import projects


NOW = "2026-10-13T12:00:00"


def test_set_stage_to_archived_stamps_archived_at(fresh_db):
    """set_stage 迁入 archived 时写入归档时间（显式注入 now 保证确定性）。"""
    out = projects.set_stage("p1", "archived", now=NOW)
    assert out["stage"] == "archived"
    assert out["archived_at"] == NOW


def test_archive_shortcut_stamps_archived_at(fresh_db):
    """archive() 与 set_stage('archived') 同效。"""
    out = projects.archive("p1", now=NOW)
    assert out["stage"] == "archived"
    assert out["archived_at"] == NOW


def test_archive_without_now_fills_timestamp(fresh_db):
    """不传 now 时内部兜底当前时间——门禁派发等不传参的路径也能记时间。"""
    out = projects.archive("p1")
    assert out["archived_at"] and len(out["archived_at"]) > 10  # ISO 字符串


def test_non_archived_stage_has_null_archived_at(fresh_db):
    """非归档态 archived_at 恒为空。"""
    out = projects.set_stage("p1", "frozen", now=NOW)
    assert out["archived_at"] is None


def test_unarchive_clears_archived_at(fresh_db):
    """迁出归档态清空时间戳。"""
    projects.archive("p1", now=NOW)
    out = projects.unarchive("p1", "probe")
    assert out["stage"] == "probe"
    assert out["archived_at"] is None


def test_gate_set_stage_stamps_approve_time(fresh_db):
    """门禁 approve set_stage 时，archived_at 记批准时间。"""
    from app.store import proposals

    proposals.propose("set_stage", {"project_id": "p1", "stage": "archived"},
                      reason="跑完了", now="2026-10-12T08:00:00")
    proposals.approve(1, now=NOW)
    assert projects.get_project("p1")["archived_at"] == NOW


def test_state_api_includes_archived_at(fresh_db):
    """/api/state 的项目带 archived_at 字段。"""
    from fastapi.testclient import TestClient
    from app import api

    projects.archive("p1", now=NOW)
    r = TestClient(api.app).get("/api/state")
    assert r.status_code == 200
    p = next(p for p in r.json()["projects"] if p["id"] == "p1")
    assert p["archived_at"] == NOW


def test_migration_adds_archived_at_keeps_history_null(tmp_path, monkeypatch):
    """旧库补列迁移：archived_at 列加上，历史归档项目保持 NULL（不回填）。"""
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "old.db")
    conn = sqlite3.connect(tmp_path / "old.db")
    conn.execute(
        "CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, stage TEXT NOT NULL, "
        "drive TEXT NOT NULL, kind TEXT NOT NULL, trigger TEXT NOT NULL DEFAULT '', "
        "ord INTEGER NOT NULL DEFAULT 0)"
    )
    conn.execute(
        "INSERT INTO projects (id, name, stage, drive, kind, trigger, ord) "
        "VALUES ('old', '老项目', 'archived', 'self', 'biz', '', 0)"
    )
    conn.commit()
    conn.close()

    db_mod.init_db()  # 幂等迁移补列

    with db_mod.get_conn() as c:
        row = c.execute("SELECT archived_at FROM projects WHERE id = 'old'").fetchone()
    assert row["archived_at"] is None
