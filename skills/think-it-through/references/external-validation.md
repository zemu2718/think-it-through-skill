# 授权、能力与回执

本文件是 v0.2.0 的横向授权总合同，只定义所有 Gate 和宿主共同遵守的授权、能力状态、执行回执与持久化边界。

具体路由规则分别见：

- [Evidence Policy](../policies/evidence-routing.md)：未知应由谁回答、何时值得调研、范围与停止条件；
- [Participation Policy](../policies/participation-routing.md)：何时增加 Agent 或真人参与、数量与综合纪律；
- [consent schema](../core/consent.schema.json)：授权记录结构；
- [receipt schema](../core/receipts.schema.json)：执行回执结构。

## 时序边界

```text
R-align → R-method → A
→ Gate-routing
→ 必要时提出一份有界方案
→ 用户明确授权
→ 执行并生成回执
→ B
```

R 和 A 不调用、索取或建议外部能力。Gate 提案不是执行授权；只有用户对当前方案的明确选择或文字同意才形成授权。拒绝、撤销、能力不可用或执行失败都不能阻塞 B。

## 四类授权

| 授权 | 允许 | 不自动允许 |
| --- | --- | --- |
| `capability_call` 能力调用 | 调用明确工具、Skill、搜索或服务 | 增加 Agent、读取私有数据或改变外部世界 |
| `participation_delegation` 参与 / 委派 | 增加明确 Agent，或请求真人参与 | 联网、私有数据、发送邀请或联系他人 |
| `private_data_access` 私有数据访问 | 读取明确资源和最小数据范围 | 其他资源、写入或外部行动 |
| `external_action` 外部行动 | 向明确目标发送、发布、购买、删除、联系或修改 | 更广的工具、数据或后续行动 |

方法确认、A 的回答、B 的反馈、附注、普通后续消息、宿主 `Other`、历史偏好、Agent 上限或工具可用性都不构成上述授权。

## 最小授权记录

每次授权至少记录：

```text
consent_id
类型
用途与要改变的决定
具体 provider / 工具 / 参与者 / 目标
任务或数据范围
读 / 写 / 发送性质
成本与延迟
失败降级
有效范围
用户选择：granted / denied / unknown
```

授权必须具体、最小、可撤销。新 provider、新资源、新 Agent 任务或新外部目标不得借用旧授权。用户拒绝、收窄或撤销时立即遵守，不得换工具绕过。

## 能力协商

每项能力分别记录：

| 维度 | 合法状态 |
| --- | --- |
| 可用性 | `available / unavailable / unknown` |
| 就绪度 | `ready / requires_approval / requires_auth / failed` |

`unknown` 不得当作可用。产品或官方文档说明支持某能力，不等于当前会话已经启用、认证或获授权。

## 私有数据与外部行动

私有数据访问遵守四条最小原则：

- 只请求当前判断和已授权任务所需的资源、字段或目录；
- 先说明 provider、范围、用途和哪些参与者会收到；
- 未授权或读取失败时保留未知，不补造结果；
- 回执说明实际访问与未访问的范围。

外部行动默认先生成草稿、预览或可转发材料。只有取得本次 `external_action` 授权后才执行；高风险或难撤回行动还要遵守宿主门禁。允许生成草稿不等于允许发送。

## 执行回执

真实调用完成、部分完成、失败、拒绝或取消后，记录可审计事实：

```text
operation_id
consent_id
provider 与能力
计划范围与实际范围
started / completed / partial / failed / declined / cancelled / unavailable
来源或参与者
使用的数据和权限
失败、未完成工作与降级
```

回执不保存隐藏思维链。未调用时不得生成完成记录；部分成功不得写成全部完成。

## 降级

能力不可用、状态未知、需要认证、用户不授权或执行失败时：

1. 保留已有事实和未知；
2. 说明缺口如何限制判断；
3. 降低承诺或提高可逆性；
4. 基于已有信息进入 B；
5. 不循环索权、不重复调用、不编造结果。

## 持久化

默认只在对话中生成可复制的决策快照：

```json
{
  "mode": "conversation_only",
  "authorized": false
}
```

写入文件或远端必须有具体 destination 和 consent ID；改变外部系统状态时还要满足相应外部行动授权。不得持久化隐藏思维链。用户应知道保存了什么、保存到哪里，并能修改或删除。

## B 反馈边界

B 的四项反馈只路由已经交付的内容。它不执行实验，也不授权能力、参与 / 委派、私有数据、持久化或外部行动；新的执行需求必须重新进入对应 Gate 或宿主确认。
