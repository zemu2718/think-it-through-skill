# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

本仓库发布纯指令型 Agent Skill“想清楚 · Think It Through”。它在重要选择或重要执行前，把“表面任务 → 真实目的 → 决策问题”收敛为内部 R-align / R-method / A / B 状态流程，再给一个可验证、尽量可撤回的现实实验。产品原则以 `PRODUCT.md` 为准，正式行为、验收和安全合同以 `REQUIREMENTS.md` 为准。

当前可靠调用方式是 `/think-it-through`。自动发现的冻结 v0.1 holdout 仅为 9/16（正例 1/8、负例 8/8），不要把自然语言自动加载或其他客户端兼容性描述为已经通过。

## 常用命令

仓库没有应用运行时、构建系统或常驻服务；开发工作主要是编辑 Markdown/YAML/JSON、运行 Python 合同测试、校验仓库和构建 `.skill` 包。CI 使用 Python 3.12 与 PyYAML；本机优先用 `uv` 复现：

```bash
# 完整测试
uv run --python 3.12 --with pyyaml \
  python -m unittest discover -s scripts -p 'test_*.py' -v

# 仓库结构、合同、链接、来源、冻结证据和分发文件集合
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

当前评分器的 CLI 必须提供结构化交互证据：

```bash
PYTHONPATH=scripts uv run --python 3.12 --with pyyaml \
  python scripts/grade_contracts.py \
  --stage R \
  --r-mode align \
  --input /path/to/assistant-output.md \
  --interaction-json /path/to/interaction-evidence.json
```

构建新版本分发包时必须使用新的空目录；脚本会拒绝覆盖已有 archive 或 `unpacked/`：

```bash
python3 scripts/build_distribution.py --output-dir dist/vX.Y.Z
unzip -t dist/vX.Y.Z/think-it-through.skill
```

分发包刻意排除 `evals/`，并在构建时解包复验文件集合和字节内容。`dist/` 被 Git 忽略。

## 架构与维护边界

### 唯一维护源与本地副本

`skills/think-it-through/` 是唯一维护源：

- `SKILL.md`：入口、适用边界、内部状态机、阶段等待边界和回复合同；保持少于 500 行。
- `references/core-analysis.md`：各阶段共享的问题重构、证据与数字纪律。
- `references/interaction-ux.md`：用户可见表达及原生控件优先合同。
- `references/method-selection.md`：R-method 路由、组合确认和增量调整语义。
- `references/two-sided-steelman.md`、`pre-mortem.md` 与 `references/methods/`：可选分析方法。
- `references/external-validation.md`、`safety-boundaries.md`：工具、数据、外部行动授权及高风险边界。
- `evals/`：当前 fixtures、UX 合同和冻结行为评测定义；不进入 `.skill` 包。

`.claude/skills/think-it-through/` 是被忽略的项目级安装副本，不是第二维护源。源码稳定后做非删除式同步并比较：

```bash
rsync -a skills/think-it-through/ .claude/skills/think-it-through/
diff -qr skills/think-it-through .claude/skills/think-it-through
```

不要先在 `.claude/skills/` 修改再回抄；也不要把本地设置或该副本加入版本控制。

### 当前 v0.1.5 交互合同

宿主提供 `AskUserQuestion` 或等价工具时必须优先实际调用，Markdown 不能冒充工具调用。控件由答案形态决定，而不是由阶段名固定：

- `compatible-set`：可并存目的或可组合方法使用原生多选。
- `finite-mutually-exclusive`：真实有限互斥边界使用原生单选。
- `open`：直接自由回答，不调用选择控件；A 不允许 `compatible-set`。
- R-align 用户回答后先合并可并存目的、不默认排序；只有用户提供的真实排他约束会改变当前决定时才继续澄清。
- R-method 方法调整仍留在 R-method，提交唯一最终组合后才进入 A。
- B 先完成判断与一个现实实验，再调用四项原生单选；该问题只收集反馈方向，不索取新的决策信息。
- B 只有在实际观察到与选择并存的宿主附注时才使用 `native-note`；否则原生单选使用 `follow-up-message`，文本降级使用 `inline-text`。宿主 `Other` 不是独立备注。
- 只有控件不可用、失败或被拒绝时才文本降级；B 使用普通编号，不用方括号或伪 radio。产品不得自建“其他/Other”；自由文字与选择冲突时以文字为准。
- 用户可见输出一意一段；承接、解释、操作提示和正式问题用空行分开，正式问题独立位于最后；选项短、平行、同层级，B 的动作、观察、复判分别成段。

`scripts/grade_contracts.py` 是当前合同评分器。其 `InteractionEvidence` 把宿主状态、交互表面、实际工具调用、single/multi/none、产品选项、宿主自由输入、原生问题正文和 `supplement_mode` 作为可观察证据；failed/rejected 记录已发生的调用 trace，而 surface 记录最终呈现。当前行为修改应同时更新：

1. `SKILL.md` 和相关 reference；
2. `REQUIREMENTS.md`，必要时 `PRODUCT.md`；
3. `scripts/grade_contracts.py` 与 `scripts/test_contract_graders.py`；
4. `skills/think-it-through/evals/fixtures/` 中对应场景；
5. 用户可见变化涉及命令、兼容性、benchmark 或安全边界时，同步中英文 README；
6. `scripts/validate_repo.py` 的版本和一致性断言。

### 方法注册与第三方来源

七张专项卡由 `references/methods/registry.yaml` 注册；路由顺序是“基础分析是否足够 → 双向钢人 → 失败预演 → 至多一张填补独特缺口的专项卡”，去重后保留 0～3 项，零张专项卡合法。新增或修改第三方改编时必须同步固定 commit、准确源文件、许可证、`THIRD_PARTY_NOTICES.md`、`docs/third-party-audit.md`，并在 `07-method-routing.json` 覆盖适用、不适用和重叠三种情况。

### 当前合同与冻结历史证据严格隔离

不要用当前合同重新评分或改写 v0.1 快照：

- `scripts/grade_contracts.py`：当前 v0.1.5 评分器。
- `scripts/grade_contracts_v0_1.py`：冻结 legacy 评分器。
- `scripts/grade_behavior_runs.py`：必须显式从 `grade_contracts_v0_1` 导入。
- `scripts/test_legacy_behavior_grader.py`：保护导入隔离、transcript 哈希和冻结评分重现。
- `benchmarks/behavior-v0.1/`：逐字 transcript、评分、语义 rubric 和聚合结果的冻结快照。
- `benchmarks/trigger-v0.1/`：冻结 description 与 discovery dev/holdout 结果。

`validate_repo.py` 固定检查 behavior benchmark 的完整文件集合和 SHA-256，也固定 Skill description 的 SHA-256。不要修改历史 transcript、评分、语义评审、benchmark 或冻结 description，除非明确建立新的评测版本和证据链。触发词调整只使用 `skills/think-it-through/evals/trigger-dev.json`；同一发布版本不得根据 frozen holdout 继续调优。

### 版本与证据声明

合同变化需要同步 `SKILL.md` metadata、方法 registry、current fixtures、UX eval/rubric、评分器输出、validator 以及公开文档中的当前版本。静态 fixtures、单元测试和线框只能证明合同定义，不能证明真实模型调用了原生控件或宿主呈现了独立附注。没有新模型运行或真实用户评审时，真实多轮行为、原生反馈单选 UI、独立附注呈现和真实用户体验必须继续标为 `未实测 / not_run`；旧 v0.1 分数不能证明当前版本行为。
