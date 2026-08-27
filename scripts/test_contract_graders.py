#!/usr/bin/env python3
"""用合规和违规样本验证机械合同评分器。"""

from __future__ import annotations

import unittest

from grade_contracts import grade_a, grade_b, grade_r


class ContractGraderTests(unittest.TestCase):
    def assert_all_pass(self, checks) -> None:
        failed = [check.text for check in checks if not check.passed]
        self.assertEqual([], failed)

    def assert_has_failure(self, checks, name: str) -> None:
        matches = [check for check in checks if check.text == name]
        self.assertEqual(1, len(matches), name)
        self.assertFalse(matches[0].passed, name)

    def test_valid_r(self) -> None:
        text = """## 推荐怎样分析

暂定真实目的是验证付费，而不是先把推广材料做完。

- **检验最强替代方向**：区分继续开发与先验证需求。

可选择：按推荐继续 / 调整分析方式 / 只做基础分析 / 补充背景

我会等你确认本轮分析方式后再继续。"""
        self.assert_all_pass(grade_r(text))

    def test_r_with_judgment_fails(self) -> None:
        text = "按推荐继续 / 调整分析方式 / 只做基础分析 / 补充背景\n我会等你确认。\n建议：你应该停止。"
        checks = grade_r(text)
        self.assert_has_failure(checks, "阶段 R 不给判断")

    def test_valid_a(self) -> None:
        text = """## 真正要决定什么
是否继续开发，还是先验证陌生客户愿意付费。

## 综合后的关键分析
继续开发依赖需求真实存在；最强替代方向是先验证，代价更低。

## 真正分歧与关键变量
关键不是功能能否完成，而是现有版本是否解决了足以付费的问题。

如果十个符合画像的陌生商家中没有一个愿意为现有版本付费，这会不会让你停止未来三个月的开发？"""
        self.assert_all_pass(grade_a(text))

    def test_a_with_two_questions_fails(self) -> None:
        checks = grade_a("你有预算吗？你愿意继续吗？")
        self.assert_has_failure(checks, "阶段 A 恰好一个问号")

    def test_a_with_content_after_question_fails(self) -> None:
        checks = grade_a("哪个证据会改变决定？\n请想好后回复。")
        self.assert_has_failure(checks, "阶段 A 以唯一问号结束")

    def test_a_with_multiple_answer_slots_fails(self) -> None:
        checks = grade_a("预算是多少、期限是多久，以及最低回报是什么？")
        self.assert_has_failure(checks, "阶段 A 的唯一问题只有一个答案槽")

    def test_a_with_hidden_information_request_fails(self) -> None:
        checks = grade_a("请先提供预算和期限。哪个收入阈值会改变决定？")
        self.assert_has_failure(checks, "阶段 A 不用陈述句隐藏追加信息请求")

    def test_cancelled_premortem_fails(self) -> None:
        checks = grade_a("真正分歧在付费意愿。\n假设三个月后失败，最早信号是什么？", ["pre-mortem"])
        self.assert_has_failure(checks, "阶段 A 不变相执行已取消方法")

    def test_valid_b_unexecuted(self) -> None:
        text = """## 判断：小步验证

你的回答说明，继续开发依赖一个尚未验证的付费假设。目前已确认的是产品存在，付费意愿仍是关键未知。

**成立条件与反转证据**
若陌生目标客户愿为现有版本付费，判断可转向有条件推进；若持续拒绝，继续开发的依据被削弱。

**一个最小下一步**
未来七天只向十位符合画像的陌生商家演示现有版本，不新增功能；至少两位愿意按明确价格付费才复判是否推进，零付费则停止本轮开发投入。"""
        self.assert_all_pass(grade_b(text, already_executed=False))

    def test_b_with_question_fails(self) -> None:
        text = "## 判断：暂停\n你还想继续吗？\n**一个最小下一步**\n暂停七天。"
        checks = grade_b(text, already_executed=True)
        self.assert_has_failure(checks, "阶段 B 不再提出信息问题")

    def test_b_external_before_next_step_fails(self) -> None:
        text = "## 判断：小步验证\n先做外部验证。\n**一个最小下一步**\n访谈五人。\n反转证据是有人付费。"
        checks = grade_b(text, already_executed=False)
        self.assert_has_failure(checks, "可选外部验证位于完整判断和下一步之后")

    def test_b_with_parallel_actions_fails(self) -> None:
        text = """## 判断：调整
反转证据是出现陌生付费。

**一个最小下一步**
1. 访谈五位用户。
2. 重写首页。
3. 发起预售。"""
        checks = grade_b(text, already_executed=True)
        self.assert_has_failure(checks, "阶段 B 只有一个主下一步")

    def test_b_that_infers_authorization_fails(self) -> None:
        text = """## 判断：小步验证
反转证据是出现稳定需求。

**一个最小下一步**
既然你已经授权联网，所以我会自动联系潜在客户。"""
        checks = grade_b(text, already_executed=False)
        self.assert_has_failure(checks, "阶段 B 不把一种授权推定为另一种")


if __name__ == "__main__":
    unittest.main()
