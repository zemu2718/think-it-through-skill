# Changelog

本项目的重要版本变更记录在此。发布支持范围、仓库合同校验和具体会话执行事实分层管理。

版本条目记录仓库指定的源码版本历史；同名 Git tag、GitHub Release 和可下载 asset 是否存在，必须由对应的公开对象单独证明。

格式参考 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，版本遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [Unreleased]

### Changed

- 将双语 README 首图由宽幅 Banner 换为用户选定的双主题 `/think-it-through` 调用卡片；两张 600×600 RGBA 图片以独立固定哈希作为 canonical raster variants 纳入资产清单，安装区继续保留带 Claude Code 范围说明的可复制命令，并删除不再使用的旧宽幅 Banner 源图、派生图、生成分支及无实际消费方的 Brand Mark 变体。

## [0.4.0] - 2026-09-02

### Added

- 新增以 Thinking Light / Clarity Aperture 为一级识别的双主题 README Banner，并保留固定哈希 canonical source、来源说明和确定性派生参数。
- 新增 v0.4.0 项目可行性参考与 grader-only `PROJECT_VIABILITY` 评分入口，把问题存在、问题强度、方案适配和替代生态分开记录，并用确定性 sidecar、正例和单变量反证 fixture 防止证据缺口被解释成正式自研依据。
- 新增 v0.4.0 非规范性架构说明，解释实现形态去锚、两遍搜索、候选核验、最强现实替代试用、可选独立反方和承诺上限为何分布接入现有 R / A / Gate / B，而不新增 Veto Gate、协议状态、方法卡或 core schema。

### Changed

- 将当前稳定源码与正式产品合同升级为 v0.4.0：产品、功能、自研和技术形态先作为候选解法；重大投入前按用户结果与失败机制优先、实现与产品术语补查的顺序发现现实替代，并优先核验和试用最强路径；未授权、失败、来源不足、候选未核验或试用未执行时，最多允许低成本、可撤回的有限验证。
- 加固 Evidence 与 Participation Gate 的 provider、授权 ID、scope、终态、回执、Agent 计数和最小 payload 一致性；四类授权继续互不继承，默认仍是零外部调用和单 Agent。
- 同步 current schemas、fixtures、rubrics、compatibility identity、runtime smoke 静态 harness 和分发 manifest 到 v0.4.0，同时保持所有未执行 runtime 能力为 `not_run`，不把静态合同冒充真实搜索、试用、Agent、自然发现、原生 UI 或兼容证据。
- 将 v0.4.0 设为当前稳定源码、正式产品合同和最新真实公开发布；同名不可变 Git tag、GitHub Release、可下载 asset 与校验和共同建立公开发布身份，v0.3.0 继续作为历史发布保留，冻结 v0.1 benchmark、grader、description 和哈希保持不变。
- 将 Brand Mark 调整为头像与紧凑场景资产，并把 Decision Thread / Decision Hinge 保留为 Social Preview 的二级解释语法。
- 统一 Brand Mark 与 Social Preview 的暖中性色、深墨、克制深青和极少暖色视觉语言，同时保持可选 Gate、未知边界与结果复判语义。
- 移除 README 中的单一合成 SaaS 案例、三条示例输入和四个 Decision Case SVG 及对应 manifest、文档与旧校验合同；不改变产品行为、安全、授权、runtime、兼容性或 evidence 合同。
- 扩展资产生成与 freshness 检查，使 README Banner 与 Social Preview 的派生 PNG 均由同一脚本生成、完整解码并按像素校验；本地生成不代表 GitHub 已配置 Social Preview。
- 更新双语 README 首图、品牌派生摘要、视觉资产说明与贡献维护流程；不改变产品行为、安全、授权、兼容性或 evidence 合同。
- 统一双语首屏、产品定位、品牌摘要与 Social Preview 为“AI 能把事情做得很快，但什么值得做，仍由用户决定”的表达，并将首屏价值说明收敛为“开始或继续投入前，想清楚再决定”，直接覆盖开始前与继续投入前的判断，不改变产品行为、安全、授权、runtime、兼容性或 evidence 合同。
- 发布不可变 `v0.4.0` Git tag 与 GitHub Release，提供经 manifest 复验的 `think-it-through.skill` 和 `SHA256SUMS`，并将 GitHub CLI、固定 `skills@1.5.23` 与手动 tag 安装入口固定到 v0.4.0；安装结果不提升 L3～L5。
- 将 GitHub 根 README 设为中文默认入口，并将英文入口迁移至 `README.en.md`；不改变产品行为、资产、分发或兼容性合同。
- 将双语 README 的首要安装入口改为把仓库链接交给用户当前使用的 Agent，并继续明确区分文件安装与真实 runtime 验证。
- 将双语 README 重排为“用户结果 → 调用时机 → 工作原理与最小必要方法 → 安装使用 → 默认安全”的普通用户路径，移除首屏显式入口并只在安装区保留 `/think-it-through`；首屏仅增加 MIT License、最新 Release 与 `main` 分支 Validate 三枚可验证状态徽章，不以徽章声明 runtime 兼容；进一步删除首屏偏内部的 Agent Skill 品类说明，克制显示 Banner，将综合判断按立项前与开始后拆分表达，并把用户结果、四步说明、适用边界、方法解释、安装和安全说明中的内部协议口吻改为普通用户能直接理解的表达；同时以“安装 / 开始使用”两个平行操作步骤区分跨宿主安装请求、Claude Code 调用与真实 runtime 验证，将默认安全与更多信息拆开，并将详情入口按安装与兼容、了解边界和参与改进分组；详细安装、版本核验、兼容层级与证据治理继续由对应双语指南承接，不改变产品行为、安全、授权、runtime、兼容矩阵、冻结证据、视觉资产或分发合同。
- 在双语 README 的安装区补充简洁的 Skills CLI GitHub 直装入口，与把仓库链接交给当前 Agent 的路径并列；调整两种安装方式、能力边界和帮助链接的顺序与分段，将“你会得到什么”改写为明确方向、可验证的下一步和可回看的依据，并整体精简生硬术语、长段落和开始使用门槛；固定版本、文件核验和兼容边界仍由详细指南承接。

### Validation

- Python 3.12 单元测试：190 项通过。
- 仓库发布前校验：3206 项通过；README Banner 与 Social Preview 的完整解码、尺寸、预算和像素 stale check 通过。
- `.skill` 分发包：30 个 manifest 文件构建成功，归档完整性、解包文件集合与源码逐字节一致性复验通过。
- 固定 Agent Skills revision 格式校验通过；固定 `skills@1.5.23` 在 Node 22.20.0 下完成 1 项 archive discovery 与 8 个 installer target 精确复制 smoke。该结果只建立格式与 L1/L2 机械路径，不提升 L3～L5。
- 未运行 Claude Code / Codex real-runtime provider smoke；公开兼容矩阵继续如实保持 `not_run`。

## [0.3.0] - 2026-08-31

### Added

- 建立 v0.3.0 开放 Agent Skills 稳定源码：新增通用 Adapter、L0～L5 兼容矩阵、机器可读证据 schema 与固定版本验证路径。
- 新增精确分发 manifest，供 builder、validator 与 tests 共同使用。
- 新增隔离的安装器 smoke 和需单独授权执行的 Claude Code / Codex runtime smoke harness。
- 新增已加载 Skill 在高价值承诺节点使用的一次性上下文检查点合同、intent、静态 fixture 与 current grader；真实多轮行为保持 `not_run`。
- 新增 Decision Thread 品牌摘要，以 Decision Hinge 为一级识别符号，并建立 manifest 驱动的 Brand Mark、双语/主题 Decision Case 与可复现 Social Preview 管线；派生 PNG 继续使用固定 `resvg-py` / Pillow 和像素级 stale 检查。

### Changed

- 将当前源码合同、schema、fixtures 与评分器升级为 v0.3.0，同时保持冻结 v0.1 evidence 与 description 不变。
- 把格式符合、安装器发现、可安装、runtime 加载、纯文本行为与原生能力分层声明；安装器 target 数不再被视为 runtime 认证。
- 将 v0.3.0 设为当前稳定源码和正式产品合同；同名 Git tag、GitHub Release 与可下载 asset 已分别创建，runtime 兼容证据仍按真实执行独立声明，不覆盖或改写 v0.2.0 历史事实。
- 增加安装与 runtime 公开反馈表单；反馈只有绑定准确版本、完成复现、脱敏与审阅并形成 approved evidence 后，才能改变兼容矩阵。
- 重构中英文 README 为“识别产品与可信状态 → 看见错误执行的代价 → 用具体案例判断适用性 → 安装并完成第一次体验 → 渐进披露安全与证据”的正式首次访客路径，并删除失效候选分支引用。
- 用小尺寸 Brand Mark 取代抽象 Hero，用四个语言/主题 Decision Case 显化同一 SaaS 请求的执行优先与决定优先路径；Social Preview 重绘为深墨、留白和无字体依赖的原创路径字标。

### Validation

- Python 单元测试：170 项通过。
- 仓库发布前校验：2998 项通过；派生视觉资产完整解码、尺寸与像素 stale check 通过。
- `.skill` 分发包：29 个 manifest 文件构建成功，归档完整性、解包文件集合与源码逐字节一致性复验通过。
- 固定 Agent Skills revision 格式校验通过；固定 `skills@1.5.23` 在 Node 22.20.0 下完成 1 项 archive discovery 与 8 个 installer target 精确复制 smoke。该结果只建立格式与 L1/L2 机械路径，不提升 L3～L5。
- 未运行 Claude Code / Codex real-runtime provider smoke；公开兼容矩阵继续如实保持 `not_run`。

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
