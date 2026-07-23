"""共享 fixture：每个测试用独立临时 DB，种一个项目。"""
from __future__ import annotations

import pytest


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    """把 DB_PATH 指向临时文件并建表，种一个 probe 项目 p1。"""
    from app.store import db as db_mod

    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    db_mod.init_db()
    with db_mod.transaction() as conn:
        conn.execute(
            "INSERT INTO projects (id, name, stage, drive, kind, trigger, ord) "
            "VALUES ('p1', '测试项目', 'probe', 'self', 'biz', '', 0)"
        )
    return db_mod
