## 1. Store 层（TDD：Red → Green）

- [x] 1.1 写 `tests/test_learning_store.py`（Red，复用 fresh_db + 固定 NOW）：track CRUD（id l1,l2/ord/空标题或 goal → DomainError/不存在 → KeyError）；跑确认全红
- [x] 1.2 同文件补大纲与状态用例（Red）：set_curriculum 首次落地 N 个 todo；整体替换 + 同名继承状态（改名/移除相应消失）；分身经 dispatch 的门禁路径；point 状态机 todo→learned/revisit、revisit→learned/todo、非法状态 → DomainError；learned_at 写入
- [x] 1.3 同文件补小结与下一课用例（Red）：submit_lesson_note 追加式（同点多条）、track 删除级联、大纲替换不影响历史小结；next_point（todo 队首/回炉优先/走完 None）
- [x] 1.4 `app/domain.py`：`VALID_TRACK_STATUSES`/`VALID_POINT_STATUSES` + label；`PROPOSAL_ACTIONS` +3（add_track/set_curriculum/set_point_status）
- [x] 1.5 `app/store/db.py`：SCHEMA 追加 learning_tracks/knowledge_points/lesson_notes 三表；跑全量确认无回归
- [x] 1.6 写 `app/store/learning.py`（Green）：add/edit/remove track、set_track_status、set_curriculum（同名继承）、set_point_status、list_tracks(now?)、get_track（详情+notes）、list_notes、submit_lesson_note、next_point、learning.handles/dispatch；跑 `pytest tests/test_learning_store.py` 全绿
- [x] 1.7 `tests/test_gate.py` 补用例：add_track 提议→批准落地、reject 不落地；set_curriculum 批准落地/同名继承；set_point_status 批准生效/非法状态批准被拦保持 pending；跑 `pytest tests/test_gate.py` 全绿

## 2. API 层（TDD：Red → Green）

- [x] 2.1 写 `tests/test_learning_api.py`（Red）：GET /api/learning 概览（进度计数/下一课）；track add/edit/remove/status、curriculum 直设、point status 200 路径；校验失败 400；不存在 404
- [x] 2.2 `app/api.py`（Green）：约 8 端点 + Pydantic body + `_guard`；跑 `pytest tests/test_learning_api.py` 全绿

## 3. MCP 层（TDD：Red → Green）

- [x] 3.1 `tests/test_mcp_contract.py`：精确集合 9→11（+get_learning/submit_lesson_note）（Red）；教学端到端：get_learning 取下一课 → submit_lesson_note → 小结可见（Red）；确认无直写工具测试对新白名单自动生效
- [x] 3.2 `app/mcp_server.py`（Green）：两个新工具 + docstring（下一课语义/小结纪律，指向 docs/teaching-sop.md）；跑 `pytest tests/test_mcp_contract.py` 全绿

## 4. 前端

- [x] 4.1 `app/web/index.html`：「讲武」tab（track 卡片：标题/目标/进度 learned/total/下一课/状态操作；展开知识点清单三键自评 懂了/没懂/重置；小结历史复用回答视图样式）；load() 并入 /api/learning；actionLabel +3；自查无装饰性 emoji
- [x] 4.2 本地 smoke：建 track → 门禁批 set_curriculum（模拟分身）→ 看板自评 → 分身 submit_lesson_note → 讲武 tab 进度/小结正确；XSS 回归（来源链接白名单）

## 5. 文档与收尾

- [ ] 5.1 写 `docs/teaching-sop.md`：上课流程（取下一课→讲解→引导自评→代写提议→存档）、没懂回炉、小结规范、无检索降级、微信入口说明（无 cron，进度驱动）
- [ ] 5.2 CLAUDE.md：模块清单加 learning.py；红线 1 例外清单补 lesson_notes（派生物直落）
- [ ] 5.3 全量回归：`uv run pytest -q` 全绿（11 工具契约 + 守门测试）；`openspec validate add-learning` 通过
