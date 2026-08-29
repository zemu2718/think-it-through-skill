# Claude Code Adapter

## 定位

本 Adapter 把 Portable Decision Core 映射到当前 Claude Code 会话的真实能力。它描述适配合同，不代表任意安装、版本或会话都具备同一工具集合；每次运行仍需能力协商。

当前可靠加载方式是显式 `/think-it-through`。冻结自动发现 holdout 仍为正例 1/8、负例 8/8，不能把自然语言自动加载描述为已经通过。

## 能力协商

按当前会话实际检测：

- 原生单选 / 多选：`AskUserQuestion` 或等价工具；
- 公开调研：真实存在且可用的 WebSearch、WebFetch 或 MCP provider；
- 私有资料：用户指定且当前已认证、已授权的 provider；
- 子 Agent：真实可用的 Agent 能力；
- 并行编排：真实可用且已获用户明确同意的 Workflow 或等价能力；
- 文件读写与持久化：当前工具、权限和具体目标；
- 文本降级：普通消息。

官方或产品层支持不等于当前会话 `available / ready`。工具未加载、权限未知、需要认证或调用失败时必须如实记录。

## 原生选择

宿主提供 `AskUserQuestion` 或等价工具时：

- `compatible-set` 使用实际原生多选；
- `finite-mutually-exclusive` 使用实际原生单选；
- `open` 直接自由回答，不调用选择工具；
- B 完整交付判断、实验和快照后，实际调用四项原生单选。

Markdown 不能冒充工具调用。只有控件不可用、调用失败或被用户拒绝时才文本降级，且失败 / 拒绝要保留工具调用 trace。

产品不自建 `Other`。宿主自由输入与产品选择平权，冲突时自由文字优先。宿主 `Other` 是替代式自由输入，不是“选择 + 独立附注”。

B 只有实际观察到与选择并存的独立附注时才使用 `native-note`；否则原生单选使用 `follow-up-message`，文本降级使用 `inline-text`。

## 方法选项

支持 option description 的交互表面，把正式名称、推荐状态和当前价值放进同一个原生多选项。推荐标记进入 label 或宿主支持的等价字段，当前价值进入 description。

如果当前工具不能可靠显示 description，就使用控件前紧邻说明或纯文本 Adapter，但仍只做一次最终组合提交。不得完整解释一遍后在控件中只重复名称，也不得因工具限制隐藏推荐状态或用户调整语义。

## Evidence Gate

只有满足 `policies/evidence-routing.md` 且用户同意本次范围时调用公开调研工具。每个 provider 的授权、认证、来源质量和失败互不替代。

调用后记录实际来源、日期、范围和状态。网络搜索不继承私有数据访问；只读搜索不继承写入、发送或其他外部行动。失败后按证据策略降级进入 B。

## Participation Gate

默认当前主 Agent。使用 Agent 前：

1. 识别不重复的独立任务；
2. 计算包含主 Agent 的总参与上限；
3. 单屏展示具体任务、总数 / 额外数、数据、能力、成本与延迟影响和降级；
4. 取得 `participation_delegation` 授权；
5. 按任务裁剪上下文，并禁止额外 Agent 递归委派；
6. 主 Agent 统一综合并给实际数量回执。

复杂 Workflow 或大规模编排需要用户明确选择，不能由一般 Agent consent、历史偏好或“在上限内自动”推定。项目或用户设置的更严格 Agent 总额度必须同时遵守。

Claude Code 子 Agent 的隔离上下文、工具约束和并行能力不证明结论质量必然提高。不得以 Agent 数或一致意见替代来源和现实证据。

## 真人参与与外部行动

默认只生成可转发材料。向飞书、邮件、聊天、工单、社交平台或其他外部服务发送、发布、邀请或修改内容均需独立、具体、当次确认。一个服务的授权不能复用于另一个目标。

## 决策快照

默认在对话中输出可复制 Markdown。写入仓库、本地文件、记忆、云端或外部系统前确认具体路径、内容和有效范围。若未获得授权，`persistence.mode` 必须为 `conversation_only`。

## 执行回执与失败

每个实际能力调用按 `core/receipts.schema.json` 记录 provider、状态、范围、来源、Agent 计划 / 实际数量、私有数据和外部行动使用、失败及降级。

工具调用被拒绝后不原样重试；能力不可用时不声称已完成；部分 Agent 失败时保留有效材料并继续 B。

## 证据边界

此 Adapter、单元测试和 synthetic fixture 不能证明真实 Claude Code 模型已遵守方法 option UI、Evidence Gate、原生反馈 UI、独立附注或多 Agent 合同。没有真实工具 trace 和运行记录时，这些状态仍为 `not_run`。
