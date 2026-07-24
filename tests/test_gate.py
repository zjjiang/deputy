"""门禁核心行为：提议不落地、批准才生效、规则被强制、非法动作被拒。"""
from __future__ import annotations

import pytest

NOW = "2026-07-23T00:00:00+00:00"


def test_propose_does_not_mutate_source(fresh_db):
    from app.store import projects, proposals

    proposals.propose("add_todo", {"project_id": "p1", "text": "备料出的待办"},
                      reason="测试", now=NOW)
    assert projects.get_project("p1")["todos"] == []  # 没落地
    pend = proposals.list_proposals("pending")
    assert len(pend) == 1 and pend[0]["action"] == "add_todo"


def test_approve_executes(fresh_db):
    from app.store import projects, proposals

    prop = proposals.propose("add_todo", {"project_id": "p1", "text": "该落地的活"},
                             reason="测试", now=NOW)
    proposals.approve(prop["id"], now=NOW)
    p = projects.get_project("p1")
    assert len(p["todos"]) == 1 and p["todos"][0]["text"] == "该落地的活"
    assert proposals.list_proposals("pending") == []


def test_reject_does_not_execute(fresh_db):
    from app.store import projects, proposals

    prop = proposals.propose("add_todo", {"project_id": "p1", "text": "不该做的"},
                             reason="测试", now=NOW)
    proposals.reject(prop["id"], now=NOW, note="不需要")
    assert projects.get_project("p1")["todos"] == []


def test_double_decision_rejected(fresh_db):
    from app.store import proposals

    prop = proposals.propose("add_to_backlog", {"text": "x"}, reason="测试", now=NOW)
    proposals.approve(prop["id"], now=NOW)
    with pytest.raises(Exception):
        proposals.approve(prop["id"], now=NOW)


def test_unknown_action_rejected(fresh_db):
    from app.store import proposals

    with pytest.raises(Exception):
        proposals.propose("drop_database", {"x": 1}, reason="恶意", now=NOW)


def test_proposal_requires_reason(fresh_db):
    from app.store import proposals

    with pytest.raises(Exception):
        proposals.propose("add_to_backlog", {"text": "x"}, reason="  ", now=NOW)


def test_state_machine_enforced_on_approve(fresh_db):
    """批准非法迁移应失败，提议保持 pending，真源不变。"""
    from app.store import projects, proposals

    prop = proposals.propose("set_stage", {"project_id": "p1", "stage": "operate"},
                             reason="非法迁移", now=NOW)
    with pytest.raises(Exception):
        proposals.approve(prop["id"], now=NOW)
    assert projects.get_project("p1")["stage"] == "probe"
    assert len(proposals.list_proposals("pending")) == 1


def test_attack_uniqueness(fresh_db):
    """主攻唯一：已有 attack 时批准另一个进 attack 应失败。"""
    from app.store import projects, proposals

    projects.set_stage("p1", "attack")
    with fresh_db.transaction() as conn:
        conn.execute(
            "INSERT INTO projects (id, name, stage, drive, kind, trigger, ord) "
            "VALUES ('p2', '第二项目', 'probe', 'self', 'biz', '', 1)"
        )
    prop = proposals.propose("set_stage", {"project_id": "p2", "stage": "attack"},
                             reason="抢主攻", now=NOW)
    with pytest.raises(Exception):
        proposals.approve(prop["id"], now=NOW)
    assert projects.get_project("p2")["stage"] == "probe"


def test_set_kind_via_gate(fresh_db):
    """改 kind 走门禁：propose 不落地，approve 后才变。"""
    from app.store import projects, proposals

    assert projects.get_project("p1")["kind"] == "biz"
    prop = proposals.propose("set_kind", {"project_id": "p1", "kind": "tool"},
                             reason="这个转成自用工具了", now=NOW)
    # 提议未落地
    assert projects.get_project("p1")["kind"] == "biz"
    # 批准后生效
    proposals.approve(prop["id"], now=NOW)
    assert projects.get_project("p1")["kind"] == "tool"


def test_set_kind_illegal_value_rejected_on_approve(fresh_db):
    """非法 kind 的提议在 approve 时被拒，保持 pending，真源不变。"""
    from app.store import projects, proposals

    prop = proposals.propose("set_kind", {"project_id": "p1", "kind": "nonsense"},
                             reason="非法值", now=NOW)
    with pytest.raises(Exception):
        proposals.approve(prop["id"], now=NOW)
    assert projects.get_project("p1")["kind"] == "biz"
    assert len(proposals.list_proposals("pending")) == 1


def test_set_kind_direct_store_validates(fresh_db):
    """store.set_kind 直接调用也校验合法值。"""
    from app.store import projects

    with pytest.raises(Exception):
        projects.set_kind("p1", "nonsense")


def test_list_all_includes_history(fresh_db):
    """status=None 返回全部（含已决策），是 UI '最近处理过的' 的数据源。"""
    from app.store import proposals

    p1 = proposals.propose("add_to_backlog", {"text": "a"}, reason="r", now=NOW)
    proposals.approve(p1["id"], now=NOW)
    proposals.propose("add_to_backlog", {"text": "b"}, reason="r", now=NOW)
    assert len(proposals.list_proposals(None)) == 2
    assert len(proposals.list_proposals("pending")) == 1
