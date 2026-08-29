# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

本仓库发布纯指令型 Agent Skill“想清楚 · Think It Through”。v0.2.0 将其定义为重要行动前后的决策与证据协议：先把“表面任务 → 真实目的 → 决策问题”收敛为 R-align / R-method / A；用户回答后才按需要路由有界 Evidence / Participation Gate；最终 B 交付一个综合判断、一个主现实证据闭环、可复制的决策快照和四项反馈。

文档职责必须保持单一：`README.md` / `README.zh-CN.md` 是对应语言的用户入口；`PRODUCT.md` 说明产品愿景、目标用户与原则；`REQUIREMENTS.md` 是唯一正式行为、安全与验收依据；`docs/product-architecture-v0.2.0.md` 只保留非规范性架构理由、历史取舍和验证路线；`CHANGELOG.md` 记录版本事实。不要在多个文件维护第二套正式合同。

当前可靠调用方式是 `/think-it-through`。自动发现的冻结 v0.1 holdout 仅为 9/16（正例 1/8、负例 8/8），不要把自然语言自动加载或其他客户端兼容性描述为已经通过。

## 常用命令

仓库没有应用运行时、构建系统或常驻服务；开发工作主要是编辑 Markdown/YAML/JSON、运行 Python 合同测试、校验仓库和构建 `.skill` 包。CI 使用 Python 3.12 与 PyYAML；本机优先用 `uv` 复现：

```bash
# 完整测试
uv run --python 3.12 --with pyyaml \
  python -m unittest discover -s scripts -p 'test_*.py' -v

# 仓库结构、合同、schema、链接、来源、冻结证据和分发集合
uv run --python 3.12 --with pyyaml python scripts/validate_repo.py

# 单个测试文件
uv run --python 3.12 --with pyyaml \
  python -m unittest discover -s scripts -p 'test_contract_graders.py' -v

# 单个测试方法；把 scripts/ 放入导入路径
PYTHONPATH=scripts uv run --python 3.12 --with pyyaml \
  python -m unittest \
  test_contract_graders.ContractGraderTests.test_valid_r_align -v

# 改动提交前的空白检查
git diff --check
```

不用 `uv` 时，先在 Python 3.12 环境安装 `PyYAML`，再使用 CI 中的 `python -m unittest ...` 和 `python scripts/validate_repo.py`。

当前评分器的 R / A / B CLI 必须提供结构化交互证据：

```bash
PYTHONPATH=scripts uv run --python 3.12 --with pyyaml \
  python scripts/grade_contracts.py \
  --stage R \
  --r-mode align \
  --input /path/to/assistant-output.md \
  --interaction-json /path/to/interaction-evidence.json
```

Gate 与记录使用对应 JSON：

```bash
PYTHONPATH=scripts uv run --python 3.12 --with pyyaml \
  python scripts/grade_contracts.py \
  --stage EVIDENCE \
  --record-json /path/to/evidence-record.json \
  --consent-json /path/to/consent.json \
  --receipt-json /path/to/receipt-bundle.json

PYTHONPATH=scripts uv run --python 3.12 --with pyyaml \
  python scripts/grade_contracts.py \
  --stage PARTICIPATION \
  --record-json /path/to/participation-record.json \
  --consent-json /path/to/consent.json \
  --receipt-json /path/to/receipt-bundle.json

PYTHONPATH=scripts uv run --python 3.12 --with pyyaml \
  python scripts/grade_contracts.py \
  --stage DECISION_RECORD \
  --record-json /path/to/decision-record.json
```

`HUMAN` 使用 `--record-json`；不需要 interaction / consent / receipt 参数。以实际 CLI parser 和测试为准，不在脚本外复制第二套语义。

构建新版本分发包时必须使用新的空目录；脚本会拒绝覆盖已有 archive 或 `unpacked/`：

```bash
python3 scripts/build_distribution.py --output-dir dist/vX.Y.Z
unzip -t dist/vX.Y.Z/think-it-through.skill
```

分发包刻意排除 `evals/`，并在构建时解包复验文件集合和字节内容。`dist/` 被 Git 忽略。

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
- `adapters/claude-code.md`：Claude Code 当前会话的原生选择、搜索、文件、Agent 与授权映射。
- `adapters/chatgpt.md`：Skill-only / 纯文本支持范围、条件能力映射与宿主能力不得推定的边界。
- `references/core-analysis.md`：问题重构、证据状态、唯一问题、判断、主现实闭环和数字纪律。
- `references/interaction-ux.md`：答案形态驱动控件、语义排版、文本降级和 B 反馈。
- `references/method-selection.md`：结构化方法 option、路由、最终组合和增量调整。
- `references/two-sided-steelman.md`、`pre-mortem.md` 与 `references/methods/`：可选分析方法。
- `references/external-validation.md`、`safety-boundaries.md`：证据来源、四类授权和高风险边界。
- `evals/`：current fixtures、核心 / 增强 UX、触发与冻结行为定义；不进入 `.skill` 包。

调研、多 Agent、真人参与、持久化和宿主适配不是方法卡，不得进入 `references/methods/registry.yaml`。

`.claude/skills/think-it-through/` 是被忽略的项目级安装副本，不是第二维护源。源码稳定后做非删除式同步并比较：

```bash
rsync -a skills/think-it-through/ .claude/skills/think-it-through/
diff -qr skills/think-it-through .claude/skills/think-it-through
```

不要先在 `.claude/skills/` 修改再回抄；也不要把本地设置或该副本加入版本控制。

### 当前 v0.2.0 状态与交互合同

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
- 用户可见输出一意一段；段落、列表、标签—值、表格和标题按信息关系选择；正式问题独立位于最后，不按固定字符宽度硬折行。

### Evidence 与 Participation 合同

Evidence Gate 只有在外部可验证事实会改变排序、是否继续或投入边界，获取方式有限且价值高于成本时进入。必须先说明决定、证据问题、范围、停止条件、来源、provider、数据、成本和降级，再取得具体 `capability_call` 授权。结果保留来源、日期、支持 / 反对证据、冲突、空白和判断影响；失败后保留未知并继续 B。

Participation Gate 默认单 Agent。只有不重复、可验证、可停止的独立任务有明确增量时才建议额外 Agent：

```text
可用额外上限 = max(0, 用户总参与上限 - 1)
实际额外数 = min(独立任务数, 用户可用额外上限, 产品上限, 宿主上限, 成本预算)
实际总数 = 1 + 实际启动额外数
```

用户上限是硬上限，不是使用目标。额外 Agent 只接收最小上下文，禁止递归委派；主 Agent 去重来源、呈现冲突并综合，不按投票。回执中的计划、启动、完成、失败和实际总数必须一致。

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

`scripts/grade_contracts.py` 是 v0.2.0 当前评分器。其 `InteractionEvidence` 规范化字符串或结构化 option，并记录宿主状态、交互表面、实际调用、single / multi / none、宿主自由输入、原生问题正文和 `supplement_mode`。failed / rejected 记录已发生的 trace，surface 记录最终呈现。

当前行为修改应同步：

1. `SKILL.md`、core、policy、adapter 和相关 reference；
2. `REQUIREMENTS.md`，必要时 `PRODUCT.md`；
3. `scripts/grade_contracts.py` 与 `scripts/test_contract_graders.py`；
4. current fixtures 与 core / enhancement UX；
5. 用户可见命令、兼容性、benchmark、安全或证据边界变化时同步中英文 README；
6. `scripts/validate_repo.py` 的版本、schema、文件集合和一致性断言；
7. 分发集合与本地安装副本。

## 方法注册与第三方来源

七张专项卡由 `references/methods/registry.yaml` 注册；路由顺序是“基础分析是否足够 → 双向钢人 → 失败预演 → 至多一张填补独特缺口的专项卡”，去重后保留 0～3 项，零张专项卡合法。

新增或修改第三方改编时必须同步固定 commit、准确源文件、许可证、`THIRD_PARTY_NOTICES.md`、`docs/third-party-audit.md`，并在 `07-method-routing.json` 覆盖适用、不适用和重叠场景。

## 当前合同与冻结历史证据严格隔离

不要用当前合同重新评分或改写 v0.1 快照：

- `scripts/grade_contracts.py`：当前 v0.2.0 评分器；
- `scripts/grade_contracts_v0_1.py`：冻结 legacy 评分器；
- `scripts/grade_behavior_runs.py`：必须显式从 `grade_contracts_v0_1` 导入；
- `scripts/test_legacy_behavior_grader.py`：可维护的保护测试，负责导入隔离、transcript 哈希和冻结评分重现；可适配 canonical benchmark 布局，但不得改变受保护语义；
- `benchmarks/behavior-v0.1/`：逐字 transcript、评分、语义 rubric 和聚合结果；
- `benchmarks/trigger-v0.1/`：冻结 description 与 discovery dev / holdout 结果。

`validate_repo.py` 固定检查 behavior benchmark 的完整文件集合和 SHA-256，也固定 Skill description 的 SHA-256。不要修改历史 transcript、评分、语义评审、benchmark 或冻结 description，除非明确建立新的评测版本和证据链。触发词调整只使用 `skills/think-it-through/evals/trigger-dev.json`；同一发布版本不得根据 frozen holdout 继续调优。

## 版本、发布范围与证据声明

合同变化需要同步 `SKILL.md` metadata、方法 registry、core schema、policies、adapters、current fixtures、core / enhancement UX、评分器、validator 和公开文档中的版本。

对外发布状态与内部评测状态必须分层：

- README、PRODUCT、REQUIREMENTS、架构说明和 28 文件运行时包只写当前发布支持范围，不复制内部机器评测状态表；
- 当前发布范围使用“Claude Code 显式 `/think-it-through` + 纯文本跨宿主基线 + 条件能力逐会话协商”表达；
- `evals/` 继续按实际执行情况维护机器状态，正式发布不得把未运行项改成 `passed`；
- 静态规范、schema、fixtures、单元测试和线框只能证明合同定义，不能证明某次真实模型行为、原生 UI、搜索、Agent、真人参与、持久化、宿主兼容或真实 UX；
- 具体能力是否发生只由当前会话 capability observation、consent、工具 trace 与 receipt 建立；未调用、拒绝和失败不得写成完成；
- 新增宿主原生兼容或真实体验声明前，必须建立对应版本化加载、能力、交互、授权、执行与降级证据。

旧 v0.1 分数不能证明 v0.2.0 行为。
