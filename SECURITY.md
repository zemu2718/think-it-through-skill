# Security Policy

[简体中文](#简体中文)

## Supported versions

Security fixes are applied to the latest release on the default branch. Pre-release branches and old generated `.skill` packages may not receive separate fixes.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability that could expose private conversation data, cause unintended external actions, weaken authorization boundaries, or enable unsafe behavior.

Use GitHub's **Security** tab → **Report a vulnerability** for this repository:

<https://github.com/zemu2718/think-it-through-skill/security/advisories/new>

Include, when possible:

- the affected file and revision;
- a minimal reproducible prompt or package input;
- observed behavior and expected safe behavior;
- impact, including whether private data or an external action is involved;
- any suggested mitigation, without publishing exploitable details elsewhere.

If private vulnerability reporting is unavailable, open a public issue containing only a request for a private contact channel—do not include exploit details or sensitive data.

## Response expectations

A report will be acknowledged when the maintainer next reviews repository security notifications. There is no guaranteed response or remediation window in v0.1. Confirmed issues will be scoped, fixed where practical, and disclosed after a safe update is available.

## Security model

Think It Through is an instruction-only Agent Skill. It bundles Markdown, YAML, JSON fixtures, licenses, and examples; the release package should not include executable scripts. By default it neither needs network access nor reads private files.

The Skill keeps three permissions independent:

1. capability or tool invocation;
2. private data access;
3. external action such as sending, publishing, purchasing, deleting, or modifying.

Permission in one category does not grant another. Analysis-method confirmation is not tool permission, and an initial request to perform an important action is not automatically reused as post-analysis authorization.

## User safety and privacy

- Review the contents of a `.skill` archive before installing it when obtained from an untrusted mirror.
- Do not paste secrets or unnecessary personal data into a decision conversation.
- Treat generated judgments as decision support, not medical, legal, investment, or emergency professional advice.
- In immediate danger, follow local emergency guidance rather than the R → A → B flow.
- The Skill must not provide manipulation, deception, tracking, coercion, or intimidation strategies.

---

## 简体中文

### 支持版本

安全修复应用于默认分支上的最新版本。预发布分支和旧 `.skill` 包不保证单独维护。

### 报告漏洞

如果问题可能泄漏私有对话数据、造成未授权外部动作、削弱授权边界或引发不安全行为，请不要公开创建包含细节的 Issue。

请通过本仓库 **Security** → **Report a vulnerability** 私下报告：

<https://github.com/zemu2718/think-it-through-skill/security/advisories/new>

尽量包含受影响文件和版本、最小复现提示或包输入、实际与预期行为、影响范围，以及不在公开渠道披露利用细节的缓解建议。

若 GitHub 私有漏洞报告不可用，可以公开创建一个只请求私下联系方式的 Issue，但不要附漏洞细节或敏感数据。

### 响应预期

维护者下次查看仓库安全通知时会确认报告。v0.1 暂不承诺固定响应或修复时限。确认后的问题会被界定范围，在可行时修复，并在安全更新可用后披露。

### 安全模型

想清楚是纯指令型 Agent Skill。发布包应只包含 Markdown、YAML、许可证和示例，不包含可执行脚本；默认无需联网，也不会读取私有文件。

它把三类权限彼此分离：能力调用、私有数据访问、发送/发布/购买/删除/修改等外部行动。任何一种授权都不继承另一种；方法确认不是工具授权，用户最初要求执行重要动作也不能自动复用为分析后的行动授权。

### 用户安全与隐私

- 从不可信镜像获取 `.skill` 时，安装前检查归档内容。
- 不要在决策对话中粘贴密钥或不必要的个人数据。
- 输出只用于决策支持，不替代医疗、法律、投资或紧急专业帮助。
- 出现即时危险时优先遵循当地紧急指引，不运行 R → A → B。
- Skill 不得提供操控、欺骗、跟踪、胁迫或恐吓策略。
