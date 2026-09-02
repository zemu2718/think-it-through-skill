#!/usr/bin/env python3
"""用合规和违规样本验证 v0.4.1 机械合同评分器。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from grade_contracts import (
    PROJECT_CANDIDATE_CATEGORIES,
    CheckpointContext,
    InteractionEvidence,
    InteractionOption,
    extract_number_phrases,
    grade,
    grade_a,
    grade_b as grade_b_output,
    grade_checkpoint,
    grade_decision_record,
    grade_evidence_gate,
    grade_human_review,
    grade_participation_gate,
    grade_project_viability,
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


def b_snapshot_bundle() -> tuple[dict[str, object], dict[str, object]]:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "skills"
        / "think-it-through"
        / "evals"
        / "fixtures"
        / "17-portable-adapters-and-decision-record.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    return fixture["decision_record"], fixture["visible_snapshot"]


def render_b_snapshot(snapshot: dict[str, object]) -> str:
    lines = ["## 决策快照"]
    lines.extend(
        f"{label}：{item['rendered']}"
        for label, item in snapshot.items()
    )
    return "\n\n".join(lines)


def _insert_snapshot_before_feedback(
    text: str,
    snapshot: dict[str, object],
) -> str:
    snapshot_text = render_b_snapshot(snapshot)
    marker = "### 反馈"
    if marker not in text:
        return f"{text.rstrip()}\n\n{snapshot_text}"
    position = text.index(marker)
    return (
        text[:position].rstrip()
        + "\n\n"
        + snapshot_text
        + "\n\n"
        + text[position:]
    )


def grade_b(*args, **kwargs):
    record, snapshot = b_snapshot_bundle()
    kwargs.setdefault("decision_record", record)
    kwargs.setdefault("visible_snapshot", snapshot)
    if args:
        args = (
            _insert_snapshot_before_feedback(args[0], kwargs["visible_snapshot"]),
            *args[1:],
        )
    else:
        kwargs["text"] = _insert_snapshot_before_feedback(
            kwargs["text"],
            kwargs["visible_snapshot"],
        )
    return grade_b_output(*args, **kwargs)


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

    def test_fixture_08_method_fallback_cases_preserve_trace(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "skills"
            / "think-it-through"
            / "evals"
            / "fixtures"
            / "08-interactive-method-adjustment.json"
        )
        cases = json.loads(fixture_path.read_text(encoding="utf-8"))["fallback_cases"]
        self.assertEqual(
            {"unavailable", "failed", "rejected"},
            {case["host_control_status"] for case in cases},
        )
        for case in cases:
            with self.subTest(status=case["host_control_status"]):
                interaction = InteractionEvidence.from_dict(case)
                self.assertEqual("text-fallback", interaction.surface)
                self.assertEqual("multi", interaction.selection_mode)
                self.assertEqual(
                    case["host_control_status"] in {"failed", "rejected"},
                    interaction.tool_call_observed,
                )
                self.assertTrue(case["must_preserve_selection_semantics"])
                self.assertTrue(case["must_preserve_structured_method_meaning"])
                self.assertTrue(case["must_not_retry_same_call"])

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
                body = "\n\n".join(case["assistant_shape"])
                snapshot_text = render_b_snapshot(case["visible_snapshot"])
                if case["observed_interaction"]["surface"] == "text-fallback":
                    feedback_position = body.index("### 反馈")
                    text = (
                        body[:feedback_position].rstrip()
                        + "\n\n"
                        + snapshot_text
                        + "\n\n"
                        + body[feedback_position:]
                    )
                else:
                    text = f"{body}\n\n{snapshot_text}"
                interaction = InteractionEvidence.from_dict(case["observed_interaction"])
                checks = grade_b_output(
                    text,
                    already_executed=False,
                    interaction=interaction,
                    decision_record=case.get("decision_record"),
                    visible_snapshot=case.get("visible_snapshot"),
                )
                failed = [check.text for check in checks if not check.passed]
                if case.get("must_pass"):
                    self.assertEqual([], failed)
                else:
                    self.assertTrue(case.get("must_fail"))
                    self.assertTrue(failed, "负例必须由 current grader 拒绝")

    def test_b_requires_bound_lossless_visible_snapshot(self) -> None:
        record, snapshot = b_snapshot_bundle()
        text = """按目前信息，更合适的是先验证真实付款（当前判断：小步验证）。

这一步要弄清的是现有版本能否带来真实付款（核心假设）。

展示现有版本并邀请真实付款（本轮动作）。

付款支持继续，持续拒绝则反对继续（观察信号）。

出现付款时重新决定是否推进，否则停止（复判条件）。"""
        failure_name = "阶段 B 包含与 canonical DecisionRecord 无损对应的可见决策快照"

        missing = grade_b_output(
            text,
            already_executed=False,
            interaction=native_b_feedback(),
        )
        self.assert_has_failure(missing, failure_name)

        unrendered = grade_b_output(
            text,
            already_executed=False,
            interaction=native_b_feedback(),
            decision_record=record,
            visible_snapshot=snapshot,
        )
        self.assert_has_failure(unrendered, failure_name)

        mutations = {
            "assumptions": "evidence.assumptions",
            "unknowns": "evidence.unknowns",
            "participation": "participation_and_capabilities",
            "persistence": "persistence",
        }
        for name, path in mutations.items():
            with self.subTest(name=name):
                mutated = json.loads(json.dumps(snapshot))
                label = next(
                    label
                    for label, item in mutated.items()
                    if item["path"] == path
                )
                del mutated[label]
                checks = grade_b_output(
                    f"{text}\n\n{render_b_snapshot(mutated)}",
                    already_executed=False,
                    interaction=native_b_feedback(),
                    decision_record=record,
                    visible_snapshot=mutated,
                )
                self.assert_has_failure(checks, failure_name)

        mismatched = json.loads(json.dumps(snapshot))
        assumptions = next(
            item
            for item in mismatched.values()
            if item["path"] == "evidence.assumptions"
        )
        assumptions["value"] = record["evidence"]["unknowns"]
        checks = grade_b_output(
            f"{text}\n\n{render_b_snapshot(mismatched)}",
            already_executed=False,
            interaction=native_b_feedback(),
            decision_record=record,
            visible_snapshot=mismatched,
        )
        self.assert_has_failure(checks, failure_name)

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
                "tasks": ["中国市场", "2026 年"] if consent_type == "capability_call" else ["两个不重复的独立任务", "核验市场来源", "独立反证审计"],
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
            "contract_version": "0.4.1",
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
                    "conflicts_and_gaps": ["地区执行细则仍有差异"],
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
            "cost_and_latency_disclosure": {
                "cost": "调用一次公开只读检索，不涉及付费购买",
                "latency": "需要等待一次工具调用返回",
            },
            "disclosure_timing": "before_consent",
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

    def test_evidence_gate_requires_cost_disclosure_before_consent(self) -> None:
        mutations = {
            "missing-disclosure": lambda record: record.pop("cost_and_latency_disclosure"),
            "empty-disclosure": lambda record: record.update(cost_and_latency_disclosure={}),
            "missing-cost": lambda record: record["cost_and_latency_disclosure"].pop("cost"),
            "empty-cost": lambda record: record["cost_and_latency_disclosure"].update(cost=""),
            "missing-latency": lambda record: record["cost_and_latency_disclosure"].pop("latency"),
            "empty-latency": lambda record: record["cost_and_latency_disclosure"].update(latency=""),
            "missing-timing": lambda record: record.pop("disclosure_timing"),
            "after-consent": lambda record: record.update(disclosure_timing="after_consent"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                record = self.valid_evidence_record()
                mutate(record)
                checks = grade_evidence_gate(
                    record,
                    self.capability_consent(),
                    self.evidence_receipt(),
                )
                self.assert_has_failure(
                    checks,
                    "Evidence Gate 在授权前披露具体成本与延迟",
                )
                self.assert_has_failure(
                    checks,
                    "Evidence Gate 能力可用且已取得本次能力授权",
                )

        record = self.valid_evidence_record()
        record["cost_and_latency_disclosure"] = {"cost": "", "latency": ""}
        record["value_exceeds_cost"] = True
        checks = grade_evidence_gate(
            record,
            self.capability_consent(),
            self.evidence_receipt(),
        )
        self.assert_has_failure(
            checks,
            "Evidence Gate 在授权前披露具体成本与延迟",
        )

    def test_evidence_gate_rejects_noncanonical_consent_and_receipt(self) -> None:
        consent_mutations = {
            "extra-key": lambda consent: consent.update(extra="not-allowed"),
            "saved-preference": lambda consent: consent.update(valid_for="saved_preference"),
            "invalid-date-time": lambda consent: consent.update(requested_at="not-a-date"),
        }
        for name, mutate in consent_mutations.items():
            with self.subTest(kind="consent", name=name):
                consent = self.capability_consent()
                mutate(consent)
                checks = grade_evidence_gate(
                    self.valid_evidence_record(),
                    consent,
                    self.evidence_receipt(),
                )
                self.assert_has_failure(
                    checks,
                    "Evidence Gate consent 符合 canonical schema",
                )

        receipt_mutations = {
            "wrong-version": lambda receipt: receipt.update(contract_version="0.4.0"),
            "nested-extra": lambda receipt: receipt["operations"][0].update(extra="not-allowed"),
            "invalid-enum": lambda receipt: receipt["operations"][0].update(status="done"),
            "invalid-date-time": lambda receipt: receipt["operations"][0].update(started_at="today"),
        }
        for name, mutate in receipt_mutations.items():
            with self.subTest(kind="receipt", name=name):
                receipt = self.evidence_receipt()
                mutate(receipt)
                checks = grade_evidence_gate(
                    self.valid_evidence_record(),
                    self.capability_consent(),
                    receipt,
                )
                self.assert_has_failure(
                    checks,
                    "Evidence Gate receipt bundle 符合 canonical schema",
                )

    def test_evidence_gate_terminal_matrix(self) -> None:
        cases = {
            "completed": {
                "record": {},
                "operation": {
                    "status": "completed",
                    "fallback": "",
                },
            },
            "partial": {
                "record": {},
                "operation": {
                    "status": "partial",
                    "fallback": "保留地区差异并降级为现实验证",
                },
            },
            "failed": {
                "record": {
                    "supporting_evidence": [],
                    "opposing_evidence": [],
                    "impact_on_judgment": "uncertain",
                },
                "operation": {
                    "status": "failed",
                    "sources": [],
                    "fallback": "保留未知并转为现实验证",
                },
            },
            "declined": {
                "record": {
                    "supporting_evidence": [],
                    "opposing_evidence": [],
                    "impact_on_judgment": "uncertain",
                },
                "operation": {
                    "status": "declined",
                    "sources": [],
                    "fallback": "保留未知并转为现实验证",
                },
            },
            "cancelled": {
                "record": {
                    "supporting_evidence": [],
                    "opposing_evidence": [],
                    "impact_on_judgment": "uncertain",
                },
                "operation": {
                    "status": "cancelled",
                    "sources": [],
                    "fallback": "保留未知并转为现实验证",
                },
            },
            "unavailable": {
                "record": {
                    "supporting_evidence": [],
                    "opposing_evidence": [],
                    "impact_on_judgment": "uncertain",
                },
                "operation": {
                    "status": "unavailable",
                    "sources": [],
                    "fallback": "保留未知并转为现实验证",
                },
            },
        }
        for status, changes in cases.items():
            with self.subTest(status=status):
                record = self.valid_evidence_record()
                record.update(changes["record"])
                receipt = self.evidence_receipt(status)
                receipt["operations"][0].update(changes["operation"])
                self.assert_all_pass(
                    grade_evidence_gate(record, self.capability_consent(), receipt)
                )

                invalid_receipt = json.loads(json.dumps(receipt))
                if status == "completed":
                    invalid_receipt["operations"][0]["fallback"] = "不应存在的降级"
                elif status == "partial":
                    invalid_receipt["operations"][0]["fallback"] = ""
                else:
                    invalid_receipt["operations"][0]["sources"] = [
                        {
                            "title": "不应存在的来源",
                            "locator": "https://example.com/unexpected",
                            "retrieved_at": "2026-09-03T00:00:00Z",
                        }
                    ]
                checks = grade_evidence_gate(
                    record,
                    self.capability_consent(),
                    invalid_receipt,
                )
                self.assert_has_failure(
                    checks,
                    "Evidence Gate 终态、材料、冲突、判断影响与降级一致",
                )

    def test_evidence_gate_failed_receipt_requires_fallback(self) -> None:
        receipt = self.evidence_receipt("failed")
        receipt["operations"][0]["fallback"] = ""
        checks = grade_evidence_gate(
            self.valid_evidence_record(),
            self.capability_consent(),
            receipt,
        )
        self.assert_has_failure(checks, "Evidence Gate 失败或拒绝后保留未知并给出降级")

    def test_evidence_gate_rejects_empty_sources_for_completed_research(self) -> None:
        receipt = self.evidence_receipt()
        receipt["operations"][0]["sources"] = []
        checks = grade_evidence_gate(
            self.valid_evidence_record(),
            self.capability_consent(),
            receipt,
        )
        self.assert_has_failure(checks, "Evidence Gate 记录支持、反对、冲突、日期和判断影响")

    def test_evidence_gate_rejects_provider_consent_scope_or_nonterminal_mismatch(self) -> None:
        cases = {
            "provider": lambda receipt: receipt["operations"][0].update(provider="other-provider"),
            "consent": lambda receipt: receipt["operations"][0].update(consent_ids=["other-consent"]),
            "scope": lambda receipt: receipt["operations"][0].update(scope=["未授权范围"]),
            "status": lambda receipt: receipt["operations"][0].update(status="started"),
            "private": lambda receipt: receipt["operations"][0].update(private_data_accessed=True),
            "external": lambda receipt: receipt["operations"][0].update(external_action_executed=True),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                receipt = self.evidence_receipt()
                mutate(receipt)
                checks = grade_evidence_gate(
                    self.valid_evidence_record(),
                    self.capability_consent(),
                    receipt,
                )
                self.assert_has_failure(
                    checks,
                    "Evidence Gate 真实调用具有授权关联、同一 provider、终态研究回执且不越权",
                )

    @staticmethod
    def participation_receipt() -> dict[str, object]:
        return {
            "contract_version": "0.4.1",
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
                    "status": "partial",
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
            "assigned_question": "核验市场来源",
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
            "agent_payloads": [payload],
            "aggregation": "synthesis_not_vote",
            "synthesis": {
                "completed_tasks": ["核验市场来源"],
                "adopted_material": ["来源与主张对应，可作为候选事实链"],
                "set_aside_material": ["不把未核验的 Agent 主张直接升级为现实事实"],
                "unresolved_material": ["独立反证审计", "地区执行差异仍未知"],
                "conflict_handling": "保留来源发布时间冲突，不按 Agent 数量消解",
                "judgment_impact": "只能支持有限判断，不能提高正式投入承诺",
                "main_reality_loop_impact": "用同一真实任务检验地区差异与核心行为",
            },
        }

    def test_valid_participation_gate(self) -> None:
        self.assert_all_pass(
            grade_participation_gate(
                self.valid_participation_record(),
                self.capability_consent("participation_delegation"),
                self.participation_receipt(),
            )
        )

    def test_participation_accepts_multiple_ready_agent_capabilities_for_same_provider(self) -> None:
        receipt = self.participation_receipt()
        receipt["capabilities"].append(
            {
                "name": "agents.parallel",
                "availability": "available",
                "readiness": "ready",
                "provider": "test-host",
            }
        )
        self.assert_all_pass(
            grade_participation_gate(
                self.valid_participation_record(),
                self.capability_consent("participation_delegation"),
                receipt,
            )
        )

    def test_participation_rejects_noncanonical_consent_and_receipt(self) -> None:
        consent = self.capability_consent("participation_delegation")
        consent["valid_for"] = "saved_preference"
        checks = grade_participation_gate(
            self.valid_participation_record(),
            consent,
            self.participation_receipt(),
        )
        self.assert_has_failure(
            checks,
            "Participation Gate consent 符合 canonical schema",
        )

        receipt = self.participation_receipt()
        receipt["operations"][0]["agent_counts"]["extra"] = 1
        checks = grade_participation_gate(
            self.valid_participation_record(),
            self.capability_consent("participation_delegation"),
            receipt,
        )
        self.assert_has_failure(
            checks,
            "Participation Gate receipt bundle 符合 canonical schema",
        )

    def test_participation_terminal_matrix(self) -> None:
        cases = {
            "completed": {
                "planned": 2,
                "started": 2,
                "completed": 2,
                "failed": 0,
                "completed_tasks": ["核验市场来源", "独立反证审计"],
                "failed_tasks": [],
                "payload_questions": ["核验市场来源", "独立反证审计"],
                "gaps": [],
                "fallback": "",
            },
            "partial": {
                "planned": 2,
                "started": 2,
                "completed": 1,
                "failed": 1,
                "completed_tasks": ["核验市场来源"],
                "failed_tasks": ["独立反证审计"],
                "payload_questions": ["核验市场来源"],
                "gaps": ["独立反证任务失败"],
                "fallback": "主 Agent 基于已完成材料继续",
            },
            "failed": {
                "planned": 2,
                "started": 2,
                "completed": 0,
                "failed": 2,
                "completed_tasks": [],
                "failed_tasks": ["核验市场来源", "独立反证审计"],
                "payload_questions": [],
                "gaps": ["两项任务均失败"],
                "fallback": "主 Agent 基于已有信息继续",
            },
            "declined": {
                "planned": 2,
                "started": 0,
                "completed": 0,
                "failed": 0,
                "completed_tasks": [],
                "failed_tasks": [],
                "payload_questions": [],
                "gaps": ["用户拒绝委派"],
                "fallback": "保持单 Agent 继续",
            },
            "cancelled": {
                "planned": 2,
                "started": 0,
                "completed": 0,
                "failed": 0,
                "completed_tasks": [],
                "failed_tasks": [],
                "payload_questions": [],
                "gaps": ["委派已取消"],
                "fallback": "保持单 Agent 继续",
            },
            "unavailable": {
                "planned": 2,
                "started": 0,
                "completed": 0,
                "failed": 0,
                "completed_tasks": [],
                "failed_tasks": [],
                "payload_questions": [],
                "gaps": ["当前宿主无额外 Agent 能力"],
                "fallback": "保持单 Agent 继续",
            },
        }
        for status, case in cases.items():
            with self.subTest(status=status):
                record = self.valid_participation_record()
                payload_template = record["agent_payloads"][0]
                record["agent_payloads"] = [
                    {**payload_template, "assigned_question": question}
                    for question in case["payload_questions"]
                ]
                receipt = self.participation_receipt()
                operation = receipt["operations"][0]
                operation.update(
                    status=status,
                    completed_tasks=case["completed_tasks"],
                    failed_tasks=case["failed_tasks"],
                    conflicts_and_gaps=case["gaps"],
                    fallback=case["fallback"],
                )
                operation["agent_counts"] = {
                    "main": 1,
                    "planned_additional": case["planned"],
                    "started_additional": case["started"],
                    "completed_additional": case["completed"],
                    "failed_additional": case["failed"],
                    "actual_total": 1 + case["started"],
                }
                record["synthesis"].update(
                    completed_tasks=case["completed_tasks"],
                    unresolved_material=(
                        case["failed_tasks"] + case["gaps"]
                        if case["failed_tasks"] or case["gaps"]
                        else ["已完成材料仍需现实行为验证"]
                    ),
                )
                self.assert_all_pass(
                    grade_participation_gate(
                        record,
                        self.capability_consent("participation_delegation"),
                        receipt,
                    )
                )

                invalid_receipt = json.loads(json.dumps(receipt))
                invalid_receipt["operations"][0]["agent_counts"]["actual_total"] += 1
                checks = grade_participation_gate(
                    record,
                    self.capability_consent("participation_delegation"),
                    invalid_receipt,
                )
                self.assert_has_failure(
                    checks,
                    "Participation Gate 协作回执的授权、provider、终态、任务、数量和降级真实一致",
                )

                invalid_terminal = json.loads(json.dumps(receipt))
                if status == "completed":
                    invalid_terminal["operations"][0]["fallback"] = "不应存在的降级"
                elif status == "partial":
                    invalid_terminal["operations"][0]["conflicts_and_gaps"] = []
                elif status == "failed":
                    invalid_terminal["operations"][0]["completed_tasks"] = ["核验市场来源"]
                    invalid_terminal["operations"][0]["failed_tasks"] = ["独立反证审计"]
                    invalid_terminal["operations"][0]["agent_counts"].update(
                        completed_additional=1,
                        failed_additional=1,
                    )
                else:
                    invalid_terminal["operations"][0]["agent_counts"].update(
                        started_additional=1,
                        failed_additional=1,
                        actual_total=2,
                    )
                    invalid_terminal["operations"][0]["failed_tasks"] = ["核验市场来源"]
                checks = grade_participation_gate(
                    record,
                    self.capability_consent("participation_delegation"),
                    invalid_terminal,
                )
                self.assert_has_failure(
                    checks,
                    "Participation Gate 协作回执的授权、provider、终态、任务、数量和降级真实一致",
                )

    def test_participation_malformed_arrays_fail_without_exception(self) -> None:
        mutations = {
            "record-task-object": lambda record, _receipt: record.update(tasks=[{"bad": "task"}]),
            "completed-task-object": lambda _record, receipt: receipt["operations"][0].update(completed_tasks=[{"bad": "task"}]),
            "failed-task-list": lambda _record, receipt: receipt["operations"][0].update(failed_tasks=[["nested"]]),
            "scope-object": lambda _record, receipt: receipt["operations"][0].update(scope=[{"bad": "scope"}]),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                record = self.valid_participation_record()
                receipt = self.participation_receipt()
                mutate(record, receipt)
                checks = grade_participation_gate(
                    record,
                    self.capability_consent("participation_delegation"),
                    receipt,
                )
                self.assertTrue(any(not check.passed and check.severe for check in checks))

    def test_participation_payload_requires_information_but_allows_empty_claims(self) -> None:
        record = self.valid_participation_record()
        payload = record["agent_payloads"][0]
        for field in (
            "claims",
            "evidence_and_sources",
            "assumptions",
            "uncertainties",
            "conflicts",
            "what_would_reverse_this",
        ):
            payload[field] = []
        checks = grade_participation_gate(
            record,
            self.capability_consent("participation_delegation"),
            self.participation_receipt(),
        )
        self.assert_has_failure(
            checks,
            "Participation Gate 额外 Agent 不递归委派且只收最小上下文",
        )

        record = self.valid_participation_record()
        record["agent_payloads"][0].update(
            claims=[],
            evidence_and_sources=[],
            assumptions=[],
            uncertainties=["尚无足够材料形成主张"],
            conflicts=[],
            what_would_reverse_this=[],
        )
        self.assert_all_pass(
            grade_participation_gate(
                record,
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
        self.assert_has_failure(
            checks,
            "Participation Gate 声明 synthesis_not_vote 且结构化综合绑定实际完成任务与判断闭环",
        )

    def test_participation_synthesis_requires_structured_trace(self) -> None:
        mutations = {
            "plain-text": lambda synthesis: "x",
            "missing-key": lambda synthesis: {
                key: value
                for key, value in synthesis.items()
                if key != "judgment_impact"
            },
            "wrong-completed-task": lambda synthesis: {
                **synthesis,
                "completed_tasks": ["独立反证审计"],
            },
            "all-material-empty": lambda synthesis: {
                **synthesis,
                "adopted_material": [],
                "set_aside_material": [],
                "unresolved_material": [],
            },
            "failed-task-gap-hidden": lambda synthesis: {
                **synthesis,
                "unresolved_material": ["另一个未知仍待核验"],
            },
            "empty-judgment-impact": lambda synthesis: {
                **synthesis,
                "judgment_impact": "",
            },
            "empty-reality-loop-impact": lambda synthesis: {
                **synthesis,
                "main_reality_loop_impact": "",
            },
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                record = self.valid_participation_record()
                record["synthesis"] = mutate(record["synthesis"])
                checks = grade_participation_gate(
                    record,
                    self.capability_consent("participation_delegation"),
                    self.participation_receipt(),
                )
                self.assert_has_failure(
                    checks,
                    "Participation Gate 声明 synthesis_not_vote 且结构化综合绑定实际完成任务与判断闭环",
                )

    def test_participation_receipt_rejects_inconsistent_counts(self) -> None:
        receipt = self.participation_receipt()
        receipt["operations"][0]["agent_counts"]["actual_total"] = 2
        checks = grade_participation_gate(
            self.valid_participation_record(),
            self.capability_consent("participation_delegation"),
            receipt,
        )
        self.assert_has_failure(
            checks,
            "Participation Gate 协作回执的授权、provider、终态、任务、数量和降级真实一致",
        )

    def test_participation_rejects_payload_extra_key(self) -> None:
        record = self.valid_participation_record()
        record["agent_payloads"][0]["main_judgment"] = "主 Agent 偏好自研"
        checks = grade_participation_gate(
            record,
            self.capability_consent("participation_delegation"),
            self.participation_receipt(),
        )
        self.assert_has_failure(
            checks,
            "Participation Gate 额外 Agent 不递归委派且只收最小上下文",
        )

    def test_participation_payloads_match_only_completed_tasks(self) -> None:
        cases = {
            "failed-task": "独立反证审计",
            "unknown-task": "未执行的其他任务",
        }
        for name, assigned_question in cases.items():
            with self.subTest(name=name):
                record = self.valid_participation_record()
                record["agent_payloads"][0]["assigned_question"] = assigned_question
                checks = grade_participation_gate(
                    record,
                    self.capability_consent("participation_delegation"),
                    self.participation_receipt(),
                )
                self.assert_has_failure(
                    checks,
                    "Participation Gate payload 只对应实际完成且唯一的任务",
                )

    def test_participation_rejects_duplicate_payload_for_completed_task(self) -> None:
        record = self.valid_participation_record()
        record["agent_payloads"].append(dict(record["agent_payloads"][0]))
        checks = grade_participation_gate(
            record,
            self.capability_consent("participation_delegation"),
            self.participation_receipt(),
        )
        self.assert_has_failure(
            checks,
            "Participation Gate payload 只对应实际完成且唯一的任务",
        )

    def test_participation_partial_receipt_requires_explicit_gap(self) -> None:
        receipt = self.participation_receipt()
        receipt["operations"][0]["conflicts_and_gaps"] = []
        checks = grade_participation_gate(
            self.valid_participation_record(),
            self.capability_consent("participation_delegation"),
            receipt,
        )
        self.assert_has_failure(
            checks,
            "Participation Gate 协作回执的授权、provider、终态、任务、数量和降级真实一致",
        )

    def test_project_candidate_categories_remain_stable(self) -> None:
        self.assertEqual(
            {
                "status_quo",
                "manual_or_process",
                "direct_competitor",
                "adjacent_category",
                "non_isomorphic_product_or_service",
                "platform_native",
                "active_open_source_or_commercial",
                "tool_combination",
                "plugin_script_or_thin_integration",
                "local_supplement",
                "independent_build",
            },
            PROJECT_CANDIDATE_CATEGORIES,
        )
        self.assertNotIn("subtractive_solution", PROJECT_CANDIDATE_CATEGORIES)

    def test_participation_rejects_receipt_link_provider_scope_status_tasks_or_fallback(self) -> None:
        cases = {
            "provider": lambda receipt: receipt["operations"][0].update(provider="other-provider"),
            "consent": lambda receipt: receipt["operations"][0].update(consent_ids=["other-consent"]),
            "scope": lambda receipt: receipt["operations"][0].update(scope=["未授权任务"]),
            "consent-tasks": lambda _receipt: None,
            "status": lambda receipt: receipt["operations"][0].update(status="completed"),
            "tasks": lambda receipt: receipt["operations"][0].update(completed_tasks=["未知任务"]),
            "fallback": lambda receipt: receipt["operations"][0].update(fallback=""),
            "private": lambda receipt: receipt["operations"][0].update(private_data_accessed=True),
            "external": lambda receipt: receipt["operations"][0].update(external_action_executed=True),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                receipt = self.participation_receipt()
                mutate(receipt)
                consent = self.capability_consent("participation_delegation")
                if name == "consent-tasks":
                    consent["scope"]["tasks"] = ["两个不重复的独立任务"]
                checks = grade_participation_gate(
                    self.valid_participation_record(),
                    consent,
                    receipt,
                )
                self.assert_has_failure(
                    checks,
                    "Participation Gate 协作回执的授权、provider、终态、任务、数量和降级真实一致",
                )

    @staticmethod
    def human_review_record(*, external_action_executed: bool = False) -> dict[str, object]:
        return {
            "why_needed": "只有负责人掌握预算承诺",
            "question": "是否愿意承担本轮预算",
            "minimal_context": "当前需要决定是否继续投入",
            "excluded_private_context": "不共享其他人的私密意见",
            "decision_impact": "拒绝承诺时转为小步验证",
            "sender_and_collector": "由主 Agent 通过预算负责人专用邮箱发送并收集",
            "forwardable_draft": "预算负责人：我们正在判断是否继续投入。问题是：是否愿意承担本轮预算？请只回答你愿意承担的预算边界。",
            "external_action_executed": external_action_executed,
        }

    @staticmethod
    def human_consent(consent_type: str) -> dict[str, object]:
        operation = (
            "请求预算负责人回答"
            if consent_type == "participation_delegation"
            else "通过专用邮箱发送"
        )
        resources = (
            ["预算负责人"]
            if consent_type == "participation_delegation"
            else ["预算负责人", "专用邮箱"]
        )
        return {
            "consent_id": f"consent-human-{consent_type}",
            "consent_type": consent_type,
            "status": "granted",
            "scope": {
                "purpose": "取得预算负责人对本轮预算的真实承诺",
                "operations": [operation],
                "resources": resources,
                "tasks": ["是否愿意承担本轮预算"],
                "data_boundary": ["只发送可转发草稿中的最小背景"],
                "excluded": ["其他人的私密意见", "无关外部行动"],
            },
            "valid_for": "this_action",
            "requested_by": "main_agent",
            "granted_by": "user",
        }

    @classmethod
    def human_receipt(cls) -> dict[str, object]:
        participation = cls.human_consent("participation_delegation")
        external = cls.human_consent("external_action")
        return {
            "contract_version": "0.4.1",
            "capabilities": [
                {
                    "name": "humans.request_review",
                    "availability": "available",
                    "readiness": "ready",
                    "provider": "test-mail",
                }
            ],
            "operations": [
                {
                    "receipt_id": "receipt-human-send",
                    "kind": "human_review",
                    "status": "completed",
                    "provider": "test-mail",
                    "scope": [
                        "是否愿意承担本轮预算",
                        "预算负责人",
                        "专用邮箱",
                        participation["scope"]["operations"][0],
                        external["scope"]["operations"][0],
                    ],
                    "consent_ids": [
                        participation["consent_id"],
                        external["consent_id"],
                    ],
                    "private_data_accessed": False,
                    "external_action_executed": True,
                    "fallback": "",
                }
            ],
        }

    def test_human_review_defaults_to_forwardable_draft(self) -> None:
        record = self.human_review_record()
        self.assert_all_pass(grade_human_review(record))
        checks = grade_human_review(self.human_review_record(external_action_executed=True))
        self.assert_has_failure(
            checks,
            "真人实际发送同时具有 participation 与 external-action 授权及双引用回执",
        )

    def test_human_authorized_send_requires_two_consents_and_linked_receipt(self) -> None:
        record = self.human_review_record(external_action_executed=True)
        participation = self.human_consent("participation_delegation")
        external = self.human_consent("external_action")
        receipt = self.human_receipt()
        self.assert_all_pass(
            grade_human_review(record, participation, external, receipt)
        )

        cases = {
            "missing-participation": (None, external, receipt),
            "missing-external": (participation, None, receipt),
            "wrong-participation-type": (
                {**participation, "consent_type": "capability_call"},
                external,
                receipt,
            ),
            "unlinked-external": (
                participation,
                external,
                {
                    **receipt,
                    "operations": [
                        {
                            **receipt["operations"][0],
                            "consent_ids": [participation["consent_id"]],
                        }
                    ],
                },
            ),
            "not-executed": (
                participation,
                external,
                {
                    **receipt,
                    "operations": [
                        {
                            **receipt["operations"][0],
                            "external_action_executed": False,
                        }
                    ],
                },
            ),
            "provider-mismatch": (
                participation,
                external,
                {
                    **receipt,
                    "capabilities": [
                        {
                            **receipt["capabilities"][0],
                            "provider": "different-mail-provider",
                        }
                    ],
                },
            ),
            "wrong-human": (
                {
                    **participation,
                    "scope": {
                        **participation["scope"],
                        "resources": ["财务负责人"],
                    },
                },
                external,
                receipt,
            ),
            "wrong-channel": (
                participation,
                {
                    **external,
                    "scope": {
                        **external["scope"],
                        "resources": ["预算负责人", "即时消息"],
                    },
                },
                receipt,
            ),
            "shared-task-only": (
                participation,
                external,
                {
                    **receipt,
                    "operations": [
                        {
                            **receipt["operations"][0],
                            "scope": ["是否愿意承担本轮预算"],
                        }
                    ],
                },
            ),
        }
        for name, inputs in cases.items():
            with self.subTest(name=name):
                checks = grade_human_review(record, *inputs)
                self.assert_has_failure(
                    checks,
                    "真人实际发送同时具有 participation 与 external-action 授权及双引用回执",
                )

    def test_human_draft_only_rejects_execution_inputs(self) -> None:
        checks = grade_human_review(
            self.human_review_record(),
            self.human_consent("participation_delegation"),
            self.human_consent("external_action"),
            self.human_receipt(),
        )
        self.assert_has_failure(
            checks,
            "真人 draft_only 不携带 execution consent 或 receipt",
        )

    @staticmethod
    def project_capability_consent(
        consent_id: str,
        operation: str,
        task: str,
    ) -> dict[str, object]:
        return {
            "consent_id": consent_id,
            "consent_type": "capability_call",
            "status": "granted",
            "scope": {
                "purpose": "核验项目可行性证据",
                "operations": [operation],
                "resources": ["公开资料"],
                "tasks": [task],
                "data_boundary": ["仅使用公开资料"],
                "excluded": ["私有数据", "外部行动"],
            },
            "valid_for": "this_action",
            "requested_by": "main_agent",
            "granted_by": "user",
        }

    @staticmethod
    def project_delegation_consent() -> dict[str, object]:
        return {
            "consent_id": "consent-adversarial",
            "consent_type": "participation_delegation",
            "status": "granted",
            "scope": {
                "purpose": "独立挑战自研必要性",
                "operations": ["委派独立反方"],
                "resources": ["已确认事实"],
                "tasks": ["独立挑战正式自研必要性"],
                "data_boundary": ["最小上下文"],
                "excluded": ["主判断", "完整 transcript", "外部行动"],
            },
            "valid_for": "this_action",
            "requested_by": "main_agent",
            "granted_by": "user",
        }

    @classmethod
    def valid_project_viability_bundle(
        cls,
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        categories = [
            "status_quo",
            "manual_or_process",
            "direct_competitor",
            "adjacent_category",
            "non_isomorphic_product_or_service",
            "platform_native",
            "active_open_source_or_commercial",
            "tool_combination",
            "plugin_script_or_thin_integration",
            "local_supplement",
            "independent_build",
        ]
        candidate_sources = {
            "direct_competitor": ["source-outcome"],
            "platform_native": ["source-solution"],
            "active_open_source_or_commercial": ["source-solution"],
            "independent_build": ["source-solution"],
        }
        candidates = []
        for index, category in enumerate(categories):
            covered = category in candidate_sources or category == "independent_build"
            candidates.append(
                {
                    "id": "candidate-platform" if category == "platform_native" else f"candidate-{index}",
                    "name": "平台原生能力" if category == "platform_native" else f"候选路径 {index}",
                    "category": category,
                    "coverage_status": "covered" if covered else "not_applicable",
                    "material": covered,
                    "reason": "" if covered else "当前决定下没有独特增量",
                    "source_ids": candidate_sources.get(category, []),
                    "verification_dimensions": [
                        {
                            "dimension": "现实边界",
                            "status": "verified" if covered else "not_applicable",
                            "reason": "" if covered else "该路径不适用本核验维度",
                            "source_ids": candidate_sources.get(category, []),
                        }
                    ],
                }
            )

        evidence_items = [
            {"id": "e-problem", "state": "supports", "claim": "问题存在", "source_ids": ["source-outcome"]},
            {"id": "e-strength", "state": "supports", "claim": "问题强度足够", "source_ids": ["source-outcome"]},
            {"id": "e-fit", "state": "supports", "claim": "候选方案适配", "source_ids": ["source-solution"]},
            {"id": "e-alternatives", "state": "supports", "claim": "替代生态已核验", "source_ids": ["source-solution"]},
            {"id": "e-trial", "state": "opposes", "claim": "最强替代不能解决核心任务", "source_ids": ["source-trial"]},
            {"id": "e-adversarial", "state": "supports", "claim": "独立反方未发现更轻路径", "source_ids": []},
        ]
        payload = {
            "assigned_question": "独立挑战正式自研必要性",
            "claims": ["最强替代仍有核心缺口"],
            "evidence_and_sources": ["试用回执显示核心任务失败"],
            "assumptions": ["任务与成功标准保持不变"],
            "uncertainties": ["未来版本可能改善"],
            "conflicts": ["公开介绍与试用结果不同"],
            "what_would_reverse_this": ["替代方案完成核心任务"],
        }
        record = {
            "contract_version": "0.4.1",
            "decision_context": {
                "decision": "采用现实替代还是正式自研",
                "commitment_type": "重大且难撤回的产品建设",
                "material_change": False,
                "prior_conclusion_status": "none",
            },
            "user_outcome": "让小团队拥有可积累经验的协作记忆",
            "focal_solution": {"description": "建设独立记忆平台", "status": "candidate"},
            "validation_layers": {
                "problem_existence": {"status": "supported", "evidence_item_ids": ["e-problem"]},
                "problem_strength": {"status": "supported", "evidence_item_ids": ["e-strength"]},
                "solution_fit": {"status": "supported", "evidence_item_ids": ["e-fit"]},
                "alternative_ecosystem": {"status": "supported", "evidence_item_ids": ["e-alternatives"]},
            },
            "search_passes": [
                {
                    "type": "outcome_problem_first",
                    "status": "completed",
                    "query_boundaries": ["outcome-search"],
                    "consent_id": "consent-search-outcome",
                    "receipt_id": "receipt-search-outcome",
                    "source_ids": ["source-outcome"],
                },
                {
                    "type": "solution_implementation_second",
                    "status": "completed",
                    "query_boundaries": ["solution-search"],
                    "consent_id": "consent-search-solution",
                    "receipt_id": "receipt-search-solution",
                    "source_ids": ["source-solution"],
                },
            ],
            "sources": [
                {"id": "source-outcome", "receipt_id": "receipt-search-outcome", "locator": "https://example.com/outcome"},
                {"id": "source-solution", "receipt_id": "receipt-search-solution", "locator": "https://example.com/solution"},
                {"id": "source-trial", "receipt_id": "receipt-trial", "locator": "trial://local/result"},
            ],
            "candidates": candidates,
            "strongest_alternative_id": "candidate-platform",
            "alternative_trial": {
                "status": "receipt_backed",
                "candidate_id": "candidate-platform",
                "real_tasks": ["真实任务 A"],
                "success_criteria": ["保留上下文并正确召回"],
                "result": "does_not_solve",
                "consent_ids": ["consent-trial"],
                "receipt_ids": ["receipt-trial"],
                "evidence_item_ids": ["e-trial"],
                "reason": "",
            },
            "adversarial_review": {
                "required": True,
                "status": "completed",
                "consent_id": "consent-adversarial",
                "receipt_id": "receipt-adversarial",
                "payload": payload,
                "evidence_item_ids": ["e-adversarial"],
                "reason": "",
            },
            "evidence_items": evidence_items,
            "commitment": {
                "direction": "independent_build",
                "chosen_rank": 3,
                "rationale": "完整证据链仍显示核心缺口",
                "evidence_item_ids": ["e-trial"],
                "upgrade_conditions": ["仅围绕已证明缺口收缩范围"],
            },
            "no_go_conditions": [
                {"id": "no-go-1", "condition": "替代方案满足核心任务时停止自研", "evidence_item_ids": ["e-trial"]}
            ],
            "reassessment_triggers": [
                {"id": "recheck-1", "condition": "替代生态实质变化后重新核验", "evidence_item_ids": ["e-alternatives"]}
            ],
        }
        consents = {
            "consents": [
                cls.project_capability_consent("consent-search-outcome", "公开搜索", "outcome-search"),
                cls.project_capability_consent("consent-search-solution", "公开搜索", "solution-search"),
                cls.project_capability_consent("consent-trial", "本地试用", "trial-run"),
                cls.project_delegation_consent(),
            ]
        }
        operations = [
            {
                "receipt_id": "receipt-search-outcome",
                "kind": "research",
                "status": "completed",
                "provider": "test-search",
                "scope": ["outcome-search"],
                "consent_ids": ["consent-search-outcome"],
                "sources": [{"title": "结果资料", "locator": "https://example.com/outcome", "retrieved_at": "2026-09-02T00:00:00Z"}],
                "private_data_accessed": False,
                "external_action_executed": False,
                "fallback": "",
            },
            {
                "receipt_id": "receipt-search-solution",
                "kind": "research",
                "status": "completed",
                "provider": "test-search",
                "scope": ["solution-search"],
                "consent_ids": ["consent-search-solution"],
                "sources": [{"title": "方案资料", "locator": "https://example.com/solution", "retrieved_at": "2026-09-02T00:00:00Z"}],
                "private_data_accessed": False,
                "external_action_executed": False,
                "fallback": "",
            },
            {
                "receipt_id": "receipt-trial",
                "kind": "tool_call",
                "status": "completed",
                "provider": "test-tools",
                "scope": ["trial-run"],
                "consent_ids": ["consent-trial"],
                "sources": [{"title": "本地试用结果", "locator": "trial://local/result", "retrieved_at": "2026-09-02T00:00:00Z"}],
                "private_data_accessed": False,
                "external_action_executed": False,
                "fallback": "",
            },
            {
                "receipt_id": "receipt-adversarial",
                "kind": "delegation",
                "status": "completed",
                "provider": "test-host",
                "scope": ["独立挑战正式自研必要性"],
                "consent_ids": ["consent-adversarial"],
                "agent_counts": {"main": 1, "planned_additional": 1, "started_additional": 1, "completed_additional": 1, "failed_additional": 0, "actual_total": 2},
                "completed_tasks": ["独立挑战正式自研必要性"],
                "failed_tasks": [],
                "private_data_accessed": False,
                "external_action_executed": False,
                "fallback": "",
            },
        ]
        receipt = {
            "contract_version": "0.4.1",
            "capabilities": [
                {"name": "search.public_web", "availability": "available", "readiness": "ready", "provider": "test-search"},
                {"name": "tools.read", "availability": "available", "readiness": "ready", "provider": "test-tools"},
                {"name": "agents.subagent", "availability": "available", "readiness": "ready", "provider": "test-host"},
            ],
            "operations": operations,
        }
        return record, consents, receipt

    def test_valid_project_viability(self) -> None:
        record, consents, receipt = self.valid_project_viability_bundle()
        self.assert_all_pass(grade_project_viability(record, consents, receipt))

    def test_fixture_20_valid_project_viability_executes_current_grader(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "skills"
            / "think-it-through"
            / "evals"
            / "fixtures"
            / "20-project-viability-falsification.json"
        )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        positive = fixture["positive"]
        self.assertEqual("0.4.1", fixture["contract_version"])
        self.assert_all_pass(
            grade_project_viability(
                positive["record"],
                positive["consent_bundle"],
                positive["receipt_bundle"],
            )
        )

    def test_project_viability_commitment_ceiling_levels(self) -> None:
        record, consents, receipt = self.valid_project_viability_bundle()
        record["validation_layers"]["problem_existence"].update(
            status="unsupported",
            evidence_item_ids=["e-problem"],
        )
        record["evidence_items"][0]["state"] = "opposes"
        record["commitment"].update(direction="stop", chosen_rank=0)
        self.assert_all_pass(grade_project_viability(record, consents, receipt))

        record, consents, receipt = self.valid_project_viability_bundle()
        record["validation_layers"]["alternative_ecosystem"].update(
            status="unknown",
            evidence_item_ids=[],
        )
        record["commitment"].update(direction="limited_validation", chosen_rank=1)
        self.assert_all_pass(grade_project_viability(record, consents, receipt))

        record, consents, receipt = self.valid_project_viability_bundle()
        record["alternative_trial"]["result"] = "solves_core"
        record["evidence_items"][4]["state"] = "supports"
        record["commitment"].update(direction="adopt", chosen_rank=2)
        self.assert_all_pass(grade_project_viability(record, consents, receipt))

    def test_project_viability_accepts_honest_failed_search_at_limited_ceiling(self) -> None:
        record, consents, receipt = self.valid_project_viability_bundle()
        search = record["search_passes"][1]
        search.update(status="failed", source_ids=[])
        operation = receipt["operations"][1]
        operation.update(status="failed", sources=[], fallback="保留替代生态未知并只做有限验证")
        record["sources"] = [source for source in record["sources"] if source["id"] != "source-solution"]
        for item in record["evidence_items"]:
            if "source-solution" in item["source_ids"]:
                item["source_ids"] = []
        for candidate in record["candidates"]:
            if "source-solution" in candidate["source_ids"]:
                candidate.update(coverage_status="unknown", reason="搜索失败，保留未知", source_ids=[])
                for dimension in candidate["verification_dimensions"]:
                    dimension.update(status="unknown", reason="搜索失败，保留未知", source_ids=[])
        record["validation_layers"]["alternative_ecosystem"].update(
            status="unknown",
            evidence_item_ids=[],
        )
        record["commitment"].update(direction="limited_validation", chosen_rank=1)
        self.assert_all_pass(grade_project_viability(record, consents, receipt))

    def test_project_viability_user_reported_trial_cannot_raise_build_ceiling(self) -> None:
        record, consents, receipt = self.valid_project_viability_bundle()
        record["alternative_trial"].update(
            status="user_reported",
            consent_ids=[],
            receipt_ids=[],
            evidence_item_ids=["e-trial"],
            reason="用户报告同一任务未通过成功标准",
        )
        record["evidence_items"][4]["source_ids"] = []
        record["commitment"].update(
            direction="limited_validation",
            chosen_rank=1,
            evidence_item_ids=["e-trial"],
        )
        self.assert_all_pass(grade_project_viability(record, consents, receipt))

        record["commitment"].update(
            direction="independent_build",
            chosen_rank=3,
        )
        checks = grade_project_viability(record, consents, receipt)
        self.assert_has_failure(
            checks,
            "PROJECT_VIABILITY chosen commitment 不超过 computed ceiling",
        )

    def test_project_viability_rejects_sourceless_commitment_when_raising_investment(self) -> None:
        record, consents, receipt = self.valid_project_viability_bundle()
        record["commitment"]["evidence_item_ids"] = ["e-adversarial"]
        checks = grade_project_viability(record, consents, receipt)
        self.assert_has_failure(
            checks,
            "PROJECT_VIABILITY chosen commitment 不超过 computed ceiling",
        )

    def test_project_viability_rejects_noncanonical_consent_and_receipt(self) -> None:
        record, consents, receipt = self.valid_project_viability_bundle()
        consents["consents"][0]["valid_for"] = "saved_preference"
        checks = grade_project_viability(record, consents, receipt)
        self.assert_has_failure(
            checks,
            "PROJECT_VIABILITY consents 分别符合 canonical schema",
        )

        record, consents, receipt = self.valid_project_viability_bundle()
        receipt["operations"][0]["started_at"] = "not-a-date"
        checks = grade_project_viability(record, consents, receipt)
        self.assert_has_failure(
            checks,
            "PROJECT_VIABILITY receipt bundle 符合 canonical schema",
        )

    def test_project_viability_rejects_single_variable_mutations(self) -> None:
        mutations = {
            "top-level-extra": lambda record, _consents, _receipt: record.update(extra="not-allowed"),
            "focal-not-candidate": lambda record, _consents, _receipt: record["focal_solution"].update(status="accepted_solution"),
            "merged-layer": lambda record, _consents, _receipt: record["validation_layers"].pop("alternative_ecosystem"),
            "search-order": lambda record, _consents, _receipt: record["search_passes"].reverse(),
            "missing-category": lambda record, _consents, _receipt: record["candidates"].pop(),
            "empty-sources": lambda _record, _consents, receipt: receipt["operations"][0].update(sources=[]),
            "dangling-source": lambda record, _consents, _receipt: record["evidence_items"][0].update(source_ids=["missing-source"]),
            "strongest-mismatch": lambda record, _consents, _receipt: record.update(strongest_alternative_id="candidate-10"),
            "trial-not-performed-build": lambda record, _consents, _receipt: record["alternative_trial"].update(status="not_performed", result="unknown", consent_ids=[], receipt_ids=[], reason="未执行"),
            "provider-mismatch": lambda _record, _consents, receipt: receipt["operations"][0].update(provider="other-provider"),
            "scope-mismatch": lambda _record, _consents, receipt: receipt["operations"][0].update(scope=["unauthorized"]),
            "receipt-status-without-fallback": lambda _record, _consents, receipt: receipt["operations"][0].update(status="failed"),
            "payload-extra": lambda record, _consents, _receipt: record["adversarial_review"]["payload"].update(main_judgment="自研"),
            "payload-empty-question": lambda record, _consents, _receipt: record["adversarial_review"]["payload"].update(assigned_question=""),
            "payload-invalid-field": lambda record, _consents, _receipt: record["adversarial_review"]["payload"].update(claims="不是列表"),
            "payload-all-content-empty": lambda record, _consents, _receipt: record["adversarial_review"]["payload"].update(
                claims=[],
                evidence_and_sources=[],
                assumptions=[],
                uncertainties=[],
                conflicts=[],
                what_would_reverse_this=[],
            ),
            "adversarial-failed-without-trace": lambda record, _consents, _receipt: record["adversarial_review"].update(status="failed", payload=None, reason="失败"),
            "layer-supported-with-unknown-evidence": lambda record, _consents, _receipt: record["evidence_items"][0].update(state="unknown"),
            "layer-supported-with-opposing-evidence": lambda record, _consents, _receipt: record["evidence_items"][0].update(state="opposes"),
            "trial-evidence-direction-reversed": lambda record, _consents, _receipt: record["evidence_items"][4].update(state="supports"),
            "commitment-unrelated-source-backed": lambda record, _consents, _receipt: record["commitment"].update(evidence_item_ids=["e-fit"]),
            "adversarial-missing-agent-counts": lambda _record, _consents, receipt: receipt["operations"][3].pop("agent_counts"),
            "adversarial-wrong-completed-task": lambda _record, _consents, receipt: receipt["operations"][3].update(completed_tasks=["其他任务"]),
            "adversarial-hidden-failed-task": lambda _record, _consents, receipt: receipt["operations"][3].update(failed_tasks=["独立挑战正式自研必要性"]),
            "chosen-over-ceiling": lambda record, _consents, _receipt: record["validation_layers"]["alternative_ecosystem"].update(status="unknown"),
            "dangling-no-go": lambda record, _consents, _receipt: record["no_go_conditions"][0].update(evidence_item_ids=["missing"]),
            "dangling-reassessment": lambda record, _consents, _receipt: record["reassessment_triggers"][0].update(evidence_item_ids=["missing"]),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                record, consents, receipt = self.valid_project_viability_bundle()
                mutate(record, consents, receipt)
                checks = grade_project_viability(record, consents, receipt)
                self.assertTrue(any(not check.passed and check.severe for check in checks))

    @staticmethod
    def valid_decision_record() -> dict[str, object]:
        return {
            "contract_version": "0.4.1",
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

    def test_decision_record_canonical_schema_rejects_shape_version_and_format(self) -> None:
        mutations = {
            "top-level-extra": lambda record: record.update(extra="not-allowed"),
            "nested-extra": lambda record: record["judgment"].update(extra="not-allowed"),
            "wrong-version": lambda record: record.update(contract_version="0.4.0"),
            "invalid-state": lambda record: record["judgment"].update(state="maybe"),
            "invalid-created-at": lambda record: record.update(created_at="today"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                record = self.valid_decision_record()
                mutate(record)
                checks = grade_decision_record(record)
                self.assert_has_failure(
                    checks,
                    "DecisionRecord 符合 canonical schema",
                )

    def test_decision_record_malformed_nested_values_fail_without_exception(self) -> None:
        mutations = {
            "judgment-list": lambda record: record.update(judgment=[]),
            "evidence-string": lambda record: record.update(evidence="bad"),
            "experiment-number": lambda record: record.update(main_experiment=1),
            "participation-list": lambda record: record.update(participation_and_capabilities=[]),
            "persistence-null": lambda record: record.update(persistence=None),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                record = self.valid_decision_record()
                mutate(record)
                checks = grade_decision_record(record)
                self.assertTrue(any(not check.passed and check.severe for check in checks))

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
            ("adjust-next-step", "none", "await-supplement", True, False),
            ("disagree", "none", "R-method", False, False),
            ("accept", "consistent", "end", True, False),
            ("accept", "experiment-adjustment", "B-revision", True, True),
            ("accept", "new-fact", "A", False, True),
            ("accept", "purpose-change", "R-align", False, True),
        )
        for direction, supplement, stage, preserve, overridden in cases:
            with self.subTest(direction=direction, supplement=supplement):
                route = resolve_b_feedback_route(direction, supplement)
                self.assertEqual(stage, route.next_stage)
                self.assertEqual(preserve, route.preserve_judgment)
                self.assertEqual(overridden, route.text_overrode_selection)

    def test_fixture_11_feedback_routes_match_canonical_resolver(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "skills"
            / "think-it-through"
            / "evals"
            / "fixtures"
            / "11-b-experiment-and-feedback.json"
        )
        routes = json.loads(fixture_path.read_text(encoding="utf-8"))["feedback_routes"]
        for route in routes:
            with self.subTest(
                direction=route["direction_id"],
                supplement=route["supplement_type"],
            ):
                resolved = resolve_b_feedback_route(
                    route["direction_id"],
                    route["supplement_type"],
                )
                self.assertEqual(route["expected_stage"], resolved.next_stage)
                self.assertEqual(
                    route["preserve_judgment"],
                    resolved.preserve_judgment,
                )
                self.assertEqual(
                    route["text_overrode_selection"],
                    resolved.text_overrode_selection,
                )

    def test_b_feedback_routes_reject_unknown_values(self) -> None:
        with self.assertRaises(ValueError):
            resolve_b_feedback_route("unknown")
        with self.assertRaises(ValueError):
            resolve_b_feedback_route("accept", "unknown")


if __name__ == "__main__":
    unittest.main()