# 安装指南

[English](installation.en.md)

本文档只说明如何安装和核验文件，不是第二份行为、安全或兼容性合同。行为与安全以 [`REQUIREMENTS.md`](../REQUIREMENTS.md) 和 [`SECURITY.md`](../SECURITY.md) 为准；runtime 状态见[兼容性与证据说明](compatibility-and-evidence.md)及机器事实源。

当前 `main` 上的稳定源码合同和最新真实公开发布均为 v0.4.0。下面的固定 tag、下载归档和校验和共同标识这一不可变发布；runtime 兼容状态仍按实际证据单独声明。

## 推荐方式

打开你正在使用的 Agent（Claude Code、Codex、Cursor、OpenClaw、Hermes Agent、CodeBuddy、WorkBuddy、Gemini CLI、OpenCode 等），告诉它：

```text
帮我安装这个 Skill：https://github.com/zemu2718/think-it-through-skill
```

Agent 会根据当前宿主的能力、权限和 Skill 目录约定尝试完成安装；需要联网或写入文件时，仍应按宿主机制取得你的授权。能否自动完成取决于当前宿主，列出这些 Agent 不表示它们都已经通过真实 runtime 验证。

## 备用方式

### 固定版本通用安装器

发布的 `.skill` 是 ZIP 兼容归档，只包含 manifest 声明的运行时文件。固定版本的 `skills` CLI 可以先交互选择安装目标：

```bash
npx -y skills@1.5.23 add \
  https://github.com/zemu2718/think-it-through-skill/releases/download/v0.4.0/think-it-through.skill
```

如果要把复制式、用户级安装写入该安装器版本认识的全部目标：

```bash
npx -y skills@1.5.23 add \
  https://github.com/zemu2718/think-it-through-skill/releases/download/v0.4.0/think-it-through.skill \
  --agent '*' \
  --global \
  --copy \
  --yes
```

`--agent '*'` 只表示 `skills@1.5.23` 认识的全部目标映射；不表示所有 AI 客户端都在其中，也不表示这些客户端已经通过真实 runtime 验证。需要交互选择时省略该参数；只装一个目标时，把 `'*'` 换成准确 target。

### Claude Code 的 GitHub CLI

安装 [GitHub CLI 2.98.0 或更高版本](https://cli.github.com/)后，可以安装到 Claude Code 的用户目录：

```bash
gh skill install \
  zemu2718/think-it-through-skill \
  think-it-through@v0.4.0 \
  --agent claude-code \
  --scope user
```

如果当前 Claude Code 会话启动时还没有顶层 Skill 目录，请在安装后重启 Claude Code。

### 手动兜底

如果两个安装器都不支持你的宿主，请按该宿主的 Agent Skills 目录约定复制 Skill。Claude Code 的命令如下：

```bash
git clone --depth 1 --branch v0.4.0 https://github.com/zemu2718/think-it-through-skill.git
cd think-it-through-skill
git rev-parse HEAD
test ! -e ~/.claude/skills/think-it-through
mkdir -p ~/.claude/skills
cp -R skills/think-it-through ~/.claude/skills/
```

非覆盖检查会在旧副本已存在时停止。不要混合两个版本；请先检查，再自行重命名或删除旧副本后重新安装。

## 安装后

当前可靠入口是在 Claude Code 中显式调用：

```text
/think-it-through
```

安装前可以使用 Release 同时发布的 [`SHA256SUMS`](https://github.com/zemu2718/think-it-through-skill/releases/download/v0.4.0/SHA256SUMS) 核对下载归档；手动安装时用 `git rev-parse HEAD` 记录准确源码 revision。

## 安装能证明什么

无论使用哪种方式，安装都只说明文件已经进入目标目录，不能证明某个 runtime/version 已经加载、遵循 Skill 或支持原生能力。完整层级、当前状态与证据来源见[兼容性与证据说明](compatibility-and-evidence.md)。
