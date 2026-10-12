## Why

deputy 升格为三模块（作战处=项目管理 · 军情处=research · 讲武堂=学习，见 add-learning），现有门面（「二号位 · 决策中枢」、平铺 tab、「问题」tab 名）与新定位不一致。纯外观与文案调整，无行为变更，故 skip_specs。

## What Changes

- header 标语：「二号位 · 决策中枢」→「一号位的参谋部」（含状态行文案微调）
- nav tab 分组：按「作战 / 军情 / 讲武」三处分组展示（分组标题为纯样式元素）
- tab 改名：「问题」→「军情」（其余 tab 名不变）
- CLAUDE.md 与 `app/mcp_server.py` docstring 的自我介绍措辞同步（二号位→参谋部口径），并写定参谋部章程边界：
  - **素材边界**：军情处强依赖 feed-curator（情报只吃订阅语料，不做全网检索）；讲武堂素材次序为 自身知识 → 互联网 → 语料部分佐证
  - **状态归属**（状态跟着实体走）：奏折已阅 = deputy `answers.status`；课程掌握 = deputy `point.status`；原文已读/收藏 = feed-curator `reading` 表，永不搬进 deputy
  - **军情处两模式**：奏折（预设问题定时/手动简报，deputy）+ 面圣（微信对话即答，龙虾走 feed-curator 检索，不进 deputy、不落档）
- 讲武 tab 本身由 add-learning 引入，本 change 不含

## Capabilities

### New Capabilities

- 无（skip_specs：tab 文案与标语不属于 spec 化行为）

### Modified Capabilities

- 无

## Impact

- `app/web/index.html`（header/tagline/tab 分组/「军情」改名）
- `CLAUDE.md`、`app/mcp_server.py`（措辞同步）
- 现有 spec 均不涉及 tab 命名与标语，无 delta；`uv run pytest -q` 应保持全绿（纯前端文案）
