# Third-party source audit

This document records the source review for the neutral specialist method cards bundled with Think It Through. It is an engineering and licensing record, not an endorsement of every statement or behavior in the reviewed repositories. The adopted source set was established in v0.1 and remains the provenance basis for v0.2.0.

## 简体中文摘要

本文档记录随 Skill 分发的七张专项方法卡如何追溯到固定上游版本。它只说明工程审计与许可证事实，不代表本项目认可候选仓库中的所有观点、措辞或行为。

| 项目 | 结论 |
| --- | --- |
| 审计范围 | 4 个候选仓库，全部固定到明确 commit |
| 采用结果 | 仅从 `SamadhiFire/xinqingnian-maoxuan-skill` 中性改编 7 个独立方法文件 |
| 未采用 | 其余 3 个仓库，以及已选仓库中的执行路线和索引文件 |
| 采用门槛 | 独立决策价值、可中性表达、安全边界清楚、许可证允许改编与分发、可覆盖路由测试 |
| 主要修改 | 删除人物模仿、政治 / 军事与动员措辞、操控和高压策略、无证据权威；增加适用边界、可观察证据、重叠规则和可撤回复判 |
| 法律记录 | 固定来源、commit、准确文件、MIT 许可证和实质修改同时记录在本文档、方法注册表、每张方法卡和两份 `THIRD_PARTY_NOTICES.md` |

详细文件映射和英文审计记录见下文。新增或升级第三方材料时，必须重新固定版本、核对许可证并同步全部来源记录；不得只修改方法卡正文。

## Audit policy

Every candidate was inspected at a fixed Git commit. Material could be adopted only when it:

1. existed as a complete file at that revision;
2. added decision value beyond the core analysis, two-sided steelmanning, and pre-mortem;
3. could be expressed neutrally with defined inputs, outputs, use cases, and non-use cases;
4. did not depend on character imitation, attributed authority, or ideology as evidence;
5. did not introduce manipulation, deception, tracking, pressure, discrimination, or unsafe certainty;
6. had a license compatible with redistribution and adaptation;
7. could be covered by routing and overlap tests.

A candidate repository did not receive quota-based inclusion. Zero adoption was a valid outcome.

## Result summary

| Candidate | Fixed commit | Result | Reason |
| --- | --- | --- | --- |
| [`leezythu/maoxuan-skill`](https://github.com/leezythu/maoxuan-skill) | [`4376a65020b1fd96af65052ccd30accaddedc3f1`](https://github.com/leezythu/maoxuan-skill/tree/4376a65020b1fd96af65052ccd30accaddedc3f1) | Not adopted | Character voice and political/military framing were central; neutralizable parts substantially duplicated the core model or the selected source. |
| [`SamadhiFire/xinqingnian-maoxuan-skill`](https://github.com/SamadhiFire/xinqingnian-maoxuan-skill) | [`4382484d8a4867f0bf9a6d089e04939618943dfb`](https://github.com/SamadhiFire/xinqingnian-maoxuan-skill/tree/4382484d8a4867f0bf9a6d089e04939618943dfb) | Seven files adapted | Seven method files provided separable routing value after neutralization; `execution-routes.md` and the index were not adopted. |
| [`hotcoffeeshake/tong-jincheng-skill`](https://github.com/hotcoffeeshake/tong-jincheng-skill) | [`c9caaa9a6576f581c29d016c60bbe935908e20d5`](https://github.com/hotcoffeeshake/tong-jincheng-skill/tree/c9caaa9a6576f581c29d016c60bbe935908e20d5) | Not adopted | The distinctive material depended on persona and dating advice; examples included deceptive excuses, pressure, mind-reading, and gender stereotypes. |
| [`momozi1996/tianya-skills`](https://github.com/momozi1996/tianya-skills) | [`5c4c29e0540089e0502147aee45610e4b1634f50`](https://github.com/momozi1996/tianya-skills/tree/5c4c29e0540089e0502147aee45610e4b1634f50) | Not adopted | The fixed tree did not implement the advertised 20 independent analyses; persona content and high-confidence claims did not meet the evidence and neutrality threshold. |

Only adopted material appears in [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md). Rejected candidates remain here for reproducibility and are not redistributed in the Skill package.

## Adopted source and mapping

Source revision:

- Repository: [`SamadhiFire/xinqingnian-maoxuan-skill`](https://github.com/SamadhiFire/xinqingnian-maoxuan-skill)
- Commit: [`4382484d8a4867f0bf9a6d089e04939618943dfb`](https://github.com/SamadhiFire/xinqingnian-maoxuan-skill/tree/4382484d8a4867f0bf9a6d089e04939618943dfb)
- License at the fixed revision: MIT
- Copyright: `Copyright (c) 2026 SamadhiFire`

| Upstream file at the fixed commit | Neutral method card | Independent decision value | Material changes |
| --- | --- | --- | --- |
| [`references/methods/investigation.md`](https://github.com/SamadhiFire/xinqingnian-maoxuan-skill/blob/4382484d8a4867f0bf9a6d089e04939618943dfb/references/methods/investigation.md) | [`object-calibration.md`](../skills/think-it-through/references/methods/object-calibration.md) | Separates service, impact, decision, payment, response, and cost-bearing roles; identifies one evidence entry point. | Removed political and high-pressure object language; limited output to observable evidence; no automatic browsing or private-data access. |
| [`references/methods/core-contradiction.md`](https://github.com/SamadhiFire/xinqingnian-maoxuan-skill/blob/4382484d8a4867f0bf9a6d089e04939618943dfb/references/methods/core-contradiction.md) | [`system-bottleneck.md`](../skills/think-it-through/references/methods/system-bottleneck.md) | Distinguishes symptoms, causes, dependencies, governing constraints, and real control points. | Replaced political and struggle terminology; prohibited character, loyalty, and identity judgments. |
| [`references/methods/stage-judgment.md`](https://github.com/SamadhiFire/xinqingnian-maoxuan-skill/blob/4382484d8a4867f0bf9a6d089e04939618943dfb/references/methods/stage-judgment.md) | [`stage-fit.md`](../skills/think-it-through/references/methods/stage-fit.md) | Tests whether a formerly valid strategy still matches current conditions. | Removed warfare and takeover metaphors; requires at least two corroborating signals and a revisable threshold; assumes no fixed stage model. |
| [`references/methods/forces-resources.md`](https://github.com/SamadhiFire/xinqingnian-maoxuan-skill/blob/4382484d8a4867f0bf9a6d089e04939618943dfb/references/methods/forces-resources.md) | [`resource-leverage.md`](../skills/think-it-through/references/methods/resource-leverage.md) | Finds a sustainable leverage point under competing resource and dependency constraints. | Removed military language and all-in framing; added minimum retained capacity, cost limits, dependency bounds, and reallocation thresholds. |
| [`references/methods/alliance-boundaries.md`](https://github.com/SamadhiFire/xinqingnian-maoxuan-skill/blob/4382484d8a4867f0bf9a6d089e04939618943dfb/references/methods/alliance-boundaries.md) | [`boundary-contracts.md`](../skills/think-it-through/references/methods/boundary-contracts.md) | Makes shared goals, commitments, authority, responsibility, control, and exit rights testable. | Removed factional, isolation, struggle, and retaliation tactics; added consent, anti-manipulation, anti-tracking, and immediate-safety boundaries. |
| [`references/methods/communication-calibration.md`](https://github.com/SamadhiFire/xinqingnian-maoxuan-skill/blob/4382484d8a4867f0bf9a6d089e04939618943dfb/references/methods/communication-calibration.md) | [`communication-fit.md`](../skills/think-it-through/references/methods/communication-fit.md) | Aligns relevant evidence, accessibility, channel, and feedback with an already formed judgment. | Removed propaganda, unified-message, isolation, and countermeasure framing; prohibits exploiting weaknesses or hiding decision-relevant facts; does not grant permission to send. |
| [`references/methods/review-loop.md`](https://github.com/SamadhiFire/xinqingnian-maoxuan-skill/blob/4382484d8a4867f0bf9a6d089e04939618943dfb/references/methods/review-loop.md) | [`evidence-loop.md`](../skills/think-it-through/references/methods/evidence-loop.md) | Compares original goals and assumptions with real outcomes to decide whether to continue, adjust, pause, or stop. | Removed campaign, warfare, and blame language; added mechanism-based review, uncertainty, and a single re-evaluation threshold; prohibits humiliation and scapegoating. |

The canonical machine-readable mapping is [`registry.yaml`](../skills/think-it-through/references/methods/registry.yaml). Each card repeats its source file, fixed commit, license, and modification summary so provenance survives progressive loading.

### Reviewed but not adopted from the selected source

- `references/methods/execution-routes.md`: not adopted because its multi-route execution output conflicts with the stage B contract of one bounded next step and otherwise overlaps core action design.
- `references/methods/method-index.md`: used only as an audit inventory; it is not an independent decision method.
- Safety and scenario files: used as audit context only; no text was copied into the distributed method library.

## Rejected-source details

### `leezythu/maoxuan-skill`

Fixed revision: [`4376a65020b1fd96af65052ccd30accaddedc3f1`](https://github.com/leezythu/maoxuan-skill/tree/4376a65020b1fd96af65052ccd30accaddedc3f1).

The reviewed implementation depends on a first-person historical persona, addresses the user as “同志”, and uses political or military metaphors as the organizing device. After removing those properties, its reusable analysis patterns mostly duplicate Think It Through's core problem reframing, steelmanning, pre-mortem, or the seven selected method cards. No file met both the independent-value and neutral-composability tests.

The MIT file at that revision contains the copyright line `Copyright (c) 2026`. The audit preserves that line exactly here rather than inventing an owner. Because no content was adopted, this source is not included in the distribution notice.

### `hotcoffeeshake/tong-jincheng-skill`

Fixed revision: [`c9caaa9a6576f581c29d016c60bbe935908e20d5`](https://github.com/hotcoffeeshake/tong-jincheng-skill/tree/c9caaa9a6576f581c29d016c60bbe935908e20d5).

The distinctive content is primarily persona-driven dating and relationship advice. Reviewed examples included fabricated excuses framed as giving someone an “out”, persuasion based on perceived weaknesses, mind-reading, and gender-generalized assumptions. Removing those elements left no independently valuable method beyond `boundary-contracts`, `communication-fit`, and the core safety boundaries. Referenced source subtitles were not present in the fixed tree, which also prevented independent verification of that claimed evidence chain.

The fixed revision's license names `Copyright (c) 2026 hotcoffeeshake`. No content was adopted, so it is not included in the distribution notice.

### `momozi1996/tianya-skills`

Fixed revision: [`5c4c29e0540089e0502147aee45610e4b1634f50`](https://github.com/momozi1996/tianya-skills/tree/5c4c29e0540089e0502147aee45610e4b1634f50).

The fixed tree contains five complete standalone persona files; the other advertised roles are metadata profiles rather than equivalent independent analyses. `team-orchestrator.py` schedules 20 coroutines around a shared placeholder analysis function, uses a constant confidence value of `0.85`, and does not load the persona files as 20 implemented reasoning systems. The reviewed persona material also relies on imitation, inadequately substantiated quotations, and high-certainty advice in sensitive domains. It therefore failed the implementation-reality, evidence-discipline, and neutral-composability tests.

The fixed revision's license names `Copyright (c) 2026 moyan`. No content was adopted, so it is not included in the distribution notice.

## Upgrade policy

Upstream changes do not flow into a release automatically. Any future adoption or upgrade must repeat the fixed-revision review, license check, independent-value analysis, neutral rewrite, safety review, and routing tests. Public documentation must not describe rejected, missing, or merely advertised material as an implemented capability.
