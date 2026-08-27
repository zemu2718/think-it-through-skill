# Behavior benchmark v0.1

这个目录是可公开复核的固定评测快照。它包含 3 个三轮场景、每种配置各 1 次运行的原始 transcript、合同评分和 20 分语义 rubric。

- `with_skill`：加载 `think-it-through` 后的输出。
- `without_skill`：严格独立基线；生成时未读取仓库、Skill、评测定义或既有 transcript。
- `benchmark.md`：聚合结果和限制。
- `benchmark.json`：与 Skill Creator 静态 viewer 兼容的完整数据。
- `semantic-rubric.json`：逐运行语义评分汇总。

这不是总体能力排名，也不表示统计显著性。每个场景和配置只有一次运行；模型名称来自会话运行时报告；不可比较的时间与 token 未被纳入结果。
