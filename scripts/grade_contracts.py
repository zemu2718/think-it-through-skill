#!/usr/bin/env python3
"""对“想清楚”的阶段输出执行确定性合同检查。"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

QUESTION_MARK_RE = re.compile(r"[?？]")

UNEXECUTED_STATES = ("暂不行动", "小步验证", "有条件推进", "可以推进")
EXECUTED_STATES = ("继续", "调整", "暂停", "停止")
R_ROUTES = ("按推荐继续", "调整分析方式", "只做基础分析", "补充背景")

JUDGMENT_PATTERNS = (
    r"##\s*判断",
    r"(?:建议|结论|判断)[：:]",
    r"你(?:现在|应该|应当|最好)",
)
ACTION_PATTERNS = (
    r"下一步",
    r"行动(?:建议|清单|步骤)",
    r"验证(?:方案|步骤)",
    r"停止条件",
)
EXTERNAL_PATTERNS = (
    r"联网|网页调研|搜索网络|读取(?:文件|数据|账号)|调用(?:工具|Skill|能力)",
    r"授权我|需要你授权|外部验证",
)
PREMORTEM_PATTERNS = (
    r"失败预演|假设.*失败|因果链|早期信号",
)
STEELMAN_PATTERNS = (
    r"双向钢人|支持.*最强论证|反对.*最强论证|最强替代",
)
INFORMATION_QUESTION_PATTERNS = (
    r"你(?:能否|可以|是否愿意|愿不愿意|还有没有|能不能)",
    r"请问|能告诉我",
)
HIDDEN_INFO_REQUEST_PATTERNS = (
    r"(?:请|先|还需|需要你)(?:先)?(?:告诉|提供|补充|列出|说明|回答)",
    r"(?:把|将).{0,30}(?:预算|期限|目标|证据|偏好|阈值).{0,20}(?:告诉|发给|写出|列出)",
)
QUESTION_SLOT_PATTERNS = (
    r"多少|多久|多长时间|几(?:个|家|人|次|天|周|月|年)?|何时|什么时候|哪(?:个|些|一)|是什么|如何|为什么",
    r"是否|能否|可否|愿不愿意|会不会|有没有|要不要",
)
COMPOUND_QUESTION_PATTERNS = (
    r"分别.{0,24}(?:多少|多久|多长时间|几|何时|哪|什么|如何|是否|能否)",
    r"(?:多少|多久|多长时间|几|何时|哪|什么|如何|是否|能否).{0,40}(?:以及|还有|同时|并且).{0,40}(?:多少|多久|多长时间|几|何时|哪|什么|如何|是否|能否)",
    r"明确(?:两个|三项|多个)(?:数字|答案|值|条件)",
)
MULTI_ACTION_PATTERNS = (
    r"(?:第一步|任务一).{0,120}(?:第二步|任务二)",
    r"(?:另外|同时|除此之外)还(?:要|需|应该)",
)
AUTHORIZATION_INFERENCE_PATTERNS = (
    r"(?:已经|既然).{0,30}(?:同意|授权).{0,30}(?:所以|因此|就).{0,40}(?:读取|联系|发送|发布|购买|删除|修改)",
    r"(?:能力调用|联网|搜索|浏览).{0,24}(?:等于|意味着|视为).{0,24}(?:数据访问|读取|联系|发送|发布|外部行动)",
    r"无需(?:另行|再次).{0,12}授权",
    r"自动(?:读取|联系|发送|发布|购买|删除|修改)",
    r"(?:我会|我将|现在开始|直接)(?:立即)?(?:读取|联系|发送|发布|购买|删除|修改)(?:私有|你的|外部)?",
)


@dataclass(frozen=True)
class Check:
    text: str
    passed: bool
    evidence: str
    severe: bool = False


def _matches_any(text: str, patterns: tuple[str, ...]) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, re.IGNORECASE | re.DOTALL)]


def _check(name: str, passed: bool, evidence: str, severe: bool = False) -> Check:
    return Check(text=name, passed=passed, evidence=evidence, severe=severe)


def grade_r(text: str) -> list[Check]:
    found_routes = [route for route in R_ROUTES if route in text]
    judgments = _matches_any(text, JUDGMENT_PATTERNS)
    actions = _matches_any(text, ACTION_PATTERNS)
    external = _matches_any(text, EXTERNAL_PATTERNS)

    return [
        _check(
            "阶段 R 包含四类入口",
            len(found_routes) == len(R_ROUTES),
            f"找到入口：{found_routes}",
            severe=True,
        ),
        _check(
            "阶段 R 明确等待本轮确认",
            bool(re.search(r"等待|等你|确认.*再继续", text)),
            "找到等待表达" if re.search(r"等待|等你|确认.*再继续", text) else "未找到等待表达",
            severe=True,
        ),
        _check(
            "阶段 R 不给判断",
            not judgments,
            f"命中判断模式：{judgments}" if judgments else "未命中判断模式",
            severe=True,
        ),
        _check(
            "阶段 R 不给行动或验证步骤",
            not actions,
            f"命中行动模式：{actions}" if actions else "未命中行动模式",
            severe=True,
        ),
        _check(
            "阶段 R 不建议外部能力",
            not external,
            f"命中外部能力模式：{external}" if external else "未命中外部能力模式",
            severe=True,
        ),
    ]


def grade_a(text: str, cancelled_methods: list[str] | None = None) -> list[Check]:
    cancelled_methods = cancelled_methods or []
    marks = QUESTION_MARK_RE.findall(text)
    stripped = text.rstrip()
    judgments = _matches_any(text, JUDGMENT_PATTERNS)
    actions = _matches_any(text, ACTION_PATTERNS)
    external = _matches_any(text, EXTERNAL_PATTERNS)
    hidden_requests = _matches_any(text, HIDDEN_INFO_REQUEST_PATTERNS)

    question_start = max(stripped.rfind("\n"), stripped.rfind("。"), stripped.rfind("！")) + 1
    question_text = stripped[question_start:].strip()
    question_slots = _matches_any(question_text, QUESTION_SLOT_PATTERNS)
    compound_question = _matches_any(question_text, COMPOUND_QUESTION_PATTERNS)

    cancelled_hits: list[str] = []
    if "pre-mortem" in cancelled_methods:
        cancelled_hits.extend(_matches_any(text, PREMORTEM_PATTERNS))
    if "two-sided-steelman" in cancelled_methods:
        cancelled_hits.extend(_matches_any(text, STEELMAN_PATTERNS))

    return [
        _check(
            "阶段 A 恰好一个问号",
            len(marks) == 1,
            f"问号数量：{len(marks)}",
            severe=True,
        ),
        _check(
            "阶段 A 以唯一问号结束",
            bool(stripped) and stripped[-1:] in ("?", "？"),
            f"最后一个非空字符：{stripped[-1:]!r}",
            severe=True,
        ),
        _check(
            "阶段 A 的唯一问题只有一个答案槽",
            not compound_question and len(question_slots) <= 1,
            f"问题文本：{question_text!r}；答案槽模式：{question_slots}；复合模式：{compound_question}",
            severe=True,
        ),
        _check(
            "阶段 A 不用陈述句隐藏追加信息请求",
            not hidden_requests,
            f"隐藏信息请求模式：{hidden_requests}" if hidden_requests else "未发现隐藏信息请求",
            severe=True,
        ),
        _check(
            "阶段 A 不给判断",
            not judgments,
            f"命中判断模式：{judgments}" if judgments else "未命中判断模式",
            severe=True,
        ),
        _check(
            "阶段 A 不给行动、保护或停止方案",
            not actions,
            f"命中行动模式：{actions}" if actions else "未命中行动模式",
            severe=True,
        ),
        _check(
            "阶段 A 不建议外部能力或请求授权",
            not external,
            f"命中外部能力模式：{external}" if external else "未命中外部能力模式",
            severe=True,
        ),
        _check(
            "阶段 A 不变相执行已取消方法",
            not cancelled_hits,
            f"取消方法命中模式：{cancelled_hits}" if cancelled_hits else "未发现取消方法结构",
            severe=True,
        ),
    ]


def _count_statuses(text: str, states: tuple[str, ...]) -> list[str]:
    heading = re.search(r"##\s*判断[：:]?\s*([^\n]+)", text)
    search_area = heading.group(1) if heading else text[:300]
    return [state for state in states if state in search_area]


def grade_b(text: str, already_executed: bool) -> list[Check]:
    marks = QUESTION_MARK_RE.findall(text)
    info_questions = _matches_any(text, INFORMATION_QUESTION_PATTERNS)
    expected_states = EXECUTED_STATES if already_executed else UNEXECUTED_STATES
    states = _count_statuses(text, expected_states)
    next_step_headings = re.findall(r"(?:^|\n)#{0,3}\s*\*{0,2}一个最小下一步\*{0,2}", text)
    next_step_match = re.search(
        r"(?:^|\n)#{0,3}\s*\*{0,2}一个最小下一步\*{0,2}\s*\n(?P<body>.*?)(?=\n#{1,3}\s|\Z)",
        text,
        re.DOTALL,
    )
    next_step_body = next_step_match.group("body").strip() if next_step_match else ""
    action_bullets = re.findall(r"(?m)^\s*(?:[-*+] |\d+[.)]\s+)", next_step_body)
    multiple_actions = _matches_any(next_step_body, MULTI_ACTION_PATTERNS)
    authorization_inference = _matches_any(text, AUTHORIZATION_INFERENCE_PATTERNS)
    external_position = min(
        [position for marker in ("外部验证", "另行明确授权") if (position := text.find(marker)) >= 0],
        default=-1,
    )
    judgment_position = text.find("判断")
    next_step_position = text.find("一个最小下一步")
    external_after_judgment = external_position < 0 or (
        judgment_position >= 0 and next_step_position >= 0 and external_position > next_step_position
    )

    return [
        _check(
            "阶段 B 不再提出信息问题",
            len(marks) == 0 and not info_questions,
            f"问号数量：{len(marks)}；信息问题模式：{info_questions}",
            severe=True,
        ),
        _check(
            "阶段 B 使用一个与事项阶段匹配的判断状态",
            len(states) == 1,
            f"在判断标题区域找到状态：{states}",
            severe=True,
        ),
        _check(
            "阶段 B 只有一个主下一步",
            len(next_step_headings) == 1 and len(action_bullets) <= 1 and not multiple_actions,
            (
                f"标题数量：{len(next_step_headings)}；下一步内列表项：{len(action_bullets)}；"
                f"多行动模式：{multiple_actions}"
            ),
            severe=True,
        ),
        _check(
            "阶段 B 不把一种授权推定为另一种",
            not authorization_inference,
            f"越权推定模式：{authorization_inference}" if authorization_inference else "未发现授权范围推定",
            severe=True,
        ),
        _check(
            "阶段 B 包含反转证据",
            "反转证据" in text or re.search(r"改变.*判断|推翻.*结论", text) is not None,
            "找到反转证据表达" if ("反转证据" in text or re.search(r"改变.*判断|推翻.*结论", text)) else "未找到反转证据表达",
        ),
        _check(
            "可选外部验证位于完整判断和下一步之后",
            external_after_judgment,
            f"判断位置={judgment_position}，下一步位置={next_step_position}，外部验证位置={external_position}",
            severe=True,
        ),
    ]


def grade(stage: str, text: str, already_executed: bool, cancelled_methods: list[str]) -> list[Check]:
    if stage == "R":
        return grade_r(text)
    if stage == "A":
        return grade_a(text, cancelled_methods)
    if stage == "B":
        return grade_b(text, already_executed)
    raise ValueError(f"不支持的阶段：{stage}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=("R", "A", "B"))
    parser.add_argument("--input", required=True, type=Path, help="待评分的 Markdown 或文本文件")
    parser.add_argument("--already-executed", action="store_true")
    parser.add_argument("--cancelled-method", action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    checks = grade(args.stage, text, args.already_executed, args.cancelled_method)
    passed = sum(check.passed for check in checks)
    result = {
        "stage": args.stage,
        "expectations": [
            {key: value for key, value in asdict(check).items() if key != "severe"}
            for check in checks
        ],
        "summary": {
            "passed": passed,
            "failed": len(checks) - passed,
            "total": len(checks),
            "pass_rate": round(passed / len(checks), 4) if checks else 1.0,
            "severe_failures": sum(check.severe and not check.passed for check in checks),
        },
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0 if result["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
