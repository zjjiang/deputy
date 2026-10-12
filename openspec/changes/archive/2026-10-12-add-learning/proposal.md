## Why

deputy 已有两个模块在岗：作战处（项目管理）与军情处（预设问题，回答"新料动态"）。但"信息进得来"不等于"能力长上去"——用户需要系统学习自动驾驶、具身智能、AI 等主题，这既不是动态追踪（军情处），而是**进度驱动的课程式学习**：有人给大纲、给讲解、能追问、自己确认掌握。常驻分身（龙虾，微信对话入口）+ feed-curator 检索（`search_docs`/`get_doc` 即将就绪）恰好凑齐了"老师"的三件套：大纲脑、讲解嘴、图书馆。deputy 补上账本（大纲真源 + 自评进度 + 课程存档），三者各司其职。

教学强度定为**中档**：路线 + 讲解 + 自评打勾，不做 AI 考试评定。

## What Changes

- 新增「讲武堂」学习能力：`learning_tracks`（学习主题）+ `knowledge_points`（知识点大纲，有序）+ `lesson_notes`（课程小结，派生物）
- 学习循环：分身生成大纲 → **门禁批准**（`add_track` / `set_curriculum` 两个新门禁动作）→ 微信对话里按序上课 → 用户自评（懂了/没懂，没懂回炉）→ 分身把课程小结回传看板存档
- **进度是用户自评，用户说了算**：看板直接点；微信里口头说的由分身经门禁代写（`set_point_status`），AI 不自行判定掌握
- MCP 工具 9→11：`get_learning`（读全部 track/知识点/进度/下一课）、`submit_lesson_note`（课程小结直落——派生物非真源，与 answers 同一豁免逻辑）
- 看板新增「讲武」tab：track 列表 + 进度 + 知识点清单（懂了/没懂直接点）+ 课程小结历史
- 新增 `docs/teaching-sop.md`：分身教学 SOP（上课流程/追问处理/没懂回炉/小结规范）+ OpenClaw 对话入口说明
- 课堂在微信（OpenClaw），看板是成绩单与账本——学习由进度驱动（用户发起），不设定时 cron
- 与既有模块边界（feed-curator 阅览室/study-workbench 已退役，积压消化由军情处简报承接）：军情处管"新料动态与积压消化"（定期简报，AI 替你读）、讲武堂管"系统课程"（进度驱动），互不重叠

## Capabilities

### New Capabilities

- `learning`：学习主题与知识点大纲（门禁保护）、自评进度状态机、课程小结存档、分身 MCP 读写面、看板「讲武」tab、部署前提（同机 stdio 不变）

### Modified Capabilities

- （无——现有 project-management 与 preset-questions 的 requirement 均不变）

## Impact

- **代码**：`app/domain.py`（track/point 状态常量 + 门禁白名单 +3）、`app/store/db.py`（SCHEMA 追加 3 表）、`app/store/learning.py`（新建 store 模块 + 派发表）、`app/store/proposals.py`（派发路由已按归属自动兼容）、`app/api.py`（约 7 个端点）、`app/mcp_server.py`（+2 工具）、`app/web/index.html`（讲武 tab）、`docs/teaching-sop.md`（新）
- **测试**：`tests/test_learning_store.py`、`tests/test_learning_api.py`（新建）；`tests/test_mcp_contract.py`（工具集合 9→11 + 教学端到端）；`tests/test_gate.py`（3 个新门禁动作用例）
- **依赖**：无新增；部署前提不变（分身同机 stdio）
- **运维前置**：无硬依赖——教学素材以分身自身知识为主、互联网为辅（龙虾侧能力，deputy 不集成）；feed-curator 的 `search_docs`/`get_doc` 完工后可作前沿佐证，未完工不阻塞授课
- **破坏性**：无（纯新增能力）
