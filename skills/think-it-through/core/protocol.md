# Portable Decision Core 协议

## 目的与边界

本文件定义 v0.3.0 的宿主无关决策语义。`SKILL.md` 负责入口和总流程，`policies/` 负责证据与参与路由，`adapters/` 负责把语义意图映射到当前宿主的真实能力。

核心不得依赖特定模型、`AskUserQuestion`、固定 Markdown、联网、子 Agent、固定 Agent 数量或持久化服务。宿主能力只改变交互表面和可执行范围，不能改变目的对齐、用户确认、授权分离、等待边界与证据诚实。

Portable Decision Core 保证的是宿主无关语义，不是具体 runtime 的兼容认证。开放格式、安装器发现、目标目录安装、真实加载、纯文本行为与原生能力由仓库级兼容数据分别记录；前一层不得自动证明后一层。

## 正式流程前的上下文检查点

`pre-entry` 是已加载 Skill 在正式流程前的可观察入口，不是新增分析状态。显式调用直接进入 R；已经处于 R、A、Gate、B 或反馈时不得再次出现。

只有对话从探索跨入立项、选方向、重大投入、继续加码或结果复判等高价值承诺节点，且暂停检查可能避免重要错位时，才请求一次 `request_contextual_checkpoint`。该意图只说明当前承诺、一个决定敏感未知和 why-now，并请求两个互斥方向：`enter-full-check` 或 `continue-current-task`。

问后等待明确选择。选择进入才开始 R；选择继续则恢复原任务，并在当前会话对同一“决定对象 + 真实目的 + 承诺范围”静默。只有新证据、目的变化、承诺范围升级、新复判节点或新议题允许再次评估；普通补充、同义改写或时间经过不重置。不得建立跨会话画像、指纹数据库或持久偏好。

检查点不产生判断、方法确认、Gate、授权、receipt 或 DecisionRecord。确认前保持零外部调用、单主 Agent、零私有数据和零外部行动。选择本身不构成四类授权。

## 核心状态

```text
空状态
→ R-align
→ R-method
→ A
→（必要且获授权时）Evidence Gate / Participation Gate
→ B
→ 反馈 / 结束 / 新一轮 R
```

Gate 是条件能力，不是固定第四阶段。某项 Gate 不必要、不可用、未授权、被拒绝或失败时，基于已有信息继续进入条件化 B，不把用户留在等待状态。

### R-align

只收敛：

- 希望得到或保护的真实结果；
- 当前真正要决定什么；
- 是否存在会改变决定的真实排他约束。

可并存目的先合并，不默认排序。目的未清时不调研、不委派，也不让 Agent 代答用户价值。

### R-method

目的和当前决定足够清楚后，系统内部筛选 0～3 个有独特增量的方法。基本分析始终包含，不作为候选。

每个方法候选都必须包含：

- 稳定 ID；
- 正式名称；
- 当前议题中的具体价值；
- 是否为系统推荐。

`推荐` 不等于确认。只有用户本轮实际提交的选择或明确文字，才形成唯一最终组合。加入、取消、替换与纠正仍停留在 R-method；未确认或已取消的方法不得暗中执行。

### A

综合已确认方法，只索取一个用户掌握的决定敏感答案。它必须只有一个答案槽；开放答案不预造选项，真实有限且互斥的答案才使用单选。

问后停止并等待，不替用户回答。R 与 A 不调用外部能力；A 的用户答案回来后，才判断是否需要 Gate。

### Evidence Gate

仅在关键未知是会改变决定的外部可验证事实时进入。执行前说明决定、证据问题、范围、停止条件、来源要求、能力与数据边界，并取得对应授权。

执行结果必须有来源、日期、支持与反对证据、冲突与空白以及对判断的影响。能力失败或证据不足时保留未知并降级，不虚构已搜索或已验证。

### Participation Gate

仅在存在不重复、可验证、可停止的独立增量任务，或关键信息与权责属于真实参与者时进入。

默认单 Agent。多 Agent 启用前必须让用户看清具体任务、总数与额外数、数据边界、能力、相对成本与延迟及失败降级。真实价值、承诺、预算、决策权和专业责任优先路由给对应真人，不能由更多 Agent 投票替代。

### B

综合用户答案与已取得的有效证据，交付：

1. 一个明确但可调整的当前判断；
2. 推荐方向、关键依据、成立条件与反转条件；
3. 一个围绕同一核心假设的主现实证据闭环；
4. 可复制的决策快照；
5. 四项反馈入口。

主现实证据闭环可以包含必要的连续操作，但必须共享同一核心假设、资源边界、观察标准和复判点。不得把多个无关项目包装成一个实验。

四项反馈固定为：

- 方向符合我；
- 调整下一步；
- 不同意这个判断；
- 暂时先放一放。

反馈只表达用户对已完成内容的方向，不索取新的决策信息，也不授权工具、私有数据、委派或外部行动。自由文字与选择冲突时以文字为准。

## 核心意图

核心通过 `core/intents.schema.json` 表达意图，而不发出专有工具名：

- `request_contextual_checkpoint`
- `request_free_text`
- `request_selection`
- `present_method_recommendation`
- `request_method_selection`
- `present_decisive_question`
- `request_research_consent`
- `request_agent_consent`
- `request_private_data_consent`
- `request_external_action_consent`
- `delegate_analysis`
- `request_human_review`
- `present_judgment`
- `present_decision_snapshot`
- `persist_decision_snapshot`
- `request_feedback`

Adapter 可以合并相邻且语义兼容的呈现，但不得：

- 把上下文检查点选择当作方法确认、进入 Gate 或任一授权；
- 在用户选择继续后，对同一决定范围重复提醒；
- 把推荐当确认；
- 把打开控件或默认选中当提交；
- 把授权复用到不同类型或更大范围；
- 把 Markdown 线框描述为真实工具调用；
- 省略等待边界或自行回答。

## 能力协商

逐项记录当前会话能力，不根据宿主名称推断：

```text
interaction.free_text
interaction.select_one
interaction.select_many
search.public_web
search.private_corpus
tools.read
tools.write
agents.subagent
agents.parallel
humans.request_review
persistence.session
persistence.case
permissions.tool_call
permissions.private_data
permissions.external_action
fallback.text
```

每项同时记录：

- 可用性：`available / unavailable / unknown`；
- 就绪状态：`ready / requires_approval / requires_auth / failed`；
- provider、限制和证据来源。

`unknown` 不得当作可用。真实执行后用 `core/receipts.schema.json` 记录计划、实际状态、来源、权限使用、失败与降级，不保存隐藏思维链。

## 授权分离

四类授权互不继承：

1. `capability_call`：调用某项工具或能力；
2. `participation_delegation`：增加 Agent 或请求真人参与；
3. `private_data_access`：读取具体私有资源；
4. `external_action`：发送、发布、购买、删除或修改外部世界。

允许多 Agent不等于允许联网；允许联网不等于允许私有数据；任何一种都不等于允许外部行动。授权必须有具体范围和有效期；长期偏好或持久化必须由用户主动开启。

## 决策快照

B 默认在对话中输出符合 `core/decision-record.schema.json` 语义的可复制 Markdown。Markdown 是机器记录的自然语言显示投影，不是第二套 schema：Adapter 可以按用户语言本地化字段名，但不得改变 canonical key 的语义或丢失字段。默认不写文件、不上传、不保存账号偏好，也不保存隐藏思维链。

快照至少保留：议题、真实目的、本轮决定、判断、事实、推断、假设、未知、来源、反转信号、主现实实验、复判触发、参与与能力记录。事实、推断、假设和未知必须分别映射；显示层不得把 `assumptions` 与 `unknowns` 合并。若用户之后粘贴或明确授权读取快照，复判应区分判断错误、执行偏差、资源错配和条件变化。

## 完成与重新进入

- 用户接受判断或暂时放下：本轮结束；
- 用户要求调整下一步、不同意判断、提供纠正或新事实：开启新一轮 R；
- Gate 被拒绝、不可用或失败：记录后继续 B；
- 紧急危险：退出本流程，优先给即时保护指引；
- 已决定、低风险、规格清楚且可撤回的执行：本 Skill 不应阻塞。

## 运行事实不变量

本协议、Schema、静态 fixture 和单元测试定义并机械校验语义，不自行证明任何宿主能力存在或任何能力调用已经发生。

运行时必须保持：

- 能力来自当前会话的逐项观测，不从 Adapter、宿主名称或产品说明推定；
- `unknown`、不可用、未授权、被拒绝或失败的能力不得使用或写成完成；
- 未发生调用不得生成 `completed` receipt；
- 实际选择、搜索、Agent、真人参与、持久化和外部行动只由对应 trace、consent 与 receipt 建立；
- 能力不存在或失败时使用纯文本基线和条件化 B，且保留未知与降级记录。
