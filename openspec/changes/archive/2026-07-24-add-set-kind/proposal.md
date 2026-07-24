## Why

项目的 `kind`（biz 商业 / tool 自用工具）目前只能在 `add_project` 建项目时设定，之后无法修改。实际使用中会遇到需要在两类之间调整的项目（例如一个自用工具后来变成对外商业项目，或反之），现在只能删了重建，丢失 todo 和历史。

## What Changes

- 新增修改已有项目 `kind` 的能力，贯穿三层：
  - **store**：新增 `set_kind(project_id, kind)` 写函数，校验 kind ∈ {biz, tool}，复用现有事务与 `_require_project`。
  - **domain**：`PROPOSAL_ACTIONS` 白名单新增 `set_kind`（分身只能走门禁提议，不能直改）。
  - **MCP**：`propose` 工具的 action 文档补 `set_kind {project_id, kind}`；派发表 `_DISPATCH` 加对应项。
  - **API**：新增 `POST /api/project/kind`，供用户在看板直接改（不走门禁，与 set_stage/set_trigger 一致）。
- 与现有 `set_drive` / `set_stage` 完全同构，不引入新模式。

## Capabilities

### New Capabilities
- `project-management`: 项目真源的读写能力（含 stage/drive/kind/trigger/todo 的增改、门禁提议动作白名单）。本 change 首次为该 capability 建 spec，并纳入 set_kind 这条新要求。

### Modified Capabilities
<!-- 无既有 spec，全部走 New Capabilities -->

## Impact

- 代码：`app/store/projects.py`（+set_kind、+_DISPATCH 项）、`app/domain.py`（+PROPOSAL_ACTIONS 项）、`app/mcp_server.py`（propose 文档）、`app/api.py`（+端点 + Pydantic 模型）。
- 数据：无 schema 变更（projects.kind 列已存在）。
- 测试：新增 set_kind 的门禁测试（提议不落地、批准才改、非法 kind 被拒）+ API 端点测试。
- 无破坏性变更；无新依赖。
