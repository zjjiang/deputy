## Why

看板项目在同一个桶（主攻/运营/维护/探索/雪藏/归档）内目前只能按创建顺序排列，用户无法把重要的项目排到前面。`projects` 表已有 `ord` 字段用于排序，但没有任何写路径能修改它——新建项目时赋值一次后就再不会变。需要补一个"挪动顺序"的入口，且用户和分身都要能触发（分身经门禁提议，用户直接操作）。

## What Changes

- store 层新增 `reorder_project(project_id, target_id, position)`：把 `project_id` 插到 `target_id` 的前面（`before`）或后面（`after`），随后按新顺序重写全部项目的 `ord`（0,1,2,...），修掉 `add_project` 用 `COUNT(*)` 算 `ord` 在删除后可能撞号的隐患。
- `domain.PROPOSAL_ACTIONS` 新增 `reorder_project: (project_id, target_id, position)`，纳入门禁白名单。
- `app/api.py` 新增 `POST /api/project/reorder`，供用户在看板直接操作（不经门禁）。
- `app/mcp_server.py` 的 `propose` 工具文档新增 `reorder_project` 说明（不新增直写工具，仍走 `propose`）。
- 看板每张项目卡片新增 ↑/↓ 按钮，在当前所属桶的过滤列表内，把项目和上一个/下一个邻居交换位置（前端计算相邻 target_id，调用新端点）。桶边界项目对应方向的按钮禁用/隐藏。

排序作用于全局 `ord` 序列（不感知"桶"概念），桶只是前端按 stage 过滤的展示视图；同桶内挪动天然只影响该桶展示顺序，不影响其他桶。

## Capabilities

### New Capabilities
（无新增能力，扩展现有能力）

### Modified Capabilities
- `project-management`: 新增排序需求——支持修改项目 `ord` 排序，用户可直接操作、分身需经门禁提议；看板需提供排序交互。

## Impact

- `app/domain.py`：`PROPOSAL_ACTIONS` 新增一项。
- `app/store/projects.py`：新增 `reorder_project`、纳入 `_DISPATCH`；`add_project` 的 `ord` 赋值逻辑顺带修正（改为取当前最大 `ord`+1，避免撞号）。
- `app/api.py`：新增 `ProjectReorder` 请求体与 `/api/project/reorder` 端点。
- `app/mcp_server.py`：`propose` 工具的 docstring 补充新 action。
- `app/web/index.html`：项目卡片新增 ↑/↓ 按钮与对应 JS。
- `tests/`：新增门禁测试（propose 不落地/approve 生效/非法 target 被拒）与 store 单测。
- 无破坏性变更，`ord` 字段已存在，无需迁移。
