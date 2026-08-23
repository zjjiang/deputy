## Context

`app/store/db.py` 的 `projects` 表已有 `ord INTEGER NOT NULL DEFAULT 0`，读取时 `ORDER BY ord, id`，但目前只有 `add_project` 在插入时写一次 `ord`（`SELECT COUNT(*) FROM projects`），此后没有任何写路径能改动它。看板前端（`app/web/index.html`）不直接按 `stage` 分组，而是用 `BUCKETS` 常量把多个 `stage` 合并成六个展示桶（主攻/运营/维护/探索/雪藏/归档），过滤后渲染——"探索"桶合并了 `probe` 和 `spark`。

项目遵循"备料→门禁→释放"：用户在看板直接操作真源（`app/api.py` 里"你直接操作真源"一类端点），分身只能经 `propose()` 提议、用户 approve 后才派发到同一个 store 写函数（`app/store/projects.py::dispatch`）。任何新写能力必须同时接入这两条路径，且业务规则只在 store 层强制。

## Goals / Non-Goals

**Goals:**
- 支持把项目在其所属桶内挪动顺序（前移/后移一位），重要项目排前面。
- 排序操作对"桶"无感知——只操作全局 `ord` 序列，桶只是前端按 stage 过滤后的呈现视图，天然保序。
- 用户可直接操作（看板点按钮），分身只能经门禁提议，两条路径共用同一个 store 函数。
- 顺带修正 `add_project` 计算新 `ord` 时用 `COUNT(*)` 在删除项目后可能撞号的问题。

**Non-Goals:**
- 不做真正的拖拽排序（成本高，先上 ↑/↓ 按钮，体验验证后再考虑升级）。
- 不给 `ord` 排序赋予"重要性"以外的语义（不做多级排序键、不做置顶固定等）。
- 不改变 `BUCKETS` 的分组定义本身（探索桶仍混合 probe/spark）。
- 不对 `todos`/`backlog` 表的 `ord` 做同类改动（当前只解决"项目"维度的排序需求）。

## Decisions

**1. 排序原语：`reorder_project(project_id, target_id, position)`，而非"上移/下移一位"或"设置绝对序号"。**
- 为什么：以 target 相对定位（插到某项目前/后）比"上移一位"更贴合"和某个邻居比谁重要"的心智，且前端在桶内过滤后天然能算出"上一个/下一个"项目 id 作为 target，不需要后端理解桶。传绝对序号（如 `set_order(project_id, index)`）需要前端和后端对"全局索引"达成一致，容易和分桶展示的直觉脱节。
- 备选方案：直接传 `direction: up|down`，让 store 自己找同 stage 的邻居——被否决，因为"同 stage"和"同桶"不是一个概念（探索桶跨两个 stage），会把桶定义泄漏进 store 层，违反"业务规则只在 store 层，展示分组在前端"的分层。

**2. 落地方式：整表重新编号（`UPDATE ... ord = 0,1,2,...`），而非只改受影响的两三行。**
- 为什么：`ord` 目前没有唯一约束、允许有洞或重复（新建项目撞号的坑就是证据）。挪动一次就重新排一遍、保证连续无洞，实现简单（读出全部 id 按当前 `ord,id` 排序 → 在内存列表里把 `project_id` 移到 `target_id` 旁边 → 依次写回），且顺带修掉 `add_project` 的撞号隐患，不需要额外一次迁移。
- 代价：每次挪动是 O(n) 次 `UPDATE`（n = 项目总数），但项目数量级是"一人公司管理的项目列表"，几十条量级，性能不是问题。

**3. `position` 取值 `"before" | "after"`，而不是只支持一种。**
- 为什么：前端"↑"应该是"插到上一个邻居前面"，"↓"应该是"插到下一个邻居后面"——如果只支持 `before`，"↓"要传"下一个的下一个"作为 target，当目标是列表最后一个时无法表达（没有"下一个的下一个"）。两个方向都支持，语义更直接，前端逻辑更简单。

**4. 门禁 action 名 `reorder_project`，纳入 `domain.PROPOSAL_ACTIONS`，字段 `(project_id, target_id, position)`。**
- 为什么：和现有 `set_stage`/`set_kind` 等命名风格一致；三个字段对应 store 函数签名，`dispatch` 里直接透传，不需要特殊处理。

**5. API 端点 `POST /api/project/reorder`，请求体 `{project_id, target_id, position}`，与 store 函数签名一致。**
- 为什么：和 `project/stage`、`project/kind` 等既有端点风格一致，直接 `_guard(lambda: projects.reorder_project(...))`。

**6. 前端交互：卡片增加 ↑/↓ 两个按钮，点击时在"当前桶过滤后的数组"里找相邻项目算出 `target_id`，桶内首位隐藏↑、末位隐藏↓。**
- 为什么：不引入拖拽库，vanilla JS 里维持一致的极简风格；相邻邻居的计算发生在前端渲染时已有的 `byBucket` 过滤结果上（`index.html:315`），不需要额外请求。

## Risks / Trade-offs

- **[风险] 重新编号整表 `ord` 期间若中途失败，可能留下不连续或重复的 `ord`** → 缓解：整个重排放在已有的 `transaction()`（`BEGIN IMMEDIATE` + 出错 `ROLLBACK`）里执行，失败即回滚，不会留下半写状态。
- **[风险] target_id 不存在、或 target_id == project_id、或 project_id 不存在** → 缓解：store 函数显式校验，`target_id == project_id` 视为无操作直接返回当前项目（幂等），不存在的 id 抛 `KeyError`（映射 404），和现有 `_require_project` 模式一致。
- **[权衡] 排序对"桶"无感知，意味着如果同一个桶内两个项目之间插入了一个不在该桶的项目（比如 attack 和 probe 交叉排列），前端计算"上一个邻居"时必须先按桶过滤再找邻居，不能直接用全局 `ord` 相邻** → 已在前端设计里显式处理：邻居查找基于 `byBucket` 过滤后的数组，而不是全局项目列表。

## Migration Plan

无数据迁移。`ord` 列已存在（`db.py` 的 `CREATE TABLE IF NOT EXISTS`），新代码上线即可用；历史数据的 `ord` 可能有重复/有洞，首次调用 `reorder_project` 会把全表重新编号一次，之后保持连续。无需回滚脚本——纯新增写路径，不影响读路径以外的既有行为。

## Open Questions

无。
