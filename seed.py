"""初始化 DB + 从旧原型的 projects.json 迁入现有项目/todo/聚焦。

用法：
    uv run python seed.py            # 从默认旧路径迁入
    uv run python seed.py <path>     # 指定 projects.json

幂等：已存在同 id 项目则跳过（不覆盖你后来的改动）。
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from app.store.db import DB_PATH, init_db, transaction

OLD_JSON = Path(__file__).resolve().parents[1] / "opc-cockpit" / "data" / "projects.json"


def seed(src: Path) -> None:
    init_db()
    if not src.exists():
        print(f"⚠️  找不到旧数据 {src}，只初始化空库。")
        return
    data = json.loads(src.read_text(encoding="utf-8"))
    projects = data.get("projects", [])
    backlog = data.get("backlog", [])
    focus = data.get("focus")

    with transaction() as conn:
        existing = {r["id"] for r in conn.execute("SELECT id FROM projects")}
        for i, p in enumerate(projects):
            if p["id"] in existing:
                continue
            conn.execute(
                "INSERT INTO projects (id, name, stage, drive, kind, trigger, ord) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p["id"], p["name"], p["stage"], p.get("drive", "self"),
                 p.get("kind", "biz"), p.get("trigger", ""), i),
            )
            for j, t in enumerate(p.get("todos", [])):
                conn.execute(
                    "INSERT INTO todos (id, project_id, text, done, ord) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (t["id"], p["id"], t["text"], 1 if t.get("done") else 0, j),
                )
        for i, b in enumerate(backlog):
            conn.execute(
                "INSERT OR IGNORE INTO backlog (id, text, status, ord) VALUES (?, ?, ?, ?)",
                (b["id"], b["text"], b.get("status", "待归类"), i),
            )
        if focus and focus.get("summary"):
            conn.execute(
                "INSERT INTO focus (id, summary, items, by_who) VALUES (1, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET summary=excluded.summary, "
                "items=excluded.items, by_who=excluded.by_who",
                (focus["summary"], json.dumps(focus.get("items", []), ensure_ascii=False),
                 focus.get("by", "顾问")),
            )

    with sqlite3.connect(DB_PATH) as c:
        n = c.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    print(f"✅ 迁移完成，库中现有 {n} 个项目 → {DB_PATH}")


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else OLD_JSON
    seed(src)
