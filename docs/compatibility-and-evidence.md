# 兼容性与证据说明

[English](compatibility-and-evidence.en.md)

本文档解释公开状态，不是第二份兼容或行为合同。机器事实源是 [`compatibility/profile.json`](../compatibility/profile.json) 与 [`compatibility/runtime-support.json`](../compatibility/runtime-support.json)；正式行为、安全与验收边界以 [`REQUIREMENTS.md`](../REQUIREMENTS.md) 和 [`SECURITY.md`](../SECURITY.md) 为准。

## 当前发布

当前源码与正式产品合同为 v0.4.1 发布候选，尚未创建同名公开对象。最新真实公开发布仍为 [`v0.4.0`](https://github.com/zemu2718/think-it-through-skill/releases/tag/v0.4.0)，由不可变 Git tag、GitHub Release、可下载的 [`think-it-through.skill`](https://github.com/zemu2718/think-it-through-skill/releases/download/v0.4.0/think-it-through.skill) 与 [`SHA256SUMS`](https://github.com/zemu2718/think-it-through-skill/releases/download/v0.4.0/SHA256SUMS) 共同建立；v0.3.0 继续作为历史发布保留。

发布状态表示产品合同和确定性准入链已经确立，不代表所有客户端均已认证，也不会把未运行的兼容层级自动改为通过。

## 如何理解 L0～L5

“符合开放格式”“安装器能发现”“完成精确安装”“runtime 真实加载”“模型真实遵循”和“原生能力可用”是不同事实。

| 层级 | 含义 | 当前公开状态 |
| --- | --- | --- |
| L0 | 格式校验 | 公开 runtime 矩阵为 `not_run` |
| L1 | 安装器发现 | `not_run` |
| L2 | 精确安装 | `not_run` |
| L3 | 真实 runtime 加载 | `not_run` |
| L4 | 真实纯文本行为 | `not_run` |
| L5 | 真实原生能力 | `not_run` |

层级、允许的证据类型与提升规则由 [`compatibility/profile.json`](../compatibility/profile.json) 定义；逐 runtime 状态由 [`compatibility/runtime-support.json`](../compatibility/runtime-support.json) 记录，并分别受 [`runtime-support.schema.json`](../compatibility/runtime-support.schema.json) 与 [`evidence.schema.json`](../compatibility/evidence.schema.json) 约束。

## 安装目标不等于 runtime 验证

v0.4.1 当前源码为能够加载 Agent Skills 目录并遵循文本指令的宿主定义可移植纯文本基线。仓库维护 Claude Code、Codex、Cursor、Gemini CLI、Hermes Agent、OpenClaw、OpenCode 与 CodeBuddy / WorkBuddy 八个安装器目标映射；未列出的兼容宿主也可以按自身 Skill 目录约定使用同一文本合同。

映射、成功复制文件或可移植合同都不等于已验证 runtime。静态 CI、schema、fixtures、评分器和图示可以证明合同已经定义，不能证明真实模型运行、自然语言自动发现或宿主原生体验。

## 自动发现与上下文检查点

自动发现目前不是可靠入口：冻结 v0.1 holdout 的总结果是 **9/16——正例只有 1/8 触发，负例 8/8 保持不触发**。完整证据与限制见 [`benchmarks/trigger-v0.1/`](../benchmarks/trigger-v0.1/README.md)。历史 [`v0.1 行为证据`](../benchmarks/behavior-v0.1/README.md)只有三个固定场景、每个配置一次运行，不能证明 v0.2.0、v0.3.0、v0.4.0 或 v0.4.1 行为。

v0.4.1 正式合同只在 Skill 已经加载、当前没有正式流程，并且对话跨入立项、选方向、重大投入、继续加码或结果复判时，定义一个轻量上下文检查点。真实多轮状态仍为 `not_run`；合同不能证明自然语言自动发现、自动加载或对话中途可靠唤起。当前可靠入口仍是 Claude Code 中显式 `/think-it-through`。

## 反馈如何成为证据

公开、可复现的观察请使用[安装与 runtime 反馈表单](https://github.com/zemu2718/think-it-through-skill/issues/new?template=install-or-runtime-feedback.yml)。请附准确 Release tag 或 `git rev-parse HEAD` 得到的源码 commit、runtime 名称与版本、操作系统、安装方式与目标目录、最小复现步骤，以及预期和实际结果；提交前删除 API key、token、私有对话、私人文件内容和个人路径。

普通报告只是复现和优化线索。只有绑定准确源码 revision 与 runtime 版本、按需完成复现、脱敏、审阅并形成 approved evidence 后，才能更新 [`compatibility/runtime-support.json`](../compatibility/runtime-support.json)。安全漏洞请按 [`SECURITY.md`](../SECURITY.md) 私下报告。

## 机器事实来源

- 兼容层级与证据政策：[`compatibility/profile.json`](../compatibility/profile.json)
- 当前 runtime 状态：[`compatibility/runtime-support.json`](../compatibility/runtime-support.json)
- 状态与证据 schema：[`runtime-support.schema.json`](../compatibility/runtime-support.schema.json)、[`evidence.schema.json`](../compatibility/evidence.schema.json)
- 冻结自动发现证据：[`benchmarks/trigger-v0.1/`](../benchmarks/trigger-v0.1/README.md)
- 冻结历史行为证据：[`benchmarks/behavior-v0.1/`](../benchmarks/behavior-v0.1/README.md)
- 正式行为、安全与验收合同：[`REQUIREMENTS.md`](../REQUIREMENTS.md)
