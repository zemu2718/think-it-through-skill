#!/usr/bin/env python3
"""对“想清楚”v0.4.1 的阶段输出与 Gate 记录执行确定性合同检查。"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
CORE_SCHEMA_DIR = ROOT / "skills" / "think-it-through" / "core"
QUESTION_MARK_RE = re.compile(r"[?？]")

UNEXECUTED_STATES = ("暂不行动", "小步验证", "有条件推进", "可以推进")
EXECUTED_STATES = ("继续", "调整", "暂停", "停止")
B_STATUS_ENGLISH = {
    "hold": "暂不行动",
    "small test": "小步验证",
    "proceed conditionally": "有条件推进",
    "proceed": "可以推进",
    "continue": "继续",
    "adjust": "调整",
    "pause": "暂停",
    "stop": "停止",
}
B_STATUS_MARK_RE = re.compile(
    r"(?:"
    r"（当前判断：(?P<zh>暂不行动|小步验证|有条件推进|可以推进|继续|调整|暂停|停止)）|"
    r"\(current judgment:\s*(?P<en>hold|small test|proceed conditionally|proceed|continue|adjust|pause|stop)\)"
    r")",
    re.IGNORECASE,
)
B_LOOP_SUFFIXES = {
    "core_hypothesis": ("（核心假设）", "(core hypothesis)"),
    "action": ("（本轮动作）", "(action for this round)"),
    "observation": ("（观察信号）", "(signals to observe)"),
    "reassessment": ("（复判条件）", "(reassessment condition)"),
}
B_LOOP_ORDER = tuple(B_LOOP_SUFFIXES)
B_LOOP_PREFIX_RE = re.compile(
    r"(?mi)^\s*(?:[-*+]\s*)?\*{0,2}"
    r"(?:核心假设|动作|观察|复判|core hypothesis|action|observe|observation|reassess|reassessment)"
    r"\*{0,2}[：:]"
)
B_CONTENT_BOUNDARY_RE = re.compile(
    r"(?mi)^#{1,3}\s+(?:决策快照|decision snapshot|反馈|feedback)\s*$"
)
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
    r"(?:已经|既然).{0,30}(?:同意|授权|选择|反馈).{0,30}(?:所以|因此|就).{0,40}(?:执行|读取|联系|发送|发布|购买|删除|修改)",
    r"(?:能力调用|联网|搜索|浏览|方向符合|调整下一步).{0,24}(?:等于|意味着|视为).{0,24}(?:执行|数据访问|读取|联系|发送|发布|外部行动)",
    r"无需(?:另行|再次).{0,12}授权",
    r"自动(?:执行|读取|联系|发送|发布|购买|删除|修改)",
    r"(?:我会|我将|现在开始|直接)(?:立即)?(?:执行|读取|联系|发送|发布|购买|删除|修改)(?:实验|私有|你的|外部)?",
)

CHOICE_LINE_RE = re.compile(r"(?m)^\s*(?:[-*+]\s*)?\[[^\]\n]{1,48}\]\s*$")
FREE_EXPRESSION_RE = re.compile(
    r"(?:也可以|或者可以|你也能).{0,36}(?:不选|直接|按你的方式|自由|补充|纠正|说出|说说)",
    re.DOTALL,
)
OTHER_OPTION_RE = re.compile(r"(?m)^\s*(?:[-*+]\s*)?\[(?:其他|其它|Other)\]\s*$", re.IGNORECASE)
PRODUCT_OTHER_RE = re.compile(r"^(?:其他|其它|Other)$", re.IGNORECASE)
WAIT_RE = re.compile(r"等待|等你|确认.*再继续|选好.*继续|说完.*继续")

HOST_CONTROL_STATUSES = {"available", "unavailable", "failed", "rejected"}
INTERACTION_SURFACES = {"native-control", "text-fallback", "free-answer"}
SELECTION_MODES = {"multi", "single", "none"}
SUPPLEMENT_MODES = {"none", "native-note", "follow-up-message", "inline-text"}
ANSWER_SHAPES = {"compatible-set", "finite-mutually-exclusive", "open"}
METHOD_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
METHOD_DESCRIPTION_MIN_LENGTH = 12
A_ANSWER_SHAPES = {"finite-mutually-exclusive", "open"}
CONSENT_TYPES = {
    "capability_call",
    "participation_delegation",
    "private_data_access",
    "external_action",
}
CAPABILITY_AVAILABILITY = {"available", "unavailable", "unknown"}
CAPABILITY_READINESS = {"ready", "requires_approval", "requires_auth", "failed"}
OPERATION_STATUSES = {
    "planned",
    "started",
    "completed",
    "partial",
    "failed",
    "declined",
    "cancelled",
    "unavailable",
}
TERMINAL_OPERATION_STATUSES = {
    "completed",
    "partial",
    "failed",
    "declined",
    "cancelled",
    "unavailable",
}
AGENT_PAYLOAD_KEYS = {
    "assigned_question",
    "claims",
    "evidence_and_sources",
    "assumptions",
    "uncertainties",
    "conflicts",
    "what_would_reverse_this",
}
PARTICIPATION_SYNTHESIS_KEYS = {
    "completed_tasks",
    "adopted_material",
    "set_aside_material",
    "unresolved_material",
    "conflict_handling",
    "judgment_impact",
    "main_reality_loop_impact",
}
PROJECT_VIABILITY_KEYS = {
    "contract_version",
    "decision_context",
    "user_outcome",
    "focal_solution",
    "validation_layers",
    "search_passes",
    "sources",
    "candidates",
    "strongest_alternative_id",
    "alternative_trial",
    "adversarial_review",
    "evidence_items",
    "commitment",
    "no_go_conditions",
    "reassessment_triggers",
}
PROJECT_VALIDATION_LAYERS = (
    "problem_existence",
    "problem_strength",
    "solution_fit",
    "alternative_ecosystem",
)
PROJECT_SEARCH_PASS_TYPES = (
    "outcome_problem_first",
    "solution_implementation_second",
)
PROJECT_SEARCH_STATUSES = {
    "completed",
    "partial",
    "not_authorized",
    "failed",
    "not_performed",
    "unavailable",
}
PROJECT_CANDIDATE_CATEGORIES = {
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
}
PROJECT_COVERAGE_STATUSES = {"covered", "not_applicable", "unknown"}
PROJECT_VERIFICATION_STATUSES = {"verified", "not_applicable", "unknown"}
PROJECT_TRIAL_STATUSES = {"receipt_backed", "user_reported", "not_performed"}
PROJECT_ADVERSARIAL_STATUSES = {"not_needed", "completed", "not_performed", "failed"}
PROJECT_EVIDENCE_STATES = {"supports", "opposes", "conflicts", "unknown"}
PROJECT_COMMITMENT_DIRECTIONS = {
    "pause": 0,
    "stop": 0,
    "limited_validation": 1,
    "adopt": 2,
    "combine": 2,
    "thin_integration": 2,
    "independent_build": 3,
}
PROJECT_DECISION_CONTEXT_KEYS = {
    "decision",
    "commitment_type",
    "material_change",
    "prior_conclusion_status",
}
PROJECT_FOCAL_SOLUTION_KEYS = {"description", "status"}
PROJECT_LAYER_KEYS = {"status", "evidence_item_ids"}
PROJECT_SEARCH_PASS_KEYS = {
    "type",
    "status",
    "query_boundaries",
    "consent_id",
    "receipt_id",
    "source_ids",
}
PROJECT_SOURCE_KEYS = {"id", "receipt_id", "locator"}
PROJECT_CANDIDATE_KEYS = {
    "id",
    "name",
    "category",
    "coverage_status",
    "material",
    "reason",
    "source_ids",
    "verification_dimensions",
}
PROJECT_VERIFICATION_KEYS = {"dimension", "status", "reason", "source_ids"}
PROJECT_TRIAL_KEYS = {
    "status",
    "candidate_id",
    "real_tasks",
    "success_criteria",
    "result",
    "consent_ids",
    "receipt_ids",
    "evidence_item_ids",
    "reason",
}
PROJECT_TRIAL_RESULTS = {"solves_core", "partially_solves", "does_not_solve", "unknown"}
PROJECT_ADVERSARIAL_KEYS = {
    "required",
    "status",
    "consent_id",
    "receipt_id",
    "payload",
    "evidence_item_ids",
    "reason",
}
PROJECT_EVIDENCE_ITEM_KEYS = {"id", "state", "claim", "source_ids"}
PROJECT_COMMITMENT_KEYS = {
    "direction",
    "chosen_rank",
    "rationale",
    "evidence_item_ids",
    "upgrade_conditions",
}
PROJECT_CONDITION_KEYS = {"id", "condition", "evidence_item_ids"}
DECISION_STATES = {
    "hold",
    "small_test",
    "proceed_conditionally",
    "proceed",
    "continue",
    "adjust",
    "pause",
    "stop",
}
CHECKPOINT_TRIGGER_TYPES = {
    "project-initiation",
    "direction-selection",
    "major-investment",
    "continued-escalation",
    "result-reassessment",
    "close-negative",
}
CHECKPOINT_HIGH_VALUE_TRIGGERS = CHECKPOINT_TRIGGER_TYPES - {"close-negative"}
CHECKPOINT_MATERIAL_CHANGES = {
    "none",
    "new-evidence",
    "purpose-change",
    "commitment-scope-expanded",
    "new-reassessment-node",
    "new-topic",
}
CHECKPOINT_RESPONSES = {
    "not-applicable",
    "pending",
    "ambiguous",
    "enter-full-check",
    "continue-current-task",
}
CHECKPOINT_OPTION_IDS = ("enter-full-check", "continue-current-task")
CHECKPOINT_NUMBERED_RE = re.compile(r"(?m)^\s*([1-2])[.)、]\s*(.+?)\s*$")
CHECKPOINT_PSEUDO_RE = re.compile(
    r"(?m)^\s*(?:[-*+]\s+)?(?:\[[^]\n]+\]|\[[ xX]\]\s*.+|[○◯◉☐☑]\s*.+|<input\b[^>]*>.*)$",
    re.IGNORECASE,
)
CHECKPOINT_FORBIDDEN_ANALYSIS_PATTERNS = (
    r"（当前判断：|\(current judgment:",
    r"(?:建议|结论|判断)[：:]",
    r"你(?:现在|应该|应当|最好)",
    r"(?:双向钢人|失败预演|对象校准|系统瓶颈|阶段匹配|资源支点|边界契约|沟通匹配|证据闭环)",
    r"(?:核心假设|本轮动作|观察信号|复判条件)",
)
CHECKPOINT_FORBIDDEN_GATE_PATTERNS = (
    r"Evidence Gate|Participation Gate",
    r"(?:发起|开始|进行|建议|需要)(?:联网|搜索|调研|读取文件|读取数据|调用工具|启动 Agent|真人参与)",
    r"(?:授权我|需要你授权|同意联网|同意搜索|同意委派)",
)
FEEDBACK_DIRECTION_IDS = (
    "accept",
    "adjust-next-step",
    "disagree",
    "set-aside",
)
FEEDBACK_SUPPLEMENT_TYPES = {
    "none",
    "consistent",
    "experiment-adjustment",
    "judgment-disagreement",
    "new-fact",
    "purpose-change",
}
FEEDBACK_OPTION_SETS = (
    ("方向符合我", "调整下一步", "不同意这个判断", "暂时先放一放"),
    ("This direction fits", "Adjust the next step", "I disagree with this judgment", "Set it aside for now"),
)
FEEDBACK_QUESTION_RE = re.compile(
    r"(?:"
    r"这份判断(?:更)?接近你的哪种反馈|"
    r"哪一项(?:更)?接近你的反馈|"
    r"你的反馈更接近哪一项|"
    r"which (?:option|response) best matches your feedback|"
    r"how does this judgment land"
    r")[?？]",
    re.IGNORECASE,
)
NATIVE_NOTE_HINT_RE = re.compile(r"补充说明.{0,8}可选|(?:附注|备注).{0,16}(?:补充|纠正)|optional note", re.IGNORECASE)
FOLLOW_UP_HINT_RE = re.compile(
    r"选(?:中|择)后.{0,30}(?:再发|发送).{0,12}(?:普通消息|消息).{0,20}(?:补充|纠正|新事实)|"
    r"after selecting.{0,40}(?:message|reply).{0,20}(?:add|correct|new fact)",
    re.IGNORECASE,
)
INLINE_SUPPLEMENT_HINT_RE = re.compile(r"同一条消息.{0,20}补充|同一条回复.{0,20}补充|same (?:message|reply).{0,20}(?:add|explain)", re.IGNORECASE)
FEEDBACK_HEADING_RE = re.compile(r"(?m)^#{1,3}\s+(?:反馈|Feedback)\s*$", re.IGNORECASE)
NUMBERED_FEEDBACK_RE = re.compile(r"(?m)^\s*([1-4])[.)、]\s*(.+?)\s*$")
PSEUDO_FEEDBACK_RE = re.compile(
    r"(?m)^\s*(?:[-*+]\s+)?(?:\[[^]\n]+\]|\[[ xX]\]\s*.+|[○◯◉☐☑]\s*.+|<input\b[^>]*>.*)$",
    re.IGNORECASE,
)
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
    r"^(?:最强|独立)?(?:问题|问句|问号|判断|结论|下一步|主动作|动作|实验|方法|议题|答案|答案槽|方向|编号|变量|未知|证据缺口|反馈入口|阶段|状态|组合|标题|列表项|步骤|任务|事情|事|路|证据闭环)"
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
class FeedbackRoute:
    next_stage: str
    preserve_judgment: bool
    text_overrode_selection: bool


@dataclass(frozen=True)
class InteractionOption:
    label: str
    id: str | None = None
    description: str = ""
    recommended: bool | None = None

    @classmethod
    def from_value(
        cls,
        value: object,
        *,
        option_contract: str = "standard",
    ) -> InteractionOption:
        if option_contract not in {"standard", "checkpoint"}:
            raise ValueError(f"不支持的 option_contract：{option_contract}")
        if isinstance(value, str):
            if option_contract == "checkpoint":
                raise ValueError("checkpoint interaction option 必须包含稳定 id 与 label")
            if not value.strip():
                raise ValueError("interaction option 字符串不能为空")
            return cls(label=value)
        if not isinstance(value, dict):
            raise ValueError("interaction option 必须是字符串或对象")

        if option_contract == "checkpoint":
            if set(value) != {"id", "label"}:
                raise ValueError("checkpoint interaction option 必须且只能包含 id、label")
            option_id = value["id"]
            label = value["label"]
            if option_id not in CHECKPOINT_OPTION_IDS:
                raise ValueError("checkpoint interaction option id 不在稳定集合中")
            if not isinstance(label, str) or not label.strip():
                raise ValueError("interaction option label 必须是非空字符串")
            return cls(id=option_id, label=label)

        if set(value) != {"id", "label", "description", "recommended"}:
            raise ValueError("结构化 interaction option 必须且只能包含 id、label、description、recommended")
        option_id = value["id"]
        label = value["label"]
        description = value["description"]
        recommended = value["recommended"]
        if not isinstance(option_id, str) or not METHOD_ID_RE.fullmatch(option_id):
            raise ValueError("interaction option id 必须是稳定 kebab-case 字符串")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("interaction option label 必须是非空字符串")
        if not isinstance(description, str) or not description.strip():
            raise ValueError("interaction option description 必须是非空字符串")
        if not isinstance(recommended, bool):
            raise ValueError("interaction option recommended 必须是布尔值")
        return cls(
            id=option_id,
            label=label,
            description=description,
            recommended=recommended,
        )

    @property
    def visible_text(self) -> str:
        marker = "（推荐）" if self.recommended else ""
        return "\n".join(part for part in (f"{self.label}{marker}", self.description) if part)


@dataclass(frozen=True)
class InteractionEvidence:
    host_control_status: str
    surface: str
    tool_call_observed: bool
    selection_mode: str
    options: tuple[InteractionOption | str, ...] = ()
    host_free_text_available: bool = False
    question_text: str = ""
    supplement_mode: str = "none"

    def __post_init__(self) -> None:
        normalized = tuple(
            option if isinstance(option, InteractionOption) else InteractionOption.from_value(option)
            for option in self.options
        )
        object.__setattr__(self, "options", normalized)

    @property
    def option_labels(self) -> tuple[str, ...]:
        return tuple(option.label for option in self.options)

    @property
    def method_options(self) -> tuple[InteractionOption, ...]:
        return tuple(
            option
            for option in self.options
            if option.id is not None and option.recommended is not None
        )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
        *,
        option_contract: str = "standard",
    ) -> InteractionEvidence:
        options = data.get("options", [])
        if not isinstance(options, list):
            raise ValueError("interaction options 必须是数组")
        normalized_options = tuple(
            InteractionOption.from_value(option, option_contract=option_contract)
            for option in options
        )
        values = {
            "host_control_status": data.get("host_control_status"),
            "surface": data.get("surface"),
            "selection_mode": data.get("selection_mode"),
            "supplement_mode": data.get("supplement_mode", "none"),
        }
        if values["host_control_status"] not in HOST_CONTROL_STATUSES:
            raise ValueError(f"不支持的 host_control_status：{values['host_control_status']}")
        if values["surface"] not in INTERACTION_SURFACES:
            raise ValueError(f"不支持的 interaction surface：{values['surface']}")
        if values["selection_mode"] not in SELECTION_MODES:
            raise ValueError(f"不支持的 selection_mode：{values['selection_mode']}")
        if values["supplement_mode"] not in SUPPLEMENT_MODES:
            raise ValueError(f"不支持的 supplement_mode：{values['supplement_mode']}")
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
            options=normalized_options,
            host_free_text_available=host_free_text_available,
            question_text=question_text,
            supplement_mode=str(values["supplement_mode"]),
        )


def parse_interaction_evidence(
    path: Path,
    *,
    option_contract: str = "standard",
) -> InteractionEvidence:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("interaction evidence 必须是 JSON 对象")
    return InteractionEvidence.from_dict(data, option_contract=option_contract)


def parse_json_object(path: Path, label: str) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{label} 必须是 JSON 对象")
    return data


@dataclass(frozen=True)
class CheckpointContext:
    trigger_type: str
    explicit_invocation: bool
    active_flow: bool
    same_decision_cooling_down: bool
    material_change: str
    response: str
    next_stage: str
    waited_for_user: bool
    commitment: str
    decision_sensitive_unknown: str
    why_now: str
    decision_scope: dict[str, object]
    capability_calls: tuple[str, ...]
    consent_ids: tuple[str, ...]
    decision_record_created: bool
    persistence_written: bool

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CheckpointContext:
        required = {
            "trigger_type",
            "explicit_invocation",
            "active_flow",
            "same_decision_cooling_down",
            "material_change",
            "response",
            "next_stage",
            "waited_for_user",
            "commitment",
            "decision_sensitive_unknown",
            "why_now",
            "decision_scope",
            "capability_calls",
            "consent_ids",
            "decision_record_created",
            "persistence_written",
        }
        if set(data) != required:
            raise ValueError(
                f"checkpoint context 字段必须精确匹配；缺少={sorted(required - set(data))}；"
                f"多余={sorted(set(data) - required)}"
            )
        trigger_type = data["trigger_type"]
        material_change = data["material_change"]
        response = data["response"]
        next_stage = data["next_stage"]
        if trigger_type not in CHECKPOINT_TRIGGER_TYPES:
            raise ValueError(f"不支持的 checkpoint trigger_type：{trigger_type}")
        if material_change not in CHECKPOINT_MATERIAL_CHANGES:
            raise ValueError(f"不支持的 checkpoint material_change：{material_change}")
        if response not in CHECKPOINT_RESPONSES:
            raise ValueError(f"不支持的 checkpoint response：{response}")
        if next_stage not in {
            "pre-entry",
            "R-align",
            "R-method",
            "resume-current-task",
            "active-flow",
        }:
            raise ValueError(f"不支持的 checkpoint next_stage：{next_stage}")
        for field in (
            "explicit_invocation",
            "active_flow",
            "same_decision_cooling_down",
            "waited_for_user",
            "decision_record_created",
            "persistence_written",
        ):
            if not isinstance(data[field], bool):
                raise ValueError(f"checkpoint {field} 必须是布尔值")
        for field in ("commitment", "decision_sensitive_unknown", "why_now"):
            if not isinstance(data[field], str):
                raise ValueError(f"checkpoint {field} 必须是字符串")
        decision_scope = data["decision_scope"]
        if not isinstance(decision_scope, dict):
            raise ValueError("checkpoint decision_scope 必须是对象")
        for field in ("capability_calls", "consent_ids"):
            value = data[field]
            if not isinstance(value, list) or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                raise ValueError(f"checkpoint {field} 必须是非空字符串数组或空数组")
        return cls(
            trigger_type=str(trigger_type),
            explicit_invocation=data["explicit_invocation"],
            active_flow=data["active_flow"],
            same_decision_cooling_down=data["same_decision_cooling_down"],
            material_change=str(material_change),
            response=str(response),
            next_stage=str(next_stage),
            waited_for_user=data["waited_for_user"],
            commitment=data["commitment"],
            decision_sensitive_unknown=data["decision_sensitive_unknown"],
            why_now=data["why_now"],
            decision_scope=dict(decision_scope),
            capability_calls=tuple(data["capability_calls"]),
            consent_ids=tuple(data["consent_ids"]),
            decision_record_created=data["decision_record_created"],
            persistence_written=data["persistence_written"],
        )


def parse_checkpoint_context(path: Path) -> CheckpointContext:
    return CheckpointContext.from_dict(parse_json_object(path, "checkpoint context"))


def _matches_any(text: str, patterns: tuple[str, ...]) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, re.IGNORECASE | re.DOTALL)]


def _check(name: str, passed: bool, evidence: str, severe: bool = False) -> Check:
    return Check(text=name, passed=passed, evidence=evidence, severe=severe)


@lru_cache(maxsize=None)
def _schema_validator(schema_name: str) -> Draft202012Validator:
    schema = json.loads((CORE_SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _schema_errors(instance: object, schema_name: str) -> list[str]:
    errors = sorted(
        _schema_validator(schema_name).iter_errors(instance),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            error.message,
        ),
    )
    rendered = []
    for error in errors:
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        rendered.append(f"{path}: {error.message}")
    return rendered


def _schema_check(name: str, instance: object, schema_name: str) -> tuple[Check, bool]:
    errors = _schema_errors(instance, schema_name)
    valid = not errors
    return (
        _check(
            name,
            valid,
            "canonical schema 校验通过" if valid else "；".join(errors),
            severe=True,
        ),
        valid,
    )


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
    option_text = tuple(option.visible_text for option in interaction.options)
    return "\n".join((text, interaction.question_text, *option_text))


def _interaction_choices(text: str, interaction: InteractionEvidence | None) -> list[str]:
    if interaction is not None and interaction.surface == "native-control":
        return list(interaction.option_labels)
    return _choice_lines(text)


def _has_product_other(options: list[str] | tuple[str, ...]) -> bool:
    return any(PRODUCT_OTHER_RE.fullmatch(option.strip()) is not None for option in options)


def _options_have_questions(options: list[str] | tuple[str, ...]) -> bool:
    return any(QUESTION_MARK_RE.search(option) is not None for option in options)


def _semantic_paragraphs(text: str) -> list[str]:
    return [paragraph.strip() for paragraph in re.split(r"\n[ \t]*\n", text.strip()) if paragraph.strip()]


def _last_paragraph_is_only_question(text: str, require_prior_paragraph: bool = False) -> bool:
    paragraphs = _semantic_paragraphs(text)
    marks = QUESTION_MARK_RE.findall(text)
    if not paragraphs or len(marks) != 1:
        return False
    if require_prior_paragraph and len(paragraphs) < 2:
        return False
    last = paragraphs[-1].rstrip()
    return QUESTION_MARK_RE.search(last) is not None and last[-1:] in ("?", "？")


def _selection_mode_hint(text: str, selection_mode: str) -> bool:
    patterns = {
        "multi": r"可多选|可以多选|选择多个|同时选择",
        "single": r"可单选|可以单选|选择一项|选一个",
    }
    return re.search(patterns[selection_mode], text) is not None


def _selection_question_layout(question_text: str, selection_mode: str) -> bool:
    paragraphs = _semantic_paragraphs(question_text)
    if not _last_paragraph_is_only_question(question_text, require_prior_paragraph=True):
        return False
    guidance = "\n\n".join(paragraphs[:-1])
    return _selection_mode_hint(guidance, selection_mode) and _has_free_expression(guidance)


def _text_fallback_layout(text: str, selection_mode: str) -> bool:
    matches = list(CHOICE_LINE_RE.finditer(text))
    if not matches:
        return False
    prompt = text[:matches[0].start()].rstrip()
    tail = text[matches[-1].end():].strip()
    return not tail and _selection_question_layout(prompt, selection_mode)


def _selection_layout_valid(
    text: str,
    interaction: InteractionEvidence | None,
    selection_mode: str,
) -> bool:
    if interaction is None:
        return False
    if interaction.surface == "native-control":
        return _selection_question_layout(interaction.question_text, selection_mode)
    if interaction.surface == "text-fallback":
        return _text_fallback_layout(text, selection_mode)
    return False


def _free_answer_interaction_valid(interaction: InteractionEvidence | None) -> bool:
    return bool(
        interaction
        and interaction.surface == "free-answer"
        and not interaction.tool_call_observed
        and interaction.selection_mode == "none"
        and not interaction.options
        and not interaction.question_text
    )


def _native_or_fallback_valid(interaction: InteractionEvidence | None) -> bool:
    if interaction is None:
        return False
    if interaction.host_control_status == "available":
        return interaction.surface == "native-control" and interaction.tool_call_observed
    if interaction.host_control_status == "unavailable":
        return interaction.surface == "text-fallback" and not interaction.tool_call_observed
    return interaction.surface == "text-fallback" and interaction.tool_call_observed


def resolve_b_feedback_route(
    direction_id: str,
    supplement_type: str = "none",
) -> FeedbackRoute:
    """按 fixture 已标注的反馈语义返回下一位置，不猜测任意自然语言。"""
    if direction_id not in FEEDBACK_DIRECTION_IDS:
        raise ValueError(f"不支持的反馈方向：{direction_id}")
    if supplement_type not in FEEDBACK_SUPPLEMENT_TYPES:
        raise ValueError(f"不支持的反馈补充类型：{supplement_type}")

    if supplement_type == "purpose-change":
        return FeedbackRoute("R-align", False, direction_id != "disagree")
    if supplement_type == "new-fact":
        return FeedbackRoute("A", False, direction_id != "disagree")
    if supplement_type == "judgment-disagreement":
        return FeedbackRoute("R-method", False, direction_id != "disagree")
    if supplement_type == "experiment-adjustment":
        return FeedbackRoute("B-revision", True, direction_id != "adjust-next-step")
    if direction_id in {"accept", "set-aside"}:
        return FeedbackRoute("end", True, False)
    if direction_id == "adjust-next-step":
        return FeedbackRoute("await-supplement", True, False)
    return FeedbackRoute("R-method", False, False)


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


def _method_option_contract(
    interaction: InteractionEvidence | None,
) -> tuple[bool, dict[str, object]]:
    if interaction is None or interaction.surface != "native-control":
        return False, {"reason": "缺少原生方法候选证据"}
    options = interaction.method_options
    all_structured = len(options) == len(interaction.options)
    ids = [option.id for option in options]
    labels = [option.label for option in options]
    descriptions = [option.description.strip() for option in options]
    ids_valid = all(option_id and METHOD_ID_RE.fullmatch(option_id) for option_id in ids)
    labels_valid = all(
        option.id in METHOD_LABELS and METHOD_LABELS[option.id] == option.label
        for option in options
    )
    descriptions_valid = all(
        len(description) >= METHOD_DESCRIPTION_MIN_LENGTH
        and option.label not in description
        for option, description in zip(options, descriptions)
    )
    recommended_valid = all(isinstance(option.recommended, bool) for option in options)
    unique = len(ids) == len(set(ids)) and len(labels) == len(set(labels))
    passed = bool(
        options
        and all_structured
        and ids_valid
        and labels_valid
        and descriptions_valid
        and recommended_valid
        and unique
    )
    return passed, {
        "all_structured": all_structured,
        "ids": ids,
        "labels": labels,
        "descriptions_valid": descriptions_valid,
        "recommended": [option.recommended for option in options],
        "unique": unique,
    }


def _method_recommendations_match(
    interaction: InteractionEvidence | None,
    recommended_methods: list[str],
) -> tuple[bool, dict[str, object]]:
    if interaction is None:
        return False, {"reason": "缺少交互证据"}
    option_ids = [option.id for option in interaction.method_options]
    marked = [option.id for option in interaction.method_options if option.recommended]
    unknown = [method_id for method_id in recommended_methods if method_id not in METHOD_LABELS]
    passed = not unknown and marked == recommended_methods and set(recommended_methods) <= set(option_ids)
    return passed, {
        "expected": recommended_methods,
        "marked": marked,
        "option_ids": option_ids,
        "unknown": unknown,
    }


def _method_descriptions_duplicated_in_body(
    text: str,
    interaction: InteractionEvidence | None,
) -> list[str]:
    if interaction is None or interaction.surface != "native-control":
        return []
    normalized_body = re.sub(r"\s+", "", text)
    return [
        option.id or option.label
        for option in interaction.method_options
        if re.sub(r"\s+", "", option.description) in normalized_body
    ]


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


def _checkpoint_should_present(context: CheckpointContext) -> bool:
    return bool(
        context.trigger_type in CHECKPOINT_HIGH_VALUE_TRIGGERS
        and not context.explicit_invocation
        and not context.active_flow
        and (
            not context.same_decision_cooling_down
            or context.material_change != "none"
        )
    )


def _checkpoint_scope_valid(context: CheckpointContext) -> bool:
    expected = {"decision_object", "true_objective", "commitment_scope"}
    return set(context.decision_scope) == expected and all(
        _nonempty_string(context.decision_scope.get(field))
        for field in expected
    )


def _checkpoint_option_ids(interaction: InteractionEvidence | None) -> tuple[str, ...]:
    if interaction is None:
        return ()
    return tuple(option.id or "" for option in interaction.options)


def _checkpoint_numbered_options(text: str) -> tuple[str, ...]:
    matches = list(CHECKPOINT_NUMBERED_RE.finditer(text))
    if [match.group(1) for match in matches] != ["1", "2"]:
        return ()
    return tuple(match.group(2).strip() for match in matches)


def _checkpoint_interaction_valid(
    text: str,
    interaction: InteractionEvidence | None,
) -> bool:
    if interaction is None or interaction.selection_mode != "single":
        return False
    if interaction.host_control_status == "available":
        return bool(
            interaction.surface == "native-control"
            and interaction.tool_call_observed
            and _checkpoint_option_ids(interaction) == CHECKPOINT_OPTION_IDS
            and interaction.host_free_text_available
        )
    expected_call = interaction.host_control_status in {"failed", "rejected"}
    return bool(
        interaction.surface == "text-fallback"
        and interaction.tool_call_observed is expected_call
        and not interaction.options
        and _checkpoint_numbered_options(text)
    )


def _checkpoint_layout_valid(
    text: str,
    interaction: InteractionEvidence | None,
) -> bool:
    if interaction is None:
        return False
    if interaction.surface == "native-control":
        return bool(
            _selection_question_layout(interaction.question_text, "single")
            and len(QUESTION_MARK_RE.findall(interaction.question_text)) == 1
            and not _options_have_questions(interaction.option_labels)
            and CHECKPOINT_PSEUDO_RE.search(text) is None
        )
    if interaction.surface != "text-fallback":
        return False
    matches = list(CHECKPOINT_NUMBERED_RE.finditer(text))
    if not matches:
        return False
    prompt = text[:matches[0].start()].rstrip()
    tail = text[matches[-1].end():].strip()
    return bool(
        not tail
        and len(QUESTION_MARK_RE.findall(prompt)) == 1
        and _last_paragraph_is_only_question(prompt, require_prior_paragraph=True)
        and (
            _has_free_expression(prompt)
            or re.search(r"(?:直接|自由).{0,16}(?:纠正|补充|说明)", prompt) is not None
        )
        and _checkpoint_numbered_options(text)
        and CHECKPOINT_PSEUDO_RE.search(text) is None
    )


def _checkpoint_route_valid(
    context: CheckpointContext,
    should_present: bool,
) -> bool:
    if not should_present:
        if context.response != "not-applicable" or context.waited_for_user:
            return False
        if context.explicit_invocation:
            return context.next_stage in {"R-align", "R-method"}
        if context.active_flow:
            return context.next_stage == "active-flow"
        return context.next_stage == "resume-current-task"
    expected_stages = {
        "pending": {"pre-entry"},
        "ambiguous": {"pre-entry"},
        "enter-full-check": {"R-align", "R-method"},
        "continue-current-task": {"resume-current-task"},
    }
    return bool(
        context.response in expected_stages
        and context.next_stage in expected_stages[context.response]
        and context.waited_for_user
    )


def grade_checkpoint(
    text: str,
    context: CheckpointContext,
    interaction: InteractionEvidence | None = None,
) -> list[Check]:
    should_present = _checkpoint_should_present(context)
    visible_text = _visible_interaction_text(text, interaction)
    interaction_valid = (
        _checkpoint_interaction_valid(text, interaction)
        if should_present
        else interaction is None
    )
    layout_valid = (
        _checkpoint_layout_valid(text, interaction)
        if should_present
        else not text.strip()
    )
    scope_valid = (
        _checkpoint_scope_valid(context)
        if context.trigger_type in CHECKPOINT_HIGH_VALUE_TRIGGERS
        else not context.decision_scope
    )
    checkpoint_fields_valid = (
        all(
            _nonempty_string(value)
            and value in visible_text
            for value in (
                context.commitment,
                context.decision_sensitive_unknown,
                context.why_now,
            )
        )
        if should_present
        else not any(
            value.strip()
            for value in (
                context.commitment,
                context.decision_sensitive_unknown,
                context.why_now,
            )
        )
    )
    forbidden_analysis = _matches_any(
        visible_text,
        CHECKPOINT_FORBIDDEN_ANALYSIS_PATTERNS,
    )
    forbidden_gate = _matches_any(
        visible_text,
        CHECKPOINT_FORBIDDEN_GATE_PATTERNS,
    )
    authorization_inference = _matches_any(
        visible_text,
        AUTHORIZATION_INFERENCE_PATTERNS,
    )
    no_side_effects = bool(
        not context.capability_calls
        and not context.consent_ids
        and not context.decision_record_created
        and not context.persistence_written
    )
    return [
        _check(
            "上下文检查点只在高价值承诺节点且无跳过条件时出现",
            should_present == (interaction is not None or bool(text.strip())),
            (
                f"trigger={context.trigger_type}；explicit={context.explicit_invocation}；"
                f"active_flow={context.active_flow}；cooldown={context.same_decision_cooling_down}；"
                f"material_change={context.material_change}；should_present={should_present}；"
                f"output_present={interaction is not None or bool(text.strip())}"
            ),
            severe=True,
        ),
        _check(
            "上下文检查点记录同一决定的会话内语义范围",
            scope_valid,
            f"decision_scope={context.decision_scope!r}",
            severe=True,
        ),
        _check(
            "上下文检查点按宿主能力使用固定原生单选或普通编号降级",
            interaction_valid,
            (
                "无检查点时没有交互证据"
                if interaction is None
                else (
                    f"host={interaction.host_control_status}；surface={interaction.surface}；"
                    f"tool_call={interaction.tool_call_observed}；mode={interaction.selection_mode}；"
                    f"option_ids={list(_checkpoint_option_ids(interaction))}；"
                    f"fallback_options={list(_checkpoint_numbered_options(text))}"
                )
            ),
            severe=True,
        ),
        _check(
            "上下文检查点说清承诺、一个决定敏感未知和 why-now",
            checkpoint_fields_valid,
            (
                f"commitment={context.commitment!r}；"
                f"unknown={context.decision_sensitive_unknown!r}；why_now={context.why_now!r}"
            ),
            severe=True,
        ),
        _check(
            "上下文检查点保留自由纠正并把唯一问题放在选项前",
            layout_valid,
            (
                "无检查点时正文为空"
                if interaction is None
                else (
                    f"surface={interaction.surface}；question={interaction.question_text!r}；"
                    f"伪控件={CHECKPOINT_PSEUDO_RE.search(text) is not None}"
                )
            ),
            severe=True,
        ),
        _check(
            "上下文检查点等待明确选择并按进入、继续或模糊回应路由",
            _checkpoint_route_valid(context, should_present),
            (
                f"response={context.response}；next_stage={context.next_stage}；"
                f"waited={context.waited_for_user}；should_present={should_present}"
            ),
            severe=True,
        ),
        _check(
            "上下文检查点确认前不进入正式分析、方法、判断或行动",
            not forbidden_analysis,
            f"命中模式={forbidden_analysis}" if forbidden_analysis else "未命中正式流程内容",
            severe=True,
        ),
        _check(
            "上下文检查点不触发 Gate、能力调用或授权请求",
            not forbidden_gate and no_side_effects,
            (
                f"Gate/能力模式={forbidden_gate}；calls={list(context.capability_calls)}；"
                f"consents={list(context.consent_ids)}"
            ),
            severe=True,
        ),
        _check(
            "上下文检查点选择不推定授权且不创建记录或持久化",
            not authorization_inference
            and not context.decision_record_created
            and not context.persistence_written,
            (
                f"授权推定={authorization_inference}；"
                f"decision_record={context.decision_record_created}；"
                f"persistence={context.persistence_written}"
            ),
            severe=True,
        ),
    ]


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
    answer_shape: str = "compatible-set",
) -> list[Check]:
    if r_mode not in {"align", "method"}:
        raise ValueError(f"不支持的 R 子状态：{r_mode}")
    if answer_shape not in ANSWER_SHAPES:
        raise ValueError(f"不支持的 R 答案形态：{answer_shape}")

    recommended_methods = recommended_methods or []
    expected_labels, unknown_methods = _method_labels(recommended_methods)
    visible_text = _visible_interaction_text(text, interaction)
    labels_present = [label for label in METHOD_LABELS.values() if label in visible_text]
    found_labels = [label for label in expected_labels if label in visible_text]
    recommendation_details = {label: _method_detail(visible_text, label) for label in expected_labels}
    method_option_passed, method_option_evidence = _method_option_contract(interaction)
    recommendation_match_passed, recommendation_match_evidence = _method_recommendations_match(
        interaction,
        recommended_methods,
    )
    duplicated_method_descriptions = _method_descriptions_duplicated_in_body(text, interaction)
    choices = _interaction_choices(text, interaction)
    expected_selection_mode = {
        "compatible-set": "multi",
        "finite-mutually-exclusive": "single",
        "open": "none",
    }[answer_shape]
    judgments = _matches_any(visible_text, JUDGMENT_PATTERNS)
    actions = _matches_any(visible_text, ACTION_PATTERNS)
    external = _matches_any(visible_text, EXTERNAL_PATTERNS)
    duplicates = _duplicate_headings(visible_text)
    if answer_shape == "open":
        interaction_valid = _free_answer_interaction_valid(interaction)
        choices_valid = not choices
        free_input_valid = interaction_valid
        layout_valid = _last_paragraph_is_only_question(text, require_prior_paragraph=True)
    else:
        interaction_valid = bool(
            _native_or_fallback_valid(interaction)
            and interaction
            and interaction.selection_mode == expected_selection_mode
        )
        choices_valid = 2 <= len(choices) <= 4 and not _has_product_other(choices)
        free_input_valid = _free_input_valid(text, interaction)
        layout_valid = (
            _selection_layout_valid(text, interaction, expected_selection_mode)
            and len(QUESTION_MARK_RE.findall(visible_text)) == 1
            and not _options_have_questions(choices)
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
            "阶段 R 的选项数量匹配答案形态",
            choices_valid,
            (
                f"answer_shape={answer_shape}；选择数量={len(choices)}；选择={choices}；"
                f"产品自建 Other={_has_product_other(choices)}"
            ),
            severe=True,
        ),
        _check(
            "阶段 R 提供宿主自由输入或开放回答入口",
            free_input_valid,
            (
                "缺少交互证据"
                if interaction is None
                else (
                    f"answer_shape={answer_shape}；surface={interaction.surface}；"
                    f"host_free_text={interaction.host_free_text_available}；"
                    f"问题正文说明={_has_free_expression(interaction.question_text)}；"
                    f"文本自由入口={_has_free_expression(text)}"
                )
            ),
            severe=True,
        ),
        _check(
            "阶段 R 按语义分段并把正式问题放在最后",
            layout_valid,
            (
                f"answer_shape={answer_shape}；mode={expected_selection_mode}；"
                f"question={interaction.question_text!r}；选项含问号={_options_have_questions(choices)}"
                if interaction is not None
                else f"answer_shape={answer_shape}；缺少交互证据"
            ),
            severe=True,
        ),
        _check(
            "阶段 R 明确等待当前选择或表达",
            bool(
                interaction
                and (
                    (interaction.surface == "native-control" and interaction.tool_call_observed)
                    or interaction.surface == "free-answer"
                )
            )
            or WAIT_RE.search(text) is not None,
            (
                "原生控件调用后等待"
                if interaction and interaction.surface == "native-control" and interaction.tool_call_observed
                else (
                    "开放回答后等待"
                    if interaction and interaction.surface == "free-answer"
                    else ("找到文本等待表达" if WAIT_RE.search(text) else "未找到等待表达")
                )
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
                bool(re.search(r"暂定|目前听起来|我现在听到|可能是|理解", visible_text)) and free_input_valid,
                "找到暂定理解与纠正入口" if re.search(r"暂定|目前听起来|我现在听到|可能是|理解", visible_text) else "未找到暂定理解表达",
            ),
        ])
    else:
        native_method_options = bool(
            interaction
            and interaction.surface == "native-control"
            and (interaction.method_options or recommended_methods)
        )
        details_passed = (
            method_option_passed
            if native_method_options
            else all(recommendation_details.values())
        )
        checks.extend([
            _check(
                "R-method 显示推荐方法的正式名称",
                not unknown_methods and found_labels == expected_labels,
                f"预期：{expected_labels}；找到：{found_labels}；未知方法：{unknown_methods}",
                severe=True,
            ),
            _check(
                "R-method 候选具有稳定 ID、正式名称、当前价值和推荐状态",
                method_option_passed if native_method_options else True,
                (
                    str(method_option_evidence)
                    if native_method_options
                    else "文本降级由相邻方法说明合同覆盖"
                ),
                severe=True,
            ),
            _check(
                "R-method 推荐标记与本轮推荐集合一致且不冒充确认",
                recommendation_match_passed if native_method_options else not unknown_methods,
                str(recommendation_match_evidence),
                severe=True,
            ),
            _check(
                "R-method 使用白话解释每个候选的当前价值",
                details_passed,
                (
                    str(method_option_evidence)
                    if native_method_options
                    else f"方法说明：{recommendation_details}"
                ),
            ),
            _check(
                "R-method 不在正文与原生选项中重复完整说明",
                not duplicated_method_descriptions,
                f"重复说明：{duplicated_method_descriptions}",
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
    if answer_shape not in A_ANSWER_SHAPES:
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
        layout_passed = False
    elif answer_shape == "finite-mutually-exclusive":
        interaction_passed = (
            _native_or_fallback_valid(interaction)
            and interaction.selection_mode == "single"
            and 2 <= len(choices) <= 4
            and not _has_product_other(choices)
            and _free_input_valid(text, interaction)
        )
        layout_passed = (
            _selection_layout_valid(text, interaction, "single")
            and len(marks) == 1
            and not _options_have_questions(choices)
        )
    else:
        interaction_passed = _free_answer_interaction_valid(interaction)
        layout_passed = _last_paragraph_is_only_question(text, require_prior_paragraph=True)

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
                    f"mode={interaction.selection_mode}；options={list(interaction.option_labels)}；"
                    f"host_free_text={interaction.host_free_text_available}"
                )
            ),
            severe=True,
        ),
        _check(
            "阶段 A 按语义分段并把唯一问题放在最后",
            layout_passed,
            (
                f"answer_shape={answer_shape}；question={question_source!r}；"
                f"选项含问号={_options_have_questions(choices)}"
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


@dataclass(frozen=True)
class BLoopComponent:
    key: str
    content: str
    paragraph_index: int
    start: int
    end: int


@dataclass(frozen=True)
class BLoopParse:
    components: tuple[BLoopComponent, ...]
    marker_counts: dict[str, int]
    order: tuple[str, ...]
    separate_paragraphs: bool
    contents_nonempty: bool

    @property
    def complete(self) -> bool:
        return (
            all(self.marker_counts.get(key) == 1 for key in B_LOOP_ORDER)
            and self.order == B_LOOP_ORDER
            and self.separate_paragraphs
            and self.contents_nonempty
        )

    def content_for(self, key: str) -> str:
        return next((component.content for component in self.components if component.key == key), "")

    @property
    def start(self) -> int:
        return min((component.start for component in self.components), default=-1)

    @property
    def end(self) -> int:
        return max((component.end for component in self.components), default=-1)


def _b_main_content(text: str) -> str:
    boundary = B_CONTENT_BOUNDARY_RE.search(text)
    return text[:boundary.start()] if boundary else text


def _b_statuses(text: str, loop_start: int) -> list[str]:
    search_area = text[:loop_start] if loop_start >= 0 else _b_main_content(text)
    states: list[str] = []
    for match in B_STATUS_MARK_RE.finditer(search_area):
        if match.group("zh"):
            states.append(match.group("zh"))
        else:
            states.append(B_STATUS_ENGLISH[match.group("en").casefold()])
    return states


def _b_loop_suffix_match(paragraph: str) -> tuple[str, re.Match[str]] | None:
    matches: list[tuple[str, re.Match[str]]] = []
    for key, suffixes in B_LOOP_SUFFIXES.items():
        suffix_pattern = "|".join(re.escape(suffix) for suffix in suffixes)
        match = re.search(rf"(?:{suffix_pattern})(?=[。.!！]?\s*$)", paragraph, re.IGNORECASE)
        if match:
            matches.append((key, match))
    return matches[0] if len(matches) == 1 else None


def _parse_b_loop(text: str) -> BLoopParse:
    main_content = _b_main_content(text)
    paragraphs = _semantic_paragraphs(main_content)
    marker_counts = {key: 0 for key in B_LOOP_ORDER}
    components: list[BLoopComponent] = []
    cursor = 0

    for paragraph_index, paragraph in enumerate(paragraphs):
        paragraph_start = main_content.find(paragraph, cursor)
        paragraph_end = paragraph_start + len(paragraph)
        cursor = paragraph_end

        matched_keys: list[str] = []
        for key, suffixes in B_LOOP_SUFFIXES.items():
            count = sum(paragraph.casefold().count(suffix.casefold()) for suffix in suffixes)
            marker_counts[key] += count
            if count:
                matched_keys.append(key)

        suffix_match = _b_loop_suffix_match(paragraph)
        if len(matched_keys) != 1 or suffix_match is None:
            continue
        key, match = suffix_match
        content = (paragraph[:match.start()] + paragraph[match.end():]).strip()
        content = re.sub(r"[。.!！]\s*$", "", content).strip()
        components.append(
            BLoopComponent(
                key=key,
                content=content,
                paragraph_index=paragraph_index,
                start=paragraph_start,
                end=paragraph_end,
            )
        )

    component_paragraphs = [component.paragraph_index for component in components]
    return BLoopParse(
        components=tuple(components),
        marker_counts=marker_counts,
        order=tuple(component.key for component in components),
        separate_paragraphs=(
            len(component_paragraphs) == len(set(component_paragraphs)) == len(B_LOOP_ORDER)
        ),
        contents_nonempty=all(component.content for component in components),
    )


def _feedback_options_valid(options: tuple[str, ...]) -> bool:
    normalized = tuple(option.strip() for option in options)
    return normalized in FEEDBACK_OPTION_SETS and not _has_product_other(normalized)


def _numbered_feedback_options(text: str) -> tuple[str, ...]:
    matches = list(NUMBERED_FEEDBACK_RE.finditer(text))
    if [match.group(1) for match in matches] != ["1", "2", "3", "4"]:
        return ()
    return tuple(match.group(2).strip() for match in matches)


def _native_feedback_repeated(text: str) -> bool:
    labels = {label for option_set in FEEDBACK_OPTION_SETS for label in option_set}
    for line in text.splitlines():
        candidate = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)、]\s*)", "", line).strip()
        if candidate in labels:
            return True
    return False


def _b_interaction_valid(text: str, interaction: InteractionEvidence | None) -> bool:
    if interaction is None or interaction.selection_mode != "single":
        return False
    if interaction.host_control_status == "available":
        return (
            interaction.surface == "native-control"
            and interaction.tool_call_observed
            and interaction.supplement_mode in {"native-note", "follow-up-message"}
        )
    if interaction.host_control_status == "unavailable":
        return (
            interaction.surface == "text-fallback"
            and not interaction.tool_call_observed
            and interaction.supplement_mode == "inline-text"
        )
    return (
        interaction.surface == "text-fallback"
        and interaction.tool_call_observed
        and interaction.supplement_mode == "inline-text"
    )


def _b_feedback_layout_valid(text: str, interaction: InteractionEvidence | None) -> bool:
    if interaction is None:
        return False
    if interaction.surface == "native-control":
        hint_valid = (
            NATIVE_NOTE_HINT_RE.search(interaction.question_text) is not None
            if interaction.supplement_mode == "native-note"
            else FOLLOW_UP_HINT_RE.search(interaction.question_text) is not None
        )
        return (
            hint_valid
            and _last_paragraph_is_only_question(interaction.question_text, require_prior_paragraph=True)
            and len(QUESTION_MARK_RE.findall(interaction.question_text)) == 1
            and FEEDBACK_QUESTION_RE.search(interaction.question_text) is not None
            and not _options_have_questions(interaction.option_labels)
            and not _native_feedback_repeated(text)
            and PSEUDO_FEEDBACK_RE.search(text) is None
        )
    if interaction.surface == "text-fallback":
        options = _numbered_feedback_options(text)
        matches = list(NUMBERED_FEEDBACK_RE.finditer(text))
        if not matches:
            return False
        prompt = text[:matches[0].start()]
        tail = text[matches[-1].end():].strip()
        return (
            FEEDBACK_HEADING_RE.search(text) is not None
            and INLINE_SUPPLEMENT_HINT_RE.search(prompt) is not None
            and options in FEEDBACK_OPTION_SETS
            and not tail
            and PSEUDO_FEEDBACK_RE.search(text) is None
            and not QUESTION_MARK_RE.search(text)
        )
    return False


def _independent_action_items(action: str) -> list[str]:
    return re.findall(r"(?m)^\s*(?:[-*+] |\d+[.)]\s+)(.+)$", action)


def _path_value(record: dict[str, object], path: str) -> object:
    current: object = record
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _visible_snapshot_contract(
    text: str,
    decision_record: dict[str, object] | None,
    visible_snapshot: dict[str, object] | None,
) -> tuple[bool, str]:
    required_paths = {
        "contract_version",
        "topic",
        "true_objectives",
        "decision",
        "confirmed_methods",
        "judgment.state",
        "judgment.recommendation",
        "judgment.rationale",
        "judgment.validity_conditions",
        "evidence.confirmed_facts",
        "evidence.inferences",
        "evidence.assumptions",
        "evidence.unknowns",
        "evidence.sources",
        "reversal_signals",
        "main_experiment.core_hypothesis",
        "main_experiment.action",
        "main_experiment.observation",
        "main_experiment.reassessment",
        "main_experiment.user_supplied_boundaries",
        "main_experiment.suggested_boundaries",
        "reassessment_triggers",
        "participation_and_capabilities",
        "persistence",
    }
    record_valid = bool(
        isinstance(decision_record, dict)
        and all(check.passed for check in grade_decision_record(decision_record))
    )
    snapshot_shape_valid = bool(
        isinstance(visible_snapshot, dict)
        and visible_snapshot
        and all(
            isinstance(label, str)
            and bool(label.strip())
            and _exact_keys(item, {"path", "value", "rendered"})
            and _nonempty_string(item.get("path"))
            and _nonempty_string(item.get("rendered"))
            for label, item in visible_snapshot.items()
        )
    )
    snapshot_paths = {
        item.get("path")
        for item in visible_snapshot.values()
        if isinstance(item, dict)
    } if isinstance(visible_snapshot, dict) else set()
    values_match = bool(
        snapshot_shape_valid
        and isinstance(decision_record, dict)
        and all(
            item.get("value") == _path_value(decision_record, item["path"])
            for item in visible_snapshot.values()
            if isinstance(item, dict)
        )
    )
    assumptions_and_unknowns_separate = bool(
        isinstance(visible_snapshot, dict)
        and any(
            item.get("path") == "evidence.assumptions"
            for item in visible_snapshot.values()
            if isinstance(item, dict)
        )
        and any(
            item.get("path") == "evidence.unknowns"
            for item in visible_snapshot.values()
            if isinstance(item, dict)
        )
    )
    snapshot_rendered = bool(
        snapshot_shape_valid
        and re.search(r"(?mi)^#{1,3}\s+(?:决策快照|decision snapshot)\s*$", text)
        and all(
            f"{label}：{item['rendered']}" in text
            or f"{label}: {item['rendered']}" in text
            for label, item in visible_snapshot.items()
            if isinstance(item, dict)
        )
    )
    passed = bool(
        record_valid
        and snapshot_shape_valid
        and snapshot_paths == required_paths
        and values_match
        and assumptions_and_unknowns_separate
        and snapshot_rendered
    )
    missing_paths = sorted(required_paths - snapshot_paths)
    extra_paths = sorted(snapshot_paths - required_paths)
    return passed, (
        f"record_valid={record_valid}；snapshot_shape_valid={snapshot_shape_valid}；"
        f"缺少路径={missing_paths}；额外路径={extra_paths}；"
        f"values_match={values_match}；假设与未知分离={assumptions_and_unknowns_separate}；"
        f"快照已实际呈现={snapshot_rendered}"
    )


def grade_b(
    text: str,
    already_executed: bool,
    user_numbers: list[str] | None = None,
    interaction: InteractionEvidence | None = None,
    decision_record: dict[str, object] | None = None,
    visible_snapshot: dict[str, object] | None = None,
) -> list[Check]:
    visible_text = _visible_interaction_text(text, interaction)
    body_marks = QUESTION_MARK_RE.findall(text)
    visible_marks = QUESTION_MARK_RE.findall(visible_text)
    duplicates = _duplicate_headings(text)
    info_questions = _matches_any(visible_text, INFORMATION_QUESTION_PATTERNS)
    hidden_requests = _matches_any(visible_text, HIDDEN_INFO_REQUEST_PATTERNS)
    expected_states = EXECUTED_STATES if already_executed else UNEXECUTED_STATES
    loop = _parse_b_loop(text)
    states = _b_statuses(text, loop.start)
    action_content = loop.content_for("action")
    observation_content = loop.content_for("observation")
    reassessment_content = loop.content_for("reassessment")
    independent_items = _independent_action_items(action_content)
    multiple_actions = _matches_any(action_content, MULTI_ACTION_PATTERNS)
    legacy_prefixes = B_LOOP_PREFIX_RE.findall(_b_main_content(text))
    authorization_inference = _matches_any(visible_text, AUTHORIZATION_INFERENCE_PATTERNS)
    unattributed_numbers = _unattributed_b_numbers(
        _b_main_content(visible_text),
        user_numbers,
    )
    external_position = min(
        [
            position
            for marker in ("外部验证", "另行明确授权", "external validation", "separate consent")
            if (position := text.casefold().find(marker.casefold())) >= 0
        ],
        default=-1,
    )
    status_positions = [match.start() for match in B_STATUS_MARK_RE.finditer(text)]
    judgment_position = min(status_positions, default=-1)
    experiment_position = loop.start
    external_after_judgment = external_position < 0 or (
        judgment_position >= 0 and experiment_position >= 0 and external_position > loop.end
    )
    observation_signal = re.search(
        r"支持.*继续|反对.*继续|付款|拒绝|改善|恶化|support.*continu|argue.*against|payment|refusal",
        observation_content,
        re.IGNORECASE,
    )
    reassessment_signal = re.search(
        r"改变.*判断|判断.*改变|重新决定|停止|转向|复判|reassess|decide again|stop|change direction",
        reassessment_content,
        re.IGNORECASE,
    )

    interaction_passed = _b_interaction_valid(text, interaction)
    if interaction is None:
        feedback_options: tuple[str, ...] = ()
    elif interaction.surface == "native-control":
        feedback_options = interaction.option_labels
    else:
        feedback_options = _numbered_feedback_options(text)
    feedback_options_passed = _feedback_options_valid(feedback_options)
    feedback_layout_passed = _b_feedback_layout_valid(text, interaction)
    feedback_question_count = (
        len(QUESTION_MARK_RE.findall(interaction.question_text))
        if interaction and interaction.surface == "native-control"
        else 0
    )
    information_boundary_passed = (
        not body_marks
        and not info_questions
        and not hidden_requests
        and (
            feedback_question_count == 1
            if interaction and interaction.surface == "native-control"
            else not visible_marks
        )
    )
    snapshot_check, snapshot_evidence = _visible_snapshot_contract(
        text,
        decision_record,
        visible_snapshot,
    )

    return [
        _check(
            "阶段 B 有结构化交互证据",
            interaction is not None,
            "已提供交互证据" if interaction is not None else "缺少交互证据，不能证明 B 没有开启问题型控件",
            severe=True,
        ),
        _check(
            "阶段 B 按宿主能力使用原生反馈单选或明确文本降级",
            interaction_passed,
            (
                "缺少交互证据"
                if interaction is None
                else (
                    f"host={interaction.host_control_status}；surface={interaction.surface}；"
                    f"tool_call={interaction.tool_call_observed}；mode={interaction.selection_mode}；"
                    f"supplement={interaction.supplement_mode}"
                )
            ),
            severe=True,
        ),
        _check(
            "阶段 B 恰好提供四个稳定反馈方向",
            feedback_options_passed,
            f"反馈方向={list(feedback_options)}；产品自建 Other={_has_product_other(feedback_options)}",
            severe=True,
        ),
        _check(
            "阶段 B 清楚区分原生反馈与文本降级并诚实说明补充通道",
            feedback_layout_passed,
            (
                "缺少交互证据"
                if interaction is None
                else (
                    f"surface={interaction.surface}；supplement={interaction.supplement_mode}；"
                    f"question={interaction.question_text!r}；伪控件={PSEUDO_FEEDBACK_RE.search(text) is not None}"
                )
            ),
            severe=True,
        ),
        _check(
            "阶段 B 只提出一个反馈问题，不追加决策信息问题",
            information_boundary_passed,
            (
                f"正文问号={len(body_marks)}；可见问号={len(visible_marks)}；"
                f"反馈问号={feedback_question_count}；信息问题模式={info_questions}；"
                f"隐藏信息请求={hidden_requests}"
            ),
            severe=True,
        ),
        _check(
            "阶段 B 包含与 canonical DecisionRecord 无损对应的可见决策快照",
            snapshot_check,
            snapshot_evidence,
            severe=True,
        ),
        _check(
            "阶段 B 使用一个与事项阶段匹配的后置判断状态",
            len(states) == 1 and states[0] in expected_states,
            f"在主现实闭环前找到状态：{states}；允许状态={list(expected_states)}",
            severe=True,
        ),
        _check(
            "阶段 B 只有一个现实实验",
            loop.complete and len(independent_items) <= 1 and not multiple_actions,
            (
                f"标记数量={loop.marker_counts}；顺序={list(loop.order)}；"
                f"独立动作项={independent_items}；多行动模式={multiple_actions}"
            ),
            severe=True,
        ),
        _check(
            "阶段 B 的核心假设、本轮动作、观察信号和复判条件以自然句分别成段并后置标记",
            loop.complete and not legacy_prefixes,
            (
                f"标记数量={loop.marker_counts}；顺序={list(loop.order)}；"
                f"分别成段={loop.separate_paragraphs}；内容非空={loop.contents_nonempty}；"
                f"句首旧标签={legacy_prefixes}"
            ),
            severe=True,
        ),
        _check("阶段 B 不把一种授权推定为另一种", not authorization_inference, f"越权推定模式：{authorization_inference}" if authorization_inference else "未发现授权范围推定", severe=True),
        _check(
            "阶段 B 包含支持或反对继续的观察信号",
            observation_signal is not None,
            "观察段包含有区分力的现实信号" if observation_signal else "观察段未找到支持或反对继续的现实信号",
        ),
        _check(
            "阶段 B 包含会触发重新决定的复判条件",
            reassessment_signal is not None,
            "复判段包含重新决定条件" if reassessment_signal else "复判段未找到重新决定条件",
        ),
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


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(
    value: object,
    *,
    min_items: int = 0,
    unique: bool = False,
) -> bool:
    if not isinstance(value, list) or len(value) < min_items:
        return False
    if not all(_nonempty_string(item) for item in value):
        return False
    return not unique or len(value) == len(set(value))


def _required_keys(data: object, required: set[str]) -> bool:
    return isinstance(data, dict) and required <= set(data)


def _exact_keys(data: object, expected: set[str]) -> bool:
    return isinstance(data, dict) and set(data) == expected


def _unique_string_list(value: object, *, min_items: int = 0) -> bool:
    return _string_list(value, min_items=min_items, unique=True)


def _consent_scope_tokens(consent: dict[str, object] | None) -> set[str]:
    if consent is None:
        return set()
    scope = consent.get("scope")
    if not isinstance(scope, dict):
        return set()
    tokens: set[str] = set()
    for key in ("operations", "resources", "tasks", "data_boundary"):
        values = scope.get(key, [])
        if isinstance(values, list):
            tokens.update(value for value in values if _nonempty_string(value))
    return tokens


def _operation_consent_and_scope_valid(
    operation: dict[str, object] | None,
    consent: dict[str, object] | None,
) -> tuple[bool, dict[str, object]]:
    consent_id = consent.get("consent_id") if consent else None
    consent_ids = operation.get("consent_ids") if operation else None
    operation_scope = operation.get("scope") if operation else None
    authorized_tokens = _consent_scope_tokens(consent)
    consent_linked = bool(
        _nonempty_string(consent_id)
        and _unique_string_list(consent_ids, min_items=1)
        and consent_id in consent_ids
    )
    scope_valid = bool(
        _unique_string_list(operation_scope, min_items=1)
        and set(operation_scope) <= authorized_tokens
    )
    return consent_linked and scope_valid, {
        "consent_id": consent_id,
        "consent_ids": consent_ids,
        "operation_scope": operation_scope,
        "authorized_tokens": sorted(authorized_tokens),
    }


def _operation_provider_valid(
    operation: dict[str, object] | None,
    receipt_bundle: dict[str, object] | None,
    record_provider: object,
    capability_names: set[str],
) -> tuple[bool, dict[str, object]]:
    operation_provider = operation.get("provider") if operation else None
    capabilities = receipt_bundle.get("capabilities") if receipt_bundle else None
    matching = []
    if isinstance(capabilities, list):
        matching = [
            capability
            for capability in capabilities
            if isinstance(capability, dict)
            and capability.get("name") in capability_names
            and capability.get("provider") == operation_provider
            and capability.get("availability") == "available"
            and capability.get("readiness") == "ready"
        ]
    valid = bool(
        _nonempty_string(record_provider)
        and record_provider == operation_provider
        and matching
    )
    return valid, {
        "record_provider": record_provider,
        "operation_provider": operation_provider,
        "matching_capabilities": len(matching),
    }


def _operation_privilege_flags_valid(operation: dict[str, object] | None) -> bool:
    return bool(
        operation
        and operation.get("private_data_accessed") is False
        and operation.get("external_action_executed") is False
    )


def _agent_payload_valid(payload: object) -> bool:
    content_fields = AGENT_PAYLOAD_KEYS - {"assigned_question"}
    return bool(
        _exact_keys(payload, AGENT_PAYLOAD_KEYS)
        and _nonempty_string(payload.get("assigned_question"))
        and all(_string_list(payload.get(field)) for field in content_fields)
        and any(payload.get(field) for field in content_fields)
    )


def _participation_synthesis_valid(
    synthesis: object,
    completed_tasks: object,
    failed_tasks: object,
) -> tuple[bool, dict[str, object]]:
    shape_valid = _exact_keys(synthesis, PARTICIPATION_SYNTHESIS_KEYS)
    if not shape_valid:
        return False, {
            "shape_valid": False,
            "expected_keys": sorted(PARTICIPATION_SYNTHESIS_KEYS),
        }

    synthesis_tasks = synthesis.get("completed_tasks")
    adopted = synthesis.get("adopted_material")
    set_aside = synthesis.get("set_aside_material")
    unresolved = synthesis.get("unresolved_material")
    lists_valid = bool(
        _unique_string_list(synthesis_tasks)
        and _string_list(adopted)
        and _string_list(set_aside)
        and _string_list(unresolved)
    )
    completed_tasks_match = bool(
        lists_valid
        and _unique_string_list(completed_tasks)
        and synthesis_tasks == completed_tasks
    )
    material_present = bool(
        lists_valid
        and (adopted or set_aside or unresolved)
    )
    failed_tasks_explicit = bool(
        _unique_string_list(failed_tasks)
        and (
            not failed_tasks
            or (
                _string_list(unresolved, min_items=1)
                and set(failed_tasks) <= set(unresolved)
            )
        )
    )
    effects_valid = all(
        _nonempty_string(synthesis.get(field))
        for field in (
            "conflict_handling",
            "judgment_impact",
            "main_reality_loop_impact",
        )
    )
    return bool(
        lists_valid
        and completed_tasks_match
        and material_present
        and failed_tasks_explicit
        and effects_valid
    ), {
        "shape_valid": shape_valid,
        "completed_tasks": completed_tasks,
        "synthesis_completed_tasks": synthesis_tasks,
        "completed_tasks_match": completed_tasks_match,
        "failed_tasks": failed_tasks,
        "failed_tasks_explicit": failed_tasks_explicit,
        "material_present": material_present,
        "effects_valid": effects_valid,
    }


def _consent_contract(
    consent: dict[str, object] | None,
    expected_type: str,
) -> tuple[bool, dict[str, object]]:
    if expected_type not in CONSENT_TYPES:
        raise ValueError(f"不支持的授权类型：{expected_type}")
    schema_errors = _schema_errors(consent, "consent.schema.json")
    if schema_errors or not isinstance(consent, dict):
        return False, {"schema_errors": schema_errors or ["缺少授权记录"]}
    scope = consent.get("scope")
    scope_valid = bool(
        isinstance(scope, dict)
        and _nonempty_string(scope.get("purpose"))
        and _unique_string_list(scope.get("operations"), min_items=1)
        and _unique_string_list(scope.get("resources"))
        and all(
            field not in scope or _unique_string_list(scope.get(field))
            for field in ("tasks", "data_boundary", "excluded")
        )
    )
    valid = bool(
        _nonempty_string(consent.get("consent_id"))
        and consent.get("consent_type") == expected_type
        and consent.get("status") == "granted"
        and consent.get("requested_by") == "main_agent"
        and consent.get("granted_by") == "user"
        and consent.get("valid_for") in {"this_action", "this_turn", "this_session"}
        and scope_valid
    )
    return valid, {
        "type": consent.get("consent_type"),
        "status": consent.get("status"),
        "valid_for": consent.get("valid_for"),
        "scope_valid": scope_valid,
    }


def _find_operation(
    receipt_bundle: dict[str, object] | None,
    kind: str,
) -> dict[str, object] | None:
    if receipt_bundle is None:
        return None
    operations = receipt_bundle.get("operations")
    if not isinstance(operations, list):
        return None
    matches = [
        operation
        for operation in operations
        if isinstance(operation, dict) and operation.get("kind") == kind
    ]
    return matches[0] if len(matches) == 1 else None


def _capabilities_valid(receipt_bundle: dict[str, object] | None) -> bool:
    if receipt_bundle is None:
        return False
    capabilities = receipt_bundle.get("capabilities")
    if not isinstance(capabilities, list):
        return False
    for capability in capabilities:
        if not _required_keys(capability, {"name", "availability", "readiness", "provider"}):
            return False
        if capability.get("availability") not in CAPABILITY_AVAILABILITY:
            return False
        if capability.get("readiness") not in CAPABILITY_READINESS:
            return False
        if not _nonempty_string(capability.get("name")) or not _nonempty_string(capability.get("provider")):
            return False
    return True


def _evidence_terminal_valid(
    operation: dict[str, object] | None,
    supporting: object,
    opposing: object,
    conflicts: object,
    impact: object,
) -> tuple[bool, dict[str, object]]:
    if operation is None:
        return False, {"reason": "缺少 research operation"}
    status = operation.get("status")
    sources = operation.get("sources")
    fallback = operation.get("fallback")
    source_records_valid = bool(isinstance(sources, list) and sources)
    evidence_lists_valid = _string_list(supporting) and _string_list(opposing)
    has_material = bool(supporting or opposing)
    if status == "completed":
        valid = bool(
            source_records_valid
            and evidence_lists_valid
            and _string_list(conflicts)
            and impact in {"changed", "unchanged", "uncertain"}
            and (impact != "changed" or has_material)
            and fallback == ""
        )
    elif status == "partial":
        valid = bool(
            source_records_valid
            and evidence_lists_valid
            and _unique_string_list(conflicts, min_items=1)
            and impact in {"changed", "unchanged", "uncertain"}
            and (impact != "changed" or has_material)
            and _nonempty_string(fallback)
        )
    elif status in {"failed", "declined", "cancelled", "unavailable"}:
        valid = bool(
            sources == []
            and supporting == []
            and opposing == []
            and _unique_string_list(conflicts, min_items=1)
            and impact == "uncertain"
            and _nonempty_string(fallback)
        )
    else:
        valid = False
    return valid, {
        "status": status,
        "source_count": len(sources) if isinstance(sources, list) else None,
        "supporting": supporting,
        "opposing": opposing,
        "conflicts_and_gaps": conflicts,
        "impact": impact,
        "fallback": fallback,
    }


def grade_evidence_gate(
    record: dict[str, object],
    consent: dict[str, object] | None,
    receipt_bundle: dict[str, object] | None,
) -> list[Check]:
    consent_schema_check, consent_schema_valid = _schema_check(
        "Evidence Gate consent 符合 canonical schema",
        consent,
        "consent.schema.json",
    )
    receipt_schema_check, receipt_schema_valid = _schema_check(
        "Evidence Gate receipt bundle 符合 canonical schema",
        receipt_bundle,
        "receipts.schema.json",
    )
    decision = record.get("decision")
    question = record.get("question")
    scope = record.get("scope")
    stop_conditions = record.get("stop_conditions")
    source_requirements = record.get("source_requirements")
    supporting = record.get("supporting_evidence")
    opposing = record.get("opposing_evidence")
    conflicts = record.get("conflicts_and_gaps")
    evidence_date = record.get("evidence_date")
    impact = record.get("impact_on_judgment")
    unknown_type = record.get("unknown_type")
    decision_sensitive = record.get("decision_sensitive")
    bounded = record.get("bounded")
    value_exceeds_cost = record.get("value_exceeds_cost")
    cost_and_latency_disclosure = record.get("cost_and_latency_disclosure")
    disclosure_timing = record.get("disclosure_timing")
    cost_disclosure_valid = bool(
        _exact_keys(cost_and_latency_disclosure, {"cost", "latency"})
        and _nonempty_string(cost_and_latency_disclosure.get("cost"))
        and _nonempty_string(cost_and_latency_disclosure.get("latency"))
        and disclosure_timing == "before_consent"
    )
    capability = record.get("capability")
    capability_ready = bool(
        isinstance(capability, dict)
        and capability.get("availability") == "available"
        and capability.get("readiness") in {"ready", "requires_approval"}
        and _nonempty_string(capability.get("provider"))
    )
    consent_valid, consent_evidence = _consent_contract(consent, "capability_call")
    operation = _find_operation(receipt_bundle, "research") if receipt_schema_valid else None
    operation_status = operation.get("status") if operation else None
    consent_scope_valid, consent_scope_evidence = _operation_consent_and_scope_valid(
        operation,
        consent if consent_schema_valid else None,
    )
    provider_valid, provider_evidence = _operation_provider_valid(
        operation,
        receipt_bundle if receipt_schema_valid else None,
        capability.get("provider") if isinstance(capability, dict) else None,
        {"search.public_web", "search.private_corpus", "tools.read"},
    )
    operation_valid = bool(
        operation
        and operation_status in TERMINAL_OPERATION_STATUSES
        and _unique_string_list(operation.get("scope"), min_items=1)
        and _unique_string_list(operation.get("consent_ids"), min_items=1)
        and _operation_privilege_flags_valid(operation)
        and consent_scope_valid
        and provider_valid
    )
    operation_matches_record = bool(
        operation
        and operation.get("scope") == scope
        and operation.get("conflicts_and_gaps", []) == conflicts
    )
    capability_called = record.get("capability_called") is True
    route_allowed = bool(
        unknown_type == "external_verifiable_fact"
        and decision_sensitive is True
        and bounded is True
        and value_exceeds_cost is True
        and cost_disclosure_valid
        and capability_ready
        and consent_schema_valid
        and consent_valid
    )
    terminal_valid, terminal_evidence = _evidence_terminal_valid(
        operation,
        supporting,
        opposing,
        conflicts,
        impact,
    )
    return [
        consent_schema_check,
        receipt_schema_check,
        _check(
            "Evidence Gate 只路由决定敏感的外部可验证事实",
            unknown_type == "external_verifiable_fact" and decision_sensitive is True,
            f"unknown_type={unknown_type!r}；decision_sensitive={decision_sensitive!r}",
            severe=True,
        ),
        _check(
            "Evidence Gate 具有有界范围、停止条件和来源要求",
            bool(
                _nonempty_string(decision)
                and _nonempty_string(question)
                and _unique_string_list(scope, min_items=1)
                and _unique_string_list(stop_conditions, min_items=1)
                and _unique_string_list(source_requirements, min_items=1)
                and bounded is True
            ),
            f"decision={decision!r}；scope={scope!r}；stop={stop_conditions!r}；sources={source_requirements!r}",
            severe=True,
        ),
        _check(
            "Evidence Gate 在授权前披露具体成本与延迟",
            cost_disclosure_valid,
            (
                f"cost_and_latency_disclosure={cost_and_latency_disclosure!r}；"
                f"disclosure_timing={disclosure_timing!r}"
            ),
            severe=True,
        ),
        _check(
            "Evidence Gate 能力可用且已取得本次能力授权",
            route_allowed,
            (
                f"capability_ready={capability_ready}；consent={consent_evidence}；"
                f"value_exceeds_cost={value_exceeds_cost!r}；"
                f"cost_disclosure_valid={cost_disclosure_valid}"
            ),
            severe=True,
        ),
        _check(
            "Evidence Gate 真实调用具有授权关联、同一 provider、终态研究回执且不越权",
            capability_called
            and receipt_schema_valid
            and operation_valid
            and operation_matches_record,
            (
                f"capability_called={capability_called}；operation_status={operation_status!r}；"
                f"operation_valid={operation_valid}；operation_matches_record={operation_matches_record}；"
                f"consent_scope={consent_scope_evidence}；provider={provider_evidence}"
            ),
            severe=True,
        ),
        _check(
            "Evidence Gate 终态、材料、冲突、判断影响与降级一致",
            terminal_valid and _nonempty_string(evidence_date),
            f"terminal={terminal_evidence}；evidence_date={evidence_date!r}",
            severe=True,
        ),
        _check(
            "Evidence Gate 记录支持、反对、冲突、日期和判断影响",
            terminal_valid and _nonempty_string(evidence_date),
            f"terminal={terminal_evidence}；evidence_date={evidence_date!r}",
            severe=True,
        ),
        _check(
            "Evidence Gate 失败或拒绝后保留未知并给出降级",
            terminal_valid,
            str(terminal_evidence),
            severe=True,
        ),
        _check(
            "Evidence Gate 回执能力状态使用稳定枚举",
            receipt_schema_valid and _capabilities_valid(receipt_bundle),
            f"capabilities={(receipt_bundle.get('capabilities') if isinstance(receipt_bundle, dict) else None)!r}",
        ),
    ]


def _agent_counts_valid(counts: object) -> tuple[bool, dict[str, object]]:
    if not isinstance(counts, dict):
        return False, {"reason": "缺少 agent_counts"}
    keys = (
        "main",
        "planned_additional",
        "started_additional",
        "completed_additional",
        "failed_additional",
        "actual_total",
    )
    if not all(isinstance(counts.get(key), int) and not isinstance(counts.get(key), bool) for key in keys):
        return False, {"reason": "数量字段必须为整数", "counts": counts}
    main = counts["main"]
    planned = counts["planned_additional"]
    started = counts["started_additional"]
    completed = counts["completed_additional"]
    failed = counts["failed_additional"]
    actual_total = counts["actual_total"]
    passed = bool(
        main == 1
        and min(planned, started, completed, failed, actual_total) >= 0
        and started <= planned
        and completed + failed == started
        and actual_total == 1 + started
    )
    return passed, dict(counts)


def grade_participation_gate(
    record: dict[str, object],
    consent: dict[str, object] | None,
    receipt_bundle: dict[str, object] | None,
) -> list[Check]:
    consent_schema_check, consent_schema_valid = _schema_check(
        "Participation Gate consent 符合 canonical schema",
        consent,
        "consent.schema.json",
    )
    receipt_schema_check, receipt_schema_valid = _schema_check(
        "Participation Gate receipt bundle 符合 canonical schema",
        receipt_bundle,
        "receipts.schema.json",
    )
    tasks = record.get("tasks")
    independent_task_count = record.get("independent_task_count")
    user_total_limit = record.get("user_total_limit")
    product_additional_limit = record.get("product_additional_limit")
    host_additional_limit = record.get("host_additional_limit")
    budget_additional_limit = record.get("budget_additional_limit")
    planned_additional = record.get("planned_additional")
    numeric_inputs = (
        independent_task_count,
        user_total_limit,
        product_additional_limit,
        host_additional_limit,
        budget_additional_limit,
        planned_additional,
    )
    numbers_valid = all(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0
        for value in numeric_inputs
    )
    expected_additional = None
    if numbers_valid:
        expected_additional = min(
            independent_task_count,
            max(0, user_total_limit - 1),
            product_additional_limit,
            host_additional_limit,
            budget_additional_limit,
        )
    formula_valid = numbers_valid and planned_additional == expected_additional
    consent_valid, consent_evidence = _consent_contract(consent, "participation_delegation")
    operation = _find_operation(receipt_bundle, "delegation") if receipt_schema_valid else None
    counts_valid, counts_evidence = _agent_counts_valid(
        operation.get("agent_counts") if operation else None
    )
    count_matches_plan = bool(
        operation
        and isinstance(operation.get("agent_counts"), dict)
        and operation["agent_counts"].get("planned_additional") == planned_additional
    )
    no_recursive = record.get("recursive_delegation_allowed") is False
    task_payloads = record.get("agent_payloads")
    payloads_well_formed = bool(
        isinstance(task_payloads, list)
        and all(_agent_payload_valid(payload) for payload in task_payloads)
    )
    payload_questions = (
        [payload["assigned_question"] for payload in task_payloads]
        if payloads_well_formed
        else []
    )
    data_boundaries = record.get("data_boundaries")
    excluded_data = record.get("excluded_data")
    options = record.get("consent_options")
    no_vote = record.get("aggregation") == "synthesis_not_vote"
    operation_status = operation.get("status") if operation else None
    operation_provider = operation.get("provider") if operation else None
    capabilities = receipt_bundle.get("capabilities") if receipt_bundle else None
    provider_valid = bool(
        _nonempty_string(operation_provider)
        and isinstance(capabilities, list)
        and any(
            isinstance(capability, dict)
            and capability.get("name") in {"agents.subagent", "agents.parallel"}
            and capability.get("provider") == operation_provider
            and capability.get("availability") == "available"
            and capability.get("readiness") == "ready"
            for capability in capabilities
        )
    )
    consent_scope_valid, consent_scope_evidence = _operation_consent_and_scope_valid(
        operation,
        consent,
    )
    receipt_tasks_valid = False
    payloads_match_completed_tasks = False
    completed_tasks = operation.get("completed_tasks") if operation else None
    failed_tasks = operation.get("failed_tasks") if operation else None
    task_evidence: dict[str, object] = {"reason": "缺少 delegation operation"}
    if operation:
        counts = operation.get("agent_counts")
        task_lists_typed = bool(
            _unique_string_list(tasks, min_items=1)
            and _unique_string_list(completed_tasks)
            and _unique_string_list(failed_tasks)
        )
        task_lists_valid = bool(
            task_lists_typed
            and not (set(completed_tasks) & set(failed_tasks))
            and (set(completed_tasks) | set(failed_tasks)) <= set(tasks)
        )
        payloads_match_completed_tasks = bool(
            task_lists_valid
            and payloads_well_formed
            and len(payload_questions) == len(set(payload_questions))
            and set(payload_questions) == set(completed_tasks)
        )
        terminal_counts_match = bool(
            task_lists_valid
            and isinstance(counts, dict)
            and len(completed_tasks) == counts.get("completed_additional")
            and len(failed_tasks) == counts.get("failed_additional")
            and len(completed_tasks) + len(failed_tasks) == counts.get("started_additional")
        )
        started = counts.get("started_additional") if isinstance(counts, dict) else None
        planned = counts.get("planned_additional") if isinstance(counts, dict) else None
        completed_count = counts.get("completed_additional") if isinstance(counts, dict) else None
        failed_count = counts.get("failed_additional") if isinstance(counts, dict) else None
        status_matches = bool(
            operation_status in TERMINAL_OPERATION_STATUSES
            and (
                (
                    operation_status == "completed"
                    and started == planned == planned_additional
                    and completed_count == started
                    and failed_count == 0
                )
                or (
                    operation_status == "partial"
                    and isinstance(started, int)
                    and isinstance(completed_count, int)
                    and completed_count >= 1
                    and (started < planned or bool(failed_count))
                )
                or (
                    operation_status == "failed"
                    and completed_count == 0
                    and (
                        started == 0
                        or (
                            isinstance(started, int)
                            and isinstance(failed_count, int)
                            and failed_count == started
                        )
                    )
                )
                or (
                    operation_status in {"declined", "cancelled", "unavailable"}
                    and started == completed_count == failed_count == 0
                )
            )
        )
        gaps = operation.get("conflicts_and_gaps")
        fallback = operation.get("fallback")
        gap_and_fallback_valid = bool(
            (operation_status == "completed" and _string_list(gaps) and fallback == "")
            or (
                operation_status in {"partial", "failed", "declined", "cancelled", "unavailable"}
                and _unique_string_list(gaps, min_items=1)
                and _nonempty_string(fallback)
            )
        )
        receipt_tasks_valid = bool(
            task_lists_valid
            and terminal_counts_match
            and status_matches
            and gap_and_fallback_valid
        )
        task_evidence = {
            "status": operation_status,
            "task_lists_typed": task_lists_typed,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "payload_questions": payload_questions,
            "payloads_match_completed_tasks": payloads_match_completed_tasks,
            "terminal_counts_match": terminal_counts_match,
            "status_matches": status_matches,
            "conflicts_and_gaps": gaps,
            "fallback": fallback,
        }
    operation_valid = bool(
        operation
        and operation.get("kind") == "delegation"
        and operation_status in TERMINAL_OPERATION_STATUSES
        and _nonempty_string(operation.get("receipt_id"))
        and provider_valid
        and consent_scope_valid
        and receipt_tasks_valid
        and _operation_privilege_flags_valid(operation)
        and consent_schema_valid
        and isinstance(consent, dict)
        and isinstance(consent.get("scope"), dict)
        and _unique_string_list(tasks, min_items=1)
        and _unique_string_list(consent["scope"].get("tasks"))
        and set(tasks) <= set(consent["scope"].get("tasks"))
    )
    synthesis_valid, synthesis_evidence = _participation_synthesis_valid(
        record.get("synthesis"),
        completed_tasks,
        failed_tasks,
    )
    return [
        consent_schema_check,
        receipt_schema_check,
        _check(
            "Participation Gate 只为不重复的独立增量任务升级",
            bool(
                _string_list(tasks, min_items=1, unique=True)
                and isinstance(independent_task_count, int)
                and independent_task_count == len(tasks)
            ),
            f"tasks={tasks!r}；independent_task_count={independent_task_count!r}",
            severe=True,
        ),
        _check(
            "Participation Gate Agent 数量遵守总上限公式",
            formula_valid,
            f"expected_additional={expected_additional!r}；planned_additional={planned_additional!r}；user_total_limit={user_total_limit!r}",
            severe=True,
        ),
        _check(
            "Participation Gate 启用前说明数据边界、成本延迟和失败降级",
            bool(
                _string_list(data_boundaries, min_items=1)
                and _string_list(excluded_data)
                and _nonempty_string(record.get("relative_cost_and_latency"))
                and _nonempty_string(record.get("failure_fallback"))
                and _string_list(options, min_items=3)
            ),
            f"data={data_boundaries!r}；excluded={excluded_data!r}；options={options!r}",
            severe=True,
        ),
        _check(
            "Participation Gate 已取得本次参与委派授权",
            consent_valid,
            str(consent_evidence),
            severe=True,
        ),
        _check(
            "Participation Gate 额外 Agent 不递归委派且只收最小上下文",
            no_recursive and payloads_well_formed,
            f"recursive_allowed={record.get('recursive_delegation_allowed')!r}；payloads_well_formed={payloads_well_formed}",
            severe=True,
        ),
        _check(
            "Participation Gate payload 只对应实际完成且唯一的任务",
            payloads_match_completed_tasks,
            f"payload_questions={payload_questions!r}；tasks={task_evidence}",
            severe=True,
        ),
        _check(
            "Participation Gate 协作回执的授权、provider、终态、任务、数量和降级真实一致",
            counts_valid and count_matches_plan and operation_valid,
            (
                f"counts={counts_evidence}；count_matches_plan={count_matches_plan}；"
                f"consent_scope={consent_scope_evidence}；operation_provider={operation_provider!r}；"
                f"provider_valid={provider_valid}；tasks={task_evidence}"
            ),
            severe=True,
        ),
        _check(
            "Participation Gate 声明 synthesis_not_vote 且结构化综合绑定实际完成任务与判断闭环",
            no_vote and synthesis_valid,
            (
                f"aggregation={record.get('aggregation')!r}；"
                f"synthesis={synthesis_evidence}"
            ),
            severe=True,
        ),
        _check(
            "Participation Gate 回执不把委派授权继承为私有数据或外部行动",
            _operation_privilege_flags_valid(operation),
            f"private_data={operation.get('private_data_accessed') if operation else None!r}；external_action={operation.get('external_action_executed') if operation else None!r}",
            severe=True,
        ),
    ]


def _consent_bundle_by_id(
    consent_bundle: dict[str, object] | None,
) -> tuple[bool, dict[str, dict[str, object]], dict[str, object]]:
    if not _exact_keys(consent_bundle, {"consents"}):
        return False, {}, {"reason": "consent bundle 顶层必须只有 consents"}
    consents = consent_bundle.get("consents")
    if not isinstance(consents, list):
        return False, {}, {"reason": "consents 必须是数组"}
    by_id: dict[str, dict[str, object]] = {}
    valid = True
    for consent in consents:
        if not isinstance(consent, dict):
            valid = False
            continue
        consent_id = consent.get("consent_id")
        expected_type = consent.get("consent_type")
        if (
            not _nonempty_string(consent_id)
            or consent_id in by_id
            or expected_type not in CONSENT_TYPES
        ):
            valid = False
            continue
        contract_valid, _ = _consent_contract(consent, expected_type)
        valid = valid and contract_valid
        by_id[str(consent_id)] = consent
    return valid, by_id, {"count": len(consents), "ids": sorted(by_id)}


def _operations_by_receipt_id(
    receipt_bundle: dict[str, object] | None,
) -> tuple[bool, dict[str, dict[str, object]], dict[str, object]]:
    operations = receipt_bundle.get("operations") if receipt_bundle else None
    if not isinstance(operations, list):
        return False, {}, {"reason": "缺少 operations 数组"}
    by_id: dict[str, dict[str, object]] = {}
    valid = True
    for operation in operations:
        if not isinstance(operation, dict):
            valid = False
            continue
        receipt_id = operation.get("receipt_id")
        if not _nonempty_string(receipt_id) or receipt_id in by_id:
            valid = False
            continue
        by_id[receipt_id] = operation
    return valid, by_id, {"count": len(operations), "ids": sorted(by_id)}


def _ids_unique(items: object) -> tuple[bool, dict[str, dict[str, object]]]:
    if not isinstance(items, list):
        return False, {}
    by_id: dict[str, dict[str, object]] = {}
    for item in items:
        if not isinstance(item, dict):
            return False, {}
        item_id = item.get("id")
        if not _nonempty_string(item_id) or item_id in by_id:
            return False, {}
        by_id[item_id] = item
    return True, by_id


def _refs_exist(value: object, valid_ids: set[str]) -> bool:
    return _unique_string_list(value) and set(value) <= valid_ids


def _source_link_valid(
    source: dict[str, object],
    operations: dict[str, dict[str, object]],
) -> bool:
    if not _exact_keys(source, PROJECT_SOURCE_KEYS):
        return False
    operation = operations.get(source.get("receipt_id"))
    locator = source.get("locator")
    if not operation or operation.get("status") not in {"completed", "partial"} or not _nonempty_string(locator):
        return False
    sources = operation.get("sources")
    return bool(
        isinstance(sources, list)
        and any(isinstance(item, dict) and item.get("locator") == locator for item in sources)
    )


def _project_operation_link_valid(
    *,
    receipt_id: object,
    consent_id: object,
    expected_kind: str,
    consent_type: str,
    consents: dict[str, dict[str, object]],
    operations: dict[str, dict[str, object]],
    receipt_bundle: dict[str, object] | None,
    allowed_statuses: set[str],
) -> bool:
    if not _nonempty_string(receipt_id) or not _nonempty_string(consent_id):
        return False
    consent = consents.get(consent_id)
    operation = operations.get(receipt_id)
    if consent is None or operation is None:
        return False
    consent_valid, _ = _consent_contract(consent, consent_type)
    scope_valid, _ = _operation_consent_and_scope_valid(operation, consent)
    capability_names = {
        "research": {"search.public_web", "search.private_corpus", "tools.read"},
        "delegation": {"agents.subagent", "agents.parallel"},
        "tool_call": {"tools.read", "tools.write"},
    }.get(expected_kind, set())
    capabilities = receipt_bundle.get("capabilities") if receipt_bundle else None
    provider_matches = [
        capability
        for capability in capabilities
        if isinstance(capability, dict)
        and capability.get("name") in capability_names
        and capability.get("provider") == operation.get("provider")
        and capability.get("availability") == "available"
        and capability.get("readiness") == "ready"
    ] if isinstance(capabilities, list) else []
    return bool(
        consent_valid
        and operation.get("kind") == expected_kind
        and operation.get("status") in allowed_statuses
        and scope_valid
        and _operation_privilege_flags_valid(operation)
        and bool(provider_matches)
    )


def _project_evidence_source_backed(
    evidence_item_ids: object,
    evidence_by_id: dict[str, dict[str, object]],
    sources_by_id: dict[str, dict[str, object]],
    operations: dict[str, dict[str, object]],
    *,
    allowed_receipt_ids: set[str] | None = None,
) -> bool:
    if not _unique_string_list(evidence_item_ids, min_items=1):
        return False
    for evidence_id in evidence_item_ids:
        item = evidence_by_id.get(evidence_id)
        source_ids = item.get("source_ids") if isinstance(item, dict) else None
        if not _unique_string_list(source_ids, min_items=1):
            return False
        for source_id in source_ids:
            source = sources_by_id.get(source_id)
            if (
                source is None
                or (
                    allowed_receipt_ids is not None
                    and source.get("receipt_id") not in allowed_receipt_ids
                )
                or not _source_link_valid(source, operations)
            ):
                return False
    return True


def _project_evidence_states(
    evidence_item_ids: object,
    evidence_by_id: dict[str, dict[str, object]],
) -> set[str] | None:
    if not _unique_string_list(evidence_item_ids):
        return None
    items = [evidence_by_id.get(evidence_id) for evidence_id in evidence_item_ids]
    if any(item is None for item in items):
        return None
    states = {item.get("state") for item in items if isinstance(item, dict)}
    if not states <= PROJECT_EVIDENCE_STATES:
        return None
    return states


def _project_layer_evidence_valid(
    layer: object,
    evidence_by_id: dict[str, dict[str, object]],
) -> bool:
    if not isinstance(layer, dict):
        return False
    states = _project_evidence_states(layer.get("evidence_item_ids"), evidence_by_id)
    if states is None:
        return False
    status = layer.get("status")
    if status == "supported":
        return states == {"supports"}
    if status == "unsupported":
        return states == {"opposes"}
    if status == "conflicted":
        return "conflicts" in states or {"supports", "opposes"} <= states
    if status == "unknown":
        return not states or "unknown" in states
    return False


def _project_trial_evidence_valid(
    result: object,
    evidence_item_ids: object,
    evidence_by_id: dict[str, dict[str, object]],
) -> bool:
    states = _project_evidence_states(evidence_item_ids, evidence_by_id)
    if states is None:
        return False
    if result == "solves_core":
        return states == {"supports"}
    if result == "partially_solves":
        return "conflicts" in states or {"supports", "opposes"} <= states
    if result == "does_not_solve":
        return states == {"opposes"}
    if result == "unknown":
        return not states or "unknown" in states
    return False


def _project_adversarial_operation_valid(
    adversarial: dict[str, object],
    *,
    consents: dict[str, dict[str, object]],
    operations: dict[str, dict[str, object]],
    receipt_bundle: dict[str, object] | None,
    expected_status: str,
) -> bool:
    consent_id = adversarial.get("consent_id")
    receipt_id = adversarial.get("receipt_id")
    if not _project_operation_link_valid(
        receipt_id=receipt_id,
        consent_id=consent_id,
        expected_kind="delegation",
        consent_type="participation_delegation",
        consents=consents,
        operations=operations,
        receipt_bundle=receipt_bundle,
        allowed_statuses={expected_status},
    ):
        return False
    consent = consents.get(consent_id)
    operation = operations.get(receipt_id)
    if not isinstance(consent, dict) or not isinstance(operation, dict):
        return False
    scope = consent.get("scope")
    authorized_tasks = scope.get("tasks") if isinstance(scope, dict) else None
    completed_tasks = operation.get("completed_tasks")
    failed_tasks = operation.get("failed_tasks")
    counts = operation.get("agent_counts")
    counts_valid, _ = _agent_counts_valid(counts)
    if not (
        _unique_string_list(authorized_tasks, min_items=1)
        and len(authorized_tasks) == 1
        and operation.get("scope") == authorized_tasks
        and operation.get("consent_ids") == [consent_id]
        and _unique_string_list(completed_tasks)
        and _unique_string_list(failed_tasks)
        and counts_valid
        and isinstance(counts, dict)
        and counts.get("planned_additional") == 1
    ):
        return False
    task = authorized_tasks[0]
    if expected_status == "completed":
        payload = adversarial.get("payload")
        return bool(
            _agent_payload_valid(payload)
            and payload.get("assigned_question") == task
            and completed_tasks == [task]
            and failed_tasks == []
            and counts.get("started_additional") == 1
            and counts.get("completed_additional") == 1
            and counts.get("failed_additional") == 0
            and counts.get("actual_total") == 2
            and operation.get("fallback") == ""
        )
    if expected_status == "failed":
        started = counts.get("started_additional")
        expected_failed_tasks = [task] if started == 1 else []
        return bool(
            started in {0, 1}
            and completed_tasks == []
            and failed_tasks == expected_failed_tasks
            and counts.get("completed_additional") == 0
            and counts.get("failed_additional") == started
            and counts.get("actual_total") == 1 + started
            and _nonempty_string(operation.get("fallback"))
        )
    return False


def _project_ceiling(
    layers: dict[str, object],
    search_passes: object,
    candidates: object,
    alternative_trial: object,
    adversarial_review: object,
    *,
    receipt_backed_trial_evidence: bool,
) -> tuple[int, list[str]]:
    reasons: list[str] = []
    problem_existence = layers.get("problem_existence")
    problem_strength = layers.get("problem_strength")
    if isinstance(problem_existence, dict) and problem_existence.get("status") == "unsupported":
        return 0, ["证据不支持问题存在"]
    if isinstance(problem_strength, dict) and problem_strength.get("status") == "unsupported":
        return 0, ["证据不支持问题强度达到投入门槛"]

    layer_statuses = [
        layer.get("status") if isinstance(layer, dict) else None
        for layer in layers.values()
    ]
    search_complete = bool(
        isinstance(search_passes, list)
        and len(search_passes) == 2
        and all(isinstance(item, dict) and item.get("status") == "completed" for item in search_passes)
    )
    candidate_coverage_complete = bool(
        isinstance(candidates, list)
        and candidates
        and all(
            isinstance(candidate, dict)
            and (
                candidate.get("coverage_status") == "covered"
                or (
                    candidate.get("coverage_status") == "not_applicable"
                    and _nonempty_string(candidate.get("reason"))
                )
                or (candidate.get("material") is False and candidate.get("coverage_status") == "unknown")
            )
            and isinstance(candidate.get("verification_dimensions"), list)
            and bool(candidate.get("verification_dimensions"))
            and all(
                isinstance(dimension, dict)
                and (
                    dimension.get("status") == "verified"
                    or (
                        dimension.get("status") == "not_applicable"
                        and _nonempty_string(dimension.get("reason"))
                    )
                    or (candidate.get("material") is False and dimension.get("status") == "unknown")
                )
                for dimension in candidate.get("verification_dimensions", [])
            )
            for candidate in candidates
        )
    )
    trial_status = alternative_trial.get("status") if isinstance(alternative_trial, dict) else None
    trial_result = alternative_trial.get("result") if isinstance(alternative_trial, dict) else None
    adversarial_required = bool(
        isinstance(adversarial_review, dict) and adversarial_review.get("required") is True
    )
    adversarial_complete = bool(
        isinstance(adversarial_review, dict)
        and (
            adversarial_review.get("required") is False
            or adversarial_review.get("status") == "completed"
        )
    )
    if any(status != "supported" for status in layer_statuses):
        reasons.append("四个价值维度仍有未知、冲突或不支持")
    if not search_complete:
        reasons.append("两遍搜索未完整完成")
    if not candidate_coverage_complete:
        reasons.append("material 候选覆盖或核验不完整")
    if trial_status == "not_performed" or trial_result == "unknown":
        reasons.append("最强替代未试用或结果未知")
    if adversarial_required and not adversarial_complete:
        reasons.append("必要反方未完成")
    if reasons:
        return 1, reasons
    if trial_result in {"solves_core", "partially_solves"}:
        return 2, ["现实替代经同任务试用可用"]
    if (
        trial_status == "receipt_backed"
        and trial_result == "does_not_solve"
        and receipt_backed_trial_evidence
    ):
        return 3, ["receipt-backed 且 source-backed 的试用证据支持进入正式自研比较"]
    if trial_status == "user_reported" and trial_result == "does_not_solve":
        return 1, ["用户报告可保留为输入，但没有 receipt/source chain 时最多有限验证"]
    return 1, ["试用证据不足以升级承诺"]


def grade_project_viability(
    record: dict[str, object],
    consent_bundle: dict[str, object] | None,
    receipt_bundle: dict[str, object] | None,
) -> list[Check]:
    top_level_valid = _exact_keys(record, PROJECT_VIABILITY_KEYS)
    contract_version_valid = record.get("contract_version") == "0.4.1"
    consent_instances = (
        consent_bundle.get("consents")
        if _exact_keys(consent_bundle, {"consents"})
        and isinstance(consent_bundle.get("consents"), list)
        else []
    )
    consent_schema_errors = [
        error
        for index, item in enumerate(consent_instances)
        for error in (
            f"consents.{index}.{message}"
            for message in _schema_errors(item, "consent.schema.json")
        )
    ]
    consent_schema_valid = bool(
        _exact_keys(consent_bundle, {"consents"})
        and isinstance(consent_bundle.get("consents"), list)
        and not consent_schema_errors
    )
    consent_schema_check = _check(
        "PROJECT_VIABILITY consents 分别符合 canonical schema",
        consent_schema_valid,
        "canonical schema 校验通过" if consent_schema_valid else "；".join(consent_schema_errors or ["consent bundle 形状无效"]),
        severe=True,
    )
    receipt_schema_check, receipt_schema_valid = _schema_check(
        "PROJECT_VIABILITY receipt bundle 符合 canonical schema",
        receipt_bundle,
        "receipts.schema.json",
    )
    consent_bundle_valid, consents, consent_evidence = _consent_bundle_by_id(consent_bundle)
    operation_bundle_valid, operations, operation_evidence = _operations_by_receipt_id(
        receipt_bundle if receipt_schema_valid else None
    )
    all_operation_consents_resolve = bool(
        operation_bundle_valid
        and all(
            set(operation.get("consent_ids", [])) <= set(consents)
            for operation in operations.values()
            if isinstance(operation.get("consent_ids"), list)
        )
    )
    receipt_contract_valid = bool(
        receipt_schema_valid
        and receipt_bundle
        and receipt_bundle.get("contract_version") == "0.4.1"
        and _capabilities_valid(receipt_bundle)
        and all_operation_consents_resolve
        and all(
            operation.get("status") in TERMINAL_OPERATION_STATUSES
            and _nonempty_string(operation.get("provider"))
            and _unique_string_list(operation.get("scope"), min_items=1)
            and _unique_string_list(operation.get("consent_ids"), min_items=1)
            and _operation_privilege_flags_valid(operation)
            and (
                operation.get("status") == "completed"
                or _nonempty_string(operation.get("fallback"))
            )
            for operation in operations.values()
        )
    )

    decision_context = record.get("decision_context")
    focal_solution = record.get("focal_solution")
    framing_valid = bool(
        _exact_keys(decision_context, PROJECT_DECISION_CONTEXT_KEYS)
        and _nonempty_string(decision_context.get("decision"))
        and _nonempty_string(decision_context.get("commitment_type"))
        and isinstance(decision_context.get("material_change"), bool)
        and decision_context.get("prior_conclusion_status") in {"none", "current", "pending_reassessment"}
        and (
            decision_context.get("material_change") is False
            or decision_context.get("prior_conclusion_status") == "pending_reassessment"
        )
        and _nonempty_string(record.get("user_outcome"))
        and _exact_keys(focal_solution, PROJECT_FOCAL_SOLUTION_KEYS)
        and _nonempty_string(focal_solution.get("description"))
        and focal_solution.get("status") == "candidate"
    )

    evidence_items = record.get("evidence_items")
    evidence_ids_valid, evidence_by_id = _ids_unique(evidence_items)
    evidence_items_valid = bool(
        evidence_ids_valid
        and all(
            _exact_keys(item, PROJECT_EVIDENCE_ITEM_KEYS)
            and item.get("state") in PROJECT_EVIDENCE_STATES
            and _nonempty_string(item.get("claim"))
            and _unique_string_list(item.get("source_ids"))
            for item in evidence_by_id.values()
        )
    )
    evidence_ids = set(evidence_by_id)

    sources = record.get("sources")
    source_ids_valid, sources_by_id = _ids_unique(sources)
    source_links_valid = bool(
        source_ids_valid
        and bool(sources_by_id)
        and all(_source_link_valid(source, operations) for source in sources_by_id.values())
    )
    source_ids = set(sources_by_id)
    evidence_source_refs_valid = bool(
        evidence_items_valid
        and all(_refs_exist(item.get("source_ids"), source_ids) for item in evidence_by_id.values())
    )

    layers = record.get("validation_layers")
    layers_valid = bool(
        _exact_keys(layers, set(PROJECT_VALIDATION_LAYERS))
        and all(
            _exact_keys(layers.get(name), PROJECT_LAYER_KEYS)
            and layers[name].get("status") in {"supported", "unsupported", "conflicted", "unknown"}
            and _refs_exist(layers[name].get("evidence_item_ids"), evidence_ids)
            and _project_layer_evidence_valid(layers[name], evidence_by_id)
            for name in PROJECT_VALIDATION_LAYERS
        )
    )

    search_passes = record.get("search_passes")
    search_passes_valid = bool(
        isinstance(search_passes, list)
        and len(search_passes) == 2
        and [item.get("type") for item in search_passes if isinstance(item, dict)] == list(PROJECT_SEARCH_PASS_TYPES)
        and all(
            _exact_keys(item, PROJECT_SEARCH_PASS_KEYS)
            and item.get("status") in PROJECT_SEARCH_STATUSES
            and _unique_string_list(item.get("query_boundaries"), min_items=1)
            and _refs_exist(item.get("source_ids"), source_ids)
            and (
                (
                    item.get("status") in {"completed", "partial"}
                    and bool(item.get("source_ids"))
                    and _project_operation_link_valid(
                        receipt_id=item.get("receipt_id"),
                        consent_id=item.get("consent_id"),
                        expected_kind="research",
                        consent_type="capability_call",
                        consents=consents,
                        operations=operations,
                        receipt_bundle=receipt_bundle,
                        allowed_statuses={"completed", "partial"},
                    )
                )
                or (
                    item.get("status") == "not_authorized"
                    and item.get("source_ids") == []
                    and not item.get("receipt_id")
                    and not item.get("consent_id")
                )
                or (
                    item.get("status") in {"not_performed", "unavailable"}
                    and item.get("source_ids") == []
                    and not item.get("receipt_id")
                )
                or (
                    item.get("status") == "failed"
                    and item.get("source_ids") == []
                    and _project_operation_link_valid(
                        receipt_id=item.get("receipt_id"),
                        consent_id=item.get("consent_id"),
                        expected_kind="research",
                        consent_type="capability_call",
                        consents=consents,
                        operations=operations,
                        receipt_bundle=receipt_bundle,
                        allowed_statuses={"failed"},
                    )
                    and _nonempty_string(operations[item.get("receipt_id")].get("fallback"))
                )
            )
            for item in search_passes
        )
    )

    candidates = record.get("candidates")
    candidate_ids_valid, candidates_by_id = _ids_unique(candidates)
    candidate_categories = {
        candidate.get("category") for candidate in candidates_by_id.values()
    }
    categories_complete = candidate_categories == PROJECT_CANDIDATE_CATEGORIES
    candidates_valid = bool(
        candidate_ids_valid
        and categories_complete
        and all(
            _exact_keys(candidate, PROJECT_CANDIDATE_KEYS)
            and _nonempty_string(candidate.get("name"))
            and candidate.get("category") in PROJECT_CANDIDATE_CATEGORIES
            and candidate.get("coverage_status") in PROJECT_COVERAGE_STATUSES
            and isinstance(candidate.get("material"), bool)
            and _refs_exist(candidate.get("source_ids"), source_ids)
            and (
                (
                    candidate.get("coverage_status") == "covered"
                    and bool(candidate.get("source_ids"))
                )
                or (
                    candidate.get("coverage_status") == "not_applicable"
                    and _nonempty_string(candidate.get("reason"))
                    and not candidate.get("source_ids")
                )
                or (
                    candidate.get("coverage_status") == "unknown"
                    and _nonempty_string(candidate.get("reason"))
                    and not candidate.get("source_ids")
                )
            )
            and isinstance(candidate.get("verification_dimensions"), list)
            and bool(candidate.get("verification_dimensions"))
            and all(
                _exact_keys(dimension, PROJECT_VERIFICATION_KEYS)
                and _nonempty_string(dimension.get("dimension"))
                and dimension.get("status") in PROJECT_VERIFICATION_STATUSES
                and _refs_exist(dimension.get("source_ids"), source_ids)
                and (
                    (
                        dimension.get("status") == "verified"
                        and bool(dimension.get("source_ids"))
                    )
                    or (
                        dimension.get("status") == "not_applicable"
                        and _nonempty_string(dimension.get("reason"))
                        and not dimension.get("source_ids")
                    )
                    or (
                        dimension.get("status") == "unknown"
                        and _nonempty_string(dimension.get("reason"))
                        and not dimension.get("source_ids")
                    )
                )
                for dimension in candidate.get("verification_dimensions")
            )
            for candidate in candidates_by_id.values()
        )
    )
    strongest_id = record.get("strongest_alternative_id")
    strongest_valid = bool(
        _nonempty_string(strongest_id)
        and strongest_id in candidates_by_id
        and candidates_by_id[strongest_id].get("category") != "independent_build"
        and candidates_by_id[strongest_id].get("coverage_status") in {"covered", "unknown"}
        and candidates_by_id[strongest_id].get("material") is True
        and (
            candidates_by_id[strongest_id].get("coverage_status") == "covered"
            or _nonempty_string(candidates_by_id[strongest_id].get("reason"))
        )
    )

    trial = record.get("alternative_trial")
    trial_evidence_ids = (
        trial.get("evidence_item_ids") if isinstance(trial, dict) else None
    )
    trial_receipt_ids = trial.get("receipt_ids") if isinstance(trial, dict) else None
    trial_evidence_direction_valid = bool(
        isinstance(trial, dict)
        and _project_trial_evidence_valid(
            trial.get("result"),
            trial_evidence_ids,
            evidence_by_id,
        )
    )
    receipt_backed_trial_evidence = bool(
        _unique_string_list(trial_receipt_ids, min_items=1)
        and _project_evidence_source_backed(
            trial_evidence_ids,
            evidence_by_id,
            sources_by_id,
            operations,
            allowed_receipt_ids=set(trial_receipt_ids),
        )
        and trial_evidence_direction_valid
    )
    trial_valid = bool(
        _exact_keys(trial, PROJECT_TRIAL_KEYS)
        and trial.get("status") in PROJECT_TRIAL_STATUSES
        and trial.get("candidate_id") == strongest_id
        and _unique_string_list(trial.get("real_tasks"), min_items=1)
        and _unique_string_list(trial.get("success_criteria"), min_items=1)
        and trial.get("result") in PROJECT_TRIAL_RESULTS
        and _refs_exist(trial.get("evidence_item_ids"), evidence_ids)
        and trial_evidence_direction_valid
        and _unique_string_list(trial.get("consent_ids"))
        and _unique_string_list(trial.get("receipt_ids"))
        and (
            (
                trial.get("status") == "receipt_backed"
                and bool(trial.get("consent_ids"))
                and bool(trial.get("receipt_ids"))
                and len(trial.get("consent_ids")) == len(trial.get("receipt_ids"))
                and all(
                    _project_operation_link_valid(
                        receipt_id=receipt_id,
                        consent_id=consent_id,
                        expected_kind="tool_call",
                        consent_type="capability_call",
                        consents=consents,
                        operations=operations,
                        receipt_bundle=receipt_bundle,
                        allowed_statuses={"completed"},
                    )
                    and bool(operations[receipt_id].get("sources"))
                    for consent_id, receipt_id in zip(
                        trial.get("consent_ids"), trial.get("receipt_ids")
                    )
                )
                and receipt_backed_trial_evidence
            )
            or (
                trial.get("status") == "user_reported"
                and not trial.get("consent_ids")
                and not trial.get("receipt_ids")
                and all(
                    not evidence_by_id[evidence_id].get("source_ids")
                    for evidence_id in trial.get("evidence_item_ids")
                )
                and trial.get("result") in {
                    "solves_core",
                    "partially_solves",
                    "does_not_solve",
                }
                and _nonempty_string(trial.get("reason"))
            )
            or (
                trial.get("status") == "not_performed"
                and not trial.get("consent_ids")
                and not trial.get("receipt_ids")
                and not trial.get("evidence_item_ids")
                and trial.get("result") == "unknown"
                and _nonempty_string(trial.get("reason"))
            )
        )
    )

    adversarial = record.get("adversarial_review")
    adversarial_valid = bool(
        _exact_keys(adversarial, PROJECT_ADVERSARIAL_KEYS)
        and isinstance(adversarial.get("required"), bool)
        and adversarial.get("status") in PROJECT_ADVERSARIAL_STATUSES
        and _refs_exist(adversarial.get("evidence_item_ids"), evidence_ids)
        and (
            (
                adversarial.get("required") is False
                and adversarial.get("status") == "not_needed"
                and not adversarial.get("consent_id")
                and not adversarial.get("receipt_id")
                and adversarial.get("payload") is None
                and _nonempty_string(adversarial.get("reason"))
            )
            or (
                adversarial.get("required") is True
                and adversarial.get("status") == "completed"
                and _project_adversarial_operation_valid(
                    adversarial,
                    consents=consents,
                    operations=operations,
                    receipt_bundle=receipt_bundle,
                    expected_status="completed",
                )
            )
            or (
                adversarial.get("required") is True
                and adversarial.get("status") == "not_performed"
                and not adversarial.get("consent_id")
                and not adversarial.get("receipt_id")
                and adversarial.get("payload") is None
                and _nonempty_string(adversarial.get("reason"))
            )
            or (
                adversarial.get("required") is True
                and adversarial.get("status") == "failed"
                and adversarial.get("payload") is None
                and _nonempty_string(adversarial.get("reason"))
                and _project_adversarial_operation_valid(
                    adversarial,
                    consents=consents,
                    operations=operations,
                    receipt_bundle=receipt_bundle,
                    expected_status="failed",
                )
            )
        )
    )

    conditions_valid = True
    for key in ("no_go_conditions", "reassessment_triggers"):
        valid_ids, by_id = _ids_unique(record.get(key))
        conditions_valid = bool(
            conditions_valid
            and valid_ids
            and bool(by_id)
            and all(
                _exact_keys(item, PROJECT_CONDITION_KEYS)
                and _nonempty_string(item.get("condition"))
                and _refs_exist(item.get("evidence_item_ids"), evidence_ids)
                for item in by_id.values()
            )
        )

    commitment = record.get("commitment")
    ceiling_rank, ceiling_reasons = _project_ceiling(
        layers if isinstance(layers, dict) else {},
        search_passes,
        candidates,
        trial,
        adversarial,
        receipt_backed_trial_evidence=receipt_backed_trial_evidence,
    )
    direction = commitment.get("direction") if isinstance(commitment, dict) else None
    chosen_rank = commitment.get("chosen_rank") if isinstance(commitment, dict) else None
    commitment_evidence_ids = (
        commitment.get("evidence_item_ids") if isinstance(commitment, dict) else None
    )
    commitment_evidence_refs_valid = _refs_exist(
        commitment_evidence_ids,
        evidence_ids,
    )
    commitment_evidence_source_backed = _project_evidence_source_backed(
        commitment_evidence_ids,
        evidence_by_id,
        sources_by_id,
        operations,
    )
    trial_result = trial.get("result") if isinstance(trial, dict) else None
    commitment_trial_evidence_valid = bool(
        _unique_string_list(commitment_evidence_ids, min_items=1)
        and _unique_string_list(trial_evidence_ids, min_items=1)
        and set(commitment_evidence_ids) == set(trial_evidence_ids)
        and trial_evidence_direction_valid
    )
    commitment_direction_valid = bool(
        (
            chosen_rank == 2
            and trial_result in {"solves_core", "partially_solves"}
        )
        or (
            chosen_rank == 3
            and trial_result == "does_not_solve"
            and receipt_backed_trial_evidence
        )
    )
    source_backing_required = isinstance(chosen_rank, int) and chosen_rank >= 2
    commitment_valid = bool(
        _exact_keys(commitment, PROJECT_COMMITMENT_KEYS)
        and direction in PROJECT_COMMITMENT_DIRECTIONS
        and isinstance(chosen_rank, int)
        and not isinstance(chosen_rank, bool)
        and chosen_rank == PROJECT_COMMITMENT_DIRECTIONS[direction]
        and chosen_rank <= ceiling_rank
        and _nonempty_string(commitment.get("rationale"))
        and commitment_evidence_refs_valid
        and (
            not source_backing_required
            or (
                commitment_evidence_source_backed
                and commitment_trial_evidence_valid
                and commitment_direction_valid
            )
        )
        and _unique_string_list(commitment.get("upgrade_conditions"), min_items=1)
    )

    return [
        consent_schema_check,
        receipt_schema_check,
        _check(
            "PROJECT_VIABILITY sidecar 顶层 exact keys 与 v0.4.1 identity 正确",
            top_level_valid and contract_version_valid,
            f"keys={sorted(record)}；contract_version={record.get('contract_version')!r}",
            severe=True,
        ),
        _check(
            "PROJECT_VIABILITY 将实现形态去锚为候选并处理实质变化复查",
            framing_valid,
            f"decision_context={decision_context!r}；focal_solution={focal_solution!r}",
            severe=True,
        ),
        _check(
            "PROJECT_VIABILITY 四个价值维度与 evidence items 分开且引用有效",
            layers_valid and evidence_items_valid and evidence_source_refs_valid,
            f"layers_valid={layers_valid}；evidence_items_valid={evidence_items_valid}；source_refs={evidence_source_refs_valid}",
            severe=True,
        ),
        _check(
            "PROJECT_VIABILITY 两遍搜索顺序、状态、来源、授权与研究回执一致",
            search_passes_valid and consent_bundle_valid and operation_bundle_valid and receipt_contract_valid,
            f"search_passes_valid={search_passes_valid}；consents={consent_evidence}；operations={operation_evidence}",
            severe=True,
        ),
        _check(
            "PROJECT_VIABILITY source ID 唯一并关联 receipt locator",
            source_links_valid,
            f"source_ids={sorted(source_ids)}；source_links_valid={source_links_valid}",
            severe=True,
        ),
        _check(
            "PROJECT_VIABILITY material 候选类别、核验维度与最强替代引用完整",
            candidates_valid and strongest_valid,
            f"categories={sorted(str(item) for item in candidate_categories)}；strongest={strongest_id!r}",
            severe=True,
        ),
        _check(
            "PROJECT_VIABILITY 最强替代试用状态、任务、标准、结果与授权回执一致",
            trial_valid,
            f"trial={trial!r}",
            severe=True,
        ),
        _check(
            "PROJECT_VIABILITY 必要反方使用七字段 exact payload 并与委派授权回执一致",
            adversarial_valid,
            f"adversarial_review={adversarial!r}",
            severe=True,
        ),
        _check(
            "PROJECT_VIABILITY no-go 与复查触发器存在且引用有效",
            conditions_valid,
            f"conditions_valid={conditions_valid}",
            severe=True,
        ),
        _check(
            "PROJECT_VIABILITY chosen commitment 不超过 computed ceiling",
            commitment_valid,
            (
                f"direction={direction!r}；chosen_rank={chosen_rank!r}；"
                f"ceiling_rank={ceiling_rank}；source_backing_required={source_backing_required}；"
                f"source_backed={commitment_evidence_source_backed}；"
                f"trial_evidence={commitment_trial_evidence_valid}；"
                f"direction_valid={commitment_direction_valid}；"
                f"reasons={ceiling_reasons}"
            ),
            severe=True,
        ),
    ]


def _operation_links_consents(
    operation: dict[str, object] | None,
    consents: tuple[dict[str, object] | None, ...],
) -> tuple[bool, dict[str, object]]:
    consent_ids = operation.get("consent_ids") if operation else None
    expected_ids = [
        consent.get("consent_id") if isinstance(consent, dict) else None
        for consent in consents
    ]
    linked = bool(
        _unique_string_list(consent_ids, min_items=len(consents))
        and len(consent_ids) == len(consents)
        and all(_nonempty_string(consent_id) for consent_id in expected_ids)
        and set(consent_ids) == set(expected_ids)
    )
    scopes_valid = bool(
        operation
        and _unique_string_list(operation.get("scope"), min_items=1)
        and all(
            isinstance(consent, dict)
            and isinstance(consent.get("scope"), dict)
            and set(consent["scope"].get("operations", []))
            <= set(operation.get("scope", []))
            and set(consent["scope"].get("resources", []))
            <= set(operation.get("scope", []))
            and set(consent["scope"].get("tasks", []))
            <= set(operation.get("scope", []))
            for consent in consents
        )
    )
    return linked and scopes_valid, {
        "operation_consent_ids": consent_ids,
        "expected_consent_ids": expected_ids,
        "scopes_valid": scopes_valid,
    }


def _human_target_channel_valid(
    record: dict[str, object],
    participation_consent: dict[str, object] | None,
    external_action_consent: dict[str, object] | None,
    operation: dict[str, object] | None,
) -> tuple[bool, dict[str, object]]:
    participation_scope = (
        participation_consent.get("scope")
        if isinstance(participation_consent, dict)
        else None
    )
    external_scope = (
        external_action_consent.get("scope")
        if isinstance(external_action_consent, dict)
        else None
    )
    participation_resources = (
        participation_scope.get("resources")
        if isinstance(participation_scope, dict)
        else None
    )
    external_resources = (
        external_scope.get("resources")
        if isinstance(external_scope, dict)
        else None
    )
    participation_tasks = (
        participation_scope.get("tasks")
        if isinstance(participation_scope, dict)
        else None
    )
    external_tasks = (
        external_scope.get("tasks")
        if isinstance(external_scope, dict)
        else None
    )
    participation_operations = (
        participation_scope.get("operations")
        if isinstance(participation_scope, dict)
        else None
    )
    external_operations = (
        external_scope.get("operations")
        if isinstance(external_scope, dict)
        else None
    )
    question = record.get("question")
    shape_valid = bool(
        _nonempty_string(question)
        and _unique_string_list(participation_resources, min_items=1)
        and len(participation_resources) == 1
        and _unique_string_list(external_resources, min_items=2)
        and len(external_resources) == 2
        and external_resources[0] == participation_resources[0]
        and external_resources[1] != external_resources[0]
        and participation_tasks == [question]
        and external_tasks == [question]
        and _unique_string_list(participation_operations, min_items=1)
        and len(participation_operations) == 1
        and _unique_string_list(external_operations, min_items=1)
        and len(external_operations) == 1
        and participation_operations[0] != external_operations[0]
    )
    target = participation_resources[0] if shape_valid else None
    channel = external_resources[1] if shape_valid else None
    expected_scope = (
        {
            question,
            target,
            channel,
            participation_operations[0],
            external_operations[0],
        }
        if shape_valid
        else set()
    )
    operation_scope = operation.get("scope") if isinstance(operation, dict) else None
    trace_valid = bool(
        shape_valid
        and _unique_string_list(operation_scope, min_items=len(expected_scope))
        and len(operation_scope) == len(expected_scope)
        and set(operation_scope) == expected_scope
    )
    rendered_valid = bool(
        shape_valid
        and target in record.get("sender_and_collector", "")
        and channel in record.get("sender_and_collector", "")
        and question in record.get("forwardable_draft", "")
    )
    return shape_valid and trace_valid and rendered_valid, {
        "question": question,
        "target": target,
        "channel": channel,
        "operation_scope": operation_scope,
        "trace_valid": trace_valid,
        "rendered_valid": rendered_valid,
    }


def grade_human_review(
    record: dict[str, object],
    participation_consent: dict[str, object] | None = None,
    external_action_consent: dict[str, object] | None = None,
    receipt_bundle: dict[str, object] | None = None,
) -> list[Check]:
    required_text = (
        "why_needed",
        "question",
        "minimal_context",
        "excluded_private_context",
        "decision_impact",
        "sender_and_collector",
        "forwardable_draft",
    )
    draft_only = record.get("external_action_executed") is False
    authorized_send = record.get("external_action_executed") is True
    execution_inputs_absent = (
        participation_consent is None
        and external_action_consent is None
        and receipt_bundle is None
    )
    participation_schema_check, participation_schema_valid = _schema_check(
        "真人 authorized_send 的 participation consent 符合 canonical schema",
        participation_consent,
        "consent.schema.json",
    ) if not draft_only else (
        _check(
            "真人 draft_only 不携带 execution consent 或 receipt",
            execution_inputs_absent,
            f"execution_inputs_absent={execution_inputs_absent}",
            severe=True,
        ),
        execution_inputs_absent,
    )
    external_schema_check, external_schema_valid = _schema_check(
        "真人 authorized_send 的 external-action consent 符合 canonical schema",
        external_action_consent,
        "consent.schema.json",
    ) if not draft_only else (
        _check(
            "真人 draft_only 保持外部行动未执行",
            record.get("external_action_executed") is False,
            f"external_action_executed={record.get('external_action_executed')!r}",
            severe=True,
        ),
        record.get("external_action_executed") is False,
    )
    receipt_schema_check, receipt_schema_valid = _schema_check(
        "真人 authorized_send receipt bundle 符合 canonical schema",
        receipt_bundle,
        "receipts.schema.json",
    ) if not draft_only else (
        _check(
            "真人参与默认只生成材料，不自动发送或联系",
            execution_inputs_absent,
            f"external_action_executed={record.get('external_action_executed')!r}；execution_inputs_absent={execution_inputs_absent}",
            severe=True,
        ),
        execution_inputs_absent,
    )
    operation = (
        _find_operation(receipt_bundle, "human_review")
        if not draft_only and receipt_schema_valid
        else None
    )
    consent_links_valid, consent_link_evidence = _operation_links_consents(
        operation,
        (participation_consent, external_action_consent),
    ) if not draft_only else (execution_inputs_absent, {"draft_only": True})
    provider_valid, provider_evidence = _operation_provider_valid(
        operation,
        receipt_bundle if receipt_schema_valid else None,
        operation.get("provider") if operation else None,
        {"humans.request_review"},
    ) if not draft_only else (execution_inputs_absent, {"draft_only": True})
    participation_valid, participation_evidence = _consent_contract(
        participation_consent,
        "participation_delegation",
    ) if not draft_only else (execution_inputs_absent, {"draft_only": True})
    external_valid, external_evidence = _consent_contract(
        external_action_consent,
        "external_action",
    ) if not draft_only else (execution_inputs_absent, {"draft_only": True})
    target_channel_valid, target_channel_evidence = _human_target_channel_valid(
        record,
        participation_consent,
        external_action_consent,
        operation,
    ) if not draft_only else (execution_inputs_absent, {"draft_only": True})
    authorized_send_valid = bool(
        authorized_send
        and participation_schema_valid
        and external_schema_valid
        and receipt_schema_valid
        and participation_valid
        and external_valid
        and consent_links_valid
        and provider_valid
        and target_channel_valid
        and operation
        and operation.get("status") == "completed"
        and operation.get("external_action_executed") is True
        and operation.get("private_data_accessed") is False
        and operation.get("fallback", "") == ""
    )
    return [
        _check(
            "真人参与请求具有最小可转发合同",
            all(_nonempty_string(record.get(field)) for field in required_text),
            f"fields={{field: bool(record.get(field)) for field in {required_text!r}}}",
            severe=True,
        ),
        participation_schema_check,
        external_schema_check,
        receipt_schema_check,
        _check(
            "真人实际发送同时具有 participation 与 external-action 授权及双引用回执",
            execution_inputs_absent if draft_only else authorized_send_valid,
            (
                f"draft_only={draft_only}；authorized_send={authorized_send}；"
                f"participation={participation_evidence}；external={external_evidence}；"
                f"links={consent_link_evidence}；provider={provider_evidence}；"
                f"target_channel={target_channel_evidence}；"
                f"operation_status={operation.get('status') if operation else None!r}"
            ),
            severe=True,
        ),
    ]


def grade_decision_record(record: dict[str, object]) -> list[Check]:
    schema_check, schema_valid = _schema_check(
        "DecisionRecord 符合 canonical schema",
        record,
        "decision-record.schema.json",
    )
    required = {
        "contract_version",
        "topic",
        "true_objectives",
        "decision",
        "judgment",
        "evidence",
        "reversal_signals",
        "main_experiment",
        "reassessment_triggers",
        "participation_and_capabilities",
        "persistence",
    }
    judgment = record.get("judgment") if schema_valid else None
    evidence = record.get("evidence") if schema_valid else None
    experiment = record.get("main_experiment") if schema_valid else None
    participation = record.get("participation_and_capabilities") if schema_valid else None
    persistence = record.get("persistence") if schema_valid else None
    evidence_valid = bool(
        _required_keys(evidence, {"confirmed_facts", "inferences", "assumptions", "unknowns", "sources"})
        and all(
            _string_list(evidence.get(field))
            for field in ("confirmed_facts", "inferences", "assumptions", "unknowns")
        )
        and isinstance(evidence.get("sources"), list)
        and all(
            _required_keys(source, {"title", "locator", "evidence_date"})
            and all(_nonempty_string(source.get(field)) for field in ("title", "locator", "evidence_date"))
            for source in evidence.get("sources", [])
        )
    )
    judgment_valid = bool(
        _required_keys(judgment, {"state", "recommendation", "rationale", "validity_conditions"})
        and judgment.get("state") in DECISION_STATES
        and _nonempty_string(judgment.get("recommendation"))
        and _string_list(judgment.get("rationale"), min_items=1)
        and _string_list(judgment.get("validity_conditions"))
    )
    experiment_valid = bool(
        _required_keys(experiment, {"core_hypothesis", "action", "observation", "reassessment"})
        and all(
            _nonempty_string(experiment.get(field))
            for field in ("core_hypothesis", "action", "observation", "reassessment")
        )
    )
    participation_required = {
        "main_agents",
        "additional_agents_planned",
        "additional_agents_started",
        "additional_agents_completed",
        "additional_agents_failed",
        "private_data_accessed",
        "external_action_executed",
        "consent_ids",
        "receipt_ids",
    }
    participation_valid = bool(
        _required_keys(participation, participation_required)
        and participation.get("main_agents") == 1
        and all(
            isinstance(participation.get(field), int)
            and not isinstance(participation.get(field), bool)
            and participation.get(field) >= 0
            for field in (
                "additional_agents_planned",
                "additional_agents_started",
                "additional_agents_completed",
                "additional_agents_failed",
            )
        )
        and participation.get("additional_agents_started") <= participation.get("additional_agents_planned")
        and participation.get("additional_agents_completed") + participation.get("additional_agents_failed") == participation.get("additional_agents_started")
        and isinstance(participation.get("private_data_accessed"), bool)
        and isinstance(participation.get("external_action_executed"), bool)
        and _string_list(participation.get("consent_ids"))
        and _string_list(participation.get("receipt_ids"))
    )
    persistence_valid = bool(
        _required_keys(persistence, {"mode", "authorized"})
        and (
            (
                persistence.get("mode") == "conversation_only"
                and persistence.get("authorized") is False
                and "destination" not in persistence
                and "consent_id" not in persistence
            )
            or (
                persistence.get("mode") in {"authorized_file", "authorized_remote"}
                and persistence.get("authorized") is True
                and _nonempty_string(persistence.get("destination"))
                and _nonempty_string(persistence.get("consent_id"))
            )
        )
    )
    return [
        schema_check,
        _check(
            "DecisionRecord 使用 v0.4.1 且包含全部核心字段",
            schema_valid and _required_keys(record, required) and record.get("contract_version") == "0.4.1",
            f"缺少字段={sorted(required - set(record))}；version={record.get('contract_version')!r}",
            severe=True,
        ),
        _check(
            "DecisionRecord 记录议题、真实目的和本轮决定",
            bool(
                _nonempty_string(record.get("topic"))
                and _string_list(record.get("true_objectives"), min_items=1)
                and _nonempty_string(record.get("decision"))
            ),
            f"topic={record.get('topic')!r}；objectives={record.get('true_objectives')!r}；decision={record.get('decision')!r}",
            severe=True,
        ),
        _check("DecisionRecord 判断结构完整", judgment_valid, f"judgment={judgment!r}", severe=True),
        _check("DecisionRecord 区分事实、推断、假设、未知与来源", evidence_valid, f"evidence={evidence!r}", severe=True),
        _check(
            "DecisionRecord 包含反转信号和复判触发",
            _string_list(record.get("reversal_signals"), min_items=1)
            and _string_list(record.get("reassessment_triggers"), min_items=1),
            f"reversal={record.get('reversal_signals')!r}；triggers={record.get('reassessment_triggers')!r}",
            severe=True,
        ),
        _check("DecisionRecord 主实验围绕一个核心假设", experiment_valid, f"experiment={experiment!r}", severe=True),
        _check("DecisionRecord 参与与能力记录数量一致", participation_valid, f"participation={participation!r}", severe=True),
        _check("DecisionRecord 默认仅在对话中，持久化需明确授权", persistence_valid, f"persistence={persistence!r}", severe=True),
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
    answer_shape: str | None = None,
    checkpoint_context: CheckpointContext | None = None,
    decision_record: dict[str, object] | None = None,
    visible_snapshot: dict[str, object] | None = None,
) -> list[Check]:
    resolved_answer_shape = answer_shape or (
        "compatible-set" if stage == "R" else "open"
    )
    if stage == "CHECKPOINT":
        if checkpoint_context is None:
            raise ValueError("CHECKPOINT 阶段必须提供 checkpoint context")
        return grade_checkpoint(text, checkpoint_context, interaction)
    if stage == "R":
        return grade_r(
            text,
            recommended_methods,
            r_mode=r_mode,
            interaction=interaction,
            answer_shape=resolved_answer_shape,
        )
    if stage == "A":
        return grade_a(
            text,
            cancelled_methods,
            confirmed_methods,
            user_numbers,
            interaction=interaction,
            answer_shape=resolved_answer_shape,
        )
    if stage == "B":
        return grade_b(
            text,
            already_executed,
            user_numbers,
            interaction=interaction,
            decision_record=decision_record,
            visible_snapshot=visible_snapshot,
        )
    raise ValueError(f"不支持的阶段：{stage}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        required=True,
        choices=("CHECKPOINT", "R", "A", "B", "EVIDENCE", "PARTICIPATION", "PROJECT_VIABILITY", "HUMAN", "DECISION_RECORD"),
    )
    parser.add_argument("--input", required=True, type=Path, help="待评分的 Markdown、文本或 JSON 文件")
    parser.add_argument("--already-executed", action="store_true")
    parser.add_argument("--r-mode", choices=("align", "method"), default="method")
    parser.add_argument(
        "--answer-shape",
        choices=tuple(sorted(ANSWER_SHAPES)),
        default=None,
        help="答案形态；未提供时 R 默认 compatible-set，A 默认 open",
    )
    parser.add_argument("--interaction-json", type=Path, help="CHECKPOINT/R/A/B 的本轮结构化交互证据 JSON")
    parser.add_argument("--context-json", type=Path, help="CHECKPOINT 的结构化会话上下文 JSON")
    parser.add_argument("--decision-record-json", type=Path, help="B 的 canonical DecisionRecord JSON")
    parser.add_argument("--visible-snapshot-json", type=Path, help="B 的用户可见快照投影 JSON")
    parser.add_argument("--consent-json", type=Path, help="Evidence / Participation 的授权记录、HUMAN consent bundle 或 PROJECT_VIABILITY consent bundle JSON")
    parser.add_argument("--receipt-json", type=Path, help="Evidence / Participation / HUMAN / PROJECT_VIABILITY 的能力回执 JSON")
    parser.add_argument("--cancelled-method", action="append", default=[])
    parser.add_argument("--confirmed-method", action="append", default=[])
    parser.add_argument("--recommended-method", action="append", default=[])
    parser.add_argument("--user-number", action="append", default=[], help="用户已提供的数字短语，可重复")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.stage in {"CHECKPOINT", "R", "A", "B"}:
        if args.stage == "CHECKPOINT":
            if args.context_json is None:
                parser.error("CHECKPOINT 阶段必须提供 --context-json")
            context = parse_checkpoint_context(args.context_json)
            should_present = _checkpoint_should_present(context)
            if should_present and args.interaction_json is None:
                parser.error("需要呈现 CHECKPOINT 时必须提供 --interaction-json")
            interaction = (
                parse_interaction_evidence(
                    args.interaction_json,
                    option_contract="checkpoint",
                )
                if args.interaction_json is not None
                else None
            )
            text = args.input.read_text(encoding="utf-8")
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
                checkpoint_context=context,
            )
        else:
            if args.interaction_json is None:
                parser.error("R/A/B 阶段必须提供 --interaction-json")
            if args.stage == "B" and (
                args.decision_record_json is None
                or args.visible_snapshot_json is None
            ):
                parser.error(
                    "B 阶段必须同时提供 --decision-record-json 和 "
                    "--visible-snapshot-json"
                )
            text = args.input.read_text(encoding="utf-8")
            interaction = parse_interaction_evidence(args.interaction_json)
            decision_record = (
                parse_json_object(args.decision_record_json, "B DecisionRecord")
                if args.stage == "B"
                else None
            )
            visible_snapshot = (
                parse_json_object(args.visible_snapshot_json, "B visible snapshot")
                if args.stage == "B"
                else None
            )
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
                decision_record=decision_record,
                visible_snapshot=visible_snapshot,
            )
    else:
        record = parse_json_object(args.input, args.stage)
        if args.stage in {"EVIDENCE", "PARTICIPATION", "PROJECT_VIABILITY"}:
            if args.consent_json is None or args.receipt_json is None:
                parser.error(f"{args.stage} 必须同时提供 --consent-json 和 --receipt-json")
            consent = parse_json_object(args.consent_json, "consent")
            receipt = parse_json_object(args.receipt_json, "receipt")
            if args.stage == "EVIDENCE":
                checks = grade_evidence_gate(record, consent, receipt)
            elif args.stage == "PARTICIPATION":
                checks = grade_participation_gate(record, consent, receipt)
            else:
                checks = grade_project_viability(record, consent, receipt)
        elif args.stage == "HUMAN":
            if (args.consent_json is None) != (args.receipt_json is None):
                parser.error("HUMAN authorized_send 必须同时提供 --consent-json 和 --receipt-json")
            if args.consent_json is None:
                checks = grade_human_review(record)
            else:
                consent_bundle = parse_json_object(args.consent_json, "HUMAN consent bundle")
                receipt = parse_json_object(args.receipt_json, "receipt")
                consents = consent_bundle.get("consents")
                if not _exact_keys(consent_bundle, {"consents"}) or not isinstance(consents, list):
                    parser.error("HUMAN --consent-json 必须是仅含 consents 数组的对象")
                participation_consents = [
                    consent
                    for consent in consents
                    if isinstance(consent, dict)
                    and consent.get("consent_type") == "participation_delegation"
                ]
                external_consents = [
                    consent
                    for consent in consents
                    if isinstance(consent, dict)
                    and consent.get("consent_type") == "external_action"
                ]
                if len(consents) != 2 or len(participation_consents) != 1 or len(external_consents) != 1:
                    parser.error("HUMAN authorized_send 必须提供且仅提供一份 participation 与一份 external-action consent")
                checks = grade_human_review(
                    record,
                    participation_consents[0],
                    external_consents[0],
                    receipt,
                )
        else:
            checks = grade_decision_record(record)
    passed = sum(check.passed for check in checks)
    result = {
        "contract_version": "0.4.1",
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
