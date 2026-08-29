# Contributing to Think It Through

Thank you for helping people make consequential decisions with more clarity and control.

[简体中文](#简体中文)

## What makes a useful contribution

The most valuable changes are concrete and testable:

- a realistic decision scenario that exposes a state-contract failure;
- a trigger positive or close negative that improves discovery without hijacking unrelated work;
- a simpler instruction that preserves R-align → R-method → A → optional Gate → B behavior;
- a method-card routing test for applicability, non-applicability, or overlap;
- an accessibility, privacy, safety, or provenance correction;
- a reproducible packaging or validation fix.

Please do not add a framework, persona, method card, or tool integration merely to expand the feature list. It must change a real decision and pass the requirements in [`REQUIREMENTS.md`](REQUIREMENTS.md).

## Before opening a pull request

Use the document that matches your task:

| If you are changing | Read first |
| --- | --- |
| Product purpose, audience, or non-goals | [`PRODUCT.md`](PRODUCT.md) |
| Behavior, safety, or acceptance criteria | [`REQUIREMENTS.md`](REQUIREMENTS.md) |
| Runtime instructions | The relevant part of [`SKILL.md`](skills/think-it-through/SKILL.md) |
| Architecture rationale or future evidence work | [`docs/product-architecture-v0.2.0.md`](docs/product-architecture-v0.2.0.md) |

Then:

1. For behavior changes, add or update a fixture under `skills/think-it-through/evals/fixtures/`. Evidence, participation, human-review, persistence, and host changes must also update the relevant core schema, policy, or adapter.
2. For trigger changes, use `trigger-dev.json`. Do not inspect or tune against the frozen holdout for the same release.
3. Run:

   ```bash
   python3 -m unittest discover -s scripts -p 'test_*.py' -v
   python3 scripts/validate_repo.py
   ```

4. Keep English and Chinese README instructions synchronized when changing user-facing commands, compatibility, benchmarks, or security boundaries.
5. Describe what changed, why it changes a decision, and how it was verified.

## Third-party material

Do not paste or loosely paraphrase external methods without provenance. A proposed adaptation must include:

- repository URL and fixed commit;
- exact source file;
- license and copyright at that revision;
- independent decision value;
- neutralization and safety changes;
- applicability, non-applicability, and overlap tests.

Update both copies of `THIRD_PARTY_NOTICES.md` only when material is actually distributed. See [`docs/third-party-audit.md`](docs/third-party-audit.md).

## Scope and conduct

Be specific, evidence-minded, and respectful. Do not submit manipulative, deceptive, coercive, discriminatory, privacy-invasive, or persona-authority behavior. Avoid invented metrics, testimonials, users, compatibility claims, and benchmark results.

For a security issue, follow [`SECURITY.md`](SECURITY.md) instead of opening a public issue.

## License

By contributing, you agree that your contribution is licensed under the repository's [MIT License](LICENSE).

---

## 简体中文

感谢你帮助更多人在重要决定前想清楚。

### 什么样的贡献最有价值

优先提交具体、可测试的改进：

- 能暴露状态合同问题的真实决策场景；
- 能提升发现性又不误触无关任务的正向或近邻负向触发样本；
- 在保留 R-align → R-method → A → 可选 Gate → B 行为的前提下简化指令；
- 专项方法卡的适用、不适用或重叠路由测试；
- 可访问性、隐私、安全或来源追溯修正；
- 可复现的打包和校验修复。

不要只为扩大功能表而加入框架、人物、方法卡或工具集成。它必须能改变真实决策，并符合 [`REQUIREMENTS.md`](REQUIREMENTS.md)。

### 提交 Pull Request 前

先按修改类型选择文档，不必从头阅读全部规范：

| 如果你要修改 | 先读 |
| --- | --- |
| 产品目的、目标用户或非目标 | [`PRODUCT.md`](PRODUCT.md) |
| 行为、安全或验收标准 | [`REQUIREMENTS.md`](REQUIREMENTS.md) |
| 运行时指令 | [`SKILL.md`](skills/think-it-through/SKILL.md) 的相关部分 |
| 架构理由或后续实测路线 | [`docs/product-architecture-v0.2.0.md`](docs/product-architecture-v0.2.0.md) |

然后：

1. 行为修改应在 `skills/think-it-through/evals/fixtures/` 增加或更新夹具；证据、参与、真人评审、持久化或宿主行为变化还必须同步相应 core schema、policy 或 adapter。
2. 触发修改只使用 `trigger-dev.json`；同一版本不得读取最终 holdout 后继续调优。
3. 运行：

   ```bash
   python3 -m unittest discover -s scripts -p 'test_*.py' -v
   python3 scripts/validate_repo.py
   ```

4. 修改用户命令、兼容性、benchmark 或安全边界时，同步英文和中文 README。
5. 在 PR 中说明改了什么、为什么会改变决策，以及如何验证。

### 第三方材料

不得在缺少来源的情况下复制或宽泛改写外部方法。第三方改编必须提供仓库 URL、固定 commit、准确文件、该版本许可证与版权、独立价值、中性与安全修改，以及适用/不适用/重叠测试。

只有实际分发第三方材料时才同步更新两份 `THIRD_PARTY_NOTICES.md`。详见 [`docs/third-party-audit.md`](docs/third-party-audit.md)。

### 范围与行为

保持具体、重证据和尊重。不得提交操控、欺骗、胁迫、歧视、侵犯隐私或以人物权威替代证据的行为；不得虚构指标、评价、用户、兼容性或 benchmark。

安全问题请按 [`SECURITY.md`](SECURITY.md) 私下报告，不要公开创建 Issue。
