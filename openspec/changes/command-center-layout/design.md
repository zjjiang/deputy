## Context

`/api/state` 返回 projects（含 id/name/stage/drive/kind/trigger/todos）+ focus + backlog。当前 renderBoard 把项目按 stage 排序后平铺。本 change 只改 renderBoard 的组织方式与样式，不动数据。

## Goals / Non-Goals

**Goals:**
- 界面结构 = 用户操作系统：按桶分组、主攻最重、焦点优先。
- 一眼看全盘分布（桶位概览）。
- 保持克制专业，不回到 emoji/渐变。

**Non-Goals:**
- 不改数据结构/API/行为。
- 不改门禁 tab、需求池 tab 的核心逻辑（跟随新配色即可）。
- 不引入框架/构建。

## Decisions

- **桶（bucket）定义**（由 stage 映射，不新增字段）：
  - 主攻 = attack；运营 = operate；维护/收租 = maintain；探索 = probe/spark；雪藏 = frozen；归档 = archived。
- **布局**：
  - 顶部 `header` 保持；其下加 `focus` 报头（强调，最醒目）。
  - `overview` 概览条：各桶名 + 计数，等宽数字，横向排列。
  - 项目**按桶分区**渲染，每区一个 `section-label`（如"主攻 · 1"）。主攻卡整行、字大、左 edge 4px 强调红；运营/维护正常；雪藏/归档收窄、降饱和。
- **配色**沿用上一版 token（靛蓝强调 + 中性灰 + 语义色），语义色左竖线加宽到 4px、颜色加深一档，确保可辨。
- **项目 ID**：卡片名旁以 `--mono` 小灰字显示（如 `p3`）。
- 空桶不渲染分区（避免噪音）。

## Risks / Trade-offs

- 按桶分组后，若某桶为空则跳过——需确保排序稳定、分区标题与内容不错位。
- CSS 特异性：新增 section/bucket 类时注意与 .card 既有 padding/margin 不打架。
- 概览条在窄屏需可换行，不撑破布局。
