"""真源读写 —— 项目/todo/需求池/聚焦。业务规则（状态机、主攻唯一）在此强制。

所有写函数是"释放"层：只由 API 直接调用（用户在看板上操作），
或由 proposals.approve() 在用户批准后派发调用。分身不能直接调这些。
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from .. import domain
from .db import get_conn, transaction


# ---------- 读 ----------

def _project_row_to_dict(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    todos = conn.execute(
        "SELECT id, text, done, done_at FROM todos WHERE project_id = ? ORDER BY ord, id",
        (row["id"],),
    ).fetchall()
    return {
        "id": row["id"],
        "name": row["name"],
        "stage": row["stage"],
        "drive": row["drive"],
        "kind": row["kind"],
        "trigger": row["trigger"],
        "todos": [
            {"id": t["id"], "text": t["text"], "done": bool(t["done"]), "done_at": t["done_at"]} for t in todos
        ],
    }


def _auto_focus(projects: list[dict[str, Any]]) -> dict[str, Any]:
    """规则兜底：没人写 focus 时按状态生成。主攻必上，有扳机的雪藏也提醒。"""
    attack = [p for p in projects if p["stage"] == "attack"]
    frozen_trig = [p for p in projects if p["stage"] == "frozen" and p["trigger"]]
    items = [p["id"] for p in attack] + [p["id"] for p in frozen_trig]
    if attack:
        s = f"周末只盯 {attack[0]['name']}。"
    else:
        s = "主攻位空着 —— 先从验证/雪藏里提一个进来。"
    if frozen_trig:
        s += "另外这些雪藏项目在等你的决策扳机。"
    s += "其余有人扛/在等信号，不用分心。"
    return {"summary": s, "items": items, "by": "自动"}


def get_state() -> dict[str, Any]:
    """全量状态：项目 + 各维度中文含义 + 需求池 + 此刻聚焦。"""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY ord, id").fetchall()
        projects = [_project_row_to_dict(conn, r) for r in rows]
        backlog = [
            {"id": b["id"], "text": b["text"], "status": b["status"]}
            for b in conn.execute("SELECT * FROM backlog ORDER BY ord, id").fetchall()
        ]
        frow = conn.execute("SELECT * FROM focus WHERE id = 1").fetchone()
    if frow and frow["summary"]:
        focus = {
            "summary": frow["summary"],
            "items": json.loads(frow["items"]),
            "by": frow["by_who"],
        }
    else:
        focus = _auto_focus(projects)
    return {
        "stages": domain.STAGE_LABELS,
        "drives": domain.DRIVE_LABELS,
        "kinds": domain.KIND_LABELS,
        "focus": focus,
        "projects": projects,
        "backlog": backlog,
    }


def get_project(project_id: str) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"找不到项目 id={project_id}")
        return _project_row_to_dict(conn, row)


# ---------- 写（释放层） ----------

def _next_todo_id(conn: sqlite3.Connection, project_id: str) -> str:
    existing = {
        r["id"]
        for r in conn.execute(
            "SELECT id FROM todos WHERE project_id = ?", (project_id,)
        )
    }
    n = 1
    while f"t{n}" in existing:
        n += 1
    return f"t{n}"


def _require_project(conn: sqlite3.Connection, project_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise KeyError(f"找不到项目 id={project_id}")
    return row


def set_focus(summary: str, items: list[str] | None = None, by: str = "我") -> dict[str, Any]:
    if not summary or not summary.strip():
        raise domain.DomainError("聚焦结论不能为空")
    with transaction() as conn:
        valid = {r["id"] for r in conn.execute("SELECT id FROM projects")}
        picked = [i for i in (items or []) if i in valid]
        conn.execute(
            "INSERT INTO focus (id, summary, items, by_who) VALUES (1, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET summary=excluded.summary, "
            "items=excluded.items, by_who=excluded.by_who",
            (summary.strip(), json.dumps(picked, ensure_ascii=False), by),
        )
    return {"summary": summary.strip(), "items": picked, "by": by}


def add_to_backlog(text: str) -> dict[str, Any]:
    if not text or not text.strip():
        raise domain.DomainError("需求内容不能为空")
    with transaction() as conn:
        n = conn.execute("SELECT COUNT(*) AS c FROM backlog").fetchone()["c"]
        bid = f"b{n + 1}"
        conn.execute(
            "INSERT INTO backlog (id, text, status, ord) VALUES (?, ?, '待归类', ?)",
            (bid, text.strip(), n),
        )
    return {"id": bid, "text": text.strip(), "status": "待归类"}


def add_todo(project_id: str, text: str) -> dict[str, Any]:
    if not text or not text.strip():
        raise domain.DomainError("todo 内容不能为空")
    with transaction() as conn:
        _require_project(conn, project_id)
        tid = _next_todo_id(conn, project_id)
        n = conn.execute(
            "SELECT COUNT(*) AS c FROM todos WHERE project_id = ?", (project_id,)
        ).fetchone()["c"]
        conn.execute(
            "INSERT INTO todos (id, project_id, text, done, ord) VALUES (?, ?, ?, 0, ?)",
            (tid, project_id, text.strip(), n),
        )
    return get_project(project_id)


def toggle_todo(project_id: str, todo_id: str, done: bool = True, *, now: str | None = None) -> dict[str, Any]:
    with transaction() as conn:
        cur = conn.execute(
            "UPDATE todos SET done = ?, done_at = ? WHERE project_id = ? AND id = ?",
            (1 if done else 0, now if done else None, project_id, todo_id),
        )
        if cur.rowcount == 0:
            raise KeyError(f"项目 {project_id} 下找不到 todo {todo_id}")
    return get_project(project_id)


def edit_todo(project_id: str, todo_id: str, text: str) -> dict[str, Any]:
    if not text or not text.strip():
        raise domain.DomainError("todo 内容不能为空")
    with transaction() as conn:
        cur = conn.execute(
            "UPDATE todos SET text = ? WHERE project_id = ? AND id = ?",
            (text.strip(), project_id, todo_id),
        )
        if cur.rowcount == 0:
            raise KeyError(f"项目 {project_id} 下找不到 todo {todo_id}")
    return get_project(project_id)


def remove_todo(project_id: str, todo_id: str) -> dict[str, Any]:
    with transaction() as conn:
        cur = conn.execute(
            "DELETE FROM todos WHERE project_id = ? AND id = ?", (project_id, todo_id)
        )
        if cur.rowcount == 0:
            raise KeyError(f"项目 {project_id} 下找不到 todo {todo_id}")
    return get_project(project_id)


def set_stage(project_id: str, stage: str) -> dict[str, Any]:
    if stage not in domain.VALID_STAGES:
        raise domain.DomainError(f"非法状态 {stage}")
    with transaction() as conn:
        row = _require_project(conn, project_id)
        cur = row["stage"]
        if stage == cur:
            return get_project(project_id)
        allowed = domain.STAGE_TRANSITIONS.get(cur, frozenset())
        if stage not in allowed:
            raise domain.DomainError(
                f"不允许的状态迁移：{cur} → {stage}。"
                f"{cur} 只能迁移到 {sorted(allowed) or '（无，终态）'}"
            )
        if stage == "attack":
            others = conn.execute(
                "SELECT name FROM projects WHERE stage = 'attack' AND id != ?",
                (project_id,),
            ).fetchall()
            if others:
                names = "、".join(o["name"] for o in others)
                raise domain.DomainError(
                    f"主攻同时只能有一个。请先把「{names}」移出主攻。"
                )
        conn.execute("UPDATE projects SET stage = ? WHERE id = ?", (stage, project_id))
    return get_project(project_id)


def set_drive(project_id: str, drive: str) -> dict[str, Any]:
    if drive not in domain.VALID_DRIVES:
        raise domain.DomainError(f"非法驱动 {drive}")
    with transaction() as conn:
        _require_project(conn, project_id)
        conn.execute("UPDATE projects SET drive = ? WHERE id = ?", (drive, project_id))
    return get_project(project_id)


def set_kind(project_id: str, kind: str) -> dict[str, Any]:
    """改项目类型 biz(商业)/tool(自用工具)。任意互转，无状态约束。"""
    if kind not in domain.VALID_KINDS:
        raise domain.DomainError(f"非法类型 {kind}")
    with transaction() as conn:
        _require_project(conn, project_id)
        conn.execute("UPDATE projects SET kind = ? WHERE id = ?", (kind, project_id))
    return get_project(project_id)


def set_trigger(project_id: str, trigger: str) -> dict[str, Any]:
    with transaction() as conn:
        _require_project(conn, project_id)
        conn.execute(
            "UPDATE projects SET trigger = ? WHERE id = ?",
            ((trigger or "").strip(), project_id),
        )
    return get_project(project_id)


def add_project(
    name: str, stage: str = "spark", drive: str = "self", kind: str = "biz"
) -> dict[str, Any]:
    if not name or not name.strip():
        raise domain.DomainError("项目名不能为空")
    if stage not in domain.VALID_STAGES:
        raise domain.DomainError(f"非法状态 {stage}")
    if drive not in domain.VALID_DRIVES:
        raise domain.DomainError(f"非法驱动 {drive}")
    if kind not in domain.VALID_KINDS:
        raise domain.DomainError(f"非法类型 {kind}")
    if stage == "attack":
        raise domain.DomainError("新项目不能直接进主攻，请先建后再改状态")
    with transaction() as conn:
        existing = {r["id"] for r in conn.execute("SELECT id FROM projects")}
        n = 1
        while f"n{n}" in existing:
            n += 1
        pid = f"n{n}"
        ordv = conn.execute("SELECT COUNT(*) AS c FROM projects").fetchone()["c"]
        conn.execute(
            "INSERT INTO projects (id, name, stage, drive, kind, trigger, ord) "
            "VALUES (?, ?, ?, ?, ?, '', ?)",
            (pid, name.strip(), stage, drive, kind, ordv),
        )
    return get_project(pid)


def rename_project(project_id: str, name: str) -> dict[str, Any]:
    if not name or not name.strip():
        raise domain.DomainError("项目名不能为空")
    with transaction() as conn:
        _require_project(conn, project_id)
        conn.execute(
            "UPDATE projects SET name = ? WHERE id = ?", (name.strip(), project_id)
        )
    return get_project(project_id)


def archive(project_id: str) -> dict[str, Any]:
    return set_stage(project_id, "archived")


def unarchive(project_id: str, stage: str = "frozen") -> dict[str, Any]:
    if stage not in domain.VALID_STAGES or stage == "archived":
        raise domain.DomainError(f"恢复目标状态非法：{stage}")
    with transaction() as conn:
        row = _require_project(conn, project_id)
        if row["stage"] != "archived":
            raise domain.DomainError(f"项目 {project_id} 当前不是归档状态")
        if stage == "attack":
            others = conn.execute(
                "SELECT name FROM projects WHERE stage = 'attack' AND id != ?",
                (project_id,),
            ).fetchall()
            if others:
                names = "、".join(o["name"] for o in others)
                raise domain.DomainError(f"主攻同时只能有一个，请先移出「{names}」")
        conn.execute("UPDATE projects SET stage = ? WHERE id = ?", (stage, project_id))
    return get_project(project_id)


def delete_project(project_id: str) -> dict[str, Any]:
    with transaction() as conn:
        cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        if cur.rowcount == 0:
            raise KeyError(f"找不到项目 id={project_id}")
    return {"deleted": project_id}


# ---------- 派发（供 proposals.approve 调用）----------

_DISPATCH = {
    "set_focus": lambda a: set_focus(a["summary"], a.get("items"), a.get("by", "分身")),
    "add_todo": lambda a: add_todo(a["project_id"], a["text"]),
    "toggle_todo": lambda a, now=None: toggle_todo(a["project_id"], a["todo_id"], a.get("done", True), now=now),
    "edit_todo": lambda a: edit_todo(a["project_id"], a["todo_id"], a["text"]),
    "remove_todo": lambda a: remove_todo(a["project_id"], a["todo_id"]),
    "set_stage": lambda a: set_stage(a["project_id"], a["stage"]),
    "set_drive": lambda a: set_drive(a["project_id"], a["drive"]),
    "set_kind": lambda a: set_kind(a["project_id"], a["kind"]),
    "set_trigger": lambda a: set_trigger(a["project_id"], a["trigger"]),
    "add_project": lambda a: add_project(
        a["name"], a.get("stage", "spark"), a.get("drive", "self"), a.get("kind", "biz")
    ),
    "rename_project": lambda a: rename_project(a["project_id"], a["name"]),
    "add_to_backlog": lambda a: add_to_backlog(a["text"]),
}


def dispatch(action: str, args: dict[str, Any], *, now: str | None = None) -> Any:
    """执行一个已批准的动作。未知 action 抛错。"""
    fn = _DISPATCH.get(action)
    if fn is None:
        raise domain.DomainError(f"未知动作 {action}")
    # 需要 now 的 action 通过 lambda 默认参数接收
    import inspect
    sig = inspect.signature(fn)
    if "now" in sig.parameters:
        return fn(args, now=now)
    return fn(args)
