## 1. 测试先行（Red）

- [x] 1.1 `tests/test_gate.py`：加 set_kind 门禁测试——propose 不落地、approve 后 kind 变、非法 kind 提议 approve 时被拒且保持 pending。
- [x] 1.2 `tests/test_api.py`：加 `POST /api/project/kind` 测试——合法改成功、非法 kind→400、不存在项目→404。
- [x] 1.3 `tests/test_mcp_contract.py`：确认 set_kind 不作为独立 MCP 工具泄漏（应已被现有 forbidden 检查覆盖，验证即可）。
- [x] 1.4 运行 `uv run pytest -q`，确认新测试**失败**（Red）。

## 2. 实现（Green）

- [x] 2.1 `app/store/projects.py`：新增 `set_kind(project_id, kind)`（照 set_drive）；`_DISPATCH` 加 `set_kind`。
- [x] 2.2 `app/domain.py`：`PROPOSAL_ACTIONS` 加 `"set_kind": ("project_id", "kind")`。
- [x] 2.3 `app/mcp_server.py`：`propose` docstring 的 action 列表补 `set_kind {project_id, kind}`。
- [x] 2.4 `app/api.py`：加 `ProjectKind` 模型 + `POST /api/project/kind` 端点。
- [x] 2.5 运行 `uv run pytest -q`，全绿（Green）。

## 3. 收尾

- [ ] 3.1 （可选）看板 UI 加改 kind 的入口——本 change 不强制，后端能力先就位。
- [ ] 3.2 开分支 `feat/set-kind` → PR → 审阅通过合 main。
- [ ] 3.3 归档：`/opsx:archive` 或 openspec-archive-change。
