"""预设问题读写 —— 问题配置 + 版本化回答档案。

写边界（与门禁的关系）：
  - questions 的建/改走门禁：add_question / edit_question 在 domain.PROPOSAL_ACTIONS，
    分身只能 propose，用户批准后经 dispatch 落地；停用/删除是用户专属动作。
  - answers 由分身经 MCP submit_answer 直接落库：回答是派生物非真源（见 spec）。
所有时间由调用方传入：时间戳用 UTC ISO；run_date 用东八区日历日（YYYY-MM-DD）。
"""
from __future__ import annotations

import inspect
import json
import sqlite3
from datetime import datetime
from typing import Any

from .. import domain
from .db import get_conn, transaction


# ---------- 校验 ----------

def _require_question(conn: sqlite3.Connection, question_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM questions WHERE id = ?", (question_id,)
    ).fetchone()
    if row is None:
        raise KeyError(f"找不到问题 id={question_id}")
    return row


def _validate_filter(flt: Any) -> dict[str, Any]:
    """校验问题过滤器：白名单键 + kinds ⊆ VALID_KINDS + days/max_docs 正整数。

    domain 是 feed-curator 侧的不透明字符串，这里只查类型不查语义。
    """
    if flt is None:
        return {}
    if not isinstance(flt, dict):
        raise domain.DomainError("filter 必须是对象")
    unknown = set(flt) - set(domain.VALID_QUESTION_FILTER_KEYS)
    if unknown:
        raise domain.DomainError(
            f"filter 含未知键 {sorted(unknown)}，可用 {sorted(domain.VALID_QUESTION_FILTER_KEYS)}"
        )
    kinds = flt.get("kinds")
    if kinds is not None:
        if not isinstance(kinds, list) or any(
            k not in domain.VALID_KINDS for k in kinds
        ):
            raise domain.DomainError(
                f"kinds 必须是 {sorted(domain.VALID_KINDS)} 的子集"
            )
    for key in ("days", "max_docs"):
        val = flt.get(key)
        if val is not None and (not isinstance(val, int) or isinstance(val, bool) or val < 1):
            raise domain.DomainError(f"filter.{key} 必须是正整数")
    if "domain" in flt and not isinstance(flt["domain"], str):
        raise domain.DomainError("filter.domain 必须是字符串")
    return flt


# ---------- 行转换 ----------

def _row_to_question(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "prompt": row["prompt"],
        "filter": json.loads(row["filter_json"]),
        "cadence": row["cadence"],
        "active": bool(row["active"]),
        "requested_at": row["requested_at"],
        "last_run_at": row["last_run_at"],
        "ord": row["ord"],
        "created": row["created"],
    }


def _row_to_answer(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "question_id": row["question_id"],
        "body_md": row["body_md"],
        "sources": json.loads(row["sources"]),
        "confidence": row["confidence"],
        "meta": json.loads(row["meta_json"]),
        "model": row["model"],
        "run_date": row["run_date"],
        "version": row["version"],
        "status": row["status"],
        "read_at": row["read_at"],
        "created": row["created"],
    }


# ---------- 到期判定（纯规则，now 注入）----------

def _due_info(row: sqlite3.Row, now: str) -> tuple[bool, str | None]:
    """到期 = active 且（有手动请求 / 从未运行 / 距上次运行 ≥ 周期）。

    manual 节奏只认请求标记——first-run/scheduled 都不适用于它。
    """
    if not row["active"]:
        return False, None
    if row["requested_at"]:
        return True, "manual-request"
    period_days = domain.CADENCE_PERIODS.get(row["cadence"])
    if period_days is None:  # manual 只看请求标记
        return False, None
    if not row["last_run_at"]:
        return True, "first-run"
    elapsed = (
        datetime.fromisoformat(now) - datetime.fromisoformat(row["last_run_at"])
    ).total_seconds()
    if elapsed >= period_days * 86400:
        return True, "scheduled"
    return False, None


# ---------- 读 ----------

def get_question(question_id: str, with_answers: int = 0) -> dict[str, Any]:
    """读单题。with_answers > 0 时附最近 N 天的每日最新版回答（增量回答依据）。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM questions WHERE id = ?", (question_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"找不到问题 id={question_id}")
        q = _row_to_question(row)
        if with_answers > 0:
            q["answers"] = _latest_per_day(conn, question_id, with_answers)
    return q


def _latest_per_day(
    conn: sqlite3.Connection, question_id: str, limit: int
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT a.* FROM answers a
        JOIN (
            SELECT run_date, MAX(version) AS mv FROM answers
            WHERE question_id = ? GROUP BY run_date
        ) t ON a.run_date = t.run_date AND a.version = t.mv
        WHERE a.question_id = ?
        ORDER BY a.run_date DESC, a.id DESC
        LIMIT ?
        """,
        (question_id, question_id, limit),
    ).fetchall()
    return [_row_to_answer(r) for r in rows]


def list_questions(now: str, due_only: bool = False) -> list[dict[str, Any]]:
    """列问题，附 due/due_reason（由 now 判定）。due_only=True 只回到期题。"""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM questions ORDER BY ord, id").fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        due, reason = _due_info(r, now)
        if due_only and not due:
            continue
        q = _row_to_question(r)
        q["due"] = due
        q["due_reason"] = reason
        out.append(q)
    return out


def list_answers(question_id: str, limit: int = 30) -> list[dict[str, Any]]:
    """列某题的全部版本（含 superseded），新的在前。"""
    if limit < 1:
        raise domain.DomainError("limit 必须为正整数")
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM answers WHERE question_id = ? "
            "ORDER BY run_date DESC, version DESC, id DESC LIMIT ?",
            (question_id, limit),
        ).fetchall()
    return [_row_to_answer(r) for r in rows]


# ---------- 写（questions 走门禁/用户直写；answers 走分身提交）----------

def add_question(
    title: str,
    prompt: str,
    filter: dict[str, Any] | None = None,
    cadence: str = "daily",
    *,
    now: str,
) -> dict[str, Any]:
    if not title or not title.strip():
        raise domain.DomainError("问题标题不能为空")
    if not prompt or not prompt.strip():
        raise domain.DomainError("问题 prompt 不能为空")
    if cadence not in domain.VALID_CADENCES:
        raise domain.DomainError(
            f"非法节奏 {cadence}，应为 {sorted(domain.VALID_CADENCES)}"
        )
    flt = _validate_filter(filter)
    with transaction() as conn:
        existing = {r["id"] for r in conn.execute("SELECT id FROM questions")}
        n = 1
        while f"q{n}" in existing:
            n += 1
        qid = f"q{n}"
        max_ord = conn.execute("SELECT MAX(ord) AS m FROM questions").fetchone()["m"]
        ordv = 0 if max_ord is None else max_ord + 1
        conn.execute(
            "INSERT INTO questions (id, title, prompt, filter_json, cadence, active, ord, created) "
            "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (
                qid,
                title.strip(),
                prompt.strip(),
                json.dumps(flt, ensure_ascii=False),
                cadence,
                ordv,
                now,
            ),
        )
    return get_question(qid)


def edit_question(
    question_id: str,
    *,
    title: str | None = None,
    prompt: str | None = None,
    cadence: str | None = None,
    filter: dict[str, Any] | None = None,
    now: str,
) -> dict[str, Any]:
    """只更新提供了的字段（None = 不改）。校验规则与 add_question 一致。"""
    if title is not None and not title.strip():
        raise domain.DomainError("问题标题不能为空")
    if prompt is not None and not prompt.strip():
        raise domain.DomainError("问题 prompt 不能为空")
    if cadence is not None and cadence not in domain.VALID_CADENCES:
        raise domain.DomainError(f"非法节奏 {cadence}")
    flt = _validate_filter(filter) if filter is not None else None
    with transaction() as conn:
        _require_question(conn, question_id)
        if title is not None:
            conn.execute(
                "UPDATE questions SET title = ? WHERE id = ?",
                (title.strip(), question_id),
            )
        if prompt is not None:
            conn.execute(
                "UPDATE questions SET prompt = ? WHERE id = ?",
                (prompt.strip(), question_id),
            )
        if cadence is not None:
            conn.execute(
                "UPDATE questions SET cadence = ? WHERE id = ?", (cadence, question_id)
            )
        if flt is not None:
            conn.execute(
                "UPDATE questions SET filter_json = ? WHERE id = ?",
                (json.dumps(flt, ensure_ascii=False), question_id),
            )
    return get_question(question_id)


def set_question_active(question_id: str, active: bool) -> dict[str, Any]:
    """停用/启用。停用后永不到期，且拒收新回答。用户专属动作，不走门禁。"""
    with transaction() as conn:
        _require_question(conn, question_id)
        conn.execute(
            "UPDATE questions SET active = ? WHERE id = ?",
            (1 if active else 0, question_id),
        )
    return get_question(question_id)


def remove_question(question_id: str) -> dict[str, Any]:
    """硬删，级联删全部回答（FK ON DELETE CASCADE）。用户专属动作。"""
    with transaction() as conn:
        cur = conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        if cur.rowcount == 0:
            raise KeyError(f"找不到问题 id={question_id}")
    return {"deleted": question_id}


def request_run(question_id: str, *, now: str) -> dict[str, Any]:
    """手动「跑一次」：打请求标记，分身下轮轮询取走（submit 时清除）。"""
    with transaction() as conn:
        _require_question(conn, question_id)
        conn.execute(
            "UPDATE questions SET requested_at = ? WHERE id = ?", (now, question_id)
        )
    return get_question(question_id)


def submit_answer(
    question_id: str,
    body_md: str,
    sources: list[dict[str, Any]] | None = None,
    confidence: str = "",
    model: str = "",
    *,
    run_date: str,
    now: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """分身回填回答：append-only 版本化。同题同日每次提交 = 新版本，
    旧版本标 superseded；同一事务推进 last_run_at 并清除手动请求标记。
    """
    if not body_md or not body_md.strip():
        raise domain.DomainError("回答正文不能为空")
    if confidence and confidence not in domain.VALID_CONFIDENCES:
        raise domain.DomainError(
            f"非法 confidence {confidence}，应为 {sorted(domain.VALID_CONFIDENCES)}"
        )
    try:
        datetime.strptime(run_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        raise domain.DomainError("run_date 必须是 YYYY-MM-DD 格式") from None
    if sources is not None and not isinstance(sources, list):
        raise domain.DomainError("sources 必须是数组")
    if meta is not None and not isinstance(meta, dict):
        raise domain.DomainError("meta 必须是对象")
    with transaction() as conn:
        row = _require_question(conn, question_id)
        if not row["active"]:
            raise domain.DomainError(f"问题 {question_id} 已停用，拒收回答")
        cur = conn.execute(
            "SELECT COALESCE(MAX(version), 0) AS mv FROM answers "
            "WHERE question_id = ? AND run_date = ?",
            (question_id, run_date),
        ).fetchone()
        version = cur["mv"] + 1
        conn.execute(
            "UPDATE answers SET status = 'superseded' "
            "WHERE question_id = ? AND run_date = ?",
            (question_id, run_date),
        )
        ins = conn.execute(
            "INSERT INTO answers (question_id, body_md, sources, confidence, meta_json, "
            "model, run_date, version, status, created) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)",
            (
                question_id,
                body_md.strip(),
                json.dumps(sources or [], ensure_ascii=False),
                confidence,
                json.dumps(meta or {}, ensure_ascii=False),
                model,
                run_date,
                version,
                now,
            ),
        )
        aid = ins.lastrowid
        conn.execute(
            "UPDATE questions SET last_run_at = ?, requested_at = NULL WHERE id = ?",
            (now, question_id),
        )
    with get_conn() as conn:
        arow = conn.execute("SELECT * FROM answers WHERE id = ?", (aid,)).fetchone()
    return _row_to_answer(arow)


def mark_answer_read(answer_id: int, *, now: str) -> dict[str, Any]:
    """标已读，记录 read_at（对标 todos.done_at）。只影响这一条回答。"""
    with transaction() as conn:
        cur = conn.execute(
            "UPDATE answers SET status = 'read', read_at = ? WHERE id = ?",
            (now, answer_id),
        )
        if cur.rowcount == 0:
            raise KeyError(f"找不到回答 id={answer_id}")
    with get_conn() as conn:
        arow = conn.execute(
            "SELECT * FROM answers WHERE id = ?", (answer_id,)
        ).fetchone()
    return _row_to_answer(arow)


def delete_answer(answer_id: int) -> dict[str, Any]:
    """删单条回答（其余版本不受影响）。"""
    with transaction() as conn:
        cur = conn.execute("DELETE FROM answers WHERE id = ?", (answer_id,))
        if cur.rowcount == 0:
            raise KeyError(f"找不到回答 id={answer_id}")
    return {"deleted": answer_id}


# ---------- 派发（供 proposals.approve 调用；仅建题/改题两个门禁动作）----------

_DISPATCH = {
    "add_question": lambda a, now=None: add_question(
        a["title"], a["prompt"], filter=a.get("filter"),
        cadence=a.get("cadence", "daily"), now=now,
    ),
    "edit_question": lambda a, now=None: edit_question(
        a["question_id"], title=a.get("title"), prompt=a.get("prompt"),
        cadence=a.get("cadence"), filter=a.get("filter"), now=now,
    ),
}


def handles(action: str) -> bool:
    """本模块是否负责派发该动作（供 proposals.approve 路由）。"""
    return action in _DISPATCH


def dispatch(action: str, args: dict[str, Any], *, now: str | None = None) -> Any:
    """执行一个已批准的问题动作。未知 action 抛错。"""
    fn = _DISPATCH.get(action)
    if fn is None:
        raise domain.DomainError(f"未知动作 {action}")
    # 需要 now 的 action 通过 lambda 默认参数接收（与 projects.dispatch 同构）
    sig = inspect.signature(fn)
    if "now" in sig.parameters:
        return fn(args, now=now)
    return fn(args)
