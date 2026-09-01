<div align="center">

[English](README.en.md)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme-banner-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="assets/readme-banner-light.png">
  <img src="assets/readme-banner-light.png" alt="多层观察框架逐步对齐成一个清晰开口，并保留一个让判断可以再次修正的小轴点。" width="960">
</picture>

# 想清楚 · Think It Through

**AI 能把事情做得很快，但不能替你决定什么值得做。**

重要投入前，先把真正要做的决定想清楚，再行动。

[![MIT License](https://img.shields.io/github/license/zemu2718/think-it-through-skill?style=flat-square)](LICENSE) [![Latest Release](https://img.shields.io/github/v/release/zemu2718/think-it-through-skill?style=flat-square&label=release)](https://github.com/zemu2718/think-it-through-skill/releases/latest) [![Validate](https://github.com/zemu2718/think-it-through-skill/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/zemu2718/think-it-through-skill/actions/workflows/validate.yml?query=branch%3Amain)

[什么时候调用](#什么时候调用) · [如何工作](#它怎样帮你想清楚) · [安装](#安装与使用) · [默认安全](#默认安全与更多信息)

</div>

## 你会得到什么

- **一个综合判断：** 现在更适合推进、先验证，还是对已经开始的事情继续、调整、暂停或停止，并说明这个判断成立的条件。
- **一个现实检验：** 下一步做什么、观察什么，以及什么结果会改变当前判断。
- **一份决策快照：** 保留目标、事实、推断、假设、未知、投入边界和重新判断的条件。

## 什么时候调用

**记住一个简单规则：** 重要投入前先想清楚；现实结果回来后，别惯性继续，先重新判断。

| 决策节点 | 可以直接带来的议题 |
| --- | --- |
| **立项前** | 这个项目值不值得做，全面开发前最该先验证什么？ |
| **选方向前** | 哪条路更服务真正目的，哪个未知会改变方案排序？ |
| **投入资源前** | 是否应该开发、招聘、采购、发布、推广、合作或作出更难撤回的承诺？ |
| **继续加码前** | 现有证据是否值得再投入时间、预算、范围或声誉成本？ |
| **结果回来后** | 根据实际发生的事，应该继续、调整、暂停还是停止？ |

单纯查事实、决定已明确的低风险执行、纯创作，以及没有待决用户选择的代码审查或调研，不需要进入完整流程。紧急事件先采取保护动作；医疗、法律、投资等专业事项不能用它替代持证专业判断。

## 它怎样帮你想清楚

### 工作路径

1. **先确认真正要决定什么。** 从表面任务出发，分清眼前动作和真正希望得到或保护的结果，把宽泛议题收敛为当前决定。
2. **找到会改变方向的一个未知。** 区分事实、推断、假设和未知，只追问一个会改变方案排序、行动方向或投入边界的问题。
3. **让答案来自正确的地方。** 价值、底线和风险承受由你回答；公开事实只有确实会改变判断时才调研；承诺、客户行为和专业责任交给对应真人或现实结果。
4. **让现实结果修正判断。** 给出有成立条件和反转条件的综合判断，再设计一个尽量可撤回的现实检验，并在结果回来后重新判断。

### 会用到哪些方法

**每次都会先做基础分析。** 它会帮你对齐真正目的与当前决定，分清已经知道的、暂时推断的和仍需验证的，并找到最可能改变判断的关键未知。

两种核心方法会按需加入：

- **双向钢人：** 用相近的证据标准检验当前方向和最强替代方向，避免只为已有倾向寻找理由。
- **失败预演：** 假设当前路径已经失败，倒推最可能的失败机制、早期信号和保护边界。

<details>
<summary><strong>查看七种专项方法</strong></summary>

- **对象校准：** 分清使用者、付费者、受影响者和代价承担者，确认到底为谁解决什么问题。
- **系统瓶颈：** 多个问题互相牵制时，分清表面症状和真正牵动全局的约束。
- **阶段匹配：** 判断外部条件是否已经变化，以及过去有效的策略还适不适合现在。
- **资源支点：** 时间、资金或能力有限时，找出最值得集中投入的位置和承诺边界。
- **边界契约：** 把合作中的责任、投入、决定权、承诺和退出条件说清楚并变得可检验。
- **沟通匹配：** 判断已经清楚后，让信息、证据、渠道和反馈方式适合对象与目的。
- **证据闭环：** 把原目标和假设与已经发生的结果对齐，重新判断继续、调整、暂停还是停止。

</details>

你不需要预先了解或选择这些方法。它只会推荐当前问题真正需要的思考角度，并在使用前让你确认。

需要查资料，或请其他 Agent、真人补充信息时，它会先说明原因并征得你的同意。

## 安装与使用

把下面这句话发给你正在使用的 Agent：

```text
帮我安装这个 Skill：https://github.com/zemu2718/think-it-through-skill
```

这是面向不同宿主的一句话安装请求；当前 Agent 会根据自身能力、权限和 Skill 目录约定尝试安装。无法完成时，请查看[详细安装指南](docs/installation.md)；宿主状态与证据边界见[兼容性说明](docs/compatibility-and-evidence.md)。安装只表示文件进入目标目录，不等于宿主已经通过真实运行验证。

目前有可靠调用说明的入口是 Claude Code。在其中安装后，显式调用：

```text
/think-it-through
```

然后直接说出正在考虑的选择、准备采取的动作和已经知道的约束。

## 默认安全与更多信息

没有另行取得具体授权时，Skill 默认：

- **不联网**；
- **不读取私有数据**；
- **只使用当前主 Agent**；
- **不写入文件或远端保存**；
- **不执行外部行动**，包括发送、发布、购买、删除或联系他人。

需要这些能力时，它会分别说明要做什么并先征得你的同意；一项同意不会自动扩张到其他能力。

- **开始使用：** [安装指南](docs/installation.md) · [兼容性与证据](docs/compatibility-and-evidence.md)
- **了解边界：** [产品说明](PRODUCT.md) · [正式合同](REQUIREMENTS.md) · [安全政策](SECURITY.md)
- **参与改进：** [参与贡献](CONTRIBUTING.md) · [反馈问题](https://github.com/zemu2718/think-it-through-skill/issues/new?template=install-or-runtime-feedback.yml)

如果你实际用过后觉得有帮助，欢迎 Star，方便以后再次找到。

想清楚使用 [MIT License](LICENSE)。第三方来源与改编记录见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) 和[第三方审计](docs/third-party-audit.md)。
