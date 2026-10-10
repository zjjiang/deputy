"""questions store 行为：CRUD、到期判定、版本化回答。store 不取时钟，NOW 全部注入。"""
from __future__ import annotations

import pytest

T0 = "2026-07-23T00:00:00+00:00"


def _mk(fresh_db, title="测试题", prompt="本周有什么动向?", **kw):
    from app.store import questions

    kw.setdefault("now", T0)
    return questions.add_question(title, prompt, **kw)


def _submit(fresh_db, qid, body="回答内容", **kw):
    from app.store import questions

    kw.setdefault("run_date", "2026-07-23")
    kw.setdefault("now", T0)
    return questions.submit_answer(qid, body, **kw)


def _due_map(fresh_db, now):
    from app.store import questions

    return {q["id"]: q for q in questions.list_questions(now)}


# ---------- CRUD ----------

def test_add_question_generates_ids_and_ord(fresh_db):
    q1 = _mk(fresh_db)
    q2 = _mk(fresh_db, title="第二题")
    assert q1["id"] == "q1" and q2["id"] == "q2"
    assert q2["ord"] == q1["ord"] + 1
    assert q1["active"] is True
    assert q1["cadence"] == "daily"
    assert q1["filter"] == {}
    assert q1["last_run_at"] is None and q1["requested_at"] is None


def test_add_question_empty_title_or_prompt_rejected(fresh_db):
    with pytest.raises(Exception):
        _mk(fresh_db, title="   ")
    with pytest.raises(Exception):
        _mk(fresh_db, prompt="")


def test_add_question_illegal_cadence_rejected(fresh_db):
    with pytest.raises(Exception):
        _mk(fresh_db, cadence="hourly")


def test_add_question_filter_validation(fresh_db):
    with pytest.raises(Exception):
        _mk(fresh_db, filter={"kinds": "paper"})  # kinds 必须是数组
    with pytest.raises(Exception):
        _mk(fresh_db, filter={"days": 0})  # 非正整数
    with pytest.raises(Exception):
        _mk(fresh_db, filter={"max_docs": -1})
    with pytest.raises(Exception):
        _mk(fresh_db, filter={"unknown": 1})  # 未知过滤键
    # kinds/domain 是 feed-curator 侧分类法，deputy 不校验取值、透传
    q = _mk(fresh_db, filter={"kinds": ["paper", "article"], "domain": "具身智能", "days": 7})
    assert q["filter"] == {"kinds": ["paper", "article"], "domain": "具身智能", "days": 7}


def test_edit_question(fresh_db):
    from app.store import questions

    q = _mk(fresh_db)
    q2 = questions.edit_question(q["id"], title="改名", cadence="weekly", now=T0)
    assert q2["title"] == "改名" and q2["cadence"] == "weekly"
    with pytest.raises(Exception):
        questions.edit_question("q99", title="x", now=T0)  # 不存在
    with pytest.raises(Exception):
        questions.edit_question(q["id"], cadence="bad", now=T0)  # 非法取值
    with pytest.raises(Exception):
        questions.edit_question(q["id"], title=" ", now=T0)  # 空标题


def test_set_question_active(fresh_db):
    from app.store import questions

    q = _mk(fresh_db)
    q2 = questions.set_question_active(q["id"], False)
    assert q2["active"] is False
    q3 = questions.set_question_active(q["id"], True)
    assert q3["active"] is True
    with pytest.raises(Exception):
        questions.set_question_active("q99", False)


def test_remove_question_cascades_answers(fresh_db):
    from app.store import questions

    q = _mk(fresh_db)
    _submit(fresh_db, q["id"])
    questions.remove_question(q["id"])
    with pytest.raises(Exception):
        questions.get_question(q["id"])
    assert questions.list_answers(q["id"]) == []


def test_remove_missing_question(fresh_db):
    from app.store import questions

    with pytest.raises(Exception):
        questions.remove_question("q99")


def test_get_question_missing(fresh_db):
    from app.store import questions

    with pytest.raises(Exception):
        questions.get_question("q99")


# ---------- 到期判定 ----------

def test_due_first_run(fresh_db):
    q = _mk(fresh_db)
    row = _due_map(fresh_db, T0)[q["id"]]
    assert row["due"] is True and row["due_reason"] == "first-run"


def test_daily_not_due_within_period(fresh_db):
    q = _mk(fresh_db)
    _submit(fresh_db, q["id"])
    row = _due_map(fresh_db, "2026-07-23T23:00:00+00:00")[q["id"]]  # 23h 后
    assert row["due"] is False and row["due_reason"] is None


def test_daily_due_after_exact_period(fresh_db):
    q = _mk(fresh_db)
    _submit(fresh_db, q["id"])
    row = _due_map(fresh_db, "2026-07-24T00:00:00+00:00")[q["id"]]  # 恰 24h
    assert row["due"] is True and row["due_reason"] == "scheduled"


def test_weekly_due_at_exact_7d(fresh_db):
    q = _mk(fresh_db, cadence="weekly")
    _submit(fresh_db, q["id"])
    not_yet = _due_map(fresh_db, "2026-07-29T23:59:59+00:00")[q["id"]]
    assert not_yet["due"] is False
    due = _due_map(fresh_db, "2026-07-30T00:00:00+00:00")[q["id"]]  # 恰 7 天
    assert due["due"] is True and due["due_reason"] == "scheduled"


def test_inactive_never_due(fresh_db):
    from app.store import questions

    q = _mk(fresh_db)  # 从未运行，本应 first-run 到期
    questions.set_question_active(q["id"], False)
    row = _due_map(fresh_db, T0)[q["id"]]
    assert row["due"] is False and row["due_reason"] is None


def test_manual_not_due_without_request(fresh_db):
    q = _mk(fresh_db, cadence="manual")
    row = _due_map(fresh_db, T0)[q["id"]]
    assert row["due"] is False and row["due_reason"] is None


def test_requested_overrides_last_run(fresh_db):
    from app.store import questions

    q = _mk(fresh_db)
    _submit(fresh_db, q["id"])  # 当天已跑，本不到期
    questions.request_run(q["id"], now="2026-07-23T12:00:00+00:00")
    row = _due_map(fresh_db, "2026-07-23T12:30:00+00:00")[q["id"]]
    assert row["due"] is True and row["due_reason"] == "manual-request"
    with pytest.raises(Exception):
        questions.request_run("q99", now=T0)  # 不存在


def test_request_run_is_idempotent_on_rerequest(fresh_db):
    from app.store import questions

    q = _mk(fresh_db, cadence="manual")
    questions.request_run(q["id"], now=T0)
    questions.request_run(q["id"], now="2026-07-23T01:00:00+00:00")
    row = _due_map(fresh_db, T0)[q["id"]]
    assert row["due"] is True  # 仍到期，只是刷新标记


# ---------- submit 与版本化 ----------

def test_submit_creates_v1_and_updates_question(fresh_db):
    q = _mk(fresh_db)
    a = _submit(
        fresh_db,
        q["id"],
        body="v1 内容",
        sources=[{"doc_id": 1, "title": "t", "url": "https://example.com"}],
        confidence="high",
        model="龙虾",
        meta={"gaps": ["缺竞品维度"]},
    )
    assert a["version"] == 1 and a["status"] == "new"
    assert a["sources"][0]["doc_id"] == 1
    assert a["meta"]["gaps"] == ["缺竞品维度"]
    assert a["confidence"] == "high" and a["model"] == "龙虾"
    qd = _due_map(fresh_db, T0)[q["id"]]
    assert qd["last_run_at"] == T0


def test_same_day_resubmit_creates_v2_and_supersedes_v1(fresh_db):
    q = _mk(fresh_db)
    _submit(fresh_db, q["id"], body="v1")
    v2 = _submit(fresh_db, q["id"], body="v2", now="2026-07-23T12:00:00+00:00")
    assert v2["version"] == 2 and v2["status"] == "new"
    from app.store import questions

    rows = questions.list_answers(q["id"])
    assert len(rows) == 2
    by_v = {r["version"]: r for r in rows}
    assert by_v[1]["status"] == "superseded"  # 保留可查
    assert by_v[1]["body_md"] == "v1"
    assert by_v[2]["status"] == "new"


def test_cross_day_resets_version(fresh_db):
    q = _mk(fresh_db)
    _submit(fresh_db, q["id"], body="d1v1")
    _submit(fresh_db, q["id"], body="d1v2", now="2026-07-23T12:00:00+00:00")
    a3 = _submit(fresh_db, q["id"], body="d2v1", run_date="2026-07-24",
                 now="2026-07-24T00:30:00+00:00")
    assert a3["version"] == 1  # 新的一天从 v1 重新计
    from app.store import questions

    all_rows = questions.list_answers(q["id"])
    assert len(all_rows) == 3
    d1 = [r for r in all_rows if r["run_date"] == "2026-07-23"]
    assert {r["version"]: r["status"] for r in d1} == {1: "superseded", 2: "new"}


def test_submit_clears_requested_and_advances_last_run(fresh_db):
    from app.store import questions

    q = _mk(fresh_db, cadence="manual")
    questions.request_run(q["id"], now=T0)
    _submit(fresh_db, q["id"], now="2026-07-23T06:00:00+00:00")
    qd = questions.get_question(q["id"])
    assert qd["requested_at"] is None
    assert qd["last_run_at"] == "2026-07-23T06:00:00+00:00"


def test_submit_rejections(fresh_db):
    q = _mk(fresh_db)
    with pytest.raises(Exception):
        _submit(fresh_db, q["id"], body="   ")  # 空正文
    with pytest.raises(Exception):
        _submit(fresh_db, q["id"], confidence="certain")  # 非法 confidence
    with pytest.raises(Exception):
        _submit(fresh_db, q["id"], run_date="07/23")  # 非法 run_date 格式
    with pytest.raises(Exception):
        _submit(fresh_db, "q99")  # 不存在问题
    from app.store import questions

    questions.set_question_active(q["id"], False)
    with pytest.raises(Exception):
        _submit(fresh_db, q["id"])  # 已停用


def test_get_question_with_answers_latest_per_day(fresh_db):
    from app.store import questions

    q = _mk(fresh_db)
    _submit(fresh_db, q["id"], body="d1v1")
    _submit(fresh_db, q["id"], body="d1v2", now="2026-07-23T12:00:00+00:00")
    _submit(fresh_db, q["id"], body="d2v1", run_date="2026-07-24",
            now="2026-07-24T01:00:00+00:00")
    qd = questions.get_question(q["id"], with_answers=2)
    answers = qd["answers"]
    assert [a["body_md"] for a in answers] == ["d2v1", "d1v2"]  # 各日最新版，新日在前
    assert all(a["status"] != "superseded" for a in answers)


def test_mark_answer_read_only_affects_that_row(fresh_db):
    from app.store import questions

    q = _mk(fresh_db)
    _submit(fresh_db, q["id"], body="v1")
    v2 = _submit(fresh_db, q["id"], body="v2", now="2026-07-23T12:00:00+00:00")
    v1 = [r for r in questions.list_answers(q["id"]) if r["version"] == 1][0]
    questions.mark_answer_read(v1["id"], now=T0)
    rows = {r["id"]: r for r in questions.list_answers(q["id"])}
    assert rows[v1["id"]]["status"] == "read"
    assert rows[v2["id"]]["status"] == "new"
    with pytest.raises(Exception):
        questions.mark_answer_read(9999, now=T0)


def test_delete_answer(fresh_db):
    from app.store import questions

    q = _mk(fresh_db)
    _submit(fresh_db, q["id"], body="v1")
    v2 = _submit(fresh_db, q["id"], body="v2", now="2026-07-23T12:00:00+00:00")
    questions.delete_answer(v2["id"])
    rows = questions.list_answers(q["id"])
    assert len(rows) == 1 and rows[0]["body_md"] == "v1"
    with pytest.raises(Exception):
        questions.delete_answer(v2["id"])  # 已删除


def test_list_answers_limit_and_order(fresh_db):
    from app.store import questions

    q = _mk(fresh_db)
    _submit(fresh_db, q["id"], body="d1v1")
    _submit(fresh_db, q["id"], body="d1v2", now="2026-07-23T12:00:00+00:00")
    _submit(fresh_db, q["id"], body="d2v1", run_date="2026-07-24",
            now="2026-07-24T01:00:00+00:00")
    rows = questions.list_answers(q["id"], limit=2)
    assert [r["body_md"] for r in rows] == ["d2v1", "d1v2"]  # 新在前
