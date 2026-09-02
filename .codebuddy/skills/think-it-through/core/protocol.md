# Portable Decision Core 协议

## 目的与边界

本文件定义 v0.4.1 的宿主无关决策语义。`SKILL.md` 负责入口和总流程，`policies/` 负责证据与参与路由，`adapters/` 负责把语义意图映射到当前宿主的真实能力。

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
→ Gate-routing
→（必要且获授权时）Evidence Gate / Participation Gate
→ Gate-routing
→ B
→ 反馈 / 结束 / 新一轮 R
```

Gate 是条件能力，不是固定第四阶段。每个 Gate 执行、部分执行、失败、被拒绝、取消或不可用后都回 Gate-routing；只有另一类尚未处理、仍决定敏感且有独特增量的 Gate 才继续，同一 Gate 不围绕同一未知重复执行。A 已获得回应后，跨方法、搜索和参与的新增分析只有在至少一个剩余未知仍预计改变正式判断状态、material 路径排序、承诺上限，或决定主现实证据闭环当前能否执行及其结果能否区分会导致不同判断的路径，而且下一步已获准或可按合同取得授权、能够执行、边际价值高于成本时才继续。只改善措辞、背景完整度、指标精度或报告观感不能支持扩展；否则保留未知并进入条件化 B。

用户只拒绝某项能力但仍要判断时，记录后进入条件化 B。用户明确要求停止整个流程、不再分析或不再给报告时，立即确认停止，不回 Gate-routing，也不输出完整 B。

### R-align

只收敛：

- 希望得到或保护的真实结果；
- 当前真正要决定什么；
- 是否存在会改变决定的真实排他约束；
- 产品、功能、自研或技术形态是否只是尚未验证的候选解法。

可并存目的先合并，不默认排序。目的未清时不调研、不委派，也不让 Agent 代答用户价值。

### R-method

目的和当前决定足够清楚后，系统内部筛选 0～3 个有独特增量的方法。基本分析始终包含，不作为候选。项目可行性是基础分析与 Gate 路由规则，不是方法卡，不改变七张专项卡或 0～3 项上限。零候选时自然说明只需基本分析，不发出方法选择 intent、不展示空菜单或要求确认，直接进入 A；有一个真实候选时继续使用可确认路径。

每个方法候选都必须包含：

- 稳定 ID；
- 正式名称；
- 当前议题中的具体价值；
- 是否为系统推荐。

`推荐` 不等于确认。只有用户本轮实际提交的选择或明确文字，才形成唯一最终组合。加入、取消、替换与纠正仍停留在 R-method；未确认或已取消的方法不得暗中执行。

### A

综合已确认方法，只索取一个用户掌握的决定敏感答案。它必须只有一个答案槽；开放答案不预造选项，真实有限且互斥的答案才使用单选。

问后停止并等待，不替用户回答。A 尚未获得回应且议题未变时继续等待，不能用分析停止规则跳过；用户实质改题时回 R。正常回答、不完整回答、“不知道”或拒绝回答都算 A 已获得回应，此后才进入 Gate-routing。R 与 A 不调用外部能力。

### Evidence Gate

仅在关键未知是会改变决定的外部可验证事实时进入。执行前说明决定、证据问题、范围、停止条件、来源要求、能力与数据边界、具体相对成本与延迟，并取得对应授权；grader-only record 必须用 exact-key `cost_and_latency_disclosure` 对象分别记录非空成本和延迟，并明确记录披露先于授权，价值高于成本的布尔结论不能替代该披露。

执行结果必须有来源、日期、支持与反对证据、冲突与空白以及对判断的影响。项目可行性事实按 outcome/problem-first、solution/implementation-second 发现候选，再按类型核验现实边界；公开资料只建立候选池，重大投入前尽可能以同一真实任务试用最强替代。能力失败、未发现、候选未核验、替代未试用或证据不足时保留未知并降级，不虚构已搜索、已验证或“替代不存在”。

### Participation Gate

仅在存在不重复、可验证、可停止的独立增量任务，或关键信息与权责属于真实参与者时进入。

默认单 Agent。多 Agent 启用前必须让用户看清具体任务、总数与额外数、数据边界、能力、相对成本与延迟及失败降级。项目可行性的独立反方仅在不重复、可验证、可停止且有明确增量时启用；只接收最小上下文，不接收主判断、偏好方案或完整 transcript。真实价值、承诺、预算、决策权和专业责任优先路由给对应真人，不能由更多 Agent 投票替代。grader-only `synthesis` 以 exact-key 结构分别记录实际完成任务、采用 / 搁置 / 未决材料、冲突处理、判断影响和主现实证据闭环影响；这只机械建立材料链，不把结构完整性冒充深层综合质量。

### B

综合用户答案与已取得的有效证据，交付：

1. 一个明确但可调整的当前判断；
2. 推荐方向、关键依据、成立条件与反转条件；
3. 一个围绕同一核心假设的主现实证据闭环；
4. 可复制的决策快照；
5. 四项反馈入口。

主现实证据闭环可以包含必要的连续操作，但必须共享同一核心假设、资源边界、观察标准和复判点。不得把多个无关项目包装成一个实验。

项目可行性议题在同一判断与快照中表达采用、组合/薄集成、有限验证、自研、暂停或停止，并给承诺上限、no-go、升级条件和复查触发。候选同时检查不新增、删除、简化、缩小或停掉已有部分，并复用现有路径语义。问题存在、问题强度、方案适配和替代生态分别判断；任何关键层未知或冲突，或搜索、来源、核验、最强替代试用、必要反方缺失或失败时，最多允许低成本、可撤回验证。

简单、单来源且无真实冲突的决定只需用短自然语言说明关键依据、成立边界、仍决定敏感的未知和反转条件，不输出“无冲突”“无搁置”等占位栏目。只有使用多个方法、来源或参与者，或存在 material 搁置项、真实冲突时，B 才显式去重事实链、定位冲突、说明采用/搁置/未决材料，并解释它们如何共同导出一个判断和主现实证据闭环。观点罗列、票数、角色权威、模型自评或 Agent 一致性不能代替综合，也不能仅凭自身成为外部事实或提高承诺上限。用户可见快照按复杂度使用紧凑或完整投影，但 canonical DecisionRecord 始终无损；`hold / pause / stop` 的实验 action 仍使用“不新增投入，仅观察明确反转信号”等非空自然表达。

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

允许多 Agent不等于允许联网；允许联网不等于允许私有数据；任何一种都不等于允许外部行动。执行 consent 只允许 `this_action / this_turn / this_session`，并必须有具体范围；保存的长期偏好只控制是否主动询问、默认协作方式或宿主设置，不能作为执行授权。新 provider、新资源、新 Agent 任务、新真人或新外部目标仍需当前、具体且范围匹配的授权。持久偏好必须由用户主动开启并可查看、修改和删除。

请求真人回答具体问题需要 `participation_delegation`；通过具体渠道向同一具体目标实际发送、邀请、预约或联系还需要独立 `external_action`。两项可同屏解释，但必须生成两份 consent；两份 consent、`authorized_send` 意图和实际 operation receipt 共同绑定同一问题、真人、渠道与行动，不能只共享任务 token。`draft_only` 不携带执行 consent，也不证明真人已参与。

## 决策快照

B 默认在对话中输出符合 `core/decision-record.schema.json` 语义的可复制 Markdown。Markdown 是机器记录的自然语言显示投影，不是第二套 schema：Adapter 可以按用户语言本地化字段名，但不得改变 canonical key 的语义或丢失字段。默认不写文件、不上传、不保存账号偏好，也不保存隐藏思维链。

快照至少保留：议题、真实目的、本轮决定、判断、事实、推断、假设、未知、来源、反转信号、主现实实验、复判触发、参与与能力记录。项目可行性的承诺上限、no-go、升级与复查继续映射这些现有语义，不新增项目专用 canonical key、状态或持久化模式。事实、推断、假设和未知必须分别映射；显示层不得把 `assumptions` 与 `unknowns` 合并。若用户之后粘贴或明确授权读取快照，复判应区分判断错误、执行偏差、资源错配和条件变化。

## Skill 加载资源

由 `distribution/package-manifest.json` 随 `.skill` 分发，并通过 `SKILL.md` 引用的只读 core、policy、adapter 和 reference 属于 Skill 加载资源。按需读取这些 bundled resources 不构成用户工作区 `tools.read`、`private_data_access` 或独立 capability call。用户文件、项目工作区、账号资源和外部文件仍按实际 provider、资源范围和授权处理。

## 完成与重新进入

- 用户接受判断或暂时放下：本轮结束；
- 只有“调整下一步”但没有补充：等待普通后续消息，不猜测变更；
- 只修改实验：直接修订主现实证据闭环并重新给紧凑 B，保留当前判断；
- 新事实：回 A 形成新的决定敏感未知；目的变化：回 R-align；不同意判断或确需更换分析角度：回 R-method；
- 目标用户、场景、定位、关键依赖或替代生态实质变化：旧项目可行性结论进入待复核，按变化类型回到合适位置；
- Gate 被拒绝、不可用或失败：记录后回 Gate-routing，只有另一类未处理且有独特增量的 Gate 才继续，否则进入 B；
- 用户明确终止整个流程：只确认停止，不继续路由或输出完整 B；
- 紧急危险：退出本流程，优先给即时保护指引；
- 已决定、低风险、规格清楚且可撤回的执行：本 Skill 不应阻塞。

## 运行事实不变量

本协议、Schema、静态 fixture 和单元测试定义并机械校验语义，不自行证明任何宿主能力存在或任何能力调用已经发生。

运行时必须保持：

- 能力来自当前会话的逐项观测，不从 Adapter、宿主名称或产品说明推定；
- `unknown`、不可用、未授权、被拒绝或失败的能力不得使用或写成完成；
- 未发生调用不得生成 `completed` receipt；
- 实际选择、搜索、Agent、真人参与、持久化和外部行动只由对应 trace、consent 与 receipt 建立；
- 能力不存在或失败时使用纯文本基线和条件化 B，且保留未知与降级记录；
- 未搜索、未授权、未发现、来源不足、候选未核验、替代未试用或反方失败不得作为扩大投入或正式自研的证据；
- receipt 只证明操作与返回材料发生；模型自评、方法输出、未核验 Agent 主张和模型一致性不得自行成为外部事实或提高承诺；
- A 获得回应后，分析不再预计改变判断状态、material 路径排序、承诺上限，或主现实证据闭环当前能否执行及其结果区分力时停止扩展，保留未知并给条件化 B；A 尚未获得回应不能用此规则跳过等待。
