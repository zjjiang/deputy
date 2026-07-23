"""门禁队列 —— 决策中枢的灵魂。

规矩（"人类做门禁"，A 档）：
  - 分身只能 propose(...)：把想做的写操作扣进队列，status=pending，绝不直接改真源。
  - 用户 approve(id)：系统才把该动作派发到 projects 的写函数，真正落地。
  - 用户 reject(id, note)：驳回，不执行。
派发只认 domain.PROPOSAL_ACTIONS 白名单，未知动作/缺参数一律拒。
"""
from __future__ import annotations

import json
from typing import Any

from .. import domain
from . import projects as proj
from .db import get_conn, transaction


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "action": row["action"],
        "args": json.loads(row["args"]),
        "reason": row["reason"],
        "by": row["by_who"],
        "status": row["status"],
        "created": row["created"],
        "decided": row["decided"],
        "note": row["note"],
    }


def propose(
    action: str,
    args: dict[str, Any],
    reason: str,
    now: str,
    by: str = "分身",
) -> dict[str, Any]:
    """分身提交一条提议。校验动作合法 + 必需参数齐全，但不执行。
    now = ISO 时间字符串，由调用层传入（MCP/API 层负责取时间）。
    """
    if action not in domain.PROPOSAL_ACTIONS:
        raise domain.DomainError(
            f"未知提议动作 {action}，应为 {sorted(domain.PROPOSAL_ACTIONS)}"
        )
    required = domain.PROPOSAL_ACTIONS[action]
    # 只校验"必填键存在"，具体值合法性留到 approve 派发时由 store 层把关。
    missing = [k for k in required if k not in args and k not in ("items", "done")]
    if missing:
        raise domain.DomainError(f"动作 {action} 缺少参数：{missing}")
    if not reason or not reason.strip():
        raise domain.DomainError("提议必须附理由（为什么提这个）")
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO proposals (action, args, reason, by_who, status, created) "
            "VALUES (?, ?, ?, ?, 'pending', ?)",
            (action, json.dumps(args, ensure_ascii=False), reason.strip(), by, now),
        )
        pid = cur.lastrowid
        row = conn.execute("SELECT * FROM proposals WHERE id = ?", (pid,)).fetchone()
    return _row_to_dict(row)


def list_proposals(status: str | None = "pending") -> list[dict[str, Any]]:
    """列提议。默认只看 pending（待你批的）；status=None 看全部。"""
    with get_conn() as conn:
        if status is None:
            rows = conn.execute(
                "SELECT * FROM proposals ORDER BY id DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM proposals WHERE status = ? ORDER BY id DESC", (status,)
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _get_pending(conn: Any, proposal_id: int) -> Any:
    row = conn.execute(
        "SELECT * FROM proposals WHERE id = ?", (proposal_id,)
    ).fetchone()
    if row is None:
        raise KeyError(f"找不到提议 id={proposal_id}")
    if row["status"] != "pending":
        raise domain.DomainError(
            f"提议 {proposal_id} 已经是 {row['status']}，不能重复处理"
        )
    return row


def approve(proposal_id: int, now: str) -> dict[str, Any]:
    """批准并执行。派发到 store 写函数；执行成功后标记 approved。
    若派发时业务规则不通过（如非法状态迁移），提议保持 pending，抛错给用户看。
    """
    with get_conn() as conn:
        row = _get_pending(conn, proposal_id)
        action = row["action"]
        args = json.loads(row["args"])
    # 先执行（projects 层自带事务与规则校验），成功再落状态，避免"标了approved但没执行"。
    result = proj.dispatch(action, args)
    with transaction() as conn:
        conn.execute(
            "UPDATE proposals SET status = 'approved', decided = ? WHERE id = ?",
            (now, proposal_id),
        )
    return {"approved": proposal_id, "action": action, "result": result}


def reject(proposal_id: int, now: str, note: str = "") -> dict[str, Any]:
    """驳回，不执行。可附理由。"""
    with transaction() as conn:
        _get_pending(conn, proposal_id)
        conn.execute(
            "UPDATE proposals SET status = 'rejected', decided = ?, note = ? WHERE id = ?",
            (now, note.strip(), proposal_id),
        )
    return {"rejected": proposal_id, "note": note.strip()}


def clear_decided() -> dict[str, Any]:
    """清掉已批准/已驳回的历史提议（保持队列干净）。"""
    with transaction() as conn:
        cur = conn.execute("DELETE FROM proposals WHERE status != 'pending'")
    return {"cleared": cur.rowcount}
