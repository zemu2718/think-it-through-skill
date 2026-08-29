# Changelog

本项目的重要版本变更记录在此。发布支持范围、仓库合同校验和具体会话执行事实分层管理。

格式参考 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，版本遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [Unreleased]

### Added

- 准备 v0.3.0 开放 Agent Skills 候选：新增通用 Adapter、L0～L5 兼容矩阵、机器可读证据 schema 与固定版本验证路径。
- 新增精确分发 manifest，供 builder、validator 与 tests 共同使用。
- 新增隔离的安装器 smoke 和需单独授权执行的 Claude Code / Codex runtime smoke harness。

### Changed

- 将当前源码合同、schema、fixtures 与评分器升级为 v0.3.0，同时保持冻结 v0.1 evidence 与 description 不变。
- 把格式符合、安装器发现、可安装、runtime 加载、纯文本行为与原生能力分层声明；安装器 target 数不再被视为 runtime 认证。
- v0.3.0 在正式 tag 与 Release 前保持候选状态，不覆盖或改写 v0.2.0 发布事实。

## [0.2.0] - 2026-08-29

### Added

- 新增宿主无关的 Portable Decision Core，以及 intent、consent、receipt 和 DecisionRecord JSON Schema。
- 新增 Evidence Gate 与 Participation Gate，用于路由决定敏感的有界调研、额外 Agent 和真人参与。
- 新增纯文本、Claude Code 与 ChatGPT Adapter；纯文本协议作为跨宿主基线。
- 新增结构化方法 option、对话内决策快照、结果复判和八维增强 UX rubric。
- 新增 Evidence、Participation、真人参与、Adapter、DecisionRecord 和主现实证据闭环 fixtures。
- 提供由 28 个运行时源文件组成的 `.skill` 分发集合，不包含 evals、benchmarks、examples 或本机配置。

### Changed

- 正式发布入口为 Claude Code 中显式调用 `/think-it-through`；自然语言自动发现不作为当前发布入口。
- 状态合同扩展为 `R-align → R-method → A → Gate-routing → 可选 Gate → B`。
- 方法推荐在同一选择单元内呈现正式名称、推荐状态和当前价值；推荐不等于确认。
- 多 Agent 默认关闭，实际数量受独立任务、用户总参与上限、产品与宿主上限及成本预算共同约束。
- 授权拆分为能力调用、参与 / 委派、私有数据访问和外部行动四类，彼此不继承。
- B 统一交付一个综合判断、一个主现实证据闭环、可复制的决策快照和四项反馈。
- 阶段 B 改为自然语言优先：完整含义在前，核心假设、本轮动作、观察信号和复判条件按需在句末标记，不再使用连续的句首专业标签。
- 决策快照使用面向读者的自然字段，并与稳定的 DecisionRecord schema 无损映射；事实、推断、假设和未知分别保留。
- 原生控件、搜索、额外 Agent、私有数据、持久化和外部行动改为逐会话协商、按条件路由并取得对应授权；实际执行由 trace 和 receipt 建立。
- ChatGPT Adapter 明确为 Skill-only / 纯文本语义映射，不构成原生兼容认证。
- 重构中英文用户文档，按“了解价值 → 查看体验 → 安装使用 → 理解边界”组织，并优先使用对应语言的自然表达。
- 统一 Gate 提案、授权与执行时序，以及 `Gate-routing` 的状态和机器合同。
- 删除分发包内与冻结 benchmark 重复的 v0.1 示例副本，保留唯一历史证据来源。
- 更新安全、第三方来源、产品与架构文档的职责和 v0.2.0 发布语义。
- 增强文档职责、双语共享事实、安装安全、冻结证据和分发集合校验。

### Validation

- Python 单元测试：99 项通过。
- 仓库发布前校验：2350 项通过。
- `.skill` 分发包：28 个文件构建成功，归档完整性、解包文件集合、源码逐字节一致性与运行时发布状态边界复验通过。
- 冻结 v0.1 benchmark、legacy grader 与 Skill description 继续与当前合同隔离。

## [0.1.5] - 2026-08-29

### Changed

- 按答案形态选择原生多选、单选或开放回答。
- 可并存目的先合并，不默认排序或制造虚假排他。
- 优化 R / A / B 的语义分段、问题位置和终端可读性。
- B 增加四项稳定反馈方向及原生控件能力诚实合同。

## [0.1.4] - 2026-08-29

### Changed

- 优化回复话术格式、段落关系和用户选择体验。

## [0.1.3] - 2026-08-29

### Added

- 建立 R-align / R-method、原生控件与自由文字纠正合同。

## [0.1.0] - 2026-08-27

### Added

- 发布初始 Skill、方法卡、评测 fixtures、评分工具链和冻结 v0.1 行为证据。

[0.1.5]: https://github.com/zemu2718/think-it-through-skill/compare/4512702...4381d0e
[0.1.4]: https://github.com/zemu2718/think-it-through-skill/compare/301747b...4512702
[0.1.3]: https://github.com/zemu2718/think-it-through-skill/compare/eca08e2...301747b
[0.1.0]: https://github.com/zemu2718/think-it-through-skill/commit/eca08e2
