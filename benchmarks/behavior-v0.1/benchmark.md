# Behavior Benchmark: think-it-through

**Date**: 2026-08-27T06:47:08Z
**Scope**: 3 paired, three-turn scenarios; one run per scenario and configuration

| Metric | With Skill | Without Skill | Delta |
| --- | ---: | ---: | ---: |
| Contract assertion pass rate | 100.0% | 57.4% | +0.43 |
| Semantic rubric score | 98.3% | 38.3% | +0.60 |
| Runs passing the full semantic gate | 3/3 | 0/3 | — |

## Limitations

- 每个场景、每种配置仅运行一次；结果用于合同回归，不表示总体能力或统计显著性。
- 运行模型名称来自会话运行时报告，未通过独立 API 元数据核验；严格独立 baseline 未读取仓库、Skill、评测定义或既有 transcript。
- 合同断言由确定性检查和保守场景检查组成；20 分语义 rubric 由主评审逐维度复核，并绑定 transcript SHA-256。
- 完整语义门槛要求无严重失败、总分至少 18/20，且问题质量、B 判断、用户控制与安全均为 2 分。
- 运行时未为所有运行暴露可比 token；with_skill 的分段 wall-clock 也不可可靠测量，因此不比较时间或 token。
- 无 Skill 基线也常能给出有用建议；此 benchmark 只检验 R→A→B 等明确产品合同及对应 rubric，不是笼统回答质量排名。
