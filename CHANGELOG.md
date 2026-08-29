# Changelog

本项目的重要变更记录在此。版本状态、真实运行证据与静态合同分别说明，避免把规范或测试结果写成真实用户体验。

格式参考 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，版本遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [Unreleased]

### Planned

- 在真实 Claude Code 多轮会话中验收 v0.2.0 核心路径与失败降级路径。
- 根据真实 transcript、能力 trace 和外部测试者反馈决定正式稳定版发布时间。

## [0.2.0-rc.1] - 2026-08-29

### Added

- 新增宿主无关的 Portable Decision Core、intent / consent / receipt / DecisionRecord JSON Schema。
- 新增 Evidence Gate 与 Participation Gate，支持决定敏感的有界调研、额外 Agent 和真人参与路由。
- 新增纯文本、Claude Code 与 ChatGPT Adapter；纯文本为一等参考实现。
- 新增结构化方法 option、对话内决策快照、结果复判和八维增强 UX rubric。
- 新增 Evidence、Participation、真人参与、Adapter、DecisionRecord 和主现实证据闭环 fixtures。

### Changed

- 状态合同扩展为 `R-align → R-method → A → Gate-routing → 可选 Gate → B`。
- 方法推荐改为在同一选择单元内呈现正式名称、推荐状态和当前价值；推荐不等于确认。
- 多 Agent 默认关闭，实际数量受独立任务、用户总参与上限、产品与宿主上限及成本预算共同约束。
- 授权拆分为能力调用、参与 / 委派、私有数据访问和外部行动四类，彼此不继承。
- B 统一交付一个综合判断、一个主现实证据闭环、可复制的决策快照和四项反馈。
- 当前评分器、fixtures、UX 规则、公开文档、仓库 validator 与分发集合升级到 v0.2.0。

### Validation

- Python 单元测试：99 项通过。
- 仓库发布前校验：2285 项通过。
- `.skill` 分发包：30 个文件，构建、解包、文件集合、逐字节复验及 `unzip -t` 通过。
- 冻结 v0.1 行为与触发 benchmark、legacy grader 和 description 哈希保持隔离。

### Experimental

- Evidence Gate、多 Agent 和真人参与已进入静态合同，但真实 Claude Code 运行体验尚未验收。
- ChatGPT 与其他宿主仅定义纯文本保真和未来映射，不构成兼容实测。

### Known limitations

- 可靠入口仍是 Claude Code 中显式调用 `/think-it-through`。
- 冻结 v0.1 自动发现 holdout 为 9/16（正例 1/8、负例 8/8），不能宣称自然语言自动加载已经通过。
- v0.2.0 真实模型多轮行为、方法 option UI、Evidence Gate、原生反馈 UI、独立附注、多 Agent、真人参与、跨宿主、解决方案复判和真实用户体验均为 `not_run`。

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

[Unreleased]: https://github.com/zemu2718/think-it-through-skill/compare/v0.2.0-rc.1...HEAD
[0.2.0-rc.1]: https://github.com/zemu2718/think-it-through-skill/compare/4381d0e...v0.2.0-rc.1
[0.1.5]: https://github.com/zemu2718/think-it-through-skill/compare/4512702...4381d0e
[0.1.4]: https://github.com/zemu2718/think-it-through-skill/compare/301747b...4512702
[0.1.3]: https://github.com/zemu2718/think-it-through-skill/compare/eca08e2...301747b
[0.1.0]: https://github.com/zemu2718/think-it-through-skill/commit/eca08e2
