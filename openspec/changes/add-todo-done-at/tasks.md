## 1. 测试先行（Red）

- [x] 1.1 `tests/test_gate.py`：toggle_todo 门禁测试——approve 后 done_at 有值（=approve 时间）、再 undone 后 done_at 为 null。
- [x] 1.2 `tests/test_api.py`：POST /api/todo/toggle 测试——done 后返回有 done_at、undone 后 done_at 为 null。
- [x] 1.3 旧数据兼容测试：done_at 列不存在时系统启动不报错、get_project 正常返回（done_at=null）。
- [x] 1.4 运行 pytest，确认新测试失败（Red）。

## 2. 实现（Green）

- [x] 2.1 `app/db.py`：init 逻辑加幂等 ALTER TABLE（检测 done_at 列不存在则加）。
- [x] 2.2 `app/store/projects.py`：toggle_todo 加 `now` 参数；done=True 写 done_at=now，done=False 写 done_at=NULL。
- [x] 2.3 `app/store/projects.py`：get_project 序列化 todo 时加 `done_at` 字段。
- [x] 2.4 `app/api.py`：/api/todo/toggle 调用 toggle_todo 时取 isoformat 传入 now。
- [x] 2.5 `app/store/projects.py`：_DISPATCH["toggle_todo"] 传 now（来自 approve 的 now 参数）。
- [x] 2.6 运行 pytest，全绿（Green）。

## 3. 收尾

- [ ] 3.1 开分支 feat/todo-done-at → PR → 合 main。
- [ ] 3.2 归档 change。
