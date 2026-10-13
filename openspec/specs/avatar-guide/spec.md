## Purpose

分身（龙虾/OpenClaw）工作指引的投递契约：总章程作为唯一权威正文随代码版本化，MCP 握手下发精简章程，部署文档只留铁律与指路——指引跟着代码走 PR，杜绝人肉搬运造成的漂移。

## Requirements

### Requirement: 分身总章程唯一真源

deputy SHALL 在仓库内提供分身总章程文档（`docs/avatar-guide.md`），作为分身（龙虾/OpenClaw）工作指引的**唯一权威正文**，随代码走 PR 版本化。章程 SHALL 至少包含以下章节：身份与三处地图（作战处/军情处/讲武堂及各自动作入口）、门禁铁律（分身对真源只读、写走 propose、绝不自批 approve/reject）、feed-curator 关系（奏折/面圣/翻阅三模式的取料通道与边界：军情只吃订阅语料、讲武堂自身知识优先、阅读状态只存 feed-curator）、MCP 工具地图（全部读工具/门禁工具/派生物直落工具及用途）、SOP 索引（thinking-sop / teaching-sop）。

易变细则（工具清单、取料映射表、处室工作方式）SHALL 只活在章程或其索引到的 SOP 中；其他文档引用指引时 SHALL 指路章程而非内联这些细则。部署文档（`docs/lobster-setup.md`）的 OpenClaw 侧人设段 SHALL 只保留身份一句话、门禁铁律与指路章程，SHALL NOT 内联工具清单或处室细则。

#### Scenario: 章程必含章节齐全

- **WHEN** 阅读章程文档
- **THEN** 身份与三处地图、门禁铁律、feed-curator 三模式关系、工具地图、SOP 索引五块内容齐备，其中工具地图覆盖 MCP 当前全部工具

#### Scenario: 部署文档不再内联会过期的细则

- **WHEN** 阅读 `docs/lobster-setup.md` 的 OpenClaw 人设段
- **THEN** 段内只有身份、铁律与"细则读 docs/avatar-guide.md"指路，没有工具数量/清单等随代码漂移的内容

### Requirement: MCP 握手下发精简章程

MCP server SHALL 在握手初始化结果中声明非空的 instructions（精简章程）：内容 SHALL 含分身身份、门禁铁律要点（真源只读、写走 propose、绝不自批 approve/reject）与指路总章程（`docs/avatar-guide.md`）。instructions 的下发 SHALL NOT 改变工具面：不新增、不删除、不修改任何工具及其行为，既有守门约束（MCP 不得暴露直写真源的工具）保持原样。

#### Scenario: 初始化返回精简章程

- **WHEN** MCP 客户端与 deputy 完成握手
- **THEN** 初始化结果携带非空 instructions，内容含门禁铁律要点与指路 `docs/avatar-guide.md`

#### Scenario: 指引下发不改变工具面

- **WHEN** 客户端列出 deputy 的全部 MCP 工具
- **THEN** 工具集合与变更前一致，仍不含任何直接写真源的工具
