#!/usr/bin/env python3
"""对“想清楚”v0.1.3 的阶段输出执行确定性合同检查。"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

QUESTION_MARK_RE = re.compile(r"[?？]")

UNEXECUTED_STATES = ("暂不行动", "小步验证", "有条件推进", "可以推进")
EXECUTED_STATES = ("继续", "调整", "暂停", "停止")
METHOD_LABELS = {
    "two-sided-steelman": "双向钢人",
    "pre-mortem": "失败预演",
    "object-calibration": "对象校准",
    "system-bottleneck": "系统瓶颈",
    "stage-fit": "阶段匹配",
    "resource-leverage": "资源支点",
    "boundary-contracts": "边界契约",
    "communication-fit": "沟通匹配",
    "evidence-loop": "证据闭环",
}
METHOD_OUTPUT_PATTERNS = {
    "two-sided-steelman": (r"最强竞争|最强替代|当前方向.{0,40}最强替代|两个?最强|两条.{0,20}(?:路径|方向)",),
    "pre-mortem": (r"失败预演|假设.*失败|因果链|早期信号",),
    "object-calibration": (r"使用者|付费者|服务对象|代价承担",),
    "system-bottleneck": (r"瓶颈|主导约束|控制点",),
    "stage-fit": (r"阶段|过去.{0,30}当前|条件变化",),
    "resource-leverage": (r"资源|时间|资金|支点|集中投入",),
    "boundary-contracts": (r"权责|责任|决定权|退出",),
    "communication-fit": (r"表达|信息|渠道|反馈",),
    "evidence-loop": (r"现实结果|实际结果|原假设|继续|调整|暂停|停止",),
}

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
    r"(?:第一步|任务一).{0,160}(?:第二步|任务二)",
    r"(?:另外|同时|除此之外)还(?:要|需|应该)",
)
AUTHORIZATION_INFERENCE_PATTERNS = (
    r"(?:已经|既然).{0,30}(?:同意|授权).{0,30}(?:所以|因此|就).{0,40}(?:读取|联系|发送|发布|购买|删除|修改)",
    r"(?:能力调用|联网|搜索|浏览).{0,24}(?:等于|意味着|视为).{0,24}(?:数据访问|读取|联系|发送|发布|外部行动)",
    r"无需(?:另行|再次).{0,12}授权",
    r"自动(?:读取|联系|发送|发布|购买|删除|修改)",
    r"(?:我会|我将|现在开始|直接)(?:立即)?(?:读取|联系|发送|发布|购买|删除|修改)(?:私有|你的|外部)?",
)

CHOICE_LINE_RE = re.compile(r"(?m)^\s*(?:[-*+]\s*)?\[[^\]\n]{1,48}\]\s*$")
FREE_EXPRESSION_RE = re.compile(
    r"(?:也可以|或者可以|你也能).{0,36}(?:不选|直接|按你的方式|自由|补充|纠正|说出|说说)",
    re.DOTALL,
)
OTHER_OPTION_RE = re.compile(r"(?m)^\s*(?:[-*+]\s*)?\[(?:其他|其它|Other)\]\s*$", re.IGNORECASE)
PRODUCT_OTHER_RE = re.compile(r"^(?:其他|其它|Other)$", re.IGNORECASE)
WAIT_RE = re.compile(r"等待|等你|确认.*再继续|选好.*继续|说完.*继续")

HOST_CONTROL_STATUSES = {"available", "unavailable", "failed"}
INTERACTION_SURFACES = {"native-control", "text-fallback", "free-answer", "declarative-feedback"}
SELECTION_MODES = {"multi", "single", "none"}
ANSWER_SHAPES = {"finite-mutually-exclusive", "open"}
NATURAL_ECHO_RE = re.compile(
    r"(?m)^(?P<line>[^\n]*(?:按刚才选的来|按这些角度|按这个角度|这轮(?:就)?先做基本梳理|这次(?:就)?先做基本梳理|本轮(?:就)?按)[^\n]*)$"
)

ARABIC_NUMBER = r"\d+(?:\.\d+)?"
CHINESE_NUMBER = r"[〇零一二两三四五六七八九十百千万亿]+"
NUMBER_TOKEN = rf"(?:{ARABIC_NUMBER}|{CHINESE_NUMBER})"
NUMBER_UNIT = r"(?:人民币|块钱|个月|小时|分钟|星期|元|人|名|位|家|个|天|日|周|月|年|次|%|％)"
NUMBER_WITH_UNIT_RE = re.compile(rf"(?<![\d.])(?P<number>{NUMBER_TOKEN})\s*(?P<unit>{NUMBER_UNIT})")
PERCENT_OF_RE = re.compile(rf"百分之\s*(?P<number>{NUMBER_TOKEN})")
STRUCTURAL_AFTER_RE = re.compile(
    r"^(?:最强|独立)?(?:问题|问句|问号|判断|结论|下一步|主动作|动作|实验|方法|议题|答案|答案槽|方向|变量|未知|证据缺口|反馈入口|阶段|状态|组合|标题|列表项|步骤|任务|事情|事|路|证据闭环)"
)
SUGGESTED_NUMBER_RE = re.compile(r"建议(?:的)?(?:边界|起点)|启发式(?:的)?(?:边界|起点)")


@dataclass(frozen=True)
class Check:
    text: str
    passed: bool
    evidence: str
    severe: bool = False


@dataclass(frozen=True)
class NumberPhrase:
    text: str
    key: tuple[str, str]
    start: int
    end: int
    segment: str


@dataclass(frozen=True)
class InteractionEvidence:
    host_control_status: str
    surface: str
    tool_call_observed: bool
    selection_mode: str
    options: tuple[str, ...] = ()
    host_free_text_available: bool = False
    question_text: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> InteractionEvidence:
        options = data.get("options", [])
        if not isinstance(options, list) or any(not isinstance(option, str) for option in options):
            raise ValueError("interaction options 必须是字符串数组")
        values = {
            "host_control_status": data.get("host_control_status"),
            "surface": data.get("surface"),
            "selection_mode": data.get("selection_mode"),
        }
        if values["host_control_status"] not in HOST_CONTROL_STATUSES:
            raise ValueError(f"不支持的 host_control_status：{values['host_control_status']}")
        if values["surface"] not in INTERACTION_SURFACES:
            raise ValueError(f"不支持的 interaction surface：{values['surface']}")
        if values["selection_mode"] not in SELECTION_MODES:
            raise ValueError(f"不支持的 selection_mode：{values['selection_mode']}")
        tool_call_observed = data.get("tool_call_observed")
        host_free_text_available = data.get("host_free_text_available")
        question_text = data.get("question_text", "")
        if not isinstance(tool_call_observed, bool):
            raise ValueError("tool_call_observed 必须是布尔值")
        if not isinstance(host_free_text_available, bool):
            raise ValueError("host_free_text_available 必须是布尔值")
        if not isinstance(question_text, str):
            raise ValueError("question_text 必须是字符串")
        return cls(
            host_control_status=str(values["host_control_status"]),
            surface=str(values["surface"]),
            tool_call_observed=tool_call_observed,
            selection_mode=str(values["selection_mode"]),
            options=tuple(options),
            host_free_text_available=host_free_text_available,
            question_text=question_text,
        )


def parse_interaction_evidence(path: Path) -> InteractionEvidence:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("interaction evidence 必须是 JSON 对象")
    return InteractionEvidence.from_dict(data)


def _matches_any(text: str, patterns: tuple[str, ...]) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, re.IGNORECASE | re.DOTALL)]


def _check(name: str, passed: bool, evidence: str, severe: bool = False) -> Check:
    return Check(text=name, passed=passed, evidence=evidence, severe=severe)


def _duplicate_headings(text: str) -> list[str]:
    headings = [match.strip().casefold() for match in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*$", text)]
    return sorted({heading for heading in headings if headings.count(heading) > 1})


def _method_labels(method_ids: list[str]) -> tuple[list[str], list[str]]:
    expected = [METHOD_LABELS[method_id] for method_id in method_ids if method_id in METHOD_LABELS]
    unknown = [method_id for method_id in method_ids if method_id not in METHOD_LABELS]
    return expected, unknown


def _choice_lines(text: str) -> list[str]:
    return [match.group(0).strip() for match in CHOICE_LINE_RE.finditer(text)]


def _has_free_expression(text: str) -> bool:
    return FREE_EXPRESSION_RE.search(text) is not None


def _visible_interaction_text(text: str, interaction: InteractionEvidence | None) -> str:
    if interaction is None:
        return text
    return "\n".join((text, interaction.question_text, *interaction.options))


def _interaction_choices(text: str, interaction: InteractionEvidence | None) -> list[str]:
    if interaction is not None and interaction.surface == "native-control":
        return list(interaction.options)
    return _choice_lines(text)


def _has_product_other(options: list[str] | tuple[str, ...]) -> bool:
    return any(PRODUCT_OTHER_RE.fullmatch(option.strip()) is not None for option in options)


def _native_or_fallback_valid(interaction: InteractionEvidence | None) -> bool:
    if interaction is None:
        return False
    if interaction.host_control_status == "available":
        return interaction.surface == "native-control" and interaction.tool_call_observed
    return interaction.surface == "text-fallback" and not interaction.tool_call_observed


def _free_input_valid(text: str, interaction: InteractionEvidence | None) -> bool:
    if interaction is None:
        return False
    if interaction.surface == "native-control":
        return interaction.host_free_text_available and _has_free_expression(interaction.question_text)
    if interaction.surface == "text-fallback":
        return _has_free_expression(text) and OTHER_OPTION_RE.search(text) is None
    return False


def _method_detail(text: str, label: str) -> bool:
    for line in text.splitlines():
        if label not in line:
            continue
        label_position = line.find(label)
        opening_position = max(line.rfind("（", 0, label_position), line.rfind("(", 0, label_position))
        closing_positions = [position for token in ("）", ")") if (position := line.find(token, label_position)) >= 0]
        if opening_position >= 0 and closing_positions and len(line.strip()) >= len(label) + 18:
            return True
    return False


def _chinese_to_decimal(text: str) -> Decimal | None:
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000, "亿": 100000000}
    if not text:
        return None
    if all(character in digits for character in text):
        return Decimal("".join(str(digits[character]) for character in text))
    total = 0
    section = 0
    number = 0
    for character in text:
        if character in digits:
            number = digits[character]
            continue
        unit = units.get(character)
        if unit is None:
            return None
        if unit < 10000:
            section += (number or 1) * unit
        else:
            section += number
            total += (section or 1) * unit
            section = 0
        number = 0
    return Decimal(total + section + number)


def _normalize_number(text: str) -> str:
    try:
        value = Decimal(text)
    except Exception:
        value = _chinese_to_decimal(text)
    if value is None:
        return text
    normalized = format(value.normalize(), "f")
    return normalized.rstrip("0").rstrip(".") if "." in normalized else normalized


def _normalize_unit(unit: str) -> str:
    aliases = {
        "人民币": "元",
        "块钱": "元",
        "名": "人",
        "位": "人",
        "日": "天",
        "星期": "周",
        "个月": "月",
        "％": "%",
    }
    return aliases.get(unit, unit)


def _local_segment(text: str, start: int, end: int) -> str:
    left = max(text.rfind(separator, 0, start) for separator in ("\n", "。", "！", "？", "；", ";")) + 1
    right_candidates = [text.find(separator, end) for separator in ("\n", "。", "！", "？", "；", ";")]
    right_candidates = [position for position in right_candidates if position >= 0]
    right = min(right_candidates, default=len(text))
    return text[left:right].strip()


def extract_number_phrases(text: str) -> list[NumberPhrase]:
    phrases: list[NumberPhrase] = []
    occupied: list[tuple[int, int]] = []

    for match in PERCENT_OF_RE.finditer(text):
        phrases.append(NumberPhrase(
            text=match.group(0),
            key=(_normalize_number(match.group("number")), "%"),
            start=match.start(),
            end=match.end(),
            segment=_local_segment(text, match.start(), match.end()),
        ))
        occupied.append((match.start(), match.end()))

    for match in NUMBER_WITH_UNIT_RE.finditer(text):
        if any(match.start() < end and match.end() > start for start, end in occupied):
            continue
        suffix = text[match.end():match.end() + 14]
        prefix = text[max(0, match.start() - 8):match.start()]
        if match.group("unit") == "个" and (
            STRUCTURAL_AFTER_RE.match(suffix)
            or re.search(r"(?:只(?:改|做|选|问|给|保留)?|同一|这个|当前)$", prefix)
        ):
            continue
        phrases.append(NumberPhrase(
            text=match.group(0),
            key=(_normalize_number(match.group("number")), _normalize_unit(match.group("unit"))),
            start=match.start(),
            end=match.end(),
            segment=_local_segment(text, match.start(), match.end()),
        ))
    return sorted(phrases, key=lambda phrase: phrase.start)


def _provided_number_keys(user_numbers: list[str] | None) -> set[tuple[str, str]]:
    return {
        phrase.key
        for source in (user_numbers or [])
        for phrase in extract_number_phrases(source)
    }


def _unmatched_a_numbers(text: str, user_numbers: list[str] | None) -> list[NumberPhrase]:
    provided = _provided_number_keys(user_numbers)
    return [phrase for phrase in extract_number_phrases(text) if phrase.key not in provided]


def _unattributed_b_numbers(text: str, user_numbers: list[str] | None) -> list[NumberPhrase]:
    provided = _provided_number_keys(user_numbers)
    return [
        phrase
        for phrase in extract_number_phrases(text)
        if phrase.key not in provided and SUGGESTED_NUMBER_RE.search(phrase.segment) is None
    ]


def grade_r(
    text: str,
    recommended_methods: list[str] | None = None,
    r_mode: str = "method",
    interaction: InteractionEvidence | None = None,
    method_selection_mode: str = "multi",
) -> list[Check]:
    if r_mode not in {"align", "method"}:
        raise ValueError(f"不支持的 R 子状态：{r_mode}")
    if method_selection_mode not in {"multi", "single"}:
        raise ValueError(f"不支持的 R-method 选择形态：{method_selection_mode}")

    recommended_methods = recommended_methods or []
    expected_labels, unknown_methods = _method_labels(recommended_methods)
    visible_text = _visible_interaction_text(text, interaction)
    labels_present = [label for label in METHOD_LABELS.values() if label in visible_text]
    found_labels = [label for label in expected_labels if label in visible_text]
    recommendation_details = {label: _method_detail(visible_text, label) for label in expected_labels}
    choices = _interaction_choices(text, interaction)
    expected_selection_mode = "multi" if r_mode == "align" else method_selection_mode
    judgments = _matches_any(visible_text, JUDGMENT_PATTERNS)
    actions = _matches_any(visible_text, ACTION_PATTERNS)
    external = _matches_any(visible_text, EXTERNAL_PATTERNS)
    duplicates = _duplicate_headings(visible_text)
    interaction_valid = (
        _native_or_fallback_valid(interaction)
        and interaction is not None
        and interaction.selection_mode == expected_selection_mode
    )
    checks = [
        _check(
            "阶段 R 有结构化交互证据",
            interaction is not None,
            "已提供交互证据" if interaction is not None else "缺少交互证据，不能从 Markdown 推断宿主能力",
            severe=True,
        ),
        _check(
            "阶段 R 在控件可用时使用原生选择，否则文本降级",
            interaction_valid,
            (
                "缺少交互证据"
                if interaction is None
                else (
                    f"host={interaction.host_control_status}；surface={interaction.surface}；"
                    f"tool_call={interaction.tool_call_observed}；mode={interaction.selection_mode}；"
                    f"expected_mode={expected_selection_mode}"
                )
            ),
            severe=True,
        ),
        _check(
            "阶段 R 提供少量产品选项",
            2 <= len(choices) <= 4 and not _has_product_other(choices),
            f"选择数量：{len(choices)}；选择：{choices}；产品自建 Other={_has_product_other(choices)}",
            severe=True,
        ),
        _check(
            "阶段 R 提供宿主自由输入或等价文本入口",
            _free_input_valid(text, interaction),
            (
                "缺少交互证据"
                if interaction is None
                else (
                    f"surface={interaction.surface}；host_free_text={interaction.host_free_text_available}；"
                    f"问题正文说明={_has_free_expression(interaction.question_text)}；"
                    f"文本自由入口={_has_free_expression(text)}"
                )
            ),
            severe=True,
        ),
        _check(
            "阶段 R 明确等待当前选择或表达",
            bool(interaction and interaction.surface == "native-control" and interaction.tool_call_observed)
            or WAIT_RE.search(text) is not None,
            (
                "原生控件调用后等待"
                if interaction and interaction.surface == "native-control" and interaction.tool_call_observed
                else ("找到文本等待表达" if WAIT_RE.search(text) else "未找到等待表达")
            ),
            severe=True,
        ),
        _check("阶段 R 不给判断", not judgments, f"命中判断模式：{judgments}" if judgments else "未命中判断模式", severe=True),
        _check("阶段 R 不给行动或验证步骤", not actions, f"命中行动模式：{actions}" if actions else "未命中行动模式", severe=True),
        _check("阶段 R 不建议外部能力", not external, f"命中外部能力模式：{external}" if external else "未命中外部能力模式", severe=True),
        _check("阶段 R 不含重复标题", not duplicates, f"重复标题：{duplicates}" if duplicates else "未发现重复标题"),
    ]

    if r_mode == "align":
        checks.extend([
            _check(
                "R-align 不提前展示或执行方法",
                not labels_present and not recommended_methods,
                f"用户可见方法名：{labels_present}；传入推荐方法：{recommended_methods}",
                severe=True,
            ),
            _check(
                "R-align 将理解标为暂定并允许纠正",
                bool(re.search(r"暂定|目前听起来|我现在听到|可能是|理解", visible_text)) and _free_input_valid(text, interaction),
                "找到暂定理解与纠正入口" if re.search(r"暂定|目前听起来|我现在听到|可能是|理解", visible_text) else "未找到暂定理解表达",
            ),
        ])
    else:
        checks.extend([
            _check(
                "R-method 显示推荐方法的正式名称",
                not unknown_methods and found_labels == expected_labels,
                f"预期：{expected_labels}；找到：{found_labels}；未知方法：{unknown_methods}",
                severe=True,
            ),
            _check(
                "R-method 使用白话在前并解释当前价值",
                all(recommendation_details.values()),
                f"方法说明：{recommendation_details}",
            ),
        ])
    return checks


def grade_a(
    text: str,
    cancelled_methods: list[str] | None = None,
    confirmed_methods: list[str] | None = None,
    user_numbers: list[str] | None = None,
    interaction: InteractionEvidence | None = None,
    answer_shape: str = "open",
) -> list[Check]:
    if answer_shape not in ANSWER_SHAPES:
        raise ValueError(f"不支持的 A 答案形态：{answer_shape}")

    cancelled_methods = cancelled_methods or []
    confirmed_methods = [method for method in (confirmed_methods or []) if method != "basic-analysis"]
    native_question = interaction.question_text if interaction and interaction.surface == "native-control" else ""
    visible_text = _visible_interaction_text(text, interaction)
    question_source = native_question if native_question else text
    marks = QUESTION_MARK_RE.findall(visible_text)
    stripped = question_source.rstrip()
    judgments = _matches_any(visible_text, JUDGMENT_PATTERNS)
    actions = _matches_any(visible_text, ACTION_PATTERNS)
    external = _matches_any(visible_text, EXTERNAL_PATTERNS)
    hidden_requests = _matches_any(visible_text, HIDDEN_INFO_REQUEST_PATTERNS)
    expected_labels, unknown_methods = _method_labels(confirmed_methods)
    echo_match = NATURAL_ECHO_RE.search(text[:500])
    echo_text = echo_match.group("line") if echo_match else ""
    found_labels = [label for label in expected_labels if label in echo_text]
    unexpected_labels = [label for label in METHOD_LABELS.values() if label not in expected_labels and label in echo_text]
    basic_only_echo = bool(re.search(r"基本梳理|基础分析", echo_text))
    analysis_text = visible_text
    if echo_match:
        analysis_text = text[:echo_match.start()] + text[echo_match.end():] + "\n" + native_question
    method_outputs = {
        method_id: _matches_any(analysis_text, METHOD_OUTPUT_PATTERNS.get(method_id, ()))
        for method_id in confirmed_methods
    }
    missing_outputs = [method_id for method_id, hits in method_outputs.items() if not hits]
    duplicates = _duplicate_headings(visible_text)
    choices = _interaction_choices(text, interaction)
    unmatched_numbers = _unmatched_a_numbers(visible_text, user_numbers)

    question_start = max(stripped.rfind("\n"), stripped.rfind("。"), stripped.rfind("！")) + 1
    question_text = stripped[question_start:].strip()
    question_slots = _matches_any(question_text, QUESTION_SLOT_PATTERNS)
    compound_question = _matches_any(question_text, COMPOUND_QUESTION_PATTERNS)
    if interaction is None:
        interaction_passed = False
    elif answer_shape == "finite-mutually-exclusive":
        interaction_passed = (
            _native_or_fallback_valid(interaction)
            and interaction.selection_mode == "single"
            and 2 <= len(choices) <= 4
            and not _has_product_other(choices)
            and _free_input_valid(text, interaction)
        )
    else:
        interaction_passed = (
            interaction.surface == "free-answer"
            and not interaction.tool_call_observed
            and interaction.selection_mode == "none"
            and not interaction.options
        )

    cancelled_hits: list[str] = []
    if "pre-mortem" in cancelled_methods:
        cancelled_hits.extend(_matches_any(text, PREMORTEM_PATTERNS))
    if "two-sided-steelman" in cancelled_methods:
        cancelled_hits.extend(_matches_any(text, STEELMAN_PATTERNS))

    echo_passed = (
        not unknown_methods
        and echo_match is not None
        and found_labels == expected_labels
        and not unexpected_labels
        and (bool(expected_labels) or basic_only_echo)
    )

    return [
        _check(
            "阶段 A 有结构化交互证据",
            interaction is not None,
            "已提供交互证据" if interaction is not None else "缺少交互证据，不能从 Markdown 推断宿主能力",
            severe=True,
        ),
        _check(
            "阶段 A 的交互形态匹配答案形态",
            interaction_passed,
            (
                "缺少交互证据"
                if interaction is None
                else (
                    f"answer_shape={answer_shape}；host={interaction.host_control_status}；"
                    f"surface={interaction.surface}；tool_call={interaction.tool_call_observed}；"
                    f"mode={interaction.selection_mode}；options={list(interaction.options)}；"
                    f"host_free_text={interaction.host_free_text_available}"
                )
            ),
            severe=True,
        ),
        _check(
            "阶段 A 自然回显最终确认的方法组合",
            echo_passed,
            (
                f"预期方法：{expected_labels or ['基本梳理']}；回显：{echo_text!r}；"
                f"找到：{found_labels}；多余：{unexpected_labels}；未知：{unknown_methods}"
            ),
            severe=True,
        ),
        _check(
            "阶段 A 的确认方法产生独特分析产出",
            not unknown_methods and not missing_outputs,
            f"各方法命中：{method_outputs}；缺少产出：{missing_outputs}",
            severe=True,
        ),
        _check("阶段 A 恰好一个问号", len(marks) == 1, f"问号数量：{len(marks)}", severe=True),
        _check("阶段 A 以唯一问号结束", bool(stripped) and stripped[-1:] in ("?", "？"), f"最后一个非空字符：{stripped[-1:]!r}", severe=True),
        _check(
            "阶段 A 的唯一问题只有一个答案槽",
            not compound_question and len(question_slots) <= 1,
            f"问题文本：{question_text!r}；答案槽模式：{question_slots}；复合模式：{compound_question}",
            severe=True,
        ),
        _check(
            "阶段 A 的有限答案保留自由输入，开放答案不造选项",
            (
                answer_shape == "finite-mutually-exclusive"
                and 2 <= len(choices) <= 4
                and not _has_product_other(choices)
                and _free_input_valid(text, interaction)
            )
            or (answer_shape == "open" and not choices),
            (
                f"答案形态={answer_shape}；选择数量={len(choices)}；"
                f"产品自建 Other={_has_product_other(choices)}；"
                f"自由输入={_free_input_valid(text, interaction)}"
            ),
            severe=True,
        ),
        _check("阶段 A 不用陈述句隐藏追加信息请求", not hidden_requests, f"隐藏信息请求模式：{hidden_requests}" if hidden_requests else "未发现隐藏信息请求", severe=True),
        _check("阶段 A 不给判断", not judgments, f"命中判断模式：{judgments}" if judgments else "未命中判断模式", severe=True),
        _check("阶段 A 不给行动、保护或停止方案", not actions, f"命中行动模式：{actions}" if actions else "未命中行动模式", severe=True),
        _check("阶段 A 不建议外部能力或请求授权", not external, f"命中外部能力模式：{external}" if external else "未命中外部能力模式", severe=True),
        _check("阶段 A 不变相执行已取消方法", not cancelled_hits, f"取消方法命中模式：{cancelled_hits}" if cancelled_hits else "未发现取消方法结构", severe=True),
        _check(
            "阶段 A 不使用用户未提供的决定相关数字",
            not unmatched_numbers,
            (
                "未发现用户未提供的决定相关数字"
                if not unmatched_numbers
                else f"未匹配数字：{[(phrase.text, phrase.segment) for phrase in unmatched_numbers]}"
            ),
            severe=True,
        ),
        _check("阶段 A 不含重复标题", not duplicates, f"重复标题：{duplicates}" if duplicates else "未发现重复标题"),
    ]


def _count_statuses(text: str, states: tuple[str, ...]) -> list[str]:
    experiment_start = text.find("先做这一件事")
    search_area = text[:experiment_start if experiment_start >= 0 else 500]
    status_match = re.search(
        r"(?:按目前信息，我更建议|我的判断|判断)[：:]\s*(?:\*{1,2})?(?P<state>[^。；;，,\n*]+)",
        search_area,
    )
    if status_match:
        status_text = status_match.group("state").strip()
        return [state for state in states if state in status_text]
    return []


def _experiment_body(text: str) -> tuple[int, str]:
    matches = list(re.finditer(r"(?m)^\s*#{0,3}\s*\*{0,2}先做这一件事\*{0,2}\s*$", text))
    if len(matches) != 1:
        return len(matches), ""
    start = matches[0].end()
    remainder = text[start:]
    feedback_match = re.search(r"(?m)^\s*\[(?:这个方向|方向对|我不同意|先放一放)", remainder)
    if feedback_match:
        remainder = remainder[:feedback_match.start()]
    next_heading = re.search(r"(?m)^#{1,3}\s+(?!\*{0,2}(?:动作|观察|复判)\b).+$", remainder)
    if next_heading:
        remainder = remainder[:next_heading.start()]
    return 1, remainder.strip()


def _independent_action_items(body: str) -> list[str]:
    items = re.findall(r"(?m)^\s*(?:[-*+] |\d+[.)]\s+)(.+)$", body)
    return [item for item in items if not re.match(r"\*{0,2}(?:动作|观察|复判)\*{0,2}[：:]", item.strip())]


def grade_b(
    text: str,
    already_executed: bool,
    user_numbers: list[str] | None = None,
    interaction: InteractionEvidence | None = None,
) -> list[Check]:
    marks = QUESTION_MARK_RE.findall(text)
    duplicates = _duplicate_headings(text)
    info_questions = _matches_any(text, INFORMATION_QUESTION_PATTERNS)
    expected_states = EXECUTED_STATES if already_executed else UNEXECUTED_STATES
    states = _count_statuses(text, expected_states)
    experiment_heading_count, experiment_body = _experiment_body(text)
    independent_items = _independent_action_items(experiment_body)
    multiple_actions = _matches_any(experiment_body, MULTI_ACTION_PATTERNS)
    action_labels = re.findall(r"(?m)^\s*(?:[-*+]\s*)?\*{0,2}动作\*{0,2}[：:]", experiment_body)
    observation_labels = re.findall(r"(?m)^\s*(?:[-*+]\s*)?\*{0,2}观察\*{0,2}[：:]", experiment_body)
    review_labels = re.findall(r"(?m)^\s*(?:[-*+]\s*)?\*{0,2}复判\*{0,2}[：:]", experiment_body)
    labels_valid = all(len(labels) <= 1 for labels in (action_labels, observation_labels, review_labels))
    if any((action_labels, observation_labels, review_labels)):
        labels_valid = labels_valid and all((action_labels, observation_labels, review_labels))
    authorization_inference = _matches_any(text, AUTHORIZATION_INFERENCE_PATTERNS)
    unattributed_numbers = _unattributed_b_numbers(text, user_numbers)
    external_position = min(
        [position for marker in ("外部验证", "另行明确授权") if (position := text.find(marker)) >= 0],
        default=-1,
    )
    judgment_position = min(
        [position for marker in ("按目前信息", "我的判断", "判断") if (position := text.find(marker)) >= 0],
        default=-1,
    )
    experiment_position = text.find("先做这一件事")
    external_after_judgment = external_position < 0 or (
        judgment_position >= 0 and experiment_position >= 0 and external_position > experiment_position
    )
    reversal = re.search(r"改变.*判断|判断.*改变|推翻.*结论|支持.*继续|反对.*继续|停止|转向|复判", text)

    interaction_passed = bool(
        interaction
        and interaction.surface == "declarative-feedback"
        and not interaction.tool_call_observed
        and interaction.selection_mode == "none"
        and not interaction.options
        and not interaction.question_text
    )

    return [
        _check(
            "阶段 B 有结构化交互证据",
            interaction is not None,
            "已提供交互证据" if interaction is not None else "缺少交互证据，不能证明 B 没有开启问题型控件",
            severe=True,
        ),
        _check(
            "阶段 B 使用陈述式反馈而非问题型控件",
            interaction_passed,
            (
                "缺少交互证据"
                if interaction is None
                else (
                    f"surface={interaction.surface}；tool_call={interaction.tool_call_observed}；"
                    f"mode={interaction.selection_mode}；options={list(interaction.options)}；"
                    f"question={interaction.question_text!r}"
                )
            ),
            severe=True,
        ),
        _check("阶段 B 不再提出信息问题", len(marks) == 0 and not info_questions, f"问号数量：{len(marks)}；信息问题模式：{info_questions}", severe=True),
        _check("阶段 B 使用一个与事项阶段匹配的判断状态", len(states) == 1, f"在判断区域找到状态：{states}", severe=True),
        _check(
            "阶段 B 只有一个现实实验",
            experiment_heading_count == 1 and bool(experiment_body) and len(independent_items) <= 1 and not multiple_actions and labels_valid,
            (
                f"实验标题数量：{experiment_heading_count}；独立列表项：{independent_items}；"
                f"多行动模式：{multiple_actions}；动作/观察/复判标签="
                f"{[len(action_labels), len(observation_labels), len(review_labels)]}"
            ),
            severe=True,
        ),
        _check("阶段 B 不把一种授权推定为另一种", not authorization_inference, f"越权推定模式：{authorization_inference}" if authorization_inference else "未发现授权范围推定", severe=True),
        _check("阶段 B 包含会改变判断的现实信号", reversal is not None, "找到改变判断的现实信号" if reversal else "未找到改变判断的现实信号"),
        _check("可选外部验证位于完整判断和现实实验之后", external_after_judgment, f"判断位置={judgment_position}，实验位置={experiment_position}，外部验证位置={external_position}", severe=True),
        _check(
            "阶段 B 的每个系统新增数字都有局部来源或建议性质",
            not unattributed_numbers,
            (
                "未发现缺少局部说明的系统新增数字"
                if not unattributed_numbers
                else f"缺少局部说明：{[(phrase.text, phrase.segment) for phrase in unattributed_numbers]}"
            ),
            severe=True,
        ),
        _check("阶段 B 不含重复标题", not duplicates, f"重复标题：{duplicates}" if duplicates else "未发现重复标题"),
    ]


def grade(
    stage: str,
    text: str,
    already_executed: bool,
    cancelled_methods: list[str],
    confirmed_methods: list[str],
    recommended_methods: list[str],
    user_numbers: list[str],
    r_mode: str,
    interaction: InteractionEvidence | None = None,
    answer_shape: str = "open",
    method_selection_mode: str = "multi",
) -> list[Check]:
    if stage == "R":
        return grade_r(
            text,
            recommended_methods,
            r_mode=r_mode,
            interaction=interaction,
            method_selection_mode=method_selection_mode,
        )
    if stage == "A":
        return grade_a(
            text,
            cancelled_methods,
            confirmed_methods,
            user_numbers,
            interaction=interaction,
            answer_shape=answer_shape,
        )
    if stage == "B":
        return grade_b(text, already_executed, user_numbers, interaction=interaction)
    raise ValueError(f"不支持的阶段：{stage}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=("R", "A", "B"))
    parser.add_argument("--input", required=True, type=Path, help="待评分的 Markdown 或文本文件")
    parser.add_argument("--already-executed", action="store_true")
    parser.add_argument("--r-mode", choices=("align", "method"), default="method")
    parser.add_argument("--method-selection-mode", choices=("multi", "single"), default="multi")
    parser.add_argument("--answer-shape", choices=tuple(sorted(ANSWER_SHAPES)), default="open")
    parser.add_argument("--interaction-json", type=Path, required=True, help="本轮结构化交互证据 JSON")
    parser.add_argument("--cancelled-method", action="append", default=[])
    parser.add_argument("--confirmed-method", action="append", default=[])
    parser.add_argument("--recommended-method", action="append", default=[])
    parser.add_argument("--user-number", action="append", default=[], help="用户已提供的数字短语，可重复")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    interaction = parse_interaction_evidence(args.interaction_json)
    checks = grade(
        args.stage,
        text,
        args.already_executed,
        args.cancelled_method,
        args.confirmed_method,
        args.recommended_method,
        args.user_number,
        args.r_mode,
        interaction,
        args.answer_shape,
        args.method_selection_mode,
    )
    passed = sum(check.passed for check in checks)
    result = {
        "contract_version": "0.1.3",
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
