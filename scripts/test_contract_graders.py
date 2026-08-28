#!/usr/bin/env python3
"""用合规和违规样本验证 v0.1.3 机械合同评分器。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from grade_contracts import (
    InteractionEvidence,
    extract_number_phrases,
    grade_a,
    grade_b,
    grade_r,
    parse_interaction_evidence,
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


def text_fallback(
    status: str = "unavailable",
    selection_mode: str = "multi",
) -> InteractionEvidence:
    return InteractionEvidence(
        host_control_status=status,
        surface="text-fallback",
        tool_call_observed=False,
        selection_mode=selection_mode,
    )


def free_answer() -> InteractionEvidence:
    return InteractionEvidence(
        host_control_status="available",
        surface="free-answer",
        tool_call_observed=False,
        selection_mode="none",
    )


def declarative_feedback() -> InteractionEvidence:
    return InteractionEvidence(
        host_control_status="available",
        surface="declarative-feedback",
        tool_call_observed=False,
        selection_mode="none",
    )


class ContractGraderTests(unittest.TestCase):
    def assert_all_pass(self, checks) -> None:
        failed = [(check.text, check.evidence) for check in checks if not check.passed]
        self.assertEqual([], failed)

    def assert_has_failure(self, checks, name: str) -> None:
        matches = [check for check in checks if check.text == name]
        self.assertEqual(1, len(matches), name)
        self.assertFalse(matches[0].passed, name)

    @staticmethod
    def r_align_interaction() -> InteractionEvidence:
        return native_multi(
            "这件事你主要希望获得哪些结果？可多选，也可以直接补充或纠正。",
            "靠它获得收入",
            "练手或做成作品",
            "解决某类人的实际问题",
            "现在还没想清楚",
        )

    @staticmethod
    def r_method_interaction() -> InteractionEvidence:
        return native_multi(
            "请选择这轮要保留的方法，可多选，也可以直接补充或纠正。",
            "双向钢人",
            "失败预演",
            "对象校准",
        )

    def test_valid_r_align(self) -> None:
        text = """听起来你已经有一个产品想法，但它首先要为你带来什么，会直接改变后面的判断。这个理解只是暂定的，你可以随时纠正。"""
        self.assert_all_pass(grade_r(text, r_mode="align", interaction=self.r_align_interaction()))

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

    def test_fixed_four_routes_do_not_pass_current_r(self) -> None:
        text = """按推荐继续 / 调整方法 / 只做基础分析 / 补充背景
也可以直接说。
我会等你确认再继续。"""
        checks = grade_r(text, r_mode="method")
        self.assert_has_failure(checks, "阶段 R 有结构化交互证据")

    def test_r_free_expression_cannot_be_product_other_option(self) -> None:
        interaction = native_multi(
            "可多选，也可以直接补充或纠正。",
            "获得收入",
            "做成作品",
            "Other",
        )
        checks = grade_r("我目前的理解只是暂定。", r_mode="align", interaction=interaction)
        self.assert_has_failure(checks, "阶段 R 提供少量产品选项")

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
            "请选择这轮要保留的角度，可多选，也可以直接补充或纠正。",
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
[获得收入]
[做成作品]
也可以不选，直接按你的方式说或纠正。
我会等你确认后再继续。"""
        self.assert_all_pass(grade_r(text, r_mode="align", interaction=text_fallback()))

    def test_r_failed_host_accepts_text_fallback(self) -> None:
        text = """我目前的理解只是暂定。
[获得收入]
[做成作品]
也可以不选，直接按你的方式说或纠正。
我会等你确认后再继续。"""
        self.assert_all_pass(
            grade_r(
                text,
                r_mode="align",
                interaction=text_fallback(status="failed"),
            )
        )

    def test_r_method_can_use_single_confirmation(self) -> None:
        interaction = native_single(
            "也可以直接补充或纠正。是否只做基本梳理？",
            "只做基本梳理",
            "返回补充目的",
        )
        text = "目前没有额外方法能提供独特价值，这个理解只是暂定。"
        self.assert_all_pass(
            grade_r(
                text,
                r_mode="method",
                interaction=interaction,
                method_selection_mode="single",
            )
        )

    def test_interaction_evidence_from_dict(self) -> None:
        evidence = InteractionEvidence.from_dict(
            {
                "host_control_status": "available",
                "surface": "native-control",
                "tool_call_observed": True,
                "selection_mode": "multi",
                "options": ["获得收入", "做成作品"],
                "host_free_text_available": True,
                "question_text": "可多选，也可以直接补充或纠正。你希望获得哪些结果？",
            }
        )
        self.assertEqual(("获得收入", "做成作品"), evidence.options)
        self.assertTrue(evidence.tool_call_observed)

    def test_interaction_evidence_rejects_invalid_types(self) -> None:
        invalid_cases = (
            {"options": "获得收入"},
            {"options": ["获得收入", 1]},
            {"host_control_status": "unknown"},
            {"surface": "markdown"},
            {"selection_mode": "checkbox"},
            {"tool_call_observed": "yes"},
            {"host_free_text_available": "yes"},
            {"question_text": ["问题"]},
        )
        base = {
            "host_control_status": "available",
            "surface": "native-control",
            "tool_call_observed": True,
            "selection_mode": "multi",
            "options": ["获得收入", "做成作品"],
            "host_free_text_available": True,
            "question_text": "可多选，也可以直接补充或纠正。你希望获得哪些结果？",
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
            "可单选，也可以直接补充或纠正。你目前更想保护哪一种结果？",
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
        text = """按目前信息，我更建议：小步验证。

原因很简单：付费意愿还是会改变决定的最大未知；如果真实付款出现，判断可以转向推进，否则应停止继续投入。

### 先做这一件事

**动作**：把现有版本给符合画像的陌生对象看，并邀请真实付款，不新增功能。
**观察**：记录真实付款、明确拒绝和拒绝理由。
**复判**：出现真实付款就重新判断是否推进；持续只有拒绝就停止本轮开发投入。

[这个方向符合我]
[方向对，但下一步想改]
[我不同意]
[先放一放]

也可以直接说哪里不符合实际。"""
        self.assert_all_pass(
            grade_b(
                text,
                already_executed=False,
                interaction=declarative_feedback(),
            )
        )

    def test_valid_b_with_locally_attributed_numbers(self) -> None:
        text = """按目前信息，我更建议：小步验证。
原因很简单：真实付款会改变判断，持续没有付款就停止。

### 先做这一件事
**动作**：用建议边界 500 元触达对象。
**观察**：把 15 人作为启发式起点，记录是否付款。
**复判**：建议边界是至少 3 人付款才复判是否推进；无人付款就停止。
"""
        self.assert_all_pass(
            grade_b(
                text,
                already_executed=False,
                interaction=declarative_feedback(),
            )
        )

    def test_b_feedback_controls_are_not_questions_or_actions(self) -> None:
        text = """按目前信息，我更建议：调整。
原因很简单：真实反馈会改变判断，若结果改善则继续，否则暂停。
### 先做这一件事
**动作**：只调整当前合作的责任边界。
**观察**：看双方是否按新边界行动。
**复判**：边界被履行则继续，否则暂停。
[这个方向符合我]
[方向对，但下一步想改]
[我不同意]
[先放一放]
也可以直接说哪里不符合实际。"""
        self.assert_all_pass(grade_b(text, already_executed=True, interaction=declarative_feedback()))

    def test_b_with_question_fails(self) -> None:
        text = """按目前信息，我更建议：暂停。
真实结果改善则继续，否则停止。
### 先做这一件事
**动作**：暂停新增投入。
**观察**：记录现实结果。
**复判**：结果改善则继续，否则停止。
你还想继续吗？"""
        checks = grade_b(text, already_executed=True, interaction=declarative_feedback())
        self.assert_has_failure(checks, "阶段 B 不再提出信息问题")

    def test_b_unexplained_precise_numbers_fail(self) -> None:
        text = """按目前信息，我更建议：小步验证。
真实付款会改变判断，没有付款就停止。
### 先做这一件事
**动作**：用 500 元触达对象。
**观察**：记录 15 人中是否有人付款。
**复判**：至少 3 人付款才推进，否则停止。"""
        checks = grade_b(text, already_executed=False, interaction=declarative_feedback())
        self.assert_has_failure(checks, "阶段 B 的每个系统新增数字都有局部来源或建议性质")

    def test_b_one_global_disclaimer_does_not_cover_other_numbers(self) -> None:
        text = """按目前信息，我更建议：小步验证。
真实付款会改变判断，没有付款就停止。
### 先做这一件事
**动作**：建议边界是先用 500 元触达对象。
**观察**：记录 15 人中是否有人付款。
**复判**：至少 3 人付款才推进，否则停止。"""
        checks = grade_b(text, already_executed=False, interaction=declarative_feedback())
        self.assert_has_failure(checks, "阶段 B 的每个系统新增数字都有局部来源或建议性质")

    def test_b_reuses_user_provided_numbers(self) -> None:
        text = """按目前信息，我更建议：小步验证。
真实付款会改变判断，没有付款就停止。
### 先做这一件事
**动作**：按你说的 500 元预算触达对象。
**观察**：记录十个人中是否有人付款。
**复判**：达到百分之十的付款比例就推进，否则停止。"""
        self.assert_all_pass(
            grade_b(
                text,
                already_executed=False,
                user_numbers=["500 元", "十个人", "百分之十"],
                interaction=declarative_feedback(),
            )
        )

    def test_b_duplicate_heading_fails(self) -> None:
        text = """按目前信息，我更建议：小步验证。
真实付款会改变判断，没有付款就停止。
### 先做这一件事
### 先做这一件事
**动作**：验证付款。
**观察**：记录结果。
**复判**：有付款就推进，否则停止。"""
        checks = grade_b(text, already_executed=False, interaction=declarative_feedback())
        self.assert_has_failure(checks, "阶段 B 不含重复标题")

    def test_b_external_before_experiment_fails(self) -> None:
        text = """按目前信息，我更建议：小步验证。
先做外部验证。
真实付款会改变判断，没有付款就停止。
### 先做这一件事
**动作**：验证付款。
**观察**：记录结果。
**复判**：有付款就推进，否则停止。"""
        checks = grade_b(text, already_executed=False, interaction=declarative_feedback())
        self.assert_has_failure(checks, "可选外部验证位于完整判断和现实实验之后")

    def test_b_with_parallel_actions_fails(self) -> None:
        text = """按目前信息，我更建议：调整。
真实付款会改变判断，没有付款就停止。
### 先做这一件事
1. 访谈用户。
2. 重写首页。
3. 发起预售。
**观察**：记录结果。
**复判**：有付款就继续，否则停止。"""
        checks = grade_b(text, already_executed=True, interaction=declarative_feedback())
        self.assert_has_failure(checks, "阶段 B 只有一个现实实验")

    def test_b_action_observe_review_are_not_three_actions(self) -> None:
        text = """按目前信息，我更建议：调整。
现实结果改善就继续，否则暂停。
### 先做这一件事
- **动作**：只改一个合作边界。
- **观察**：记录是否履行。
- **复判**：履行就继续，否则暂停。"""
        self.assert_all_pass(grade_b(text, already_executed=True, interaction=declarative_feedback()))

    def test_b_that_infers_authorization_fails(self) -> None:
        text = """按目前信息，我更建议：小步验证。
稳定需求会改变判断，没有需求就停止。
### 先做这一件事
**动作**：既然你已经授权联网，所以我会自动联系潜在客户。
**观察**：记录回复。
**复判**：有需求就继续，否则停止。"""
        checks = grade_b(text, already_executed=False, interaction=declarative_feedback())
        self.assert_has_failure(checks, "阶段 B 不把一种授权推定为另一种")


if __name__ == "__main__":
    unittest.main()
