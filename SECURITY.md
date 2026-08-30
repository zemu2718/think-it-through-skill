# Security Policy

[简体中文](#简体中文)

## Supported versions

Security fixes are applied to the maintained source on the default branch. Older source snapshots and previously generated `.skill` packages may not receive separate maintenance; the README separately records whether a public Git tag, GitHub Release, or downloadable asset exists.

## Reporting a vulnerability

Do not open a public issue if a vulnerability could expose private conversation data, cause unintended external actions, weaken authorization boundaries, or enable unsafe behavior.

Use this repository's **Security** tab → **Report a vulnerability**:

<https://github.com/zemu2718/think-it-through-skill/security/advisories/new>

Include, when possible:

- affected file and revision;
- minimal reproducible prompt or package input;
- observed behavior and expected safe behavior;
- impact, including private data or external actions;
- suggested mitigation, without publishing exploitable details elsewhere.

If private vulnerability reporting is unavailable, open a public issue that asks only for a private contact channel. Do not include exploit details or sensitive data.

## Response expectations

A report will be acknowledged when the maintainer next reviews repository security notifications. No fixed response or remediation window is guaranteed. Confirmed issues will be scoped, fixed where practical, and disclosed after a safe update is available.

## Security model

Think It Through is an instruction-only Agent Skill. Its release package contains Markdown, YAML, JSON Schema, licenses, and notices; it does not contain executable scripts. By default, it needs no network access, reads no private files, uses only the current main agent, keeps the decision snapshot in the conversation, and does not change the external world.

Four permissions remain independent:

| Permission | Covers | Does not grant |
| --- | --- | --- |
| Capability call | Search, read, write, or another tool call | Delegation, private data, or external action |
| Participation / delegation | Additional agents or a human request | Network, private data, or sending the request |
| Private data access | A specific private resource and scope | Unrelated resources or external action |
| External action | Sending, publishing, purchasing, deleting, or modifying | Broader capability or data access |

Method confirmation, an agent-count limit, feedback, or an earlier request does not grant any of these permissions. A real call must produce an honest receipt; refusal, failure, and unfinished work must not be presented as completed.

## User safety and privacy

- Review a `.skill` archive before installing it from an untrusted mirror.
- Do not paste secrets or unnecessary personal data into a decision conversation.
- Treat judgments as decision support, not medical, legal, investment, or emergency professional advice.
- In immediate danger, follow local emergency guidance instead of starting or extending the decision flow.
- The Skill must not provide manipulation, deception, tracking, coercion, intimidation, or discriminatory strategies.

---

## 简体中文

### 支持版本

安全修复应用于默认分支上持续维护的源码。旧源码快照和此前生成的 `.skill` 包不保证单独维护；是否存在公开 Git tag、GitHub Release 或可下载 asset，以 README 的当前状态说明为准。

### 报告漏洞

如果问题可能泄漏私有对话数据、造成未授权外部动作、削弱授权边界或引发不安全行为，请不要公开提交漏洞细节。

请通过本仓库 **Security** → **Report a vulnerability** 私下报告：

<https://github.com/zemu2718/think-it-through-skill/security/advisories/new>

尽量包含：

- 受影响文件和版本；
- 最小复现提示或包输入；
- 实际行为与预期安全行为；
- 是否涉及私有数据或外部动作；
- 可行的缓解建议，但不要在其他公开渠道披露可利用细节。

如果 GitHub 私有漏洞报告不可用，可以公开创建一个只请求私下联系方式的 Issue；不要附漏洞细节或敏感数据。

### 响应预期

维护者下次查看仓库安全通知时会确认报告。不承诺固定响应或修复时限。确认后的问题会被界定范围，在可行时修复，并在安全更新可用后披露。

### 安全模型

想清楚是纯指令型 Agent Skill。发布包包含 Markdown、YAML、JSON Schema、许可证和第三方通知，不包含可执行脚本。默认情况下，它无需联网、不读取私有文件、只使用当前主 Agent、只在对话中保留决策快照，也不改变外部世界。

四类授权彼此独立：

| 授权 | 涵盖 | 不会自动授予 |
| --- | --- | --- |
| 能力调用 | 搜索、读取、写入或其他工具调用 | 委派、私有数据或外部行动 |
| 参与 / 委派 | 增加 Agent 或请求真人参与 | 联网、私有数据或发送请求 |
| 私有数据访问 | 读取明确资源和范围 | 其他资源或外部行动 |
| 外部行动 | 发送、发布、购买、删除或修改 | 更广的能力或数据访问 |

方法确认、Agent 数量上限、反馈或先前请求都不构成上述授权。真实调用必须形成诚实回执；拒绝、失败和未完成工作不得写成已完成。

### 用户安全与隐私

- 从不可信镜像获取 `.skill` 时，安装前检查归档内容。
- 不要在决策对话中粘贴密钥或不必要的个人数据。
- 输出只用于决策支持，不替代医疗、法律、投资或紧急专业帮助。
- 出现即时危险时，优先遵循当地紧急指引，不开始或延长决策流程。
- Skill 不得提供操控、欺骗、跟踪、胁迫、恐吓或歧视策略。
