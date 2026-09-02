# 开放 Agent Skills Adapter

## 定位

本 Adapter 定义符合开放 Agent Skills 目录约定的共同映射，不为任何具体 runtime 颁发兼容认证。宿主能够发现或安装 Skill，只说明对应步骤已经发生；是否实际加载、是否保持完整纯文本行为、是否提供原生能力，必须分别由该 runtime 与版本的运行证据建立。

## 加载与引用

- Skill 根目录名与 frontmatter `name` 均为 `think-it-through`；
- 宿主加载 `SKILL.md` 后，按需读取其中引用的 `core/`、`policies/`、`adapters/` 和 `references/`，包括项目可行性议题使用的 `references/project-viability.md`；这些由分发 manifest 声明的只读 bundled resources 属于 Skill 加载，不构成用户工作区 `tools.read`、`private_data_access` 或独立 capability call；
- 相对路径始终从 Skill 根目录解析，不能依赖仓库根目录、当前工作目录或用户主目录；
- `evals/`、兼容证据和历史 benchmark 不属于运行时包，也不是执行协议所需输入；用户文件、项目工作区、账号资源与外部文件仍须按实际 provider、资源范围和授权处理。

宿主自己的显式调用语法、自动发现规则和扫描目录不属于 Portable Decision Core。只有特定 runtime/version 的真实 trace 能证明该 Skill 已被列出、加载或显式激活。

## Portable baseline

所有开放 Agent Skills 宿主至少回落到 [`text.md`](text.md)：

- 上下文检查点只在已加载 Skill 的重要承诺节点出现一次；显式调用和 active flow 跳过；
- 开放回答直接等待；
- 单选和多选使用普通编号，不伪造控件；
- 方法推荐、确认、A 的唯一问题、B 判断、主现实证据闭环、决策快照和四项反馈保持完整；
- 不可用的搜索、额外 Agent、真人协作和持久化诚实降级；
- 未执行的能力不生成虚假 trace 或 receipt。

纯文本保真不等于宿主已实际加载；加载也不等于真实多轮行为已经通过。

## 能力协商

runtime 名称、官方功能说明、安装目录、Skill 文件或 Adapter 文件存在，都不能把搜索、安装/执行、账号认证、真实试用、额外 Agent 或其他能力直接标为 `available / ready`。每个会话仍逐项观察并记录：

- 原生自由输入、单选和多选；
- 公开搜索、私有数据和文件读写；
- 额外 Agent 与并行编排；
- 真人参与、持久化和外部行动；
- provider、限制、就绪状态和证据来源。

未观察到的能力保持 `unknown` 或 `unavailable`，并使用纯文本路径。观察到能力后仍须按四类授权分别取得 consent，真实调用后才产生 receipt。

## 兼容声明边界

仓库级兼容数据将以下事实分开：

1. 格式符合开放规范；
2. 安装器能发现 Skill；
3. 安装器能复制精确文件集合；
4. 指定 runtime/version 实际加载或激活；
5. 该 runtime 中纯文本核心行为通过；
6. 某项原生能力真实通过。

前一项不能自动证明后一项。安装器维护的 target 数量不能转述为已经验证的 runtime 数量；静态 schema、fixture、单元测试或宿主文档也不能替代真实运行证据。
