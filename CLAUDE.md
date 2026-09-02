# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

本仓库发布纯指令型 Agent Skill“想清楚 · Think It Through”。v0.4.1 将其定义为重要行动前后的决策与证据协议：先把“表面任务 → 真实目的 → 决策问题”收敛为 R-align / R-method / A；项目、功能、自研或技术形态先降级为候选，并分开判断问题存在、问题强度、方案适配和替代生态；用户回答后才按需要路由有界 Evidence / Participation Gate；最终 B 交付一个综合判断、一个主现实证据闭环、可复制的决策快照和四项反馈。

文档职责必须保持单一：`README.md` 是 GitHub 默认展示的精简中文用户入口，`README.en.md` 是英文用户入口，只负责让普通用户看懂价值、判断是否适用并开始使用；`docs/installation.md` 与 `docs/installation.en.md` 承接详细安装和文件核验；`docs/compatibility-and-evidence.md` 与 `docs/compatibility-and-evidence.en.md` 解释公开兼容状态、冻结证据和提升边界，但不是第二份合同；`PRODUCT.md` 说明产品愿景、目标用户与原则；`REQUIREMENTS.md` 是唯一正式行为、安全与验收依据；`docs/product-architecture-v0.4.0.md` 保留 v0.4.0 非规范性架构理由、历史取舍和验证路线，历史 `docs/product-architecture-v0.3.0.md` 保留；`CHANGELOG.md` 记录版本事实。不要在多个文件维护第二套正式合同。

当前可靠调用方式是 `/think-it-through`。自动发现的冻结 v0.1 holdout 仅为 9/16（正例 1/8、负例 8/8），不要把自然语言自动加载或其他客户端兼容性描述为已经通过。

README、品牌表达或视觉资产改动前先读 `.agents/brand-context.md`，但它只是 `REQUIREMENTS.md` 与 `PRODUCT.md` 的派生摘要，不是第二份合同。视觉资产由 `assets/manifest.json` 定义职责与变体；深色 README Invocation Card 是固定哈希的唯一 canonical 3D raster source，浅色卡片和 Social Preview PNG 通过 `scripts/render_assets.py` 从 manifest 声明的源确定性生成，不得手改或另存第二份主体。Social Preview 同时依赖其 SVG 布局源与深色 canonical 主体；本地生成不得误写成 GitHub 已启用。

`docs/project-viability-falsification-proposal.md` 是非规范性设计输入，不是第二份合同；已实现语义只由 v0.4.1 `REQUIREMENTS.md` 和 `skills/think-it-through/` 当前源码定义。该机制不新增协议状态、intent、授权类型、receipt kind、DecisionRecord state、core schema 或方法卡。

## 常用命令

仓库没有应用运行时、构建系统或常驻服务；开发工作主要是编辑 Markdown/YAML/JSON、运行 Python 合同测试、校验仓库和构建 `.skill` 包。CI 使用 Python 3.12 与 `requirements-validation.txt` 中固定的验证依赖；本机优先用 `uv` 复现：

```bash
# 完整测试
uv run --python 3.12 --with-requirements requirements-validation.txt \
  python -m unittest discover -s scripts -p 'test_*.py' -v

# 仓库结构、合同、schema、链接、来源、冻结证据和分发集合
uv run --python 3.12 --with-requirements requirements-validation.txt python scripts/validate_repo.py

# 编辑声明了 generator 的 canonical 视觉源后重新生成派生资产
uv run --python 3.12 --with-requirements requirements-validation.txt python scripts/render_assets.py

# 只检查派生视觉资产，不写 tracked 文件
uv run --python 3.12 --with-requirements requirements-validation.txt python scripts/render_assets.py --check

# 单个测试文件
uv run --python 3.12 --with-requirements requirements-validation.txt \
  python -m unittest discover -s scripts -p 'test_contract_graders.py' -v

# 单个测试方法；把 scripts/ 放入导入路径
PYTHONPATH=scripts uv run --python 3.12 --with-requirements requirements-validation.txt \
  python -m unittest \
  test_contract_graders.ContractGraderTests.test_valid_r_align -v

# 改动提交前的空白检查
git diff --check
```

不用 `uv` 时，先在 Python 3.12 环境安装 `requirements-validation.txt` 中的固定依赖，再使用 CI 中的 `python -m unittest ...` 和 `python scripts/validate_repo.py`。

当前评分器的 R / A / B CLI 必须提供结构化交互证据：

```bash
PYTHONPATH=scripts uv run --python 3.12 --with-requirements requirements-validation.txt \
  python scripts/grade_contracts.py \
  --stage R \
  --r-mode align \
  --input /path/to/assistant-output.md \
  --interaction-json /path/to/interaction-evidence.json

PYTHONPATH=scripts uv run --python 3.12 --with-requirements requirements-validation.txt \
  python scripts/grade_contracts.py \
  --stage B \
  --input /path/to/assistant-output.md \
  --interaction-json /path/to/interaction-evidence.json \
  --decision-record-json /path/to/decision-record.json \
  --visible-snapshot-json /path/to/visible-snapshot.json
```

Gate 与记录仍通过必填的 `--input` 读取对应 JSON；Evidence / Participation 另需授权与回执：

```bash
PYTHONPATH=scripts uv run --python 3.12 --with-requirements requirements-validation.txt \
  python scripts/grade_contracts.py \
  --stage EVIDENCE \
  --input /path/to/evidence-record.json \
  --consent-json /path/to/consent.json \
  --receipt-json /path/to/receipt-bundle.json

PYTHONPATH=scripts uv run --python 3.12 --with-requirements requirements-validation.txt \
  python scripts/grade_contracts.py \
  --stage PARTICIPATION \
  --input /path/to/participation-record.json \
  --consent-json /path/to/consent.json \
  --receipt-json /path/to/receipt-bundle.json

PYTHONPATH=scripts uv run --python 3.12 --with-requirements requirements-validation.txt \
  python scripts/grade_contracts.py \
  --stage DECISION_RECORD \
  --input /path/to/decision-record.json
```

`HUMAN` 的 `draft_only` 只需通过 `--input` 提供记录；`authorized_send` 还必须同时提供 `--consent-json` 的 exact `{"consents": [...]}` 双授权 bundle 与 `--receipt-json` 回执 bundle。`PROJECT_VIABILITY` 通过 `--input` 提供 grader-only sidecar，并可用同样的 consent wrapper 与现有 receipt bundle 校验证据链；它不是运行时状态或 DecisionRecord。`CHECKPOINT` 通过 `--input` 提供输出并要求 `--context-json`；上下文要求实际呈现检查点时还要提供 `--interaction-json`。以 `python scripts/grade_contracts.py --help`、实际 CLI parser 和测试为准，不在脚本外复制第二套参数语义。

构建新版本分发包时必须使用新的空目录；脚本会拒绝覆盖已有 archive 或 `unpacked/`：

```bash
python3 scripts/build_distribution.py --output-dir dist/vX.Y.Z
unzip -t dist/vX.Y.Z/think-it-through.skill
```

完整复现普通 CI 时，还要按 `.github/workflows/validate.yml` 运行固定 revision 的 `skills-ref` 格式检查，以及 Node 22.20.0 环境中的固定 `skills@1.5.23` L1/L2 安装器 smoke；`validate_repo.py` 不替代这两个外部工具检查。仓库没有独立的 Python lint 或 formatter 配置，不要虚构 Ruff、Black、Flake8、Mypy、Pyright 或 pytest 命令。

`distribution/package-manifest.json` 是运行时归档精确文件集合的唯一机器事实源，builder、validator 和 tests 必须共同读取它，不再复制固定文件数。分发包刻意排除 `evals/`、兼容证据、benchmark 与本机配置，并在构建时解包复验文件集合和字节内容。`dist/` 被 Git 忽略。

## 架构与维护边界

### 唯一维护源与本地副本

用户可见文档优先使用读者语言：中文入口以自然中文为主，必要的命令、标识符和首次出现的正式英文术语除外；英文入口保持英文。表格只用于同维度比较，流程图只在空间关系或分支比文字更清楚时使用，并提供等价文字或可访问描述。

`skills/think-it-through/` 是唯一维护源：

- `SKILL.md`：当前宿主入口、适用边界、精简状态机、Gate 入口、等待与回复合同；保持少于 500 行。
- `core/protocol.md`：宿主无关的状态、intent、能力协商、授权、receipt、DecisionRecord 和完成语义。
- `core/*.schema.json`：Draft 2020-12 的 intent、consent、receipt、DecisionRecord 机器合同。
- `policies/evidence-routing.md`：Evidence Gate 的必要性、范围、来源、停止、失败和回执。
- `policies/participation-routing.md`：单 / 多 Agent、总数上限、最小上下文、非递归、无投票综合和真人参与。
- `adapters/text.md`：一等纯文本参考实现。
- `adapters/agent-skills.md`：开放 Agent Skills 的共同目录、相对引用、纯文本基线与能力证据边界。
- `adapters/claude-code.md`：Claude Code 当前会话的原生选择、搜索、文件、Agent 与授权映射。
- `adapters/chatgpt.md`：Skill-only / 纯文本支持范围、条件能力映射与宿主能力不得推定的边界。
- `references/core-analysis.md`：问题重构、证据状态、唯一问题、判断、主现实闭环和数字纪律。
- `references/project-viability.md`：项目方案去锚、四维价值验证、两遍搜索、动态候选、核验、最强替代试用、独立反方和承诺上限。
- `references/interaction-ux.md`：答案形态驱动控件、语义排版、文本降级和 B 反馈。
- `references/method-selection.md`：结构化方法 option、路由、最终组合和增量调整。
- `references/two-sided-steelman.md`、`pre-mortem.md` 与 `references/methods/`：可选分析方法。
- `references/external-validation.md`、`safety-boundaries.md`：证据来源、四类授权和高风险边界。
- `evals/`：current fixtures、核心 / 增强 UX、触发与冻结行为定义；不进入 `.skill` 包。

仓库级 `compatibility/` 不进入 `.skill`：`profile.json` 固定 L0～L5、状态、证据类型和工具版本；`runtime-support.json` 是机器可读状态投影；`evidence/` 只在真实执行并完成脱敏审阅后保存证据。L0 格式、L1 发现、L2 安装、L3 加载、L4 纯文本行为和 L5 原生能力互不替代；L3～L5 只能由绑定准确 runtime version 的 `real_runtime` 证据提升。安装器 target 数不得转述为已验证 runtime 数量。

调研、build-vs-buy、现实替代试用、项目可行性、独立反方、多 Agent、真人参与、持久化和宿主适配不是方法卡，不得进入 `references/methods/registry.yaml`。

`.claude/skills/think-it-through/` 是被忽略的项目级安装副本，不是第二维护源。源码稳定后做非删除式同步并比较：

```bash
rsync -a skills/think-it-through/ .claude/skills/think-it-through/
diff -qr skills/think-it-through .claude/skills/think-it-through
```

不要先在 `.claude/skills/` 修改再回抄；也不要把本地设置或该副本加入版本控制。

### 双语 README 文案维护

README 文案修改以普通用户第一次阅读为视角，不逐句孤立修补。用户指出一处生硬、冗余或难懂的表达时，同时检查所在段落、相邻上下文、对应语言版本和全文同类表达；先形成一版完整方案，再统一修改。

文案遵循：

- 先说用户能得到什么、什么时候适用和下一步怎么做，再解释方法、必要边界和维护信息；
- 优先使用用户能直接理解的结果、动作和场景，不把内部状态、协议字段、维护分类或交付物名称直接当作用户文案；
- 每句话至少承担价值、适用性、使用方式、必要边界或下一步入口中的一项职责；没有明确职责的说明删除或移入详细指南；
- 安装、安全和兼容边界只保留用户当前操作所必需的内容，放在对应操作之后，并用最短自然语言表达，不让防御性说明打断主路径；
- 中文以自然中文为准；英文独立按自然英文重写。双语保持信息、顺序和声明边界一致，不要求逐字直译；
- 标题、列表项和相邻段落共同形成完整阅读路径，避免抽象名词堆叠、指代中断、重复标题和同义反复；
- 首屏价值说明、产品定位等 canonical 品牌文案变化时，同步 `PRODUCT.md`、品牌摘要、双语 README、`CHANGELOG.md` 和必要校验；普通措辞润色不扩大为正式合同修改；
- 修改完成前整体通读双语 README，检查生硬术语、无必要说明、上下文衔接、操作门槛、中英文一致性和事实边界。

公开文档校验优先锁定结构、必要语义、命令、链接和声明边界。除 canonical 品牌文案、可靠调用方式、安全边界及必须逐字一致的合同内容外，不绑定整句普通文案；mutation test 验证语义缺失或错误声明，而不是阻止自然润色。

### 当前 v0.4.1 状态与交互合同

唯一状态语义：

```text
空状态
→ R-align
→ R-method
→ A
→ Gate-routing
→（必要且获授权时）Evidence Gate / Participation Gate
→ B
→ 反馈 / 结束 / 新一轮 R
```

Gate 是条件能力，不是固定阶段。R 和 A 均不调用、请求或建议搜索、文件、数据、Agent 或真人参与；只有用户回答 A 后才路由。能力不可用、`unknown`、未授权、被拒绝或失败时，记录后基于已有信息进入条件化 B。

宿主提供 `AskUserQuestion` 或等价工具时必须优先实际调用，Markdown 不能冒充工具调用。控件由答案形态决定：

- `compatible-set`：可并存目的或可组合方法使用原生多选；
- `finite-mutually-exclusive`：真实有限互斥边界使用原生单选；
- `open`：直接自由回答，不调用选择控件；A 不允许 `compatible-set`；
- R-align 用户回答后先合并可并存目的、不默认排序；只有用户提供的真实排他约束会改变当前决定时才继续澄清；
- R-method 每个正式 option 必须有 `id / label / description / recommended`；推荐不等于确认；提交唯一最终组合后才进入 A；
- option description 可用时在同一选项内联，不可用时使用紧邻说明；不得在正文完整重复后只在控件列名称；
- A 只有一个答案槽并问后等待；用户回答后才进入 Gate-routing；
- B 先完成判断、主现实证据闭环和对话内决策快照，再调用四项原生单选；该问题只收集反馈方向，不索取新决策信息；
- B 只有在实际观察到与选择并存的宿主附注时才使用 `native-note`；否则原生单选使用 `follow-up-message`，文本降级使用 `inline-text`；宿主 `Other` 不是独立备注；
- 只有控件不可用、失败或被拒绝时才文本降级；使用普通编号，不用方括号、checkbox、`○` 或 HTML 伪控件；产品不得自建 Other；文字冲突时以文字为准；
- 用户可见输出一意一段；普通正文先说完整含义，专业语义只在必要时句末后置，不重新引入 `**核心假设**：`、`**动作**：`、`**观察**：`、`**复判**：` 等 current 句首模板；方法 option、Gate、授权、回执和决策快照可结构化；段落、列表、标签—值、表格和标题按信息关系选择；正式问题独立位于最后，不按固定字符宽度硬折行；
- DecisionRecord 的 canonical key 与用户可见字段分离；显示字段可以本地化，但必须无损映射，`assumptions` 与 `unknowns` 不得合并。

### Evidence 与 Participation 合同

Evidence Gate 只有在外部可验证事实会改变排序、是否继续或投入边界，获取方式有限且价值高于成本时进入。必须先说明决定、证据问题、范围、停止条件、来源、provider、数据、成本和降级，再取得具体 `capability_call` 授权。项目可行性调研先 outcome/problem-first，再 solution/implementation-second；动态覆盖非同形路径，按候选类型核验现实边界，重大投入前尽可能以同一真实任务试用最强替代。结果保留来源、日期、支持 / 反对证据、冲突、空白和判断影响；未发现、未试用、失败或来源不足均保留未知并继续 B，不得支持扩大自研。

Participation Gate 默认单 Agent。只有不重复、可验证、可停止的独立任务有明确增量时才建议额外 Agent：

```text
可用额外上限 = max(0, 用户总参与上限 - 1)
实际额外数 = min(独立任务数, 用户可用额外上限, 产品上限, 宿主上限, 成本预算)
实际总数 = 1 + 实际启动额外数
```

用户上限是硬上限，不是使用目标。额外 Agent 只接收最小上下文，禁止递归委派；项目可行性独立反方只有不重复、可验证、可停止且有明确增量时才经单独授权启用，不接收主判断、偏好方案或完整 transcript，并只返回七字段 exact payload。主 Agent 去重来源、呈现冲突并综合，不按投票。反方失败降低承诺上限；回执中的计划、启动、完成、失败和实际总数必须一致。

真人掌握的价值、权责、承诺、客户行为和专业责任不得由 Agent 代答。默认只生成最小可转发草稿；发送、邀请、建群、预约和联系需要独立外部行动授权。

### 授权、能力与持久化

四类授权互不继承：

```text
capability_call
participation_delegation
private_data_access
external_action
```

允许多 Agent不等于允许联网、私有数据或外部行动。方法确认、Agent 上限、B 反馈或历史偏好也不构成授权。

能力逐项记录 `available / unavailable / unknown` 与 `ready / requires_approval / requires_auth / failed`。`unknown` 不得当作可用。真实调用产生 receipt；未调用、拒绝和失败不得伪造成完成。

DecisionRecord 默认：

```json
{
  "mode": "conversation_only",
  "authorized": false
}
```

写入文件或远端必须提供具体 destination 和 consent ID。不得持久化隐藏思维链。

### 当前评分器与同步范围

`scripts/grade_contracts.py` 是 v0.4.1 当前评分器。其 `InteractionEvidence` 规范化字符串或结构化 option，并记录宿主状态、交互表面、实际调用、single / multi / none、宿主自由输入、原生问题正文和 `supplement_mode`。failed / rejected 记录已发生的 trace，surface 记录最终呈现。

`CLAUDE.md` 本身会进入 `validate_public_docs`，且 `scripts/validate_repo.py` 对其中若干维护边界做短语断言。压缩、改名或重构本文件时必须同步 validator 与 `scripts/test_public_docs.py`，并运行完整单测和仓库校验；不要为了通过断言保留已经错误的命令。

当前行为修改应同步：

1. `SKILL.md`、core、policy、adapter 和相关 reference；
2. `REQUIREMENTS.md`，必要时 `PRODUCT.md`；
3. `scripts/grade_contracts.py` 与 `scripts/test_contract_graders.py`；
4. current fixtures 与 core / enhancement UX；
5. 普通用户价值、适用性和开始使用路径变化时同步双语 README；详细安装变化同步 `docs/installation*.md`；兼容性、benchmark 或证据边界变化同步 `docs/compatibility-and-evidence*.md`；安全边界按读者路径同步 README 摘要、对应指南与正式文档；
6. `scripts/validate_repo.py` 的版本、schema、文件集合和一致性断言；
7. 分发集合与本地安装副本。

`PROJECT_VIABILITY` 是 grader-only sidecar stage，顶层 exact keys 与 commitment ceiling 只在 `REQUIREMENTS.md` 定义；它不嵌入 DecisionRecord、不复制 consent/receipt，也不成为第五个 core schema。current fixture 20 与专用单测负责其防回归；静态通过不证明真实搜索、试用或反方发生。

## 方法注册与第三方来源

七张专项卡由 `references/methods/registry.yaml` 注册；路由顺序是“基础分析是否足够 → 双向钢人 → 失败预演 → 至多一张填补独特缺口的专项卡”，去重后保留 0～3 项，零张专项卡合法。

新增或修改第三方改编时必须同步固定 commit、准确源文件、许可证、`THIRD_PARTY_NOTICES.md`、`docs/third-party-audit.md`，并在 `07-method-routing.json` 覆盖适用、不适用和重叠场景。

## 当前合同与冻结历史证据严格隔离

不要用当前合同重新评分或改写 v0.1 快照：

- `scripts/grade_contracts.py`：当前 v0.4.1 评分器；
- `scripts/grade_contracts_v0_1.py`：冻结 legacy 评分器；
- `scripts/grade_behavior_runs.py`：必须显式从 `grade_contracts_v0_1` 导入；
- `scripts/test_legacy_behavior_grader.py`：可维护的保护测试，负责导入隔离、transcript 哈希和冻结评分重现；可适配 canonical benchmark 布局，但不得改变受保护语义；
- `benchmarks/behavior-v0.1/`：逐字 transcript、评分、语义 rubric 和聚合结果；
- `benchmarks/trigger-v0.1/`：冻结 description 与 discovery dev / holdout 结果。

`validate_repo.py` 固定检查 behavior benchmark 的完整文件集合和 SHA-256，也固定 Skill description 的 SHA-256。不要修改历史 transcript、评分、语义评审、benchmark 或冻结 description，除非明确建立新的评测版本和证据链。触发词调整只使用 `skills/think-it-through/evals/trigger-dev.json`；同一发布版本不得根据 frozen holdout 继续调优。

## 版本、发布范围与证据声明

合同变化需要同步 `SKILL.md` metadata、方法 registry、core schema、policies、adapters、current fixtures、core / enhancement UX、评分器、validator 和公开文档中的版本。

稳定源码、公开发布对象、兼容证据、内部评测状态与具体会话事实必须分层：

- v0.4.1 是当前发布候选源码与正式产品合同，尚未创建同名公开对象；v0.4.0 是最新真实公开 tag / Release / asset / 校验和，v0.2.0 与 v0.3.0 继续作为历史发布保留，历史事实不得改写；
- 稳定源码准入由合同、schema、fixtures、grader、公开文档、确定性仓库校验、归档复验、固定格式检查和安装器 L1/L2 smoke 建立，不要求逐客户端真实验证先完成；
- Git commit、tag、GitHub Release 和可下载 asset 只在对应对象真实存在时声明；稳定源码状态不得冒充这些公开对象；
- 双语 README 保持普通用户入口，不复制安装手册、兼容矩阵或内部评测状态；双语兼容与证据说明可以解释稳定发布对象与已由实际 evidence 建立的兼容层级；PRODUCT、REQUIREMENTS 和当前架构说明按各自职责保留产品、正式合同与架构事实；运行时包不复制仓库级矩阵或内部评测状态；
- 当前可靠入口仍用“Claude Code 显式 `/think-it-through` + 纯文本跨宿主基线 + 条件能力逐会话协商”表达；
- `evals/` 继续按实际执行情况维护内部机器状态，不得把未运行项改成 `passed`；v0.4.1 发布候选源码与真实多轮状态 `not_run` 可以同时成立；
- 普通 CI 做合同、schema、L0 格式和 L1/L2 安装器检查，不调用模型 provider，也不自动修改兼容矩阵；
- 用户 Issue 和安装观察属于发布后反馈线索，只有绑定准确 revision/runtime version、可复现、脱敏并经人工审阅的 evidence 才能改变矩阵；
- Claude Code / Codex 真实 smoke 只由手动 workflow 或本地 harness 生成候选 artifact；实际 provider 调用需要独立 `capability_call` 授权，且不会自动提升 L3～L5；
- 静态规范、schema、fixtures、单元测试和线框只能证明合同定义，不能证明某次真实模型行为、原生 UI、搜索、Agent、真人参与、持久化、宿主兼容或真实 UX；
- 具体能力是否发生只由当前会话 capability observation、consent、工具 trace 与 receipt 建立；未调用、拒绝和失败不得写成完成；
- 新增宿主原生兼容或真实体验声明前，必须建立对应版本化加载、能力、交互、授权、执行与降级证据。

旧 v0.1 分数不能证明 v0.4.1 行为。
