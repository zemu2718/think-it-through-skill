<div align="center">
  <img src="assets/hero.png" alt="想清楚：多条路径收敛到一个会改变决定的问题，再形成一个可复判的现实证据闭环" width="100%">

# 想清楚 · Think It Through

**别让 AI 把错误的任务完成得无比漂亮。**

一个开源 Agent Skill：先确认真正要解决什么，再找出最可能改变决定的一个答案；只有外部证据或独立参与确实有增量时，才按授权升级，最终交付一个综合判断、一个主现实证据闭环和可复制的决策快照。

[English](README.md) · [产品文档](PRODUCT.md) · [需求与验收](REQUIREMENTS.md) · [变更记录](CHANGELOG.md) · [参与贡献](CONTRIBUTING.md)

</div>

> [!IMPORTANT]
> **v0.2.0 仍是最新稳定版；当前分支包含尚未发布的 v0.3.0 源码候选。** 当前可靠使用方式仍是在 Claude Code 中显式调用 `/think-it-through`。纯文本协议是跨宿主基线；原生控件、搜索、额外 Agent、私有数据、持久化和外部行动仅在当前会话实际具备相应能力、满足路由条件并取得对应授权时使用，实际执行以 trace 和 receipt 为准。Adapter 文档定义协议映射，不代表对应宿主已经完成原生兼容认证。

## 它解决什么问题

AI 很擅长完成明确任务。但如果眼前动作不服务真实目的，这种能力反而会放大浪费：

- 还没人证明愿意付费，就先写完整投放方案；
- 因为已经投入很多，所以继续投入；
- 合作边界尚未明确，就先优化说服话术；
- 真正只差一个会改变排序的答案，却继续生成更多选项；
- 需要当前市场事实时只凭模型记忆，或不需要调研时生成一份大报告；
- 让多个 Agent 重复分析同一问题，再用多数意见制造确定感。

想清楚会在重要行动前后插入一个克制的决策与证据协议：

```text
表面任务 → 真实目的 → 决策问题
→ 一个决定敏感答案
→ 必要且获授权的证据 / 参与
→ 判断 → 主现实证据闭环 → 复判
```

它不替你拍板，也不把流程、方法或 Agent 数量当成结果。它帮助你判断现在缺的是自己的目标与底线、公开事实、独立反证、真人承诺，还是只能由现实行为回答的证据。

## 安装前先看体验

<img src="assets/demo-flow.zh-CN.svg" alt="说出议题，对齐真实目的，只回答一个关键问题；必要且获授权时补充证据或参与，最后获得判断、决策快照和复判入口。" width="100%">

```text
R-align：先说清希望得到或保护什么
→ R-method：理解并确认最小必要思考角度
→ A：只回答一个会改变决定的问题
→ Gate-routing：必要且获授权时补充证据或参与
→ B：获得判断、主现实证据闭环、决策快照与反馈
```

Gate 是条件能力，不是固定第四阶段。默认零外部调用、当前主 Agent、对话内快照和不改变外部世界。

### 1. 先帮助你说清真正想要什么

Skill 不会看到一个产品想法，就先猜成赚钱、增长或创业。目的尚不清楚时，它只处理当前最大的一个未知。

宿主提供 `AskUserQuestion` 或等价工具时，控件由答案形态决定：

- 可并存方向 → 原生多选；
- 真实有限互斥边界 → 原生单选；
- 无法预造的开放答案 → 直接自由回答。

```text
你：我想做一个像 QQ 一样的聊天软件，你觉得怎么样？

想清楚：听起来你已经有一个产品想法，但它首先要为你带来什么，会直接改变后面的判断。

我目前先不替你假定目的。

原生多选问题：
可多选，也可以直接补充或纠正。

这件事你主要希望获得哪些结果？

☐ 练手并做成作品
☐ 解决一类人的具体问题
☐ 探索商业化可能
☐ 给现有团队或社群使用
```

复选框只是原生控件的可读线框，不是让模型输出 Markdown。控件可用时必须实际调用；只有不可用、失败或被拒绝时才使用普通编号降级。

选择与自由文字冲突时以文字为准。产品不创建“其他/Other”；宿主 `Other` 是替代式自由输入。多个目的能够并存时，Skill 先合并、不默认排序；只有用户给出的真实排他约束会改变决定时才继续澄清。

### 2. 目的清楚后，在同一处理解并选择方法

基本分析始终包含，不需要选择。系统再按当前议题考虑双向钢人、失败预演和至多一张能补足独特缺口的专项方法卡，去重后只呈现 0～3 个有增量的角度。

每个正式候选同时包含：

```text
稳定 ID + 正式方法名 + 推荐状态 + 当前价值
```

用户看到的原生多选应类似：

```text
这轮保留哪些额外思考角度？

☐ 对象校准（推荐）
  分清使用者、付费者和承担代价的人，帮助判断应该先验证谁的需求。

☐ 双向钢人（推荐）
  用相近证据标准检验当前方向和最强替代方向，避免只证明已有倾向。
```

宿主支持 option description 时，说明直接内联在选项中；不支持时使用紧邻说明；纯文本降级仍保留正式名称、推荐状态和当前价值。不得先完整解释一遍，再在控件中只重复名称。

`推荐` 不等于确认。只有本轮提交的选择或明确文字形成最终组合：

- **加入 X**：保留当前组合，再增加 X；
- **取消 X**：只移除 X；
- **用 X 替换 Y**：移除 Y，再增加 X。

默认勾选、浏览候选、历史偏好或只补充背景都不构成确认。未确认或取消的方法不得暗中执行。

### 3. 只回答一个真正关键的问题

已确认方法不会逐卡汇报或模拟专家会议，而是被综合成一个答案槽：

> 哪一个答案一旦不同，最可能改变方案排序、行动方向或是否继续？

- 答案天然有限且互斥时，实际调用原生单选；
- 答案开放时，不调用选择控件、不预造候选；
- 无论哪种形式，都只索取一个独立答案，问后立即等待；
- Skill 可以复用你给出的数字，但 A 不自行植入样本量、期限、金额、人数、比例或成功阈值。

### 4. 只有会改变判断时，才升级证据或参与

用户回答后，Skill 先判断未知应由谁回答：

| 未知 | 默认处理 |
| --- | --- |
| 目的、底线、风险承受 | 留给用户，不由搜索或 Agent 代答 |
| 当前市场、价格、法规、政策等公开事实 | 满足条件时进入 Evidence Gate |
| 不重复、可验证、可停止的独立任务 | 满足条件时进入 Participation Gate |
| 权责、预算、承诺、客户行为、专业责任 | 生成最小真人参与材料，默认不发送 |
| 只能由真实反应回答 | 留给主现实证据闭环 |

#### Evidence Gate

一次有界调研必须先说明：

- 要改变的决定与关键证据问题；
- 市场、地区、时间和对象范围；
- 停止条件和来源要求；
- provider、只读状态、数据边界；
- 相对成本、延迟和失败降级。

只有外部事实会改变方案排序、是否继续或投入边界，获取方式有限且价值高于成本，并取得具体能力授权时才执行。结果保留来源、日期、支持证据、反对证据、冲突与空白。失败、拒绝或来源冲突时不补造结果，而是保留未知、降低承诺并继续 B。

#### Participation Gate

默认单 Agent。只有存在不重复、可验证、可停止的独立增量任务时才建议额外 Agent。

用户设置的是**包含当前主 Agent 的总参与上限**：

```text
可用额外上限 = max(0, 用户总参与上限 - 1)
实际额外数 = min(独立任务数, 用户可用额外上限, 产品上限, 宿主上限, 成本预算)
实际总数 = 1 + 实际启动额外数
```

启用前必须在一个连续选择单元中展示：具体任务、主 / 额外 / 总数、数据范围、公开联网与私有数据状态、相对成本和延迟、失败降级。用户可以按建议启用、降低数量、保持单 Agent 或自由收窄。

额外 Agent 只接收最小上下文，不能递归委派。主 Agent 去重来源、呈现冲突并综合，不按多数票决定。完成后如实回执计划、启动、完成、失败和实际总数。

允许多 Agent不等于允许联网、读取私有数据或改变外部世界。

### 5. 最后交付判断、主现实证据闭环和快照

即使用户回答“不知道”、Gate 被拒绝或能力失败，Skill 也不会开启澄清问卷或无限等待，而是进入 B：

| 尚未执行 | 已经执行 |
| --- | --- |
| 暂不行动 / 小步验证 / 有条件推进 / 可以推进 | 继续 / 调整 / 暂停 / 停止 |

一个完整结果自然包含：

```text
当前判断与推荐方向
→ 最关键依据、事实 / 推断 / 假设 / 未知
→ 成立条件与反转信号
→ 一个主现实证据闭环
→ 可复制决策快照
→ 四项反馈
```

主现实证据闭环围绕同一个核心假设，但不会用一串句首专业标签制造报告感：

```text
这一步要弄清的是，现有版本能否带来足以区分方向的真实反应（核心假设）。

先展示现有版本并邀请真实付款，但不新增功能（本轮动作）。

只记录付款、明确拒绝和拒绝理由；付款支持继续，持续拒绝则反对继续（观察信号）。

出现付款时重新决定是否推进；持续只有拒绝时停止新增投入（复判条件）。
```

先读到完整含义，必要的专业语义放在句末。它可以包含检验同一假设所必需的连续操作或多人参与，但不能把多个无关项目包装成一个实验。系统新增的每个决定相关数字都要在局部标为“建议边界”“启发式起点”或注明可靠来源。

B 默认在对话中输出可复制的决策快照，不写文件、不上传：

```markdown
## 决策快照

这次要想清楚的事：
真正想得到或保护的结果：
本轮需要决定什么：
本轮采用的思考角度：
目前更合适的方向：
为什么这样判断：
判断成立的前提：
已经确认的信息：
根据现有信息可以推断：
当前判断仍依赖：
仍不知道的关键问题：
本轮依据来自哪里：
什么情况会改变判断：
要弄清什么：
先做什么：
看哪些现实信号：
什么时候重新决定：
本轮参与者与使用的能力：
这份记录保存在哪里：仅在当前对话中
```

这些自然字段与机器 DecisionRecord 一一对应，假设和未知不会被合并丢失。持久化到文件或远端必须有具体目标和授权。Skill 不保存隐藏思维链。下一次可以粘贴新旧快照，区分判断错误、执行偏差、资源错配和条件变化后复判。

### 6. 四项反馈只负责路由

完整判断、主实验和快照之后，B 实际调用一次四项原生单选：

```text
○ 方向符合我
○ 调整下一步
○ 不同意这个判断
○ 暂时先放一放
```

问题只收集对已完成内容的方向，不索取预算、期限或新证据。只有宿主实际显示并返回与选择并存的独立附注时，Skill 才使用 `native-note`；否则选择后通过一条普通消息补充。宿主 `Other` 不是独立备注，文字冲突时仍以文字为准。

任何反馈都不会自动执行实验，也不构成能力调用、参与 / 委派、私有数据、持久化或外部行动授权。控件不可用、失败或被拒绝时，使用普通编号的明确文本降级。

> [!NOTE]
> 上述交互是便于阅读的协议示意。实际会话只使用宿主当时提供的控件与能力；能力调用以 trace 和 receipt 记录。

## 四类授权必须分开

```text
能力调用 capability_call
≠ 参与 / 委派 participation_delegation
≠ 私有数据访问 private_data_access
≠ 外部行动 external_action
```

每项能力还要记录 `available / unavailable / unknown` 与 `ready / requires_approval / requires_auth / failed`。`unknown` 不得当作可用。真实调用形成 receipt；拒绝、失败和未完成工作也要如实记录。

真人掌握的价值、权责、承诺、客户行为意愿和持证专业责任不能由 Agent 代答。真人参与默认只生成可转发草稿；发送、邀请、建群、预约和联系需要独立外部行动授权。

## 跨宿主怎么工作

| Adapter | v0.3.0 候选边界 |
| --- | --- |
| 纯文本 | 跨宿主基线；无原生控件、搜索、Agent 或持久化时仍完整保留核心语义 |
| 开放 Agent Skills | 定义 Skill 根目录发现、相对引用、可移植纯文本行为与能力协商的共同边界 |
| Claude Code | 可靠入口仍是显式 `/think-it-through`；只映射当前会话观察到的能力 |
| ChatGPT | Skill-only / 纯文本语义映射；不代表原生控件、工具、Agent 或持久化认证 |

Adapter 只能改变交互表面，不能改变状态、授权、等待、判断和降级语义。Adapter、安装器 target、已复制目录或产品文档都不能证明某个具体 runtime/version 已加载 Skill 或遵守其行为。

兼容性按六个互不替代的层级记录：

| 层级 | 证明什么 | 最低证据 |
| --- | --- | --- |
| L0 | Agent Skills 格式符合性 | 固定规范 revision 的静态校验 |
| L1 | 安装器能够发现 Skill | 固定安装器版本的隔离本地 harness |
| L2 | 精确 manifest 文件集合安装成功 | 隔离安装与逐字节比较 |
| L3 | 指定 runtime/version 加载或显式激活 | 真实 runtime trace |
| L4 | 该 runtime 中纯文本行为走通 | 真实多轮 transcript 与当前评分器 |
| L5 | 该 runtime 中某项原生能力工作 | 对应 trace、授权和 receipt |

机器可读状态位于 [`compatibility/runtime-support.json`](compatibility/runtime-support.json)。初始 L0～L5 均保持 `not_run`，直到仓库提交经过审阅的真实证据。八个已命名安装器 target——Claude Code、Codex、Cursor、OpenClaw、Hermes Agent、CodeBuddy / WorkBuddy、Gemini CLI、OpenCode——只是安装映射，不是 runtime 行为认证。

## 方法透明，但不成为学习负担

基础分析始终运行。除双向钢人和失败预演外，七张专项方法卡是：

- 分清使用、付费、受影响和承担代价的人（**对象校准**）；
- 找到真正牵动全局的约束（**系统瓶颈**）；
- 判断过去有效的策略是否仍适合当前条件（**阶段匹配**）；
- 找到有限资源最值得集中的位置和承诺边界（**资源支点**）；
- 把责任、投入、决定权和退出条件变得可检验（**边界契约**）；
- 让信息、证据、渠道和反馈适合对象与目的（**沟通匹配**）；
- 用已经发生的结果复判继续、调整、暂停或停止（**证据闭环**）。

专项方法通常最多一张，零张是正常结果。市场调研、多 Agent、真人参与、持久化和宿主适配属于证据、参与或能力层，不进入方法注册表。

## 什么时候使用

v0.2.0 稳定版与 v0.3.0 源码候选的可靠入口都是：

```text
/think-it-through
```

适合不确定、代价高、难撤回，或已经持续消耗资源的重要选择：

- “这件事值不值得做？”
- “我在 A 和 B 之间纠结。”
- “投入六个月之前先帮我检验这个想法。”
- “我让 AI 执行的动作真的服务目标吗？”
- “应该继续、调整、暂停还是停止？”
- “哪些市场事实真的会改变这个决定？”
- “有必要的话，可以先说明成本和边界，再建议是否用多个 Agent。”

不适合事实查询、方法定义、规格清楚的低风险执行、纯创作娱乐、不包含待决选择的代码审查 / FMEA / 调研 / 排期，以及需要立即保护的紧急安全事件。

## 安装

下面的仓库源码安装是尚未发布的 v0.3.0 候选开发路径。源码目录包含 `evals/`，runtime 会忽略它；最小候选归档的精确内容由 [`distribution/package-manifest.json`](distribution/package-manifest.json) 定义。在完全相同的归档真正发布并复验之前，不宣称存在 v0.3.0 Release asset。

### 从源码安装到 Claude Code 个人目录

```bash
git clone https://github.com/zemu2718/think-it-through-skill.git
test ! -e ~/.claude/skills/think-it-through
mkdir -p ~/.claude/skills
cp -R think-it-through-skill/skills/think-it-through ~/.claude/skills/
```

### 从源码安装到 Claude Code 项目目录

在目标项目根目录执行：

```bash
test ! -e .claude/skills/think-it-through
mkdir -p .claude/skills
cp -R /path/to/think-it-through-skill/skills/think-it-through .claude/skills/
```

### 构建本地最小候选归档

在克隆后的仓库中执行：

```bash
python3 scripts/build_distribution.py --output-dir dist/v0.3.0-candidate
unzip -t dist/v0.3.0-candidate/think-it-through.skill
```

只应通过已经核验文档路径的 runtime 或安装器安装这个本地 `.skill`。复制成功最多证明安装器发现和可安装性，不证明 runtime 已加载或行为通过。

如果目标目录已经存在，请先自行删除或改名旧目录，不要合并两个版本。若会话启动时 Claude Code 顶层 Skill 目录尚不存在，创建后重启 Claude Code。

Skill 核心不依赖网络、API Key、账号或可执行脚本。只有当前问题满足条件并取得授权时，才可能使用宿主已有的搜索、私有数据、Agent 或持久化能力。

Claude Code 官方参考：[Extend Claude with skills](https://code.claude.com/docs/en/slash-commands)。

## 评测与证据边界

仓库分开评估：

1. **发现性**：description 是否自动加载并避开近邻负例；
2. **加载后行为**：真实模型是否遵守多轮、Gate、授权和降级合同；
3. **核心 UX**：是否帮助用户对齐、纠错、理解和行动；
4. **增强 UX**：调研、参与、跨宿主、解决方案和复判是否有真实增量。

### 冻结 v0.1 行为快照

以下结果只绑定 v0.1 的三个固定场景，既不能证明 v0.2.0，也不能证明 v0.3.0：

| 指标 | With Skill | Without Skill | 差值 |
| --- | ---: | ---: | ---: |
| 合同断言通过率 | **100.0%** | 57.4% | +0.43 |
| 20 分语义 rubric | **98.3%** | 38.3% | +0.60 |
| 通过完整语义门槛的运行 | **3/3** | 0/3 | — |

逐字 transcript、评分和 SHA-256 绑定位于 [`benchmarks/behavior-v0.1/`](benchmarks/behavior-v0.1/)。自动发现的冻结 holdout 为 **9/16**；详情见 [`benchmarks/trigger-v0.1/`](benchmarks/trigger-v0.1/)。

### v0.3.0 候选合同校验

current grader、versioned fixtures、十维 20 分核心 UX rubric 和八维 16 分增强 rubric 让源码候选保持可机械复核：

- [`ux-evals.json`](skills/think-it-through/evals/ux-evals.json)
- [`ux-rubric.md`](skills/think-it-through/evals/ux-rubric.md)
- [`enhancement-rubric.md`](skills/think-it-through/evals/enhancement-rubric.md)

```bash
uv run --python 3.12 --with-requirements requirements-validation.txt \
  python -m unittest discover -s scripts -p 'test_*.py' -v
uv run --python 3.12 --with-requirements requirements-validation.txt \
  python scripts/validate_repo.py
```

仓库合同校验与具体会话执行分开管理：前者确认分发协议和机器合同，后者只由当次能力观测、授权、trace 与 receipt 建立。新增宿主原生兼容声明，需要对应版本的加载、交互、执行与降级证据。

## 安全与隐私

- 默认零外部调用、单 Agent、对话内快照；
- 不替代医疗、法律、投资或紧急专业帮助；
- 不提供操控、欺骗、恐吓、跟踪或胁迫策略；
- 区分事实、推断、假设和未知；
- 最终选择和任何外部行动属于用户。

详见 [`SECURITY.md`](SECURITY.md) 和 [`safety-boundaries.md`](skills/think-it-through/references/safety-boundaries.md)。

## 透明的方法来源

七张专项方法卡中性改编自 `SamadhiFire/xinqingnian-maoxuan-skill` 固定版本中的 MIT 文件。每张卡都记录仓库、固定 commit、准确文件、许可证和实质修改；另外三个候选仓库经过审计后未采用。

详见 [`docs/third-party-audit.md`](docs/third-party-audit.md) 和 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

## 项目结构

```text
skills/think-it-through/
├── SKILL.md                    # 当前宿主入口与精简状态合同
├── core/                       # Portable protocol 与 JSON Schema
├── policies/                   # Evidence / Participation 路由
├── adapters/                   # Agent Skills / text / Claude Code / ChatGPT
├── references/                 # 分析、交互、方法、安全与来源
├── evals/                      # current fixtures、UX 与触发定义；不打包
├── LICENSE
└── THIRD_PARTY_NOTICES.md

distribution/package-manifest.json  # 运行时归档精确文件集合
compatibility/                  # L0～L5 profile、schema、状态与已审阅证据
benchmarks/behavior-v0.1/       # 冻结行为证据
benchmarks/trigger-v0.1/        # 冻结 discovery 证据
docs/                           # 版本化产品架构与第三方审计
scripts/                        # 版本化评分、测试、校验与打包
assets/                         # 原创项目视觉
CHANGELOG.md                    # 发布状态与版本历史
```

唯一维护源是 `skills/think-it-through/`。项目级 `.claude/skills/think-it-through/` 只是本地安装副本。运行时归档精确包含 [`distribution/package-manifest.json`](distribution/package-manifest.json) 中排序后的文件集合：运行时入口、core、policies、adapters、必要 references、许可证和第三方通知；排除 evals、兼容证据、benchmarks、历史 transcript、workspace、缓存和本机配置。

## 参与贡献

最有价值的贡献包括真实决策用例、近邻触发负例、方法路由测试、有界 Evidence / Participation 场景、跨宿主 conformance、真实 UX 评审和可复现的校验修复。新框架、角色或能力必须证明独立决策价值，而不是只让功能清单变长。

请从 [`CONTRIBUTING.md`](CONTRIBUTING.md) 开始；安全问题按 [`SECURITY.md`](SECURITY.md) 私下报告。

## 许可证

想清楚使用 [MIT License](LICENSE) 开源。第三方归属保留在 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) 中。
