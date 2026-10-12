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


def test_toggle_todo_done_at_via_gate(fresh_db):
    """门禁 approve toggle_todo 时，done_at 记 approve 时间。"""
    from app.store import projects, proposals

    # 先加一条 todo
    proposals.propose("add_todo", {"project_id": "p1", "text": "测 done_at"},
                      reason="铺测试", now="2026-07-20T10:00:00")
    proposals.approve(1, now="2026-07-20T10:00:00")
    tid = projects.get_project("p1")["todos"][0]["id"]

    # propose toggle done
    proposals.propose("toggle_todo", {"project_id": "p1", "todo_id": tid, "done": True},
                      reason="完成了", now="2026-07-21T08:00:00")
    proposals.approve(2, now="2026-07-22T09:30:00")  # approve 时间
    t = projects.get_project("p1")["todos"][0]
    assert t["done"] is True
    assert t["done_at"] == "2026-07-22T09:30:00"


def test_toggle_todo_undone_clears_done_at(fresh_db):
    """取消完成后 done_at 清空。"""
    from app.store import projects, proposals

    proposals.propose("add_todo", {"project_id": "p1", "text": "先完成再取消"},
                      reason="t", now=NOW)
    proposals.approve(1, now=NOW)
    tid = projects.get_project("p1")["todos"][0]["id"]
    # 直接 store 调用（用户侧，不走门禁）
    projects.toggle_todo("p1", tid, done=True, now="2026-07-23T12:00:00")
    assert projects.get_project("p1")["todos"][0]["done_at"] == "2026-07-23T12:00:00"
    projects.toggle_todo("p1", tid, done=False, now="2026-07-23T13:00:00")
    assert projects.get_project("p1")["todos"][0]["done_at"] is None


# ---------- 预设问题的门禁动作（add_question / edit_question）----------

NOW_Q = "2026-07-23T00:00:00+00:00"


def test_add_question_via_gate(fresh_db):
    from app.store import proposals, questions

    proposals.propose(
        "add_question",
        {"title": "分身提的题", "prompt": "本周有什么动向?", "cadence": "weekly"},
        reason="觉得该盯这个角度", now=NOW_Q,
    )
    assert questions.list_questions(NOW_Q) == []  # 提议不落地
    pend = proposals.list_proposals("pending")
    assert len(pend) == 1 and pend[0]["action"] == "add_question"
    proposals.approve(pend[0]["id"], now=NOW_Q)
    qs = questions.list_questions(NOW_Q)
    assert len(qs) == 1
    assert qs[0]["title"] == "分身提的题" and qs[0]["cadence"] == "weekly"
    assert proposals.list_proposals("pending") == []


def test_reject_question_proposal_does_not_create(fresh_db):
    from app.store import proposals, questions

    prop = proposals.propose(
        "add_question", {"title": "t", "prompt": "p"}, reason="r", now=NOW_Q
    )
    proposals.reject(prop["id"], now=NOW_Q, note="不要")
    assert questions.list_questions(NOW_Q) == []


def test_add_question_illegal_value_rejected_on_approve(fresh_db):
    from app.store import proposals, questions

    prop = proposals.propose(
        "add_question",
        {"title": "x", "prompt": "p", "cadence": "hourly"},
        reason="测试", now=NOW_Q,
    )
    with pytest.raises(Exception):
        proposals.approve(prop["id"], now=NOW_Q)  # 派发被业务规则拦截
    assert questions.list_questions(NOW_Q) == []  # 问题未创建
    pend = proposals.list_proposals("pending")
    assert len(pend) == 1 and pend[0]["id"] == prop["id"]  # 提议保持待批


def test_add_question_missing_required_args_rejected_on_propose(fresh_db):
    from app.store import proposals

    with pytest.raises(Exception):
        proposals.propose(
            "add_question", {"title": "只有标题"}, reason="缺 prompt", now=NOW_Q
        )


def test_edit_question_via_gate(fresh_db):
    from app.store import proposals, questions

    q = questions.add_question("原题", "原prompt", now=NOW_Q)
    prop = proposals.propose(
        "edit_question", {"question_id": q["id"], "title": "改过的题"},
        reason="时间窗放宽", now=NOW_Q,
    )
    assert questions.get_question(q["id"])["title"] == "原题"  # 未批准不生效
    proposals.approve(prop["id"], now=NOW_Q)
    assert questions.get_question(q["id"])["title"] == "改过的题"


# ---------- 讲武堂的门禁动作（add_track / set_curriculum / set_point_status）----------

NOW_L = "2026-10-12T00:00:00+00:00"


def test_add_track_via_gate(fresh_db):
    from app.store import learning, proposals

    proposals.propose(
        "add_track", {"title": "具身智能", "goal": "能看懂前沿论文"},
        reason="想系统学", now=NOW_L,
    )
    assert learning.list_tracks() == []  # 提议不落地
    pend = proposals.list_proposals("pending")
    assert pend[0]["action"] == "add_track"
    proposals.approve(pend[0]["id"], now=NOW_L)
    tracks = learning.list_tracks()
    assert len(tracks) == 1 and tracks[0]["title"] == "具身智能"


def test_set_curriculum_via_gate(fresh_db):
    from app.store import learning, proposals

    t = learning.add_track("具身智能", "g", now=NOW_L)
    prop = proposals.propose(
        "set_curriculum",
        {"track_id": t["id"], "points": [{"title": "A"}, {"title": "B"}]},
        reason="首份大纲", now=NOW_L,
    )
    assert learning.get_track(t["id"])["points"] == []  # 未批准不落地
    proposals.approve(prop["id"], now=NOW_L)
    pts = learning.get_track(t["id"])["points"]
    assert [p["title"] for p in pts] == ["A", "B"]


def test_set_point_status_via_gate_and_blocked_on_illegal(fresh_db):
    from app.store import learning, proposals

    t = learning.add_track("具身智能", "g", now=NOW_L)
    learning.set_curriculum(t["id"], [{"title": "A"}], now=NOW_L)
    kid = learning.get_track(t["id"])["points"][0]["id"]
    prop = proposals.propose(
        "set_point_status", {"point_id": kid, "status": "learned"},
        reason="用户在微信说懂了", now=NOW_L,
    )
    proposals.approve(prop["id"], now=NOW_L)
    assert learning.get_point(kid)["status"] == "learned"

    # 非法状态：批准时被业务规则拦截，提议保持 pending
    bad = proposals.propose(
        "set_point_status", {"point_id": kid, "status": "mastered"},
        reason="误提交", now=NOW_L,
    )
    with pytest.raises(Exception):
        proposals.approve(bad["id"], now=NOW_L)
    assert learning.get_point(kid)["status"] == "learned"  # 真源未变
    pend = proposals.list_proposals("pending")
    assert len(pend) == 1 and pend[0]["id"] == bad["id"]


def test_add_track_missing_required_args_rejected_on_propose(fresh_db):
    from app.store import proposals

    with pytest.raises(Exception):
        proposals.propose("add_track", {"title": "只有标题"}, reason="缺 goal", now=NOW_L)
