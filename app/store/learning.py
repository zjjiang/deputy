"""讲武堂（学习）读写 —— track/知识点大纲/自评进度/课程小结。

写边界（与门禁的关系）：
  - track 建立与大纲调整走门禁：add_track / set_curriculum 在 domain.PROPOSAL_ACTIONS；
  - 自评状态是用户说了算：分身代写走门禁动作 set_point_status，AI 不得自行判定掌握；
  - 课程小结（lesson_notes）是派生物，分身经 MCP submit_lesson_note 直接落库。
大纲调整是整体替换 + 同名继承状态；小结存知识点标题快照，不外键知识点。
"""
from __future__ import annotations

import inspect
import json
import sqlite3
from typing import Any

from .. import domain
from .db import get_conn, transaction


# ---------- 校验 ----------

def _require_track(conn: sqlite3.Connection, track_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM learning_tracks WHERE id = ?", (track_id,)
    ).fetchone()
    if row is None:
        raise KeyError(f"找不到学习主题 id={track_id}")
    return row


def _require_point(conn: sqlite3.Connection, point_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM knowledge_points WHERE id = ?", (point_id,)
    ).fetchone()
    if row is None:
        raise KeyError(f"找不到知识点 id={point_id}")
    return row


def _validate_curriculum_points(points: Any) -> list[dict[str, Any]]:
    """校验大纲数组：非空、元素为 {title 必填非空, summary 可选}、track 内不重名。"""
    if not isinstance(points, list) or not points:
        raise domain.DomainError("大纲不能为空")
    seen: set[str] = set()
    cleaned: list[dict[str, Any]] = []
    for p in points:
        if not isinstance(p, dict) or not isinstance(p.get("title"), str) or not p["title"].strip():
            raise domain.DomainError("大纲每个知识点必须有非空 title")
        title = p["title"].strip()
        if title in seen:
            raise domain.DomainError(f"大纲内知识点重名：{title}")
        seen.add(title)
        summary = p.get("summary", "")
        if summary is not None and not isinstance(summary, str):
            raise domain.DomainError("summary 必须是字符串")
        cleaned.append({"title": title, "summary": (summary or "").strip()})
    return cleaned


# ---------- 行转换 ----------

def _point_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "track_id": row["track_id"],
        "title": row["title"],
        "summary": row["summary"],
        "ord": row["ord"],
        "status": row["status"],
        "learned_at": row["learned_at"],
        "created": row["created"],
    }


def _note_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "track_id": row["track_id"],
        "point_title": row["point_title"],
        "body_md": row["body_md"],
        "sources": json.loads(row["sources"]),
        "model": row["model"],
        "created": row["created"],
    }


def _load_points(conn: sqlite3.Connection, track_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM knowledge_points WHERE track_id = ? ORDER BY ord, id",
        (track_id,),
    ).fetchall()
    return [_point_dict(r) for r in rows]


def _next_point(points: list[dict[str, Any]]) -> dict[str, Any] | None:
    """下一课：ord 序第一个 todo；无 todo 取第一个 revisit（回炉）；皆无 → None。"""
    for p in points:
        if p["status"] == "todo":
            return p
    for p in points:
        if p["status"] == "revisit":
            return p
    return None


def _track_dict(
    conn: sqlite3.Connection, row: sqlite3.Row, with_points: bool = False
) -> dict[str, Any]:
    track: dict[str, Any] = {
        "id": row["id"],
        "title": row["title"],
        "goal": row["goal"],
        "status": row["status"],
        "ord": row["ord"],
        "created": row["created"],
    }
    points = _load_points(conn, row["id"])
    track["progress"] = {
        "total": len(points),
        "learned": sum(1 for p in points if p["status"] == "learned"),
        "todo": sum(1 for p in points if p["status"] == "todo"),
        "revisit": sum(1 for p in points if p["status"] == "revisit"),
    }
    track["next_point"] = _next_point(points)
    if with_points:
        track["points"] = points
    return track


# ---------- 读 ----------

def get_track(track_id: str, with_notes: int = 0) -> dict[str, Any]:
    """读单 track：知识点、进度、下一课；with_notes>0 附最近 N 条课程小结。"""
    with get_conn() as conn:
        row = _require_track(conn, track_id)
        track = _track_dict(conn, row, with_points=True)
        if with_notes > 0:
            track["notes"] = _recent_notes(conn, track_id, with_notes)
    return track


def _recent_notes(
    conn: sqlite3.Connection, track_id: str, limit: int
) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM lesson_notes WHERE track_id = ? "
        "ORDER BY created DESC, id DESC LIMIT ?",
        (track_id, limit),
    ).fetchall()
    return [_note_dict(r) for r in rows]


def list_tracks() -> list[dict[str, Any]]:
    """全部 track（含 paused/done），附进度与下一课。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM learning_tracks ORDER BY ord, id"
        ).fetchall()
        return [_track_dict(conn, r) for r in rows]


def list_notes(track_id: str, limit: int = 30) -> list[dict[str, Any]]:
    """某 track 的全部课程小结，新的在前。"""
    if limit < 1:
        raise domain.DomainError("limit 必须为正整数")
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM lesson_notes WHERE track_id = ? "
            "ORDER BY created DESC, id DESC LIMIT ?",
            (track_id, limit),
        ).fetchall()
    return [_note_dict(r) for r in rows]


# ---------- 写（track/大纲/自评走门禁或用户直写；小结由分身直落）----------

def add_track(title: str, goal: str, *, now: str) -> dict[str, Any]:
    if not title or not title.strip():
        raise domain.DomainError("学习主题标题不能为空")
    if not goal or not goal.strip():
        raise domain.DomainError("学习目标不能为空")
    with transaction() as conn:
        existing = {r["id"] for r in conn.execute("SELECT id FROM learning_tracks")}
        n = 1
        while f"l{n}" in existing:
            n += 1
        tid = f"l{n}"
        max_ord = conn.execute(
            "SELECT MAX(ord) AS m FROM learning_tracks"
        ).fetchone()["m"]
        conn.execute(
            "INSERT INTO learning_tracks (id, title, goal, status, ord, created) "
            "VALUES (?, ?, ?, 'active', ?, ?)",
            (tid, title.strip(), goal.strip(), 0 if max_ord is None else max_ord + 1, now),
        )
    return get_track(tid)


def edit_track(
    track_id: str, *, title: str | None = None, goal: str | None = None, now: str
) -> dict[str, Any]:
    if title is not None and not title.strip():
        raise domain.DomainError("学习主题标题不能为空")
    if goal is not None and not goal.strip():
        raise domain.DomainError("学习目标不能为空")
    with transaction() as conn:
        _require_track(conn, track_id)
        if title is not None:
            conn.execute(
                "UPDATE learning_tracks SET title = ? WHERE id = ?",
                (title.strip(), track_id),
            )
        if goal is not None:
            conn.execute(
                "UPDATE learning_tracks SET goal = ? WHERE id = ?",
                (goal.strip(), track_id),
            )
    return get_track(track_id)


def set_track_status(track_id: str, status: str) -> dict[str, Any]:
    if status not in domain.VALID_TRACK_STATUSES:
        raise domain.DomainError(
            f"非法主题状态 {status}，应为 {sorted(domain.VALID_TRACK_STATUSES)}"
        )
    with transaction() as conn:
        _require_track(conn, track_id)
        conn.execute(
            "UPDATE learning_tracks SET status = ? WHERE id = ?", (status, track_id)
        )
    return get_track(track_id)


def remove_track(track_id: str) -> dict[str, Any]:
    """硬删，级联删知识点与课程小结。用户专属动作。"""
    with transaction() as conn:
        cur = conn.execute("DELETE FROM learning_tracks WHERE id = ?", (track_id,))
        if cur.rowcount == 0:
            raise KeyError(f"找不到学习主题 id={track_id}")
    return {"deleted": track_id}


def set_curriculum(
    track_id: str, points: list[dict[str, Any]], *, now: str
) -> dict[str, Any]:
    """整份替换大纲；同名知识点继承自评状态（learned/revisit/learned_at），
    新增默认 todo，被移除的连同进度消失（课程小结不受影响——按 track 归档）。
    """
    cleaned = _validate_curriculum_points(points)
    with transaction() as conn:
        _require_track(conn, track_id)
        old = {
            r["title"]: (r["status"], r["learned_at"])
            for r in conn.execute(
                "SELECT title, status, learned_at FROM knowledge_points "
                "WHERE track_id = ?",
                (track_id,),
            ).fetchall()
        }
        conn.execute("DELETE FROM knowledge_points WHERE track_id = ?", (track_id,))
        existing = {r["id"] for r in conn.execute("SELECT id FROM knowledge_points")}
        n = 1
        for i, p in enumerate(cleaned):
            while f"k{n}" in existing:
                n += 1
            pid = f"k{n}"
            existing.add(pid)
            status, learned_at = old.get(p["title"], ("todo", None))
            conn.execute(
                "INSERT INTO knowledge_points (id, track_id, title, summary, ord, "
                "status, learned_at, created) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (pid, track_id, p["title"], p["summary"], i, status, learned_at, now),
            )
            n += 1
    return get_track(track_id)


def get_point(point_id: str) -> dict[str, Any]:
    """读单个知识点。"""
    with get_conn() as conn:
        return _point_dict(_require_point(conn, point_id))


def set_point_status(point_id: str, status: str, *, now: str) -> dict[str, Any]:
    """用户自评。分身只能经门禁代写（AI 不得自行判定掌握）。"""
    if status not in domain.VALID_POINT_STATUSES:
        raise domain.DomainError(
            f"非法知识点状态 {status}，应为 {sorted(domain.VALID_POINT_STATUSES)}"
        )
    with transaction() as conn:
        _require_point(conn, point_id)
        conn.execute(
            "UPDATE knowledge_points SET status = ?, learned_at = ? WHERE id = ?",
            (status, now if status == "learned" else None, point_id),
        )
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM knowledge_points WHERE id = ?", (point_id,)
        ).fetchone()
    return _point_dict(row)


def submit_lesson_note(
    track_id: str,
    point_title: str,
    body_md: str,
    sources: list[dict[str, Any]] | None = None,
    model: str = "",
    *,
    now: str,
) -> dict[str, Any]:
    """分身课后小结直落（派生物）：追加式，存知识点标题快照。"""
    if not point_title or not point_title.strip():
        raise domain.DomainError("知识点标题不能为空")
    if not body_md or not body_md.strip():
        raise domain.DomainError("课程小结正文不能为空")
    if sources is not None and not isinstance(sources, list):
        raise domain.DomainError("sources 必须是数组")
    with transaction() as conn:
        _require_track(conn, track_id)
        cur = conn.execute(
            "INSERT INTO lesson_notes (track_id, point_title, body_md, sources, "
            "model, created) VALUES (?, ?, ?, ?, ?, ?)",
            (
                track_id,
                point_title.strip(),
                body_md.strip(),
                json.dumps(sources or [], ensure_ascii=False),
                model,
                now,
            ),
        )
        nid = cur.lastrowid
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM lesson_notes WHERE id = ?", (nid,)).fetchone()
    return _note_dict(row)


# ---------- 派发（供 proposals.approve 调用；三个门禁动作）----------

_DISPATCH = {
    "add_track": lambda a, now=None: add_track(a["title"], a["goal"], now=now),
    "set_curriculum": lambda a, now=None: set_curriculum(
        a["track_id"], a["points"], now=now
    ),
    "set_point_status": lambda a, now=None: set_point_status(
        a["point_id"], a["status"], now=now
    ),
}


def handles(action: str) -> bool:
    """本模块是否负责派发该动作（供 proposals.approve 路由）。"""
    return action in _DISPATCH


def dispatch(action: str, args: dict[str, Any], *, now: str | None = None) -> Any:
    """执行一个已批准的学习动作。未知 action 抛错。"""
    fn = _DISPATCH.get(action)
    if fn is None:
        raise domain.DomainError(f"未知动作 {action}")
    sig = inspect.signature(fn)
    if "now" in sig.parameters:
        return fn(args, now=now)
    return fn(args)
