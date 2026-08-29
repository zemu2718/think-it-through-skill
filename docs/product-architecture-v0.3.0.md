# 想清楚 v0.3.0 产品架构说明

> 状态：未发布候选的非规范性架构说明。正式行为、安全和验收合同以 [`REQUIREMENTS.md`](../REQUIREMENTS.md) 为准。

## 为什么需要 v0.3.0

v0.2.0 已经把决策语义从具体宿主中分离出来，但“开放格式”“安装器能复制文件”“runtime 实际加载”“行为真的通过”仍容易被一句“兼容”混在一起。v0.3.0 不重写决策流程，而是为可移植性增加可审计的证据边界。

借鉴成熟开源 Skill 的是低摩擦安装、自包含目录、纯文本兜底和明确失败模式；不照搬静默联网、自更新、写本地状态、超长单文件或把安装路径覆盖宣传成大量 runtime 已验证。没有复制 Nuwa 的代码或文字。

## 架构

```text
开放 Agent Skills 目录与 frontmatter
└── Portable Decision Core
    ├── text adapter（一等跨宿主基线）
    ├── agent-skills adapter（共同发现与能力边界）
    ├── claude-code / chatgpt adapter（已有具体映射）
    └── 条件能力：控件、搜索、Agent、数据、持久化、外部行动
```

`skills/think-it-through/` 仍是唯一维护源。运行时 `.skill` 只包含 `distribution/package-manifest.json` 列出的文件；`evals/`、compatibility evidence、benchmark 和本地配置不进入归档。

## 六层兼容模型

| 层级 | 问题 | 证据 |
| --- | --- | --- |
| L0 | 格式是否符合固定 Agent Skills 规范？ | 固定 revision 的静态参考校验 |
| L1 | 固定安装器能否发现 Skill？ | 隔离 local harness |
| L2 | 能否把精确文件安装到目标目录？ | 隔离安装与逐字节比较 |
| L3 | 指定 runtime/version 是否实际加载或激活？ | real-runtime trace |
| L4 | 纯文本 R/A/B 是否真实走通？ | real-runtime transcript + 当前 grader |
| L5 | 某项原生能力是否真实可用？ | 对应 trace、consent 与 receipt |

每一层只回答一个问题。L0 不证明 L1，L2 不证明 L3，L4 不证明任意 L5 能力。安装器维护的 target 数是路径映射范围，不是 runtime 认证数量。

## 机器数据与证据提升

`compatibility/profile.json` 固定层级、证据类型、工具版本和 cases；`runtime-support.json` 是可公开审计的状态投影；schema 与 validator 负责状态、版本和 evidence 引用的一致性。

状态使用 `passed / failed / not_run / blocked / unsupported`。证据区分 `static / synthetic / local_harness / real_runtime`。L3～L5 只接受绑定确切 runtime version 的 real-runtime 证据。普通 CI 不自动修改矩阵，手动 runtime workflow 也只生成候选 artifact；维护者脱敏、检查并批准后才提升状态。

## 普通 CI 与真实 runtime 隔离

普通 CI 可以安全完成：

- Python 合同、schema、fixture 和分发校验；
- 固定 Agent Skills revision 的 L0 检查；
- Node 22.20+ 与固定 `skills` CLI 的 L1/L2 archive 安装 smoke。

普通 CI 不读取模型 provider secret，不调用真实模型，也不把日志当作 L3～L5 evidence。

Claude Code / Codex smoke 是独立、手动、需授权的路径。它使用临时 HOME、只读工具边界与各 runtime 的显式 Skill 激活语法，只把脱敏后的用户输入、最终回答、非内容 trace 摘要、grader report、candidate evidence 和 SHA 保存为短期 artifact；原始 provider 输出不会持久化。workflow 只给当前 runtime 注入对应 provider secret，不会自动 commit 或修改公开声明。

执行前必须明确 provider、发送给 provider 的测试议题、最多四轮、预算或计费边界、失败即停止条件，以及不执行搜索、额外 Agent、私有数据、持久化和外部行动的降级范围；一次授权只覆盖该次 runtime smoke。

## 发布边界

当前源码可以准备 v0.3.0 candidate，但稳定安装命令只能指向真实存在且已核验的 Release asset。正式发布需要单独复核 candidate SHA、创建 tag/Release、上传完全相同的 bytes 并验证公开 URL。本轮架构改造不包含这些外向动作。
