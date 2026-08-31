#!/usr/bin/env python3
"""用合规和违规样本验证 v0.3.0 机械合同评分器。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from grade_contracts import (
    CheckpointContext,
    InteractionEvidence,
    InteractionOption,
    extract_number_phrases,
    grade,
    grade_a,
    grade_b,
    grade_checkpoint,
    grade_decision_record,
    grade_evidence_gate,
    grade_human_review,
    grade_participation_gate,
    grade_r,
    parse_interaction_evidence,
    resolve_b_feedback_route,
)


def native_multi(question: str, *options: str) -> InteractionEvidence:
    return InteractionEvidence(
        host_control_status="available",
        surface="native-control",
        tool_call_observed=True,
        selection_mode="multi",
        options=options,
        host_free_text_available=True,
        question_text=question,
    )


def native_single(question: str, *options: str) -> InteractionEvidence:
    return InteractionEvidence(
        host_control_status="available",
        surface="native-control",
        tool_call_observed=True,
        selection_mode="single",
        options=options,
        host_free_text_available=True,
        question_text=question,
    )


def method_option(
    method_id: str,
    description: str,
    recommended: bool,
) -> InteractionOption:
    return InteractionOption(
        id=method_id,
        label={
            "two-sided-steelman": "双向钢人",
            "pre-mortem": "失败预演",
            "object-calibration": "对象校准",
        }[method_id],
        description=description,
        recommended=recommended,
    )


def text_fallback(
    status: str = "unavailable",
    selection_mode: str = "multi",
) -> InteractionEvidence:
    return InteractionEvidence(
        host_control_status=status,
        surface="text-fallback",
        tool_call_observed=status in {"failed", "rejected"},
        selection_mode=selection_mode,
    )


def free_answer() -> InteractionEvidence:
    return InteractionEvidence(
        host_control_status="available",
        surface="free-answer",
        tool_call_observed=False,
        selection_mode="none",
    )


FEEDBACK_OPTIONS = (
    "方向符合我",
    "调整下一步",
    "不同意这个判断",
    "暂时先放一放",
)


def native_b_feedback(supplement_mode: str = "follow-up-message") -> InteractionEvidence:
    question = (
        "补充说明可选。\n\n这份判断更接近你的哪种反馈？"
        if supplement_mode == "native-note"
        else "选中后，你仍可以再发一条普通消息补充、纠正或提供新事实。\n\n这份判断更接近你的哪种反馈？"
    )
    return InteractionEvidence(
        host_control_status="available",
        surface="native-control",
        tool_call_observed=True,
        selection_mode="single",
        options=FEEDBACK_OPTIONS,
        host_free_text_available=True,
        question_text=question,
        supplement_mode=supplement_mode,
    )


def b_text_fallback(status: str = "unavailable") -> InteractionEvidence:
    return InteractionEvidence(
        host_control_status=status,
        surface="text-fallback",
        tool_call_observed=status in {"failed", "rejected"},
        selection_mode="single",
        supplement_mode="inline-text",
    )


def with_feedback_fallback(text: str) -> str:
    return text.rstrip() + """

### 反馈

当前无法显示原生单选。请回复一个编号或方向，也可以在同一条消息补充说明。

1. 方向符合我
2. 调整下一步
3. 不同意这个判断
4. 暂时先放一放"""


CHECKPOINT_COMMITMENT = "把当前原型正式立为要继续投入的项目"
CHECKPOINT_UNKNOWN = "陌生用户是否真的愿意为当前价值付费"
CHECKPOINT_WHY_NOW = "一旦开始追加开发，时间和机会成本就会上升"
CHECKPOINT_LABELS = ("进入完整检查", "继续当前任务")


def checkpoint_context(**overrides: object) -> CheckpointContext:
    payload: dict[str, object] = {
        "trigger_type": "project-initiation",
        "explicit_invocation": False,
        "active_flow": False,
        "same_decision_cooling_down": False,
        "material_change": "none",
        "response": "pending",
        "next_stage": "pre-entry",
        "waited_for_user": True,
        "commitment": CHECKPOINT_COMMITMENT,
        "decision_sensitive_unknown": CHECKPOINT_UNKNOWN,
        "why_now": CHECKPOINT_WHY_NOW,
        "decision_scope": {
            "decision_object": "当前原型",
            "true_objective": "验证是否值得继续投入",
            "commitment_scope": "从探索原型转为持续开发",
        },
        "capability_calls": [],
        "consent_ids": [],
        "decision_record_created": False,
        "persistence_written": False,
    }
    payload.update(overrides)
    return CheckpointContext.from_dict(payload)


def checkpoint_text() -> str:
    return (
        f"你正在承诺{CHECKPOINT_COMMITMENT}。\n\n"
        f"仍可能改变方向的是{CHECKPOINT_UNKNOWN}。\n\n"
        f"现在值得暂停，是因为{CHECKPOINT_WHY_NOW}。"
    )


def checkpoint_native() -> InteractionEvidence:
    return InteractionEvidence.from_dict(
        {
            "host_control_status": "available",
            "surface": "native-control",
            "tool_call_observed": True,
            "selection_mode": "single",
            "options": [
                {"id": "enter-full-check", "label": CHECKPOINT_LABELS[0]},
                {"id": "continue-current-task", "label": CHECKPOINT_LABELS[1]},
            ],
            "host_free_text_available": True,
            "question_text": "可单选，也可以直接纠正我的理解。\n\n要不要现在做一次完整检查？",
        },
        option_contract="checkpoint",
    )


def checkpoint_fallback_text() -> str:
    return checkpoint_text() + """

当前无法显示原生单选。请回复一个编号或直接纠正我的理解。

要不要现在做一次完整检查？

1. 进入完整检查
2. 继续当前任务"""


def checkpoint_fallback(status: str) -> InteractionEvidence:
    return InteractionEvidence(
        host_control_status=status,
        surface="text-fallback",
        tool_call_observed=status in {"failed", "rejected"},
        selection_mode="single",
    )


class ContractGraderTests(unittest.TestCase):
    def assert_all_pass(self, checks) -> None:
        failed = [(check.text, check.evidence) for check in checks if not check.passed]
        self.assertEqual([], failed)

    def assert_has_failure(self, checks, name: str) -> None:
        matches = [check for check in checks if check.text == name]
        self.assertEqual(1, len(matches), name)
        self.assertFalse(matches[0].passed, name)

    def test_valid_checkpoint_native_single(self) -> None:
        self.assert_all_pass(
            grade_checkpoint(
                checkpoint_text(),
                checkpoint_context(),
                checkpoint_native(),
            )
        )

    def test_grade_supports_checkpoint(self) -> None:
        self.assert_all_pass(
            grade(
                "CHECKPOINT",
                checkpoint_text(),
                False,
                [],
                [],
                [],
                [],
                "method",
                interaction=checkpoint_native(),
                checkpoint_context=checkpoint_context(),
            )
        )

    def test_checkpoint_text_fallback_matrix(self) -> None:
        for status in ("unavailable", "failed", "rejected"):
            with self.subTest(status=status):
                self.assert_all_pass(
                    grade_checkpoint(
                        checkpoint_fallback_text(),
                        checkpoint_context(),
                        checkpoint_fallback(status),
                    )
                )

    def test_checkpoint_requires_fixed_structured_options(self) -> None:
        invalid = checkpoint_native()
        invalid = InteractionEvidence(
            host_control_status=invalid.host_control_status,
            surface=invalid.surface,
            tool_call_observed=invalid.tool_call_observed,
            selection_mode=invalid.selection_mode,
            options=(
                InteractionOption(id="continue-current-task", label=CHECKPOINT_LABELS[1]),
                InteractionOption(id="enter-full-check", label=CHECKPOINT_LABELS[0]),
            ),
            host_free_text_available=True,
            question_text=invalid.question_text,
        )
        checks = grade_checkpoint(checkpoint_text(), checkpoint_context(), invalid)
        self.assert_has_failure(
            checks,
            "上下文检查点按宿主能力使用固定原生单选或普通编号降级",
        )

    def test_checkpoint_does_not_relax_method_option_parser(self) -> None:
        payload = {
            "host_control_status": "available",
            "surface": "native-control",
            "tool_call_observed": True,
            "selection_mode": "single",
            "options": [
                {"id": "enter-full-check", "label": CHECKPOINT_LABELS[0]},
                {"id": "continue-current-task", "label": CHECKPOINT_LABELS[1]},
            ],
            "host_free_text_available": True,
            "question_text": "可单选，也可以直接纠正。\n\n要不要进入完整检查？",
        }
        with self.assertRaises(ValueError):
            InteractionEvidence.from_dict(payload)
        self.assertEqual(
            ("enter-full-check", "continue-current-task"),
            tuple(
                option.id
                for option in InteractionEvidence.from_dict(
                    payload,
                    option_contract="checkpoint",
                ).options
            ),
        )

    def test_checkpoint_ambiguous_response_stays_pre_entry(self) -> None:
        self.assert_all_pass(
            grade_checkpoint(
                checkpoint_text(),
                checkpoint_context(response="ambiguous"),
                checkpoint_native(),
            )
        )
        checks = grade_checkpoint(
            checkpoint_text(),
            checkpoint_context(response="ambiguous", next_stage="R-align"),
            checkpoint_native(),
        )
        self.assert_has_failure(
            checks,
            "上下文检查点等待明确选择并按进入、继续或模糊回应路由",
        )

    def test_checkpoint_enter_and_continue_routes(self) -> None:
        for response, next_stage in (
            ("enter-full-check", "R-align"),
            ("enter-full-check", "R-method"),
            ("continue-current-task", "resume-current-task"),
        ):
            with self.subTest(response=response, next_stage=next_stage):
                self.assert_all_pass(
                    grade_checkpoint(
                        checkpoint_text(),
                        checkpoint_context(response=response, next_stage=next_stage),
                        checkpoint_native(),
                    )
                )

    def test_checkpoint_bypasses_explicit_invocation_and_active_flow(self) -> None:
        cases = (
            checkpoint_context(
                explicit_invocation=True,
                response="not-applicable",
                next_stage="R-align",
                waited_for_user=False,
                commitment="",
                decision_sensitive_unknown="",
                why_now="",
            ),
            checkpoint_context(
                active_flow=True,
                response="not-applicable",
                next_stage="active-flow",
                waited_for_user=False,
                commitment="",
                decision_sensitive_unknown="",
                why_now="",
            ),
        )
        for context in cases:
            with self.subTest(context=context):
                self.assert_all_pass(grade_checkpoint("", context))

    def test_checkpoint_close_negative_does_not_present(self) -> None:
        context = checkpoint_context(
            trigger_type="close-negative",
            response="not-applicable",
            next_stage="resume-current-task",
            waited_for_user=False,
            commitment="",
            decision_sensitive_unknown="",
            why_now="",
            decision_scope={},
        )
        self.assert_all_pass(grade_checkpoint("", context))

    def test_checkpoint_cooldown_and_material_changes(self) -> None:
        cooldown = checkpoint_context(
            same_decision_cooling_down=True,
            response="not-applicable",
            next_stage="resume-current-task",
            waited_for_user=False,
            commitment="",
            decision_sensitive_unknown="",
            why_now="",
        )
        self.assert_all_pass(grade_checkpoint("", cooldown))
        for change in (
            "new-evidence",
            "purpose-change",
            "commitment-scope-expanded",
            "new-reassessment-node",
            "new-topic",
        ):
            with self.subTest(change=change):
                self.assert_all_pass(
                    grade_checkpoint(
                        checkpoint_text(),
                        checkpoint_context(
                            same_decision_cooling_down=True,
                            material_change=change,
                        ),
                        checkpoint_native(),
                    )
                )

    def test_checkpoint_rejects_missing_required_meaning(self) -> None:
        checks = grade_checkpoint(
            checkpoint_text().replace(CHECKPOINT_UNKNOWN, "一个问题"),
            checkpoint_context(),
            checkpoint_native(),
        )
        self.assert_has_failure(
            checks,
            "上下文检查点说清承诺、一个决定敏感未知和 why-now",
        )

    def test_checkpoint_rejects_early_r_gate_or_side_effects(self) -> None:
        text = checkpoint_text() + "\n\n建议：你应该先做双向钢人并开始 Evidence Gate。"
        context = checkpoint_context(
            capability_calls=["search.public_web"],
            consent_ids=["consent-capability"],
            decision_record_created=True,
            persistence_written=True,
        )
        checks = grade_checkpoint(text, context, checkpoint_native())
        self.assert_has_failure(
            checks,
            "上下文检查点确认前不进入正式分析、方法、判断或行动",
        )
        self.assert_has_failure(
            checks,
            "上下文检查点不触发 Gate、能力调用或授权请求",
        )
        self.assert_has_failure(
            checks,
            "上下文检查点选择不推定授权且不创建记录或持久化",
        )

    @staticmethod
    def r_align_interaction() -> InteractionEvidence:
        return native_multi(
            "可多选，也可以直接补充或纠正。\n\n这件事你主要希望获得哪些结果？",
            "练手并做成作品",
            "解决一类人的具体问题",
            "探索商业化可能",
            "给现有团队或社群使用",
        )

    @staticmethod
    def r_method_interaction() -> InteractionEvidence:
        return InteractionEvidence(
            host_control_status="available",
            surface="native-control",
            tool_call_observed=True,
            selection_mode="multi",
            options=(
                method_option(
                    "two-sided-steelman",
                    "用相近证据标准比较当前方向与最强替代方向，帮助分清先开发还是先验证。",
                    True,
                ),
                method_option(
                    "pre-mortem",
                    "沿具体失败机制找出早期信号，帮助限制继续投入前的下行风险。",
                    False,
                ),
                method_option(
                    "object-calibration",
                    "分清使用者、付费者和代价承担者，帮助判断应该先验证谁的需求。",
                    False,
                ),
            ),
            host_free_text_available=True,
            question_text="当前组合已经包含基本梳理。\n\n可多选，也可以直接加入、取消、替换或纠正。\n\n这轮保留哪些思考角度？",
        )

    def test_valid_r_align(self) -> None:
        text = """听起来你已经有一个产品想法，但它首先要为你带来什么，会直接改变后面的判断。这个理解只是暂定的，你可以随时纠正。"""
        self.assert_all_pass(grade_r(text, r_mode="align", interaction=self.r_align_interaction()))

    def test_grade_defaults_r_to_compatible_set(self) -> None:
        text = """听起来你已经有一个产品想法，但它首先要为你带来什么，会直接改变后面的判断。这个理解只是暂定的，你可以随时纠正。"""
        self.assert_all_pass(
            grade(
                "R",
                text,
                False,
                [],
                [],
                [],
                [],
                "align",
                interaction=self.r_align_interaction(),
            )
        )

    def test_grade_defaults_a_to_open(self) -> None:
        text = """好，这轮先做基本梳理。

当前真正分歧是你是否愿意接受这个结果的不确定性。

什么现实结果会改变你继续投入的决定？"""
        self.assert_all_pass(
            grade(
                "A",
                text,
                False,
                [],
                [],
                [],
                [],
                "method",
                interaction=free_answer(),
            )
        )

    def test_r_align_cannot_show_method_menu(self) -> None:
        text = """我目前理解你还在找真实目的，你可以随时纠正。
[获得收入]
[做成作品]
也可以不选，直接说。
双向钢人可以帮助你比较方向，我会等你确认再继续。"""
        checks = grade_r(text, r_mode="align", interaction=self.r_align_interaction())
        self.assert_has_failure(checks, "R-align 不提前展示或执行方法")

    def test_valid_r_method(self) -> None:
        text = """你想决定的是要不要继续投入开发，而陌生客户是否愿意付费仍是最大未知。

把当前方向和最强替代方向都认真想透，再用相近证据标准检验（双向钢人）——此刻能分清继续开发和先验证哪条路更服务收入目标。"""
        self.assert_all_pass(
            grade_r(
                text,
                ["two-sided-steelman"],
                r_mode="method",
                interaction=self.r_method_interaction(),
            )
        )

    def test_r_method_rejects_legacy_string_options_for_recommendation(self) -> None:
        text = """你想决定的是要不要继续投入开发，而陌生客户是否愿意付费仍是最大未知。

把当前方向和最强替代方向都认真想透，再用相近证据标准检验（双向钢人）——此刻能分清继续开发和先验证哪条路更服务收入目标。"""
        interaction = native_multi(
            "当前组合已经包含基本梳理。\n\n可多选，也可以直接加入、取消、替换或纠正。\n\n这轮保留哪些思考角度？",
            "双向钢人",
            "失败预演",
        )
        checks = grade_r(
            text,
            ["two-sided-steelman"],
            r_mode="method",
            interaction=interaction,
        )
        self.assert_has_failure(
            checks,
            "R-method 候选具有稳定 ID、正式名称、当前价值和推荐状态",
        )

    def test_r_method_rejects_wrong_recommended_marker(self) -> None:
        interaction = self.r_method_interaction()
        options = tuple(
            InteractionOption(
                id=option.id,
                label=option.label,
                description=option.description,
                recommended=False,
            )
            for option in interaction.method_options
        )
        checks = grade_r(
            "你想决定是否继续投入。双向钢人会比较最强替代方向。",
            ["two-sided-steelman"],
            r_mode="method",
            interaction=InteractionEvidence(
                host_control_status=interaction.host_control_status,
                surface=interaction.surface,
                tool_call_observed=interaction.tool_call_observed,
                selection_mode=interaction.selection_mode,
                options=options,
                host_free_text_available=interaction.host_free_text_available,
                question_text=interaction.question_text,
            ),
        )
        self.assert_has_failure(
            checks,
            "R-method 推荐标记与本轮推荐集合一致且不冒充确认",
        )

    def test_r_method_rejects_duplicate_native_description(self) -> None:
        interaction = self.r_method_interaction()
        duplicated = interaction.method_options[0].description
        text = f"""你想决定是否继续投入。

{duplicated}"""
        checks = grade_r(
            text,
            ["two-sided-steelman"],
            r_mode="method",
            interaction=interaction,
        )
        self.assert_has_failure(
            checks,
            "R-method 不在正文与原生选项中重复完整说明",
        )

    def test_fixed_four_routes_do_not_pass_current_r(self) -> None:
        text = """按推荐继续 / 调整方法 / 只做基础分析 / 补充背景
也可以直接说。
我会等你确认再继续。"""
        checks = grade_r(text, r_mode="method")
        self.assert_has_failure(checks, "阶段 R 有结构化交互证据")

    def test_r_free_expression_cannot_be_product_other_option(self) -> None:
        interaction = native_multi(
            "可多选，也可以直接补充或纠正。\n\n这件事你主要希望获得哪些结果？",
            "获得收入",
            "做成作品",
            "Other",
        )
        checks = grade_r("我目前的理解只是暂定。", r_mode="align", interaction=interaction)
        self.assert_has_failure(checks, "阶段 R 的选项数量匹配答案形态")

    def test_r_with_judgment_fails(self) -> None:
        text = """[继续]
[调整]
也可以不选，直接说。
我会等你确认。
建议：你应该停止。"""
        checks = grade_r(text, r_mode="method", interaction=self.r_method_interaction())
        self.assert_has_failure(checks, "阶段 R 不给判断")

    def test_r_hiding_formal_method_name_fails(self) -> None:
        text = """[比较两条最强路径——认真比较两个方向]
[只做基本梳理]
也可以不选，直接说想调整什么。
我会等你确认。"""
        interaction = native_multi(
            "可多选，也可以直接补充或纠正。\n\n这轮保留哪些思考角度？",
            "比较两条最强路径",
            "只做基本梳理",
        )
        checks = grade_r(
            text,
            ["two-sided-steelman"],
            r_mode="method",
            interaction=interaction,
        )
        self.assert_has_failure(checks, "R-method 显示推荐方法的正式名称")

    def test_r_duplicate_heading_fails(self) -> None:
        text = """## 思考角度
## 思考角度
[继续]
[调整]
也可以不选，直接说。
我会等你确认。"""
        checks = grade_r(text, r_mode="method", interaction=self.r_method_interaction())
        self.assert_has_failure(checks, "阶段 R 不含重复标题")

    def test_r_available_host_cannot_use_markdown_fallback(self) -> None:
        interaction = InteractionEvidence(
            host_control_status="available",
            surface="text-fallback",
            tool_call_observed=False,
            selection_mode="multi",
        )
        text = """我目前的理解只是暂定。
[获得收入]
[做成作品]
也可以不选，直接说。
我会等你确认。"""
        checks = grade_r(text, r_mode="align", interaction=interaction)
        self.assert_has_failure(checks, "阶段 R 在控件可用时使用原生选择，否则文本降级")

    def test_r_unavailable_host_accepts_text_fallback(self) -> None:
        text = """我目前的理解只是暂定。

我会停在这里等你回答。

可多选，也可以不选，直接按你的方式说或纠正。

这件事你主要希望获得哪些结果？

[获得收入]
[做成作品]"""
        self.assert_all_pass(grade_r(text, r_mode="align", interaction=text_fallback()))

    def test_r_failed_host_accepts_text_fallback(self) -> None:
        text = """我目前的理解只是暂定。

我会停在这里等你回答。

可多选，也可以不选，直接按你的方式说或纠正。

这件事你主要希望获得哪些结果？

[获得收入]
[做成作品]"""
        self.assert_all_pass(
            grade_r(
                text,
                r_mode="align",
                interaction=text_fallback(status="failed"),
            )
        )

    def test_r_method_can_use_single_confirmation(self) -> None:
        interaction = native_single(
            "可单选，也可以直接补充或纠正。\n\n这轮是否只做基本梳理？",
            "只做基本梳理",
            "返回补充目的",
        )
        text = "目前没有额外方法能提供独特价值，这个理解只是暂定。"
        self.assert_all_pass(
            grade_r(
                text,
                r_mode="method",
                interaction=interaction,
                answer_shape="finite-mutually-exclusive",
            )
        )

    def test_r_method_after_compatible_purposes_does_not_reopen_priority(self) -> None:
        text = """我先这样理解：你希望借这个项目练手并做成作品，也希望它解决真实问题，并保留以后发展成产品的可能。

这些结果可以放在一起，不需要现在排出唯一第一名。

把当前方向和最强替代方向都认真想透，再用相近证据标准检验（双向钢人）——此刻能比较先做通用聊天工具和先找具体场景，哪条路更服务这组结果。"""
        self.assert_all_pass(
            grade_r(
                text,
                ["two-sided-steelman"],
                r_mode="method",
                interaction=self.r_method_interaction(),
                answer_shape="compatible-set",
            )
        )

    def test_r_align_can_use_single_for_real_exclusive_boundary(self) -> None:
        interaction = native_single(
            "可单选，也可以直接补充或纠正。\n\n在这个明确限制下，你准备保留哪一个结果？",
            "先保护现金流",
            "先完成作品",
            "暂不继续投入",
        )
        text = "你已经说明这笔投入只能用于一个方向；我目前的理解仍是暂定的。"
        self.assert_all_pass(
            grade_r(
                text,
                r_mode="align",
                interaction=interaction,
                answer_shape="finite-mutually-exclusive",
            )
        )

    def test_r_align_can_use_open_answer(self) -> None:
        text = """你已经指出现有选项都不贴合；我目前的理解仍是暂定的。

什么结果对你来说才算真正解决了这件事？"""
        self.assert_all_pass(
            grade_r(
                text,
                r_mode="align",
                interaction=free_answer(),
                answer_shape="open",
            )
        )

    def test_r_answer_shape_rejects_wrong_selection_mode(self) -> None:
        checks = grade_r(
            "我目前的理解仍是暂定的。",
            r_mode="align",
            interaction=self.r_align_interaction(),
            answer_shape="finite-mutually-exclusive",
        )
        self.assert_has_failure(checks, "阶段 R 在控件可用时使用原生选择，否则文本降级")

    def test_r_open_answer_rejects_native_options(self) -> None:
        checks = grade_r(
            """我目前的理解仍是暂定的。

什么结果对你来说才算真正解决了这件事？""",
            r_mode="align",
            interaction=self.r_align_interaction(),
            answer_shape="open",
        )
        self.assert_has_failure(checks, "阶段 R 的选项数量匹配答案形态")

    def test_r_native_question_requires_semantic_paragraphs(self) -> None:
        interaction = native_multi(
            "可多选，也可以直接补充或纠正。这件事你主要希望获得哪些结果？",
            "练手并做成作品",
            "解决一类人的具体问题",
        )
        checks = grade_r("我目前的理解仍是暂定的。", r_mode="align", interaction=interaction)
        self.assert_has_failure(checks, "阶段 R 按语义分段并把正式问题放在最后")

    def test_r_option_labels_cannot_contain_questions(self) -> None:
        interaction = native_multi(
            "可多选，也可以直接补充或纠正。\n\n这件事你主要希望获得哪些结果？",
            "练手并做成作品？",
            "解决一类人的具体问题",
        )
        checks = grade_r("我目前的理解仍是暂定的。", r_mode="align", interaction=interaction)
        self.assert_has_failure(checks, "阶段 R 按语义分段并把正式问题放在最后")

    def test_interaction_evidence_from_dict(self) -> None:
        evidence = InteractionEvidence.from_dict(
            {
                "host_control_status": "available",
                "surface": "native-control",
                "tool_call_observed": True,
                "selection_mode": "multi",
                "options": ["获得收入", "做成作品"],
                "host_free_text_available": True,
                "question_text": "可多选，也可以直接补充或纠正。\n\n你希望获得哪些结果？",
                "supplement_mode": "none",
            }
        )
        self.assertEqual(("获得收入", "做成作品"), evidence.option_labels)
        self.assertTrue(evidence.tool_call_observed)
        self.assertEqual("none", evidence.supplement_mode)

    def test_interaction_evidence_accepts_structured_method_options(self) -> None:
        evidence = InteractionEvidence.from_dict(
            {
                "host_control_status": "available",
                "surface": "native-control",
                "tool_call_observed": True,
                "selection_mode": "multi",
                "options": [
                    {
                        "id": "two-sided-steelman",
                        "label": "双向钢人",
                        "description": "用相近证据标准比较当前方向与最强替代方向，帮助分清先开发还是先验证。",
                        "recommended": True,
                    }
                ],
                "host_free_text_available": True,
                "question_text": "可多选，也可以直接补充或纠正。\n\n这轮保留哪些思考角度？",
            }
        )
        self.assertEqual(("双向钢人",), evidence.option_labels)
        self.assertEqual("two-sided-steelman", evidence.method_options[0].id)
        self.assertTrue(evidence.method_options[0].recommended)

    def test_interaction_evidence_rejects_invalid_types(self) -> None:
        invalid_cases = (
            {"options": "获得收入"},
            {"options": ["获得收入", 1]},
            {"host_control_status": "unknown"},
            {"surface": "markdown"},
            {"selection_mode": "checkbox"},
            {"supplement_mode": "sidecar-note"},
            {"tool_call_observed": "yes"},
            {"host_free_text_available": "yes"},
            {"question_text": ["问题"]},
            {
                "options": [
                    {
                        "id": "Two Sided",
                        "label": "双向钢人",
                        "description": "有足够长度的当前价值说明。",
                        "recommended": True,
                    }
                ]
            },
            {
                "options": [
                    {
                        "id": "two-sided-steelman",
                        "label": "双向钢人",
                        "description": "有足够长度的当前价值说明。",
                        "recommended": "yes",
                    }
                ]
            },
            {
                "options": [
                    {
                        "id": "two-sided-steelman",
                        "label": "双向钢人",
                        "description": "有足够长度的当前价值说明。",
                        "recommended": True,
                        "selected": True,
                    }
                ]
            },
        )
        base = {
            "host_control_status": "available",
            "surface": "native-control",
            "tool_call_observed": True,
            "selection_mode": "multi",
            "options": ["获得收入", "做成作品"],
            "host_free_text_available": True,
            "question_text": "可多选，也可以直接补充或纠正。\n\n你希望获得哪些结果？",
        }
        for override in invalid_cases:
            with self.subTest(override=override), self.assertRaises(ValueError):
                InteractionEvidence.from_dict({**base, **override})

    def test_parse_interaction_evidence_json(self) -> None:
        payload = {
            "host_control_status": "unavailable",
            "surface": "text-fallback",
            "tool_call_observed": False,
            "selection_mode": "single",
            "options": [],
            "host_free_text_available": False,
            "question_text": "",
        }
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "interaction.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(InteractionEvidence.from_dict(payload), parse_interaction_evidence(path))

    def test_parse_interaction_evidence_requires_object(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "interaction.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_interaction_evidence(path)

    def test_valid_a_with_open_answer(self) -> None:
        text = """好，我们就按刚才选的来：双向钢人。

## 真正要决定什么
是否继续开发，还是先验证陌生客户愿意付费。

## 综合后的关键分析
继续开发依赖需求真实存在；最强替代方向是先验证，代价更低。

## 真正分歧与关键变量
关键不是功能能否完成，而是现有版本是否解决了足以付费的问题。

什么现实结果会让你停止继续开发？"""
        self.assert_all_pass(grade_a(text, confirmed_methods=["two-sided-steelman"], interaction=free_answer()))

    def test_valid_a_with_finite_choices(self) -> None:
        text = "好，这轮先做基本梳理。"
        interaction = native_single(
            "可单选，也可以直接补充或纠正。\n\n你目前更想保护哪一种结果？",
            "尽快获得收入",
            "先积累作品",
            "暂时不投入更多",
        )
        self.assert_all_pass(
            grade_a(
                text,
                confirmed_methods=[],
                interaction=interaction,
                answer_shape="finite-mutually-exclusive",
            )
        )

    def test_a_native_question_requires_semantic_paragraphs(self) -> None:
        interaction = native_single(
            "可单选，也可以直接补充或纠正。你目前更想保护哪一种结果？",
            "尽快获得收入",
            "先积累作品",
        )
        checks = grade_a(
            "好，这轮先做基本梳理。",
            confirmed_methods=[],
            interaction=interaction,
            answer_shape="finite-mutually-exclusive",
        )
        self.assert_has_failure(checks, "阶段 A 按语义分段并把唯一问题放在最后")

    def test_a_open_question_requires_own_last_paragraph(self) -> None:
        checks = grade_a(
            "好，这轮先做基本梳理。\n什么现实结果会改变你的决定？",
            interaction=free_answer(),
        )
        self.assert_has_failure(checks, "阶段 A 按语义分段并把唯一问题放在最后")

    def test_a_rejects_compatible_set_answer_shape(self) -> None:
        with self.assertRaises(ValueError):
            grade_a(
                "好，这轮先做基本梳理。\n\n哪些结果可以同时成立？",
                interaction=free_answer(),
                answer_shape="compatible-set",
            )

    def test_a_with_two_questions_fails(self) -> None:
        checks = grade_a(
            "好，这轮先做基本梳理。\n你有预算吗？你愿意继续吗？",
            interaction=free_answer(),
        )
        self.assert_has_failure(checks, "阶段 A 恰好一个问号")

    def test_a_with_content_after_question_fails(self) -> None:
        checks = grade_a(
            "好，这轮先做基本梳理。\n哪个证据会改变决定？\n请想好后回复。",
            interaction=free_answer(),
        )
        self.assert_has_failure(checks, "阶段 A 以唯一问号结束")

    def test_a_with_multiple_answer_slots_fails(self) -> None:
        checks = grade_a(
            "好，这轮先做基本梳理。\n预算是多少、期限是多久，以及最低回报是什么？",
            interaction=free_answer(),
        )
        self.assert_has_failure(checks, "阶段 A 的唯一问题只有一个答案槽")

    def test_a_with_hidden_information_request_fails(self) -> None:
        checks = grade_a(
            "好，这轮先做基本梳理。\n请先提供预算和期限。哪个收入阈值会改变决定？",
            interaction=free_answer(),
        )
        self.assert_has_failure(checks, "阶段 A 不用陈述句隐藏追加信息请求")

    def test_cancelled_premortem_fails(self) -> None:
        checks = grade_a(
            "好，这轮先做基本梳理。\n真正分歧在付费意愿。\n假设执行后失败，最早信号是什么？",
            ["pre-mortem"],
            interaction=free_answer(),
        )
        self.assert_has_failure(checks, "阶段 A 不变相执行已取消方法")

    def test_a_missing_confirmed_method_in_echo_fails(self) -> None:
        text = """好，我们就按刚才选的来：失败预演。
两个最强竞争判断依赖不同付费假设。假设执行后失败，早期信号是无人复购。
哪个证据最可能改变决定？"""
        checks = grade_a(
            text,
            confirmed_methods=["two-sided-steelman", "pre-mortem"],
            interaction=free_answer(),
        )
        self.assert_has_failure(checks, "阶段 A 自然回显最终确认的方法组合")

    def test_a_unconfirmed_method_in_echo_fails(self) -> None:
        text = """好，我们就按刚才选的来：双向钢人 + 失败预演。
两个最强竞争判断依赖不同付费假设。假设执行后失败，早期信号是无人复购。
哪个证据最可能改变决定？"""
        checks = grade_a(
            text,
            confirmed_methods=["two-sided-steelman"],
            interaction=free_answer(),
        )
        self.assert_has_failure(checks, "阶段 A 自然回显最终确认的方法组合")

    def test_a_basic_only_requires_natural_echo(self) -> None:
        checks = grade_a(
            "哪个证据最可能改变决定？",
            confirmed_methods=[],
            interaction=free_answer(),
        )
        self.assert_has_failure(checks, "阶段 A 自然回显最终确认的方法组合")

    def test_a_missing_confirmed_method_output_fails(self) -> None:
        text = """好，我们就按刚才选的来：双向钢人 + 失败预演。
两个最强竞争判断依赖不同付费假设。
哪个证据最可能改变决定？"""
        checks = grade_a(
            text,
            confirmed_methods=["two-sided-steelman", "pre-mortem"],
            interaction=free_answer(),
        )
        self.assert_has_failure(checks, "阶段 A 的确认方法产生独特分析产出")

    def test_a_system_invented_numbers_fail(self) -> None:
        text = """好，这轮先做基本梳理。
如果十个陌生用户中没有一人付款，这会不会让你停止未来三个月的开发？"""
        checks = grade_a(text, interaction=free_answer())
        self.assert_has_failure(checks, "阶段 A 不使用用户未提供的决定相关数字")

    def test_a_reuses_user_provided_chinese_numbers(self) -> None:
        text = """好，这轮先做基本梳理。

你说的十个人中如果没有一人付款，这会不会改变你的决定？"""
        self.assert_all_pass(
            grade_a(
                text,
                user_numbers=["十个人", "一人"],
                interaction=free_answer(),
            )
        )

    def test_a_different_number_or_unit_fails(self) -> None:
        text = """好，这轮先做基本梳理。
如果二十个人都不付款，这会不会改变你的决定？"""
        checks = grade_a(
            text,
            user_numbers=["十个人"],
            interaction=free_answer(),
        )
        self.assert_has_failure(checks, "阶段 A 不使用用户未提供的决定相关数字")

    def test_structural_one_problem_is_not_numeric_anchor(self) -> None:
        phrases = extract_number_phrases("这里只问一个问题，给一个判断和一个下一步。")
        self.assertEqual([], phrases)

    def test_percentage_of_number_is_extracted(self) -> None:
        phrases = extract_number_phrases("百分之十的人愿意付费。")
        self.assertEqual([("10", "%")], [phrase.key for phrase in phrases])

    def test_valid_b_unexecuted_with_single_experiment(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。

原因很简单：付费意愿还是会改变决定的最大未知；如果真实付款出现，判断可以转向推进，否则应停止继续投入。

### 先做这一件事


这一步要弄清的是现有版本能否产生有区分力的现实反应（核心假设）。

把现有版本给符合画像的陌生对象看，并邀请真实付款，不新增功能（本轮动作）。

记录真实付款、明确拒绝和拒绝理由（观察信号）。

出现真实付款就重新判断是否推进；持续只有拒绝就停止本轮开发投入（复判条件）。"""
        self.assert_all_pass(
            grade_b(
                text,
                already_executed=False,
                interaction=native_b_feedback(),
            )
        )

    def test_valid_b_without_fixed_heading(self) -> None:
        text = """按目前信息，更合适的是先验证真实付款，再决定是否继续开发（当前判断：小步验证）。

这一步要弄清的是，现有版本能否带来有区分力的真实反应（核心假设）。

先展示现有版本，再邀请符合画像的陌生对象真实付款，但不新增功能（本轮动作）。

只记录付款、明确拒绝和拒绝理由；付款支持继续，持续拒绝则反对继续（观察信号）。

出现付款时重新决定是否推进；持续只有拒绝时停止新增投入（复判条件）。"""
        self.assert_all_pass(
            grade_b(text, already_executed=False, interaction=native_b_feedback())
        )

    def test_valid_b_english_suffix_contract(self) -> None:
        text = """Based on the current evidence, validate real payment before committing further (current judgment: small test).

The point to test is whether the current version solves a problem worth paying for (core hypothesis).

Show the existing version to suitable prospects and invite real payment without adding features (action for this round).

Record payment, explicit refusal, and refusal reasons; payment supports continuing while repeated refusal argues against it (signals to observe).

If payment appears, reassess whether to proceed; if refusals persist, stop new investment (reassessment condition)."""
        self.assert_all_pass(
            grade_b(text, already_executed=False, interaction=native_b_feedback())
        )

    def test_b_rejects_legacy_prefix_labels(self) -> None:
        text = """按目前信息，更合适的是先验证真实付款（当前判断：小步验证）。

核心假设：现有版本能否带来真实付款（核心假设）。

**动作**：展示现有版本（本轮动作）。

**观察**：付款支持继续，拒绝反对继续（观察信号）。

**复判**：有付款时重新决定是否推进，否则停止（复判条件）。"""
        checks = grade_b(text, already_executed=False, interaction=native_b_feedback())
        self.assert_has_failure(
            checks,
            "阶段 B 的核心假设、本轮动作、观察信号和复判条件以自然句分别成段并后置标记",
        )

    def test_b_rejects_missing_or_misordered_suffixes(self) -> None:
        cases = {
            "missing": """按目前信息，更合适的是先验证（当前判断：小步验证）。

先展示现有版本（本轮动作）。

付款支持继续，拒绝反对继续（观察信号）。

有付款时重新决定，否则停止（复判条件）。""",
            "misordered": """按目前信息，更合适的是先验证（当前判断：小步验证）。

先展示现有版本（本轮动作）。

要弄清的是能否带来真实付款（核心假设）。

付款支持继续，拒绝反对继续（观察信号）。

有付款时重新决定，否则停止（复判条件）。""",
            "duplicate": """按目前信息，更合适的是先验证（当前判断：小步验证）。

要弄清的是能否带来真实付款（核心假设）。

另一个假设也需要验证（核心假设）。

先展示现有版本（本轮动作）。

付款支持继续，拒绝反对继续（观察信号）。

有付款时重新决定，否则停止（复判条件）。""",
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                checks = grade_b(text, already_executed=False, interaction=native_b_feedback())
                self.assert_has_failure(checks, "阶段 B 只有一个现实实验")

    def test_valid_b_with_locally_attributed_numbers(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。
原因很简单：真实付款会改变判断，持续没有付款就停止。

### 先做这一件事

这一步要弄清的是现实触达能否带来有区分力的反应（核心假设）。

用建议边界 500 元触达对象（本轮动作）。

把 15 人作为启发式起点，记录是否付款（观察信号）。

建议边界是至少 3 人付款才复判是否推进；无人付款就停止（复判条件）。
"""
        self.assert_all_pass(
            grade_b(
                text,
                already_executed=False,
                interaction=native_b_feedback(),
            )
        )

    def test_b_feedback_controls_are_not_questions_or_actions(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：调整）。
原因很简单：真实反馈会改变判断，若结果改善则继续，否则暂停。
### 先做这一件事

这一步要弄清的是明确责任边界能否改善合作（核心假设）。

只调整当前合作的责任边界（本轮动作）。

记录双方是否按新边界行动；履行支持继续，不履行则反对继续（观察信号）。

边界被履行则继续，否则重新决定是否暂停（复判条件）。"""
        self.assert_all_pass(grade_b(text, already_executed=True, interaction=native_b_feedback()))

    def test_b_components_without_blank_lines_fail_layout(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。

真实付款会改变判断，没有付款就停止。

### 先做这一件事


这一步要弄清的是当前方案能否带来真实付款（核心假设）。

验证真实付款（本轮动作）。
记录付款或明确拒绝（观察信号）。
有付款就推进，否则停止（复判条件）。"""
        checks = grade_b(text, already_executed=False, interaction=native_b_feedback())
        self.assert_has_failure(checks, "阶段 B 的核心假设、本轮动作、观察信号和复判条件以自然句分别成段并后置标记")

    def test_b_with_question_fails(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：暂停）。
真实结果改善则继续，否则停止。
### 先做这一件事

这一步要弄清的是暂停投入后现实结果是否改善（核心假设）。

暂停新增投入（本轮动作）。

记录现实结果（观察信号）。

结果改善则继续，否则停止（复判条件）。
你还想继续吗？"""
        checks = grade_b(text, already_executed=True, interaction=native_b_feedback())
        self.assert_has_failure(checks, "阶段 B 只提出一个反馈问题，不追加决策信息问题")

    def test_b_unexplained_precise_numbers_fail(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。
真实付款会改变判断，没有付款就停止。
### 先做这一件事

这一步要弄清的是有限触达能否带来真实付款（核心假设）。

用 500 元触达对象（本轮动作）。

记录 15 人中是否有人付款（观察信号）。

至少 3 人付款才推进，否则停止（复判条件）。"""
        checks = grade_b(text, already_executed=False, interaction=native_b_feedback())
        self.assert_has_failure(checks, "阶段 B 的每个系统新增数字都有局部来源或建议性质")

    def test_b_one_global_disclaimer_does_not_cover_other_numbers(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。
真实付款会改变判断，没有付款就停止。
### 先做这一件事

这一步要弄清的是有限触达能否带来真实付款（核心假设）。

建议边界是先用 500 元触达对象（本轮动作）。

记录 15 人中是否有人付款（观察信号）。

至少 3 人付款才推进，否则停止（复判条件）。"""
        checks = grade_b(text, already_executed=False, interaction=native_b_feedback())
        self.assert_has_failure(checks, "阶段 B 的每个系统新增数字都有局部来源或建议性质")

    def test_b_reuses_user_provided_numbers(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。
真实付款会改变判断，没有付款就停止。
### 先做这一件事

这一步要弄清的是用户给定边界内能否带来真实付款（核心假设）。

按你说的 500 元预算触达对象（本轮动作）。

记录十个人中是否有人付款（观察信号）。

达到百分之十的付款比例就推进，否则停止（复判条件）。"""
        self.assert_all_pass(
            grade_b(
                text,
                already_executed=False,
                user_numbers=["500 元", "十个人", "百分之十"],
                interaction=native_b_feedback(),
            )
        )

    def test_b_duplicate_heading_fails(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。
真实付款会改变判断，没有付款就停止。
### 先做这一件事
### 先做这一件事

这一步要弄清的是当前方案能否带来真实付款（核心假设）。

验证付款（本轮动作）。

记录结果（观察信号）。

有付款就推进，否则停止（复判条件）。"""
        checks = grade_b(text, already_executed=False, interaction=native_b_feedback())
        self.assert_has_failure(checks, "阶段 B 不含重复标题")

    def test_b_external_before_experiment_fails(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。
先做外部验证。
真实付款会改变判断，没有付款就停止。
### 先做这一件事

这一步要弄清的是当前方案能否带来真实付款（核心假设）。

验证付款（本轮动作）。

记录结果（观察信号）。

有付款就推进，否则停止（复判条件）。"""
        checks = grade_b(text, already_executed=False, interaction=native_b_feedback())
        self.assert_has_failure(checks, "可选外部验证位于完整判断和现实实验之后")

    def test_b_with_parallel_actions_fails(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：调整）。
真实付款会改变判断，没有付款就停止。
### 先做这一件事

这一步要弄清的是多项改动能否共同验证同一个方向（核心假设）。

1. 访谈用户。
2. 重写首页。
3. 发起预售（本轮动作）。

记录结果（观察信号）。
有付款就继续，否则停止（复判条件）。"""
        checks = grade_b(text, already_executed=True, interaction=native_b_feedback())
        self.assert_has_failure(checks, "阶段 B 只有一个现实实验")

    def test_b_action_observe_review_are_not_three_actions(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：调整）。
现实结果改善就继续，否则暂停。
### 先做这一件事

这一步要弄清的是明确合作边界能否改善履行（核心假设）。

只改一个合作边界（本轮动作）。

记录是否履行；履行支持继续，不履行则反对继续（观察信号）。

履行就继续，否则重新决定是否暂停（复判条件）。"""
        self.assert_all_pass(grade_b(text, already_executed=True, interaction=native_b_feedback()))

    def test_b_that_infers_authorization_fails(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。
稳定需求会改变判断，没有需求就停止。
### 先做这一件事

这一步要弄清的是当前方向能否得到真实需求信号（核心假设）。

既然你已经授权联网，所以我会自动联系潜在客户（本轮动作）。

记录回复（观察信号）。

有需求就继续，否则停止（复判条件）。"""
        checks = grade_b(text, already_executed=False, interaction=native_b_feedback())
        self.assert_has_failure(checks, "阶段 B 不把一种授权推定为另一种")

    def test_valid_b_with_native_note(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。
真实付款会改变判断，没有付款就停止。

### 先做这一件事


这一步要弄清的是现有版本能否产生有区分力的现实反应（核心假设）。

展示现有版本并邀请真实付款（本轮动作）。

记录付款或明确拒绝（观察信号）。

有付款就重新判断是否推进，否则停止（复判条件）。"""
        self.assert_all_pass(
            grade_b(text, already_executed=False, interaction=native_b_feedback("native-note"))
        )

    def test_valid_b_text_fallback_matrix(self) -> None:
        base = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。
真实付款会改变判断，没有付款就停止。

### 先做这一件事


这一步要弄清的是现有版本能否产生有区分力的现实反应（核心假设）。

展示现有版本并邀请真实付款（本轮动作）。

记录付款或明确拒绝（观察信号）。

有付款就重新判断是否推进，否则停止（复判条件）。"""
        text = with_feedback_fallback(base)
        for status in ("unavailable", "failed", "rejected"):
            with self.subTest(status=status):
                self.assert_all_pass(
                    grade_b(text, already_executed=False, interaction=b_text_fallback(status))
                )

    def test_b_available_host_cannot_use_text_fallback(self) -> None:
        text = with_feedback_fallback("""按目前信息，当前更合适的方向如下（当前判断：小步验证）。
真实付款会改变判断，没有付款就停止。
### 先做这一件事

这一步要弄清的是现有版本能否产生有区分力的现实反应（核心假设）。

展示现有版本并邀请真实付款（本轮动作）。

记录付款或明确拒绝（观察信号）。

有付款就重新判断是否推进，否则停止（复判条件）。""")
        interaction = InteractionEvidence(
            host_control_status="available",
            surface="text-fallback",
            tool_call_observed=False,
            selection_mode="single",
            supplement_mode="inline-text",
        )
        checks = grade_b(text, already_executed=False, interaction=interaction)
        self.assert_has_failure(checks, "阶段 B 按宿主能力使用原生反馈单选或明确文本降级")

    def test_b_native_feedback_requires_single(self) -> None:
        interaction = InteractionEvidence(
            host_control_status="available",
            surface="native-control",
            tool_call_observed=True,
            selection_mode="multi",
            options=FEEDBACK_OPTIONS,
            question_text=native_b_feedback().question_text,
            supplement_mode="follow-up-message",
        )
        text = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。
真实付款会改变判断，没有付款就停止。
### 先做这一件事

这一步要弄清的是现有版本能否产生有区分力的现实反应（核心假设）。

展示现有版本（本轮动作）。

记录结果（观察信号）。

有付款就推进，否则停止（复判条件）。"""
        checks = grade_b(text, already_executed=False, interaction=interaction)
        self.assert_has_failure(checks, "阶段 B 按宿主能力使用原生反馈单选或明确文本降级")

    def test_b_feedback_options_must_be_exact_and_ordered(self) -> None:
        interaction = InteractionEvidence(
            host_control_status="available",
            surface="native-control",
            tool_call_observed=True,
            selection_mode="single",
            options=("调整下一步", "方向符合我", "不同意这个判断", "Other"),
            question_text=native_b_feedback().question_text,
            supplement_mode="follow-up-message",
        )
        text = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。
真实付款会改变判断，没有付款就停止。
### 先做这一件事

这一步要弄清的是现有版本能否产生有区分力的现实反应（核心假设）。

展示现有版本（本轮动作）。

记录结果（观察信号）。

有付款就推进，否则停止（复判条件）。"""
        checks = grade_b(text, already_executed=False, interaction=interaction)
        self.assert_has_failure(checks, "阶段 B 恰好提供四个稳定反馈方向")

    def test_b_native_feedback_cannot_repeat_pseudo_buttons(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。
真实付款会改变判断，没有付款就停止。
### 先做这一件事

这一步要弄清的是现有版本能否产生有区分力的现实反应（核心假设）。

展示现有版本（本轮动作）。

记录结果（观察信号）。

有付款就推进，否则停止（复判条件）。

[方向符合我]
[调整下一步]
[不同意这个判断]
[暂时先放一放]"""
        checks = grade_b(text, already_executed=False, interaction=native_b_feedback())
        self.assert_has_failure(checks, "阶段 B 清楚区分原生反馈与文本降级并诚实说明补充通道")

    def test_b_fallback_rejects_pseudo_radio(self) -> None:
        text = with_feedback_fallback("""按目前信息，当前更合适的方向如下（当前判断：小步验证）。
真实付款会改变判断，没有付款就停止。
### 先做这一件事

这一步要弄清的是现有版本能否产生有区分力的现实反应（核心假设）。

展示现有版本（本轮动作）。

记录结果（观察信号）。

有付款就推进，否则停止（复判条件）。""").replace("1. 方向符合我", "○ 方向符合我")
        checks = grade_b(text, already_executed=False, interaction=b_text_fallback())
        self.assert_has_failure(checks, "阶段 B 恰好提供四个稳定反馈方向")
        self.assert_has_failure(checks, "阶段 B 清楚区分原生反馈与文本降级并诚实说明补充通道")

    def test_b_other_cannot_claim_native_note(self) -> None:
        interaction = InteractionEvidence(
            host_control_status="available",
            surface="native-control",
            tool_call_observed=True,
            selection_mode="single",
            options=FEEDBACK_OPTIONS,
            host_free_text_available=True,
            question_text=native_b_feedback().question_text,
            supplement_mode="native-note",
        )
        text = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。
真实付款会改变判断，没有付款就停止。
### 先做这一件事

这一步要弄清的是现有版本能否产生有区分力的现实反应（核心假设）。

展示现有版本（本轮动作）。

记录结果（观察信号）。

有付款就推进，否则停止（复判条件）。"""
        checks = grade_b(text, already_executed=False, interaction=interaction)
        self.assert_has_failure(checks, "阶段 B 清楚区分原生反馈与文本降级并诚实说明补充通道")

    def test_b_feedback_selection_does_not_authorize_execution(self) -> None:
        text = """按目前信息，当前更合适的方向如下（当前判断：小步验证）。
真实付款会改变判断，没有付款就停止。
### 先做这一件事

这一步要弄清的是当前方案能否带来真实付款（核心假设）。

你选择方向符合我，因此我会立即执行实验并联系客户（本轮动作）。

记录结果（观察信号）。

有付款就推进，否则停止（复判条件）。"""
        checks = grade_b(text, already_executed=False, interaction=native_b_feedback())
        self.assert_has_failure(checks, "阶段 B 不把一种授权推定为另一种")

    def test_fixture_19_cases_execute_current_grader(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "skills"
            / "think-it-through"
            / "evals"
            / "fixtures"
            / "19-contextual-checkpoint.json"
        )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.assertIn("不是自然语言自动发现", fixture["notice"])
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                context = CheckpointContext.from_dict(case["context"])
                observed = case.get("observed_interaction")
                interaction = (
                    InteractionEvidence.from_dict(
                        observed,
                        option_contract="checkpoint",
                    )
                    if observed is not None
                    else None
                )
                checks = grade_checkpoint(
                    case["assistant_text"],
                    context,
                    interaction,
                )
                failed = [check.text for check in checks if not check.passed]
                if case["must_pass"]:
                    self.assertEqual([], failed)
                else:
                    self.assertTrue(case.get("must_fail"))
                    self.assertTrue(failed, "负例必须由 current grader 拒绝")

        base_case = fixture["cases"][0]
        for reset_case in fixture["reset_cases"]:
            with self.subTest(reset=reset_case["id"]):
                context_data = {
                    **base_case["context"],
                    "same_decision_cooling_down": True,
                    "material_change": reset_case["material_change"],
                }
                self.assert_all_pass(
                    grade_checkpoint(
                        base_case["assistant_text"],
                        CheckpointContext.from_dict(context_data),
                        InteractionEvidence.from_dict(
                            base_case["observed_interaction"],
                            option_contract="checkpoint",
                        ),
                    )
                )

    def test_fixture_14_method_cases_execute_current_grader(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "skills"
            / "think-it-through"
            / "evals"
            / "fixtures"
            / "14-inline-method-recommendation.json"
        )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        cases = fixture["cases"][:2]
        for case in cases:
            with self.subTest(case=case["id"]):
                interaction = InteractionEvidence.from_dict(case["observed_interaction"])
                checks = grade_r(
                    case["assistant_text"],
                    case["recommended_methods"],
                    r_mode=case["r_mode"],
                    interaction=interaction,
                    answer_shape=case["answer_shape"],
                )
                failed = [check.text for check in checks if not check.passed]
                if case.get("must_pass"):
                    self.assertEqual([], failed)
                else:
                    self.assertTrue(failed)

    def test_fixture_15_valid_evidence_case_executes_current_grader(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "skills"
            / "think-it-through"
            / "evals"
            / "fixtures"
            / "15-evidence-gate.json"
        )
        case = json.loads(fixture_path.read_text(encoding="utf-8"))["cases"][0]
        self.assert_all_pass(
            grade_evidence_gate(case["record"], case["consent"], case["receipt"])
        )

    def test_fixture_16_valid_participation_case_executes_current_grader(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "skills"
            / "think-it-through"
            / "evals"
            / "fixtures"
            / "16-participation-and-human.json"
        )
        case = json.loads(fixture_path.read_text(encoding="utf-8"))["cases"][0]
        self.assert_all_pass(
            grade_participation_gate(case["record"], case["consent"], case["receipt"])
        )

    def test_fixture_17_decision_record_executes_current_grader(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "skills"
            / "think-it-through"
            / "evals"
            / "fixtures"
            / "17-portable-adapters-and-decision-record.json"
        )
        record = json.loads(fixture_path.read_text(encoding="utf-8"))["decision_record"]
        self.assert_all_pass(grade_decision_record(record))

    def test_fixture_12_b_cases_execute_current_grader(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "skills"
            / "think-it-through"
            / "evals"
            / "fixtures"
            / "12-native-control-and-fallback.json"
        )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        b_cases = [
            case
            for case in fixture["cases"]
            if case.get("expected_stage") == "B"
        ]
        self.assertEqual(8, len(b_cases))

        for case in b_cases:
            with self.subTest(case=case["id"]):
                text = "\n\n".join(case["assistant_shape"])
                interaction = InteractionEvidence.from_dict(case["observed_interaction"])
                checks = grade_b(text, already_executed=False, interaction=interaction)
                failed = [check.text for check in checks if not check.passed]
                if case.get("must_pass"):
                    self.assertEqual([], failed)
                else:
                    self.assertTrue(case.get("must_fail"))
                    self.assertTrue(failed, "负例必须由 current grader 拒绝")

    @staticmethod
    def capability_consent(consent_type: str = "capability_call") -> dict[str, object]:
        return {
            "consent_id": f"consent-{consent_type}",
            "consent_type": consent_type,
            "status": "granted",
            "scope": {
                "purpose": "回答会改变是否继续投入的关键问题",
                "operations": ["只读公开检索" if consent_type == "capability_call" else "委派独立分析任务"],
                "resources": ["公开网页" if consent_type == "capability_call" else "已列明的独立任务"],
                "data_boundary": ["只使用本轮明确提供的最小上下文"],
                "excluded": ["私有文件", "外部行动"],
            },
            "valid_for": "this_action",
            "requested_by": "main_agent",
            "granted_by": "user",
        }

    @staticmethod
    def evidence_receipt(status: str = "completed") -> dict[str, object]:
        return {
            "contract_version": "0.3.0",
            "capabilities": [
                {
                    "name": "search.public_web",
                    "availability": "available",
                    "readiness": "ready",
                    "provider": "test-search",
                    "limits": ["公开只读"],
                    "evidence": "本轮 fixture 声明",
                }
            ],
            "operations": [
                {
                    "receipt_id": "receipt-research",
                    "kind": "research",
                    "status": status,
                    "provider": "test-search",
                    "scope": ["中国市场", "2026 年"],
                    "consent_ids": ["consent-capability_call"],
                    "sources": (
                        [
                            {
                                "title": "官方市场说明",
                                "locator": "https://example.com/official",
                                "retrieved_at": "2026-08-29T00:00:00Z",
                                "source_type": "primary",
                            }
                        ]
                        if status in {"completed", "partial"}
                        else []
                    ),
                    "private_data_accessed": False,
                    "external_action_executed": False,
                    "fallback": "保留未知并转为现实实验" if status != "completed" else "",
                }
            ],
        }

    @staticmethod
    def valid_evidence_record() -> dict[str, object]:
        return {
            "unknown_type": "external_verifiable_fact",
            "decision_sensitive": True,
            "bounded": True,
            "value_exceeds_cost": True,
            "decision": "是否继续投入该市场",
            "question": "当前法规是否允许该交付模式",
            "scope": ["中国市场", "2026 年"],
            "stop_conditions": ["找到直接适用的官方条款"],
            "source_requirements": ["一手官方来源优先", "主动寻找反对证据"],
            "capability": {
                "availability": "available",
                "readiness": "ready",
                "provider": "test-search",
            },
            "capability_called": True,
            "supporting_evidence": ["官方条款支持有限场景"],
            "opposing_evidence": ["部分地区要求额外许可"],
            "conflicts_and_gaps": ["地区执行细则仍有差异"],
            "evidence_date": "2026-08-29",
            "impact_on_judgment": "changed",
        }

    def test_valid_evidence_gate(self) -> None:
        self.assert_all_pass(
            grade_evidence_gate(
                self.valid_evidence_record(),
                self.capability_consent(),
                self.evidence_receipt(),
            )
        )

    def test_evidence_gate_rejects_value_question_and_missing_consent(self) -> None:
        record = {**self.valid_evidence_record(), "unknown_type": "user_value"}
        checks = grade_evidence_gate(record, None, self.evidence_receipt())
        self.assert_has_failure(checks, "Evidence Gate 只路由决定敏感的外部可验证事实")
        self.assert_has_failure(checks, "Evidence Gate 能力可用且已取得本次能力授权")

    def test_evidence_gate_failed_receipt_requires_fallback(self) -> None:
        receipt = self.evidence_receipt("failed")
        receipt["operations"][0]["fallback"] = ""
        checks = grade_evidence_gate(
            self.valid_evidence_record(),
            self.capability_consent(),
            receipt,
        )
        self.assert_has_failure(checks, "Evidence Gate 失败或拒绝后保留未知并给出降级")

    @staticmethod
    def participation_receipt() -> dict[str, object]:
        return {
            "contract_version": "0.3.0",
            "capabilities": [
                {
                    "name": "agents.subagent",
                    "availability": "available",
                    "readiness": "ready",
                    "provider": "test-host",
                }
            ],
            "operations": [
                {
                    "receipt_id": "receipt-delegation",
                    "kind": "delegation",
                    "status": "completed",
                    "provider": "test-host",
                    "scope": ["两个不重复的独立任务"],
                    "consent_ids": ["consent-participation_delegation"],
                    "agent_counts": {
                        "main": 1,
                        "planned_additional": 2,
                        "started_additional": 2,
                        "completed_additional": 1,
                        "failed_additional": 1,
                        "actual_total": 3,
                    },
                    "completed_tasks": ["核验市场来源"],
                    "failed_tasks": ["独立反证审计"],
                    "conflicts_and_gaps": ["反证审计未完成"],
                    "private_data_accessed": False,
                    "external_action_executed": False,
                    "fallback": "由主 Agent 基于已完成材料继续综合",
                }
            ],
        }

    @staticmethod
    def valid_participation_record() -> dict[str, object]:
        payload = {
            "assigned_question": "核验一个独立问题",
            "claims": ["存在一项可核验主张"],
            "evidence_and_sources": ["来源与主张对应"],
            "assumptions": ["市场范围不变"],
            "uncertainties": ["地区执行差异"],
            "conflicts": ["来源发布时间不同"],
            "what_would_reverse_this": ["新官方条款"],
        }
        return {
            "tasks": ["核验市场来源", "独立反证审计"],
            "independent_task_count": 2,
            "user_total_limit": 4,
            "product_additional_limit": 3,
            "host_additional_limit": 3,
            "budget_additional_limit": 2,
            "planned_additional": 2,
            "data_boundaries": ["仅共享已确认事实"],
            "excluded_data": ["完整私有会话"],
            "relative_cost_and_latency": "模型调用与等待时间相对增加",
            "failure_fallback": "任一任务失败仍由主 Agent 基于有效材料继续",
            "consent_options": ["按建议启用", "降低数量", "保持单 Agent"],
            "recursive_delegation_allowed": False,
            "agent_payloads": [payload, {**payload, "assigned_question": "独立尝试推翻当前判断"}],
            "aggregation": "synthesis_not_vote",
            "synthesis": "去重来源、呈现冲突后形成一个综合判断",
        }

    def test_valid_participation_gate(self) -> None:
        self.assert_all_pass(
            grade_participation_gate(
                self.valid_participation_record(),
                self.capability_consent("participation_delegation"),
                self.participation_receipt(),
            )
        )

    def test_participation_gate_rejects_count_over_limit(self) -> None:
        record = {**self.valid_participation_record(), "user_total_limit": 2}
        checks = grade_participation_gate(
            record,
            self.capability_consent("participation_delegation"),
            self.participation_receipt(),
        )
        self.assert_has_failure(checks, "Participation Gate Agent 数量遵守总上限公式")

    def test_participation_gate_rejects_recursive_or_vote_aggregation(self) -> None:
        record = {
            **self.valid_participation_record(),
            "recursive_delegation_allowed": True,
            "aggregation": "majority_vote",
        }
        checks = grade_participation_gate(
            record,
            self.capability_consent("participation_delegation"),
            self.participation_receipt(),
        )
        self.assert_has_failure(checks, "Participation Gate 额外 Agent 不递归委派且只收最小上下文")
        self.assert_has_failure(checks, "Participation Gate 由主 Agent 综合且不按多数票")

    def test_participation_receipt_rejects_inconsistent_counts(self) -> None:
        receipt = self.participation_receipt()
        receipt["operations"][0]["agent_counts"]["actual_total"] = 2
        checks = grade_participation_gate(
            self.valid_participation_record(),
            self.capability_consent("participation_delegation"),
            receipt,
        )
        self.assert_has_failure(checks, "Participation Gate 协作回执数量关系真实一致")

    def test_human_review_defaults_to_forwardable_draft(self) -> None:
        record = {
            "why_needed": "只有负责人掌握预算承诺",
            "question": "是否愿意承担本轮预算",
            "minimal_context": "当前需要决定是否继续投入",
            "excluded_private_context": "不共享其他人的私密意见",
            "decision_impact": "拒绝承诺时转为小步验证",
            "sender_and_collector": "由用户自行发送并收集",
            "forwardable_draft": "我们正在判断是否继续投入，请只回答你愿意承担的预算边界。",
            "external_action_executed": False,
        }
        self.assert_all_pass(grade_human_review(record))
        checks = grade_human_review({**record, "external_action_executed": True})
        self.assert_has_failure(checks, "真人参与默认只生成材料，不自动发送或联系")

    @staticmethod
    def valid_decision_record() -> dict[str, object]:
        return {
            "contract_version": "0.3.0",
            "topic": "是否继续开发当前产品",
            "true_objectives": ["验证陌生客户是否愿意付费"],
            "decision": "继续开发还是先验证付费意愿",
            "confirmed_methods": ["two-sided-steelman"],
            "judgment": {
                "state": "small_test",
                "recommendation": "先验证真实付款，再决定是否继续开发",
                "rationale": ["付费意愿仍是会改变决定的最大未知"],
                "validity_conditions": ["现有版本足以展示核心价值"],
            },
            "evidence": {
                "confirmed_facts": ["用户已有可展示版本"],
                "inferences": ["继续开发可能暂时无法减少最大未知"],
                "assumptions": ["陌生对象反馈比熟人反馈更能区分方向"],
                "unknowns": ["陌生对象是否愿意真实付款"],
                "sources": [],
            },
            "reversal_signals": ["出现真实付款"],
            "main_experiment": {
                "core_hypothesis": "现有版本解决了足以付费的问题",
                "action": "向符合画像的陌生对象展示现有版本并邀请真实付款",
                "observation": "记录付款、明确拒绝与拒绝理由",
                "reassessment": "出现真实付款时复判是否推进，否则停止新增投入",
                "user_supplied_boundaries": [],
                "suggested_boundaries": [],
            },
            "reassessment_triggers": ["出现真实付款或持续只有明确拒绝"],
            "participation_and_capabilities": {
                "main_agents": 1,
                "additional_agents_planned": 0,
                "additional_agents_started": 0,
                "additional_agents_completed": 0,
                "additional_agents_failed": 0,
                "human_participants_requested": [],
                "capabilities_used": [],
                "private_data_accessed": False,
                "external_action_executed": False,
                "consent_ids": [],
                "receipt_ids": [],
                "conflicts_and_gaps": [],
            },
            "persistence": {
                "mode": "conversation_only",
                "authorized": False,
            },
        }

    def test_valid_decision_record(self) -> None:
        self.assert_all_pass(grade_decision_record(self.valid_decision_record()))

    def test_decision_record_requires_authorization_for_persistence(self) -> None:
        record = self.valid_decision_record()
        record["persistence"] = {
            "mode": "authorized_file",
            "authorized": True,
        }
        checks = grade_decision_record(record)
        self.assert_has_failure(checks, "DecisionRecord 默认仅在对话中，持久化需明确授权")

    def test_decision_record_rejects_inconsistent_agent_counts(self) -> None:
        record = self.valid_decision_record()
        record["participation_and_capabilities"]["additional_agents_planned"] = 1
        record["participation_and_capabilities"]["additional_agents_started"] = 2
        checks = grade_decision_record(record)
        self.assert_has_failure(checks, "DecisionRecord 参与与能力记录数量一致")

    def test_b_feedback_routes(self) -> None:
        cases = (
            ("accept", "none", "end", True, False),
            ("set-aside", "none", "end", True, False),
            ("adjust-next-step", "none", "R-method", True, False),
            ("disagree", "none", "R-method", False, False),
            ("accept", "consistent", "end", True, False),
            ("accept", "experiment-adjustment", "R-method", True, True),
            ("accept", "new-fact", "R-method", False, True),
            ("accept", "purpose-change", "R-align", False, True),
        )
        for direction, supplement, stage, preserve, overridden in cases:
            with self.subTest(direction=direction, supplement=supplement):
                route = resolve_b_feedback_route(direction, supplement)
                self.assertEqual(stage, route.next_stage)
                self.assertEqual(preserve, route.preserve_judgment)
                self.assertEqual(overridden, route.text_overrode_selection)

    def test_b_feedback_routes_reject_unknown_values(self) -> None:
        with self.assertRaises(ValueError):
            resolve_b_feedback_route("unknown")
        with self.assertRaises(ValueError):
            resolve_b_feedback_route("accept", "unknown")


if __name__ == "__main__":
    unittest.main()