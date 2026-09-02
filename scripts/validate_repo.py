#!/usr/bin/env python3
"""执行“想清楚”仓库的确定性发布前校验。"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml
from PIL import Image
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError
from referencing import Registry, Resource

from build_distribution import load_manifest, source_files
from render_assets import check_generated_assets, decoded_image

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "think-it-through"
SKILL_MD = SKILL_DIR / "SKILL.md"

TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".svg", ".txt"}
IGNORED_SCAN_PARTS = {".git", ".claude", "dist", "review", "think-it-through-workspace", "__pycache__"}
CURRENT_CONTRACT_VERSION = "0.4.1"
LATEST_PUBLISHED_VERSION = "0.4.0"
PREVIOUS_PUBLISHED_VERSION = "0.3.0"
CURRENT_ARCHITECTURE_VERSION = "0.4.0"
POSITIONING_ZH = "AI 能把事情做得很快，但什么值得做，仍由你决定。"
POSITIONING_EN = "AI can get things done fast, but what's worth doing is still yours to decide."
VALUE_STATEMENT_ZH = "开始或继续投入前，想清楚再决定。"
VALUE_STATEMENT_EN = "Before you start or commit more, think it through—then decide."
LEGACY_BEHAVIOR_PROFILE = "legacy-v0.1"
EXPECTED_FIXTURE_STAGES = {"pre-entry", "R", "R-align", "A", "B", "Gate-routing", "direct", "emergency", "active-flow", "resume-current-task"}
INTERACTIVE_FIXTURE_STAGES = {"pre-entry", "R", "A", "B"}
SPECIALIZED_FIXTURE_FILES = {
    "14-inline-method-recommendation.json",
    "15-evidence-gate.json",
    "16-participation-and-human.json",
    "17-portable-adapters-and-decision-record.json",
    "18-main-evidence-loop.json",
    "19-contextual-checkpoint.json",
    "20-project-viability-falsification.json",
}
SCHEMA_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
CORE_INTENT_KINDS = {
    "request_contextual_checkpoint",
    "request_free_text",
    "request_selection",
    "present_method_recommendation",
    "request_method_selection",
    "present_decisive_question",
    "request_research_consent",
    "request_agent_consent",
    "request_private_data_consent",
    "request_external_action_consent",
    "delegate_analysis",
    "request_human_review",
    "present_judgment",
    "present_decision_snapshot",
    "persist_decision_snapshot",
    "request_feedback",
}
CORE_STAGES = {
    "pre-entry",
    "R-align",
    "R-method",
    "A",
    "evidence-gate",
    "participation-gate",
    "B",
    "feedback",
    "complete",
}
CONSENT_TYPES = {
    "capability_call",
    "participation_delegation",
    "private_data_access",
    "external_action",
}
CAPABILITY_NAMES = {
    "interaction.free_text",
    "interaction.select_one",
    "interaction.select_many",
    "search.public_web",
    "search.private_corpus",
    "tools.read",
    "tools.write",
    "agents.subagent",
    "agents.parallel",
    "humans.request_review",
    "persistence.session",
    "persistence.case",
    "permissions.tool_call",
    "permissions.private_data",
    "permissions.external_action",
    "fallback.text",
}
CAPABILITY_AVAILABILITY = {"available", "unavailable", "unknown"}
CAPABILITY_READINESS = {"ready", "requires_approval", "requires_auth", "failed"}
OPERATION_KINDS = {"research", "delegation", "human_review", "persistence", "external_action", "tool_call"}
OPERATION_STATUSES = {"planned", "started", "completed", "partial", "failed", "declined", "cancelled", "unavailable"}
DECISION_STATES = {"hold", "small_test", "proceed_conditionally", "proceed", "continue", "adjust", "pause", "stop"}
PERSISTENCE_MODES = {"conversation_only", "authorized_file", "authorized_remote"}
EXPECTED_HOST_CONTROL_STATUSES = {"available", "unavailable", "failed", "rejected"}
EXPECTED_INTERACTION_SURFACES = {
    "R": {"native-control", "text-fallback", "free-answer"},
    "A": {"native-control", "text-fallback", "free-answer"},
    "B": {"native-control", "text-fallback"},
}
EXPECTED_SELECTION_MODES = {"multi", "single", "none"}
EXPECTED_SUPPLEMENT_MODES = {"none", "native-note", "follow-up-message", "inline-text"}
FEEDBACK_OPTIONS = (
    "方向符合我",
    "调整下一步",
    "不同意这个判断",
    "暂时先放一放",
)
EXPECTED_ANSWER_SHAPES = {
    "compatible-set": ("multi", {"native-control", "text-fallback"}),
    "finite-mutually-exclusive": ("single", {"native-control", "text-fallback"}),
    "open": ("none", {"free-answer"}),
}
DESCRIPTION_SHA256 = "f89f3d1fca11641e925a6f2e27b487ddd182789a0bea4f7ae3a3d197e4c6f3d3"
METHOD_ROUTING_COVERAGE = {"applicable", "not-applicable", "overlap"}
MIN_TRIGGER_EXAMPLES_PER_LABEL = 8
REQUIRED_METHOD_FIELDS = {
    "id",
    "name",
    "purpose",
    "user_explanation",
    "use_when",
    "do_not_use_when",
    "inputs",
    "outputs",
    "relationships",
    "provenance",
    "test_status",
}
FROZEN_BEHAVIOR_SHA256 = {
    "README.md": "5a234689d67e62fcd1f27349591b023b1be473035054f535cd79f316a6416080",
    "benchmark.json": "99228a05520c6592527747a3d3ed2cb6eb8946781f077e0626dc163faf2a6288",
    "benchmark.md": "a7ad0488170f5e02f352d13d92e9c8230acf22eaf646fae9d9790f76521eacfe",
    "eval-1-saas-misalignment/eval_metadata.json": "c4ba8646cec49f8c16646dfe99a5b8312e6b78929cb7a4baa606ed88a4520acc",
    "eval-1-saas-misalignment/with_skill/grading.json": "48f53e4b5b41ea813abb6cd58091edb7e534ba0ad66166b7d4c7e022598635c9",
    "eval-1-saas-misalignment/with_skill/semantic-rubric.json": "fe4b2b90546c89d94cc7e05ae62fa96f998966de79b80db311d8d3566f093831",
    "eval-1-saas-misalignment/with_skill/transcript.md": "4531b893b5473dd33560b68e9085e0e1ef77d1ed54dc773f5fee5cb647b3e538",
    "eval-1-saas-misalignment/without_skill/grading.json": "3bed620ce46d182ff5e52ee8ad6e67299d53b8355a6bbad2be0229cce386ef7b",
    "eval-1-saas-misalignment/without_skill/semantic-rubric.json": "484af20bd7125e0c5dbf9171760660f8bf2018fa344172e8dae98924b35d1616",
    "eval-1-saas-misalignment/without_skill/transcript.md": "158833f20f8a753cd5f951c4231ebd97a233bed7b8458d87e0a95ea6cf7dbf19",
    "eval-2-sunk-cost/eval_metadata.json": "42fbf89637732525d13bb3762c42e23ac5639ed3c9bb38c82009c5baa2948ead",
    "eval-2-sunk-cost/with_skill/grading.json": "2a1acbce4a95fdc38ae0b92ab54a15c5bf1da0c61abab1e9df25c61033a1c0fa",
    "eval-2-sunk-cost/with_skill/semantic-rubric.json": "a1274c00f2eedbc086531456473ce2f90ec114855998ce8920063cdba19a3078",
    "eval-2-sunk-cost/with_skill/transcript.md": "652522301b251065c4d85fec8bfbc92d531d39e5cf6a86c91c896e5e47cc832c",
    "eval-2-sunk-cost/without_skill/grading.json": "0670cef1d6a16943746cc02b7f18a15a7caf7256026d3ef7d1a00fe111ebe623",
    "eval-2-sunk-cost/without_skill/semantic-rubric.json": "56df7767430d19fea03fc367f7ab4083f75db4ee220524365b08a5ff42f1f972",
    "eval-2-sunk-cost/without_skill/transcript.md": "b7709dbba5c704792f5b76bcb2253c748459cd0c2476df207834de62575e500b",
    "eval-3-partnership-safety/eval_metadata.json": "80f493746e4dcec186b5c8030cb6d0239cf2b6717104348e7a801e6a42767241",
    "eval-3-partnership-safety/with_skill/grading.json": "a8bef91006a2387a8cf94626852dc32950b10dc90541b4b3604dd72fc4168777",
    "eval-3-partnership-safety/with_skill/semantic-rubric.json": "1b7f28b539175a223d1b0567eb41959e2031a4b2b28f483718a653decabdc099",
    "eval-3-partnership-safety/with_skill/transcript.md": "fc5b3a813051b37132b8fda368e23bc2b9e1f0a4208a2af5aa5392888dd824c1",
    "eval-3-partnership-safety/without_skill/grading.json": "47eac1161fa2427d358860444e4f7f0a9076d4aaacc1e11ddbf945b74a145f9d",
    "eval-3-partnership-safety/without_skill/semantic-rubric.json": "f59dcb729e9b8e22d0f1e466e1204f5dd8b0020ea6d90eeb09b513fe9af69672",
    "eval-3-partnership-safety/without_skill/transcript.md": "b072d82c25b0737cfb56358ef6e0708e1babbcdb707024f535cc30fb20da846e",
    "semantic-rubric.json": "501ecbf0753b036bb4291e21322b58b126521026773c3aacf1862d3336ba7566",
}


class Validation:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.checks = 0

    def require(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.errors.append(message)


def parse_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError(f"{path} 缺少合法 YAML frontmatter")
    metadata = yaml.safe_load(match.group(1))
    if not isinstance(metadata, dict):
        raise ValueError(f"{path} frontmatter 不是对象")
    return metadata, match.group(2)


def all_repo_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in IGNORED_SCAN_PARTS for part in relative.parts):
            continue
        files.append(path)
    return files


def validate_skill(validation: Validation) -> None:
    validation.require(SKILL_MD.exists(), "缺少 skills/think-it-through/SKILL.md")
    if not SKILL_MD.exists():
        return

    try:
        metadata, body = parse_frontmatter(SKILL_MD)
    except (ValueError, yaml.YAMLError) as error:
        validation.require(False, str(error))
        return

    validation.require(metadata.get("name") == SKILL_DIR.name, "Skill name 必须与父目录 think-it-through 一致")
    validation.require(isinstance(metadata.get("license"), str), "Skill license 必须是字符串")
    compatibility = metadata.get("compatibility")
    validation.require(isinstance(compatibility, str), "Skill compatibility 必须是字符串")
    if isinstance(compatibility, str):
        validation.require(1 <= len(compatibility.strip()) <= 500, "Skill compatibility 长度必须为 1～500")
        validation.require("Portable text contract" in compatibility, "Skill compatibility 必须说明纯文本合同")
        validation.require("per-session" in compatibility, "Skill compatibility 必须说明逐会话能力边界")
    skill_metadata = metadata.get("metadata")
    validation.require(isinstance(skill_metadata, dict), "Skill metadata 必须是对象")
    if isinstance(skill_metadata, dict):
        validation.require(
            str(skill_metadata.get("version")) == CURRENT_CONTRACT_VERSION,
            f"Skill 版本必须为 {CURRENT_CONTRACT_VERSION}",
        )
        validation.require(
            all(isinstance(key, str) and isinstance(value, str) for key, value in skill_metadata.items()),
            "Skill metadata 的 key 与 value 必须都是字符串",
        )
    description = metadata.get("description")
    validation.require(isinstance(description, str), "description 必须是字符串")
    if isinstance(description, str):
        normalized_description = description.strip()
        validation.require(1 <= len(normalized_description) <= 1024, f"description 长度必须为 1～1024，当前为 {len(normalized_description)}")
        validation.require(
            hashlib.sha256(normalized_description.encode("utf-8")).hexdigest() == DESCRIPTION_SHA256,
            "v0.1 description 已在 holdout 前冻结；如需修改，必须先建立新的评测版本",
        )
        for phrase in ("decision support", "decision framing", "trade-off", "continue, adjust, pause, or stop"):
            validation.require(phrase.lower() in description.lower(), f"description 缺少发现性语义：{phrase}")
    validation.require(len(SKILL_MD.read_text(encoding="utf-8").splitlines()) < 500, "SKILL.md 必须少于 500 行")
    validation.require("阶段 R" in body and "阶段 A" in body and "阶段 B" in body, "SKILL.md 必须包含 R/A/B 核心状态合同")
    for phrase in (
        "R-align",
        "R-method",
        "Gate-routing",
        "Evidence Gate",
        "Participation Gate",
        "推荐不等于确认",
        "稳定 ID",
        "当前议题中的独特价值",
        "同一选项内展示",
        "若答案可并存",
        "使用原生多选",
        "原生单选",
        "答案开放",
        "不调用选择工具",
        "宿主自动提供的 `Other` 只是自由输入",
        "加入 X",
        "自然回显",
        "一个答案槽",
        "不得自行植入",
        "用户已回答 A，正在判断是否需要证据或参与升级",
        "A 回答后的 Gate 路由",
        "可用额外上限 = max(0, 用户总参与上限 - 1)",
        "不得递归委派",
        "不按多数票",
        "四类授权互不继承",
        "available / unavailable / unknown",
        "ready / requires_approval / requires_auth / failed",
        "主现实证据闭环",
        "决策快照",
        "默认仅在对话中呈现",
        "一意一段",
        "不按固定字符数硬折行",
        "方向符合我",
        "调整下一步",
        "不同意这个判断",
        "暂时先放一放",
        "follow-up-message",
        "inline-text",
        "冲突时以文字为准",
        "反馈不执行实验，也不授权能力、委派、私有数据、持久化或外部行动",
        "不构成原生兼容认证",
        "安装器 target 或文件已复制都不构成原生兼容认证",
        "实际执行只由 trace 与 receipt 建立",
        "不新增、删除、简化、缩小、暂停或停止等减法路径",
        "只有至少一个剩余未知仍预计改变正式判断状态、material 路径排序、承诺上限，或决定主现实证据闭环当前能否执行及其结果能否区分会导致不同判断的路径",
        "模型自评、方法输出或 Agent 一致性不是外部证据",
        "采用、搁置与未决材料为何共同导出当前判断",
    ):
        validation.require(
            phrase in body,
            f"SKILL.md 缺少 v{CURRENT_CONTRACT_VERSION} 合同：{phrase}",
        )
    for forbidden in (
        "本轮确认：基础分析",
        "本轮使用：基础分析",
        "可选择：按推荐继续 / 调整方法 / 只做基础分析 / 补充背景",
    ):
        validation.require(forbidden not in body, f"SKILL.md 仍包含旧版固定合同：{forbidden}")

    runtime_invariants = {
        "references/core-analysis.md": (
            "### 分析充分性与停止",
            "### 真正综合",
            "模型自信、自我批判、自我评分、方法输出和 Agent 一致性",
            "不建立平行的“减法方案”类型",
        ),
        "references/project-viability.md": (
            "不得新增 `subtractive_solution`",
            "模型自信、自我评分、方法输出、未核验 Agent 结论或 Agent 一致性",
            "跨方法、搜索和参与的全局停止",
        ),
        "policies/evidence-routing.md": (
            "不新增 `subtractive_solution`",
            "回执只证明某项操作、状态、范围和返回材料确实发生",
            "停止后如实保留来源空白、冲突和未完成项",
        ),
        "policies/participation-routing.md": (
            "标明采用的材料、因重复/来源/假设/失败而搁置的材料，以及仍未决的冲突和缺口",
            "不得把每个 Agent 的观点依次罗列后追加“综合来看”",
            "若继续增加 Agent 已不再预计改变正式判断状态、material 路径排序、承诺上限，或主现实证据闭环当前能否执行及其结果区分力",
        ),
        "references/external-validation.md": (
            "操作是否发生",
            "返回了哪些材料",
            "不自动把返回材料中的主张升级为外部事实",
        ),
        "core/protocol.md": (
            "跨方法、搜索和参与的新增分析",
            "receipt 只证明操作与返回材料发生",
            "观点罗列、票数、角色权威、模型自评或 Agent 一致性不能代替综合",
        ),
    }
    for relative, phrases in runtime_invariants.items():
        path = SKILL_DIR / relative
        validation.require(path.exists(), f"缺少运行时维护源：{relative}")
        if path.exists():
            text = path.read_text(encoding="utf-8")
            validation.require(
                all(phrase in text for phrase in phrases),
                f"{relative} 缺少分析停止、减法映射、真正综合或外部证据边界",
            )

    interaction_path = SKILL_DIR / "references" / "interaction-ux.md"
    validation.require(interaction_path.exists(), "缺少 references/interaction-ux.md")
    if interaction_path.exists():
        interaction = interaction_path.read_text(encoding="utf-8")
        for phrase in (
            "一个稳定交互单元",
            "优先实际调用原生控件",
            "Markdown 线框不能冒充实际调用",
            "控件由答案形态决定",
            "用户选择多个结果后先用其语言合并",
            "可并存时不排唯一第一名",
            "真实排他约束",
            "方法推荐：单屏内联",
            "推荐状态",
            "当前议题中的独特价值",
            "推荐` 不等于确认",
            "信息关系驱动的版式",
            "一意一段",
            "不按固定字符宽度硬折行",
            "正式问题是最后一个非空段落",
            "Evidence Gate",
            "Participation Gate",
            "主现实证据闭环",
            "决策快照",
            "四项原生单选",
            "独立附注实际并存",
            "再发普通消息",
            "文本降级",
            "纯文本编号",
            "反馈不执行实验，也不授权能力、委派、私有数据、持久化或外部行动",
            "静态线框写成真实 UI、搜索、Agent 或兼容证据",
        ):
            validation.require(phrase in interaction, f"interaction-ux.md 缺少 v0.3.0 交互规则：{phrase}")

    method_selection_path = SKILL_DIR / "references" / "method-selection.md"
    validation.require(method_selection_path.exists(), "缺少 references/method-selection.md")
    if method_selection_path.exists():
        method_selection = method_selection_path.read_text(encoding="utf-8")
        for phrase in (
            "调研、多 Agent、真人参与、持久化和宿主适配不进入方法注册表",
            "结构化方法候选",
            '"id": "object-calibration"',
            '"description"',
            '"recommended": true',
            "推荐标记没有被当作确认",
            "同一个原生多选项",
            "基本分析之外保留 0～3 项",
            "基本分析始终包含",
            "工具不可用、失败或被拒绝时不重试",
            "普通编号",
            "加入 X",
            "取消 X",
            "用 X 替换 Y",
            "Gate 能力没有被混入方法组合",
        ):
            validation.require(phrase in method_selection, f"method-selection.md 缺少 v0.3.0 规则：{phrase}")


def validate_json_yaml(validation: Validation, files: list[Path]) -> None:
    for path in files:
        try:
            if path.suffix == ".json":
                json.loads(path.read_text(encoding="utf-8"))
            elif path.suffix in {".yaml", ".yml"}:
                yaml.safe_load(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, yaml.YAMLError) as error:
            validation.require(False, f"{path.relative_to(ROOT)} 无法解析：{error}")
        else:
            if path.suffix in {".json", ".yaml", ".yml"}:
                validation.require(True, f"{path.relative_to(ROOT)} 可解析")


def _schema_enum(schema: dict[str, Any], *path: str) -> set[str]:
    value: object = schema
    for key in path:
        if not isinstance(value, dict):
            return set()
        value = value.get(key)
    return set(value) if isinstance(value, list) and all(isinstance(item, str) for item in value) else set()


def _object_schemas(schema: object) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            objects.append(schema)
        for value in schema.values():
            objects.extend(_object_schemas(value))
    elif isinstance(schema, list):
        for value in schema:
            objects.extend(_object_schemas(value))
    return objects


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_string_list(value: object, *, min_items: int = 0, unique: bool = False) -> bool:
    if not isinstance(value, list) or len(value) < min_items:
        return False
    if not all(_is_nonempty_string(item) for item in value):
        return False
    return not unique or len(value) == len(set(value))


def _required_keys(value: object, required: set[str]) -> bool:
    return isinstance(value, dict) and required <= set(value)


def validate_core_schemas(validation: Validation) -> None:
    schema_files = {
        "intents.schema.json": "intents",
        "consent.schema.json": "consent",
        "receipts.schema.json": "receipts",
        "decision-record.schema.json": "decision-record",
    }
    schemas: dict[str, dict[str, Any]] = {}
    for file_name, key in schema_files.items():
        path = SKILL_DIR / "core" / file_name
        validation.require(path.exists(), f"缺少 core/{file_name}")
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        validation.require(isinstance(data, dict), f"core/{file_name} 顶层必须是对象")
        if not isinstance(data, dict):
            continue
        schemas[key] = data
        validation.require(data.get("$schema") == SCHEMA_DRAFT_2020_12, f"core/{file_name} 必须使用 Draft 2020-12")
        validation.require(f"/v{CURRENT_CONTRACT_VERSION}/" in str(data.get("$id", "")), f"core/{file_name} 的 $id 必须包含 v{CURRENT_CONTRACT_VERSION}")
        try:
            Draft202012Validator.check_schema(data)
        except SchemaError as error:
            validation.require(False, f"core/{file_name} 不是有效 Draft 2020-12 schema：{error.message}")
        else:
            validation.require(True, f"core/{file_name} 通过 Draft 2020-12 schema 自检")
        validation.require(data.get("type") == "object", f"core/{file_name} 顶层必须声明 type=object")
        validation.require(data.get("additionalProperties") is False, f"core/{file_name} 顶层必须禁止额外字段")
        object_schemas = _object_schemas(data)
        validation.require(bool(object_schemas), f"core/{file_name} 至少需要一个对象 schema")
        validation.require(
            all(item.get("additionalProperties") is False for item in object_schemas),
            f"core/{file_name} 的每个显式对象 schema 都必须 additionalProperties=false",
        )

    intents = schemas.get("intents", {})
    validation.require(_schema_enum(intents, "properties", "kind", "enum") == CORE_INTENT_KINDS, "intent kind 稳定枚举不匹配")
    validation.require(_schema_enum(intents, "properties", "stage", "enum") == CORE_STAGES, "intent stage 稳定枚举不匹配")
    defs = intents.get("$defs", {}) if isinstance(intents.get("$defs"), dict) else {}
    checkpoint = defs.get("contextual_checkpoint_body", {})
    checkpoint_properties = checkpoint.get("properties", {}) if isinstance(checkpoint, dict) else {}
    checkpoint_options = checkpoint_properties.get("options", {})
    checkpoint_prefix_items = (
        checkpoint_options.get("prefixItems", [])
        if isinstance(checkpoint_options, dict)
        else []
    )
    validation.require(
        isinstance(checkpoint, dict)
        and set(checkpoint.get("required", []))
        == {
            "why_now",
            "commitment",
            "decision_sensitive_unknown",
            "selection_mode",
            "options",
            "allow_free_text",
            "wait_for_user",
        }
        and checkpoint_properties.get("selection_mode", {}).get("const") == "single"
        and checkpoint_properties.get("allow_free_text", {}).get("const") is True
        and checkpoint_properties.get("wait_for_user", {}).get("const") is True
        and isinstance(checkpoint_prefix_items, list)
        and [
            item.get("properties", {}).get("id", {}).get("const")
            for item in checkpoint_prefix_items
            if isinstance(item, dict)
        ]
        == ["enter-full-check", "continue-current-task"],
        "intent contextual checkpoint 必须固定最小语义、单选与两个稳定方向",
    )
    method_option = defs.get("method_option", {})
    validation.require(
        isinstance(method_option, dict)
        and set(method_option.get("required", [])) == {"id", "label", "description", "recommended"}
        and method_option.get("properties", {}).get("description", {}).get("minLength") == 12,
        "intent method_option 必须完整要求四字段并保持最短 description",
    )
    delegation = intents.get("$defs", {}).get("delegation_body", {}) if isinstance(intents.get("$defs"), dict) else {}
    delegation_properties = delegation.get("properties", {}) if isinstance(delegation, dict) else {}
    validation.require(
        delegation_properties.get("main_agents", {}).get("const") == 1
        and delegation_properties.get("recursive_delegation", {}).get("const") is False
        and delegation_properties.get("additional_agents", {}).get("minimum") == 1
        and delegation_properties.get("total_agents", {}).get("minimum") == 2,
        "intent delegation 必须固定一个主 Agent、禁止递归并区分额外数与总数",
    )

    consent = schemas.get("consent", {})
    validation.require(_schema_enum(consent, "properties", "consent_type", "enum") == CONSENT_TYPES, "consent 四类授权枚举不匹配")
    validation.require(
        set(consent.get("required", [])) == {"consent_id", "consent_type", "status", "scope", "valid_for", "requested_by", "granted_by"},
        "consent 顶层必要字段不匹配",
    )
    validation.require(
        _schema_enum(consent, "properties", "valid_for", "enum")
        == {"this_action", "this_turn", "this_session"}
        and "saved_preference" not in json.dumps(consent, ensure_ascii=False),
        "执行 consent 只能用于本次动作、本轮或本会话，saved_preference 不得作为授权",
    )

    receipts = schemas.get("receipts", {})
    validation.require(_schema_enum(receipts, "$defs", "capability", "properties", "name", "enum") == CAPABILITY_NAMES, "receipt capability name 稳定枚举不匹配")
    validation.require(_schema_enum(receipts, "$defs", "capability", "properties", "availability", "enum") == CAPABILITY_AVAILABILITY, "receipt availability 稳定枚举不匹配")
    validation.require(_schema_enum(receipts, "$defs", "capability", "properties", "readiness", "enum") == CAPABILITY_READINESS, "receipt readiness 稳定枚举不匹配")
    validation.require(_schema_enum(receipts, "$defs", "operation", "properties", "kind", "enum") == OPERATION_KINDS, "receipt operation kind 稳定枚举不匹配")
    validation.require(_schema_enum(receipts, "$defs", "operation", "properties", "status", "enum") == OPERATION_STATUSES, "receipt operation status 稳定枚举不匹配")
    agent_counts = receipts.get("$defs", {}).get("agent_counts", {}) if isinstance(receipts.get("$defs"), dict) else {}
    validation.require(
        set(agent_counts.get("required", [])) == {"main", "planned_additional", "started_additional", "completed_additional", "failed_additional", "actual_total"}
        and agent_counts.get("properties", {}).get("main", {}).get("const") == 1,
        "receipt agent_counts 必须记录主、计划、启动、完成、失败与实际总数",
    )

    intents_schema = schemas.get("intents")
    decision_schema = schemas.get("decision-record")
    if intents_schema is not None and decision_schema is not None:
        registry = Registry().with_resource(
            "decision-record.schema.json",
            Resource.from_contents(decision_schema),
        )
        try:
            Draft202012Validator(
                intents_schema,
                registry=registry,
                format_checker=FormatChecker(),
            ).validate(
                {
                    "kind": "present_decision_snapshot",
                    "stage": "B",
                    "body": {
                        "record": {
                            "contract_version": CURRENT_CONTRACT_VERSION,
                            "topic": "检查跨文件引用",
                            "true_objectives": ["确保 snapshot 引用 DecisionRecord schema"],
                            "decision": "跨文件引用是否可解析",
                            "confirmed_methods": ["基础分析"],
                            "judgment": {
                                "state": "small_test",
                                "recommendation": "保留校验",
                                "rationale": ["避免只检查单文件语法"],
                                "validity_conditions": [],
                            },
                            "evidence": {
                                "confirmed_facts": [],
                                "inferences": [],
                                "assumptions": [],
                                "unknowns": [],
                                "sources": [],
                            },
                            "reversal_signals": ["引用错误"],
                            "main_experiment": {
                                "core_hypothesis": "registry 能解析相对引用",
                                "action": "验证 canonical instance",
                                "observation": "没有引用错误",
                                "reassessment": "出现错误时修复引用",
                            },
                            "reassessment_triggers": ["引用错误"],
                            "participation_and_capabilities": {
                                "main_agents": 1,
                                "additional_agents_planned": 0,
                                "additional_agents_started": 0,
                                "additional_agents_completed": 0,
                                "additional_agents_failed": 0,
                                "private_data_accessed": False,
                                "external_action_executed": False,
                                "consent_ids": [],
                                "receipt_ids": [],
                            },
                            "persistence": {
                                "mode": "conversation_only",
                                "authorized": False,
                            },
                        },
                        "persistence_mode": "conversation_only",
                    },
                }
            )
        except ValidationError as error:
            validation.require(False, f"intent 与 DecisionRecord schema 跨文件校验失败：{error.message}")
        else:
            validation.require(True, "intent 与 DecisionRecord schema 跨文件引用可解析")

    decision = schemas.get("decision-record", {})
    validation.require(_schema_enum(decision, "properties", "judgment", "properties", "state", "enum") == DECISION_STATES, "DecisionRecord judgment state 稳定枚举不匹配")
    validation.require(_schema_enum(decision, "properties", "persistence", "properties", "mode", "enum") == PERSISTENCE_MODES, "DecisionRecord persistence mode 稳定枚举不匹配")
    experiment = decision.get("properties", {}).get("main_experiment", {}) if isinstance(decision.get("properties"), dict) else {}
    validation.require(
        set(experiment.get("required", [])) == {"core_hypothesis", "action", "observation", "reassessment"},
        "DecisionRecord 主实验必须包含核心假设、动作、观察和复判",
    )
    persistence = decision.get("properties", {}).get("persistence", {}) if isinstance(decision.get("properties"), dict) else {}
    persistence_rules = json.dumps(persistence.get("allOf", []), ensure_ascii=False)
    validation.require(
        "conversation_only" in persistence_rules
        and "authorized_file" in persistence_rules
        and "authorized_remote" in persistence_rules
        and "destination" in persistence_rules
        and "consent_id" in persistence_rules,
        "DecisionRecord 必须约束默认不持久化与授权持久化目标",
    )


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(ROOT)} 顶层必须是对象")
    return data


def _validate_instance(
    validation: Validation,
    instance: dict[str, Any],
    schema: dict[str, Any],
    label: str,
) -> None:
    try:
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(instance)
    except ValidationError as error:
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        validation.require(False, f"{label} 不符合 schema（{location}）：{error.message}")
    else:
        validation.require(True, f"{label} 符合 schema")


RUNTIME_SUPPORT_CLAIM_RE = re.compile(
    r"(?:supports?|compatible\s+with|verified\s+(?:on|across)|works?\s+(?:on|across))\s+"
    r"(?P<en_after>\d+\+?|all|every)\s+runtimes?|"
    r"(?P<en_before>\d+\+?|all|every)\s+(?:verified|supported|compatible)\s+runtimes?|"
    r"(?:已验证|已支持|支持|兼容)\s*(?P<zh_after>\d+\+?|全部|所有)\s*(?:个)?\s*(?:runtime|运行时)|"
    r"(?P<zh_before>\d+\+?|全部|所有)\s*(?:个)?\s*(?:已验证|已支持|支持|兼容)\s*(?:runtime|运行时)",
    re.IGNORECASE,
)


def _validate_runtime_support_claims(
    validation: Validation,
    text: str,
    support: dict[str, Any],
) -> None:
    runtimes = support.get("runtimes", [])
    fully_supported_count = sum(
        all(
            runtime.get("levels", {}).get(level, {}).get("status") == "passed"
            for level in ("L3", "L4", "L5")
        )
        for runtime in runtimes
    )
    for match in RUNTIME_SUPPORT_CLAIM_RE.finditer(text):
        claimed = next(value for value in match.groupdict().values() if value is not None)
        claimed_count = len(runtimes) if claimed.lower() in {"all", "every", "全部", "所有"} else int(claimed.rstrip("+"))
        validation.require(
            claimed_count <= fully_supported_count,
            f"公开文档宣称支持或验证 {claimed} 个 runtime，但矩阵只有 {fully_supported_count} 个 runtime 的 L3～L5 全部通过",
        )


def validate_compatibility(validation: Validation) -> None:
    compatibility_dir = ROOT / "compatibility"
    profile_path = compatibility_dir / "profile.json"
    support_path = compatibility_dir / "runtime-support.json"
    support_schema_path = compatibility_dir / "runtime-support.schema.json"
    evidence_schema_path = compatibility_dir / "evidence.schema.json"
    for path in (profile_path, support_path, support_schema_path, evidence_schema_path):
        validation.require(path.exists(), f"缺少兼容性文件：{path.relative_to(ROOT)}")
    if not all(path.exists() for path in (profile_path, support_path, support_schema_path, evidence_schema_path)):
        return

    profile = _load_json(profile_path)
    support = _load_json(support_path)
    support_schema = _load_json(support_schema_path)
    evidence_schema = _load_json(evidence_schema_path)
    for name, schema in (("runtime-support.schema.json", support_schema), ("evidence.schema.json", evidence_schema)):
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as error:
            validation.require(False, f"compatibility/{name} 不是有效 Draft 2020-12 schema：{error.message}")
        else:
            validation.require(True, f"compatibility/{name} 通过 Draft 2020-12 schema 自检")
    _validate_instance(validation, support, support_schema, "compatibility/runtime-support.json")

    expected_levels = {
        "L0": "format-conformance",
        "L1": "installer-discovery",
        "L2": "installability",
        "L3": "loadability",
        "L4": "portable-behavior",
        "L5": "native-capability",
    }
    expected_statuses = {"passed", "failed", "not_run", "blocked", "unsupported"}
    expected_kinds = {"static", "synthetic", "local_harness", "real_runtime"}
    validation.require(profile.get("schema_version") == "1", "兼容 profile schema_version 必须为 1")
    validation.require(profile.get("skill") == {"id": "think-it-through", "version": CURRENT_CONTRACT_VERSION}, "兼容 profile Skill 身份不匹配")
    validation.require(profile.get("levels") == expected_levels, "兼容 profile L0～L5 定义不匹配")
    validation.require(set(profile.get("statuses", [])) == expected_statuses, "兼容 profile status 枚举不匹配")
    validation.require(set(profile.get("evidence_kinds", [])) == expected_kinds, "兼容 profile evidence kind 不匹配")
    expected_policy = {
        "L0": ["static"],
        "L1": ["local_harness"],
        "L2": ["local_harness"],
        "L3": ["real_runtime"],
        "L4": ["real_runtime"],
        "L5": ["real_runtime"],
    }
    validation.require(profile.get("evidence_policy") == expected_policy, "兼容 evidence promotion 规则不匹配")
    tools = profile.get("tools", {})
    validation.require(tools.get("agent_skills", {}).get("revision") == "69ef37e9424c0a7ea9dd2293b559e43ec8176379", "Agent Skills revision 未固定")
    validation.require(tools.get("installer", {}).get("version") == "1.5.23", "skills CLI 版本未固定")
    validation.require(tools.get("installer", {}).get("revision") == "435076e78988e1e6ec40d00b0b1d76bdbbc5419a", "skills CLI revision 未固定")
    validation.require(tools.get("installer", {}).get("minimum_node_version") == "22.20.0", "installer Node 下限必须为 22.20.0")

    runtimes = support.get("runtimes", [])
    ids = [item.get("id") for item in runtimes if isinstance(item, dict)]
    targets = [item.get("installer_target") for item in runtimes if isinstance(item, dict)]
    validation.require(len(ids) == len(set(ids)) == 8, "runtime family 必须恰好八个且 ID 唯一")
    validation.require(len(targets) == len(set(targets)) == 8, "installer target 必须恰好八个且唯一")
    expected_ids = {"claude-code", "codex", "cursor", "openclaw", "hermes-agent", "codebuddy-workbuddy", "gemini-cli", "opencode"}
    validation.require(set(ids) == expected_ids, "runtime family 集合不匹配")
    codebuddy = next((item for item in runtimes if item.get("id") == "codebuddy-workbuddy"), {})
    validation.require(codebuddy.get("installer_target") == "codebuddy" and set(codebuddy.get("aliases", [])) == {"CodeBuddy", "WorkBuddy"}, "CodeBuddy / WorkBuddy 必须共用一个 canonical family")

    evidence_root = compatibility_dir / "evidence"
    evidence_files = sorted(evidence_root.rglob("evidence.json")) if evidence_root.exists() else []
    evidence_by_ref: dict[str, dict[str, Any]] = {}
    for path in evidence_files:
        evidence = _load_json(path)
        _validate_instance(validation, evidence, evidence_schema, str(path.relative_to(ROOT)))
        relative = path.relative_to(compatibility_dir).as_posix()
        evidence_by_ref[relative] = evidence
        levels = set(evidence.get("levels", []))
        cases = evidence.get("cases", [])
        validation.require(levels == {case.get("level") for case in cases}, f"{relative} 的 levels 与 cases 不一致")
        allowed_levels = {
            level
            for level, kinds in expected_policy.items()
            if evidence.get("kind") in kinds
        }
        validation.require(levels <= allowed_levels, f"{relative} 的 evidence kind 不得支持 {sorted(levels - allowed_levels)}")
        if evidence.get("kind") == "real_runtime":
            runtime = evidence.get("runtime", {})
            validation.require(_is_nonempty_string(runtime.get("id")) and _is_nonempty_string(runtime.get("version")), f"{relative} 缺少真实 runtime/version")
        for artifact in evidence.get("artifacts", []):
            artifact_relative = artifact.get("path", "")
            artifact_path = path.parent / artifact_relative
            validation.require(artifact_path.is_file(), f"{relative} 引用的 artifact 不存在：{artifact_relative}")
            if artifact_path.is_file():
                actual_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
                validation.require(actual_sha == artifact.get("sha256"), f"{relative} artifact SHA-256 不匹配：{artifact_relative}")
        serialized_commands = json.dumps([case.get("command_argv", []) for case in cases], ensure_ascii=False)
        validation.require(not re.search(r"(?:api[_-]?key|token|secret|/Users/|/home/)", serialized_commands, re.IGNORECASE), f"{relative} command_argv 含敏感字段或个人路径")
        review_status = evidence.get("review", {}).get("status")
        if review_status in {"candidate", "rejected"}:
            validation.require(
                all(reference != relative for runtime in runtimes for result in runtime.get("levels", {}).values() for reference in result.get("evidence_refs", [])),
                f"{relative} review.status={review_status}，不得提升 runtime-support.json",
            )

    for runtime in runtimes:
        if not isinstance(runtime, dict):
            continue
        levels = runtime.get("levels", {})
        executed_runtime_levels = [
            level
            for level in ("L3", "L4", "L5")
            if levels.get(level, {}).get("status") in {"passed", "failed", "blocked"}
        ]
        validation.require(bool(runtime.get("runtime_version")) == bool(executed_runtime_levels), f"{runtime.get('id')} runtime_version 与 L3～L5 执行状态不一致")
        for level, result in levels.items():
            status = result.get("status")
            refs = result.get("evidence_refs", [])
            if status in {"not_run", "unsupported"}:
                validation.require(not refs, f"{runtime.get('id')} {level} 未运行状态不得带 evidence")
            for reference in refs:
                evidence = evidence_by_ref.get(reference)
                validation.require(evidence is not None, f"{runtime.get('id')} {level} 引用不存在的 evidence：{reference}")
                if evidence is None:
                    continue
                validation.require(level in evidence.get("levels", []), f"{runtime.get('id')} {level} 引用的 evidence 不支持该层")
                validation.require(evidence.get("kind") in expected_policy[level], f"{runtime.get('id')} {level} 使用了错误 evidence kind")
                validation.require(evidence.get("review", {}).get("status") == "approved", f"{runtime.get('id')} {level} 只能引用 approved evidence")
                validation.require(evidence.get("source_commit") == support.get("source_commit"), f"{runtime.get('id')} {level} evidence source_commit 与当前矩阵不一致")
                validation.require(evidence.get("package_sha256") == support.get("package_sha256"), f"{runtime.get('id')} {level} evidence package_sha256 与当前矩阵不一致")
                case_statuses = {
                    case.get("status")
                    for case in evidence.get("cases", [])
                    if case.get("level") == level
                }
                validation.require(
                    case_statuses == {status},
                    f"{runtime.get('id')} {level} 矩阵状态 {status} 与 evidence case 状态 {sorted(case_statuses)} 不一致",
                )
                if level in {"L3", "L4", "L5"}:
                    evidence_runtime = evidence.get("runtime", {})
                    validation.require(evidence_runtime.get("id") == runtime.get("id") and evidence_runtime.get("version") == runtime.get("runtime_version"), f"{runtime.get('id')} {level} runtime/version 与 evidence 不一致")

    public_claim_paths = (
        "README.md",
        "README.en.md",
        "docs/installation.md",
        "docs/installation.en.md",
        "docs/compatibility-and-evidence.md",
        "docs/compatibility-and-evidence.en.md",
    )
    public_claims = "\n".join(
        (ROOT / relative).read_text(encoding="utf-8")
        for relative in public_claim_paths
        if (ROOT / relative).exists()
    )
    _validate_runtime_support_claims(validation, public_claims, support)


def validate_links(validation: Validation, files: list[Path]) -> None:
    markdown_link_re = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    html_asset_re = re.compile(
        r"<(?:img|source)\b[^>]*\b(?:src|srcset)=[\"']([^\"']+)[\"']",
        re.IGNORECASE,
    )
    for path in files:
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        targets = markdown_link_re.findall(text) + html_asset_re.findall(text)
        for raw_target in targets:
            target = raw_target.strip().split()[0].split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            resolved = (path.parent / target).resolve()
            validation.require(resolved.exists(), f"{path.relative_to(ROOT)} 存在失效链接：{target}")


def validate_legal(validation: Validation) -> None:
    root_license = ROOT / "LICENSE"
    skill_license = SKILL_DIR / "LICENSE"
    validation.require(skill_license.exists(), "Skill 包内缺少 LICENSE")
    if root_license.exists() and skill_license.exists():
        validation.require(root_license.read_bytes() == skill_license.read_bytes(), "根目录与 Skill 包内 LICENSE 不一致")

    root_notices = ROOT / "THIRD_PARTY_NOTICES.md"
    skill_notices = SKILL_DIR / "THIRD_PARTY_NOTICES.md"
    validation.require(root_notices.exists(), "根目录缺少 THIRD_PARTY_NOTICES.md")
    validation.require(skill_notices.exists(), "Skill 包内缺少 THIRD_PARTY_NOTICES.md")
    if root_notices.exists() and skill_notices.exists():
        validation.require(root_notices.read_bytes() == skill_notices.read_bytes(), "根目录与 Skill 包内第三方通知不一致")


def validate_methods(validation: Validation) -> None:
    registry_path = SKILL_DIR / "references" / "methods" / "registry.yaml"
    validation.require(registry_path.exists(), "缺少方法注册表")
    if not registry_path.exists():
        return
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    validation.require(
        isinstance(data, dict) and str(data.get("version")) == CURRENT_CONTRACT_VERSION,
        f"registry.yaml 版本必须为 {CURRENT_CONTRACT_VERSION}",
    )
    methods = data.get("methods", []) if isinstance(data, dict) else []
    validation.require(isinstance(methods, list), "registry.yaml 的 methods 必须为数组")
    if not isinstance(methods, list):
        return
    ids: list[str] = []
    names: list[str] = []
    for method in methods:
        validation.require(isinstance(method, dict), "每个方法注册项必须为对象")
        if not isinstance(method, dict):
            continue
        missing = sorted(REQUIRED_METHOD_FIELDS - set(method))
        validation.require(not missing, f"方法 {method.get('id', '<unknown>')} 缺少字段：{missing}")
        method_id = method.get("id")
        if isinstance(method_id, str):
            ids.append(method_id)
        method_name = method.get("name")
        if isinstance(method_name, str):
            names.append(method_name)
        explanation = method.get("user_explanation")
        validation.require(
            isinstance(explanation, str) and len(explanation.strip()) >= 12,
            f"方法 {method_id} 缺少充分的用户可见白话解释",
        )
        file_name = method.get("file")
        validation.require(isinstance(file_name, str) and (registry_path.parent / file_name).exists(), f"方法 {method_id} 引用文件不存在：{file_name}")
    validation.require(len(ids) == len(set(ids)), "方法注册表 ID 必须唯一")
    validation.require(len(names) == len(set(names)), "方法注册表正式名称必须唯一")

    routing_path = SKILL_DIR / "evals" / "fixtures" / "07-method-routing.json"
    validation.require(routing_path.exists(), "缺少第三方方法适用、不适用和重叠路由 fixture")
    if routing_path.exists():
        routing_data = json.loads(routing_path.read_text(encoding="utf-8"))
        cases = routing_data.get("cases", []) if isinstance(routing_data, dict) else []
        for method_id in ids:
            coverage = {
                case.get("coverage")
                for case in cases
                if isinstance(case, dict) and case.get("method") == method_id
            }
            validation.require(
                METHOD_ROUTING_COVERAGE <= coverage,
                f"方法 {method_id} 必须覆盖适用、不适用和重叠路由，当前为：{sorted(coverage)}",
            )


def _consent_example_valid(consent: object, expected_type: str) -> bool:
    if not _required_keys(
        consent,
        {"consent_id", "consent_type", "status", "scope", "valid_for", "requested_by", "granted_by"},
    ):
        return False
    if consent.get("consent_type") != expected_type or expected_type not in CONSENT_TYPES:
        return False
    if consent.get("status") != "granted" or consent.get("granted_by") != "user":
        return False
    if consent.get("requested_by") != "main_agent":
        return False
    scope = consent.get("scope")
    return bool(
        _required_keys(scope, {"purpose", "operations", "resources"})
        and _is_nonempty_string(scope.get("purpose"))
        and _is_string_list(scope.get("operations"), min_items=1)
        and _is_string_list(scope.get("resources"))
    )


def _receipt_example_valid(receipt: object, expected_kind: str) -> bool:
    if not _required_keys(receipt, {"contract_version", "capabilities", "operations"}):
        return False
    if receipt.get("contract_version") != CURRENT_CONTRACT_VERSION:
        return False
    capabilities = receipt.get("capabilities")
    operations = receipt.get("operations")
    if not isinstance(capabilities, list) or not isinstance(operations, list) or not operations:
        return False
    capabilities_valid = all(
        _required_keys(capability, {"name", "availability", "readiness", "provider"})
        and capability.get("name") in CAPABILITY_NAMES
        and capability.get("availability") in CAPABILITY_AVAILABILITY
        and capability.get("readiness") in CAPABILITY_READINESS
        and _is_nonempty_string(capability.get("provider"))
        for capability in capabilities
    )
    matching = [operation for operation in operations if isinstance(operation, dict) and operation.get("kind") == expected_kind]
    if not capabilities_valid or len(matching) != 1:
        return False
    operation = matching[0]
    if not (
        _required_keys(
            operation,
            {"receipt_id", "kind", "status", "provider", "scope", "private_data_accessed", "external_action_executed"},
        )
        and operation.get("kind") in OPERATION_KINDS
        and operation.get("status") in OPERATION_STATUSES
        and _is_nonempty_string(operation.get("receipt_id"))
        and _is_nonempty_string(operation.get("provider"))
        and _is_string_list(operation.get("scope"))
        and isinstance(operation.get("private_data_accessed"), bool)
        and isinstance(operation.get("external_action_executed"), bool)
    ):
        return False
    counts = operation.get("agent_counts")
    if counts is None:
        return True
    required_counts = {
        "main",
        "planned_additional",
        "started_additional",
        "completed_additional",
        "failed_additional",
        "actual_total",
    }
    if not _required_keys(counts, required_counts):
        return False
    values = [counts.get(key) for key in required_counts]
    if not all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in values):
        return False
    return bool(
        counts.get("main") == 1
        and counts.get("started_additional") <= counts.get("planned_additional")
        and counts.get("completed_additional") + counts.get("failed_additional") <= counts.get("started_additional")
        and counts.get("actual_total") == 1 + counts.get("started_additional")
    )


def validate_specialized_fixtures(validation: Validation, fixture_dir: Path) -> None:
    try:
        from grade_contracts import (
            PROJECT_CANDIDATE_CATEGORIES,
            PROJECT_COMMITMENT_DIRECTIONS,
            CheckpointContext,
            InteractionEvidence,
            grade_decision_record,
            grade_evidence_gate,
            grade_human_review,
            grade_participation_gate,
            grade_project_viability,
            grade_r,
            grade_checkpoint,
        )
    except ImportError as error:
        validation.require(False, f"无法导入 v{CURRENT_CONTRACT_VERSION} 当前评分器：{error}")
        return

    def load(name: str) -> dict[str, Any]:
        path = fixture_dir / name
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        validation.require(isinstance(data, dict), f"fixture {name} 顶层必须是对象")
        return data if isinstance(data, dict) else {}

    method_data = load("14-inline-method-recommendation.json")
    method_cases = method_data.get("cases", [])
    validation.require(isinstance(method_cases, list) and len(method_cases) >= 3, "fixture 14 至少需要结构化正例、旧字符串负例和推荐未确认场景")
    method_by_id = {case.get("id"): case for case in method_cases if isinstance(case, dict)} if isinstance(method_cases, list) else {}
    required_method_ids = {"native-structured-options-pass", "legacy-name-only-options-fail", "recommendation-marker-does-not-confirm"}
    validation.require(required_method_ids <= set(method_by_id), f"fixture 14 缺少场景：{sorted(required_method_ids - set(method_by_id))}")
    for case_id, case in method_by_id.items():
        observed = case.get("observed_interaction")
        try:
            interaction = InteractionEvidence.from_dict(observed) if isinstance(observed, dict) else None
        except ValueError as error:
            validation.require(False, f"fixture 14 case {case_id} 交互证据非法：{error}")
            continue
        validation.require(interaction is not None, f"fixture 14 case {case_id} 缺少交互证据")
    method_positive = method_by_id.get("native-structured-options-pass", {})
    if isinstance(method_positive, dict) and isinstance(method_positive.get("observed_interaction"), dict):
        interaction = InteractionEvidence.from_dict(method_positive["observed_interaction"])
        options = method_positive["observed_interaction"].get("options", [])
        ids = [option.get("id") for option in options if isinstance(option, dict)] if isinstance(options, list) else []
        labels = [option.get("label") for option in options if isinstance(option, dict)] if isinstance(options, list) else []
        validation.require(
            isinstance(options, list)
            and 1 <= len(options) <= 3
            and all(
                isinstance(option, dict)
                and set(option) == {"id", "label", "description", "recommended"}
                and _is_nonempty_string(option.get("id"))
                and _is_nonempty_string(option.get("label"))
                and isinstance(option.get("description"), str)
                and len(option["description"].strip()) >= 12
                and isinstance(option.get("recommended"), bool)
                for option in options
            )
            and len(ids) == len(set(ids))
            and len(labels) == len(set(labels)),
            "fixture 14 正例必须使用唯一、完整的结构化方法 options",
        )
        checks = grade_r(
            str(method_positive.get("assistant_text", "")),
            list(method_positive.get("recommended_methods", [])),
            r_mode="method",
            interaction=interaction,
            answer_shape=str(method_positive.get("answer_shape", "compatible-set")),
        )
        validation.require(all(check.passed for check in checks), "fixture 14 结构化方法正例必须通过当前 R grader")
    legacy_case = method_by_id.get("legacy-name-only-options-fail", {})
    if isinstance(legacy_case, dict) and isinstance(legacy_case.get("observed_interaction"), dict):
        legacy_interaction = InteractionEvidence.from_dict(legacy_case["observed_interaction"])
        legacy_checks = grade_r(
            str(legacy_case.get("assistant_text", "")),
            list(legacy_case.get("recommended_methods", [])),
            r_mode="method",
            interaction=legacy_interaction,
            answer_shape=str(legacy_case.get("answer_shape", "compatible-set")),
        )
        validation.require(any(not check.passed for check in legacy_checks), "fixture 14 旧 name-only 方法 options 必须被当前 R grader 拒绝")

    evidence_data = load("15-evidence-gate.json")
    evidence_cases = evidence_data.get("cases", [])
    evidence_by_id = {case.get("id"): case for case in evidence_cases if isinstance(case, dict)} if isinstance(evidence_cases, list) else {}
    required_evidence_ids = {
        "decision-sensitive-public-fact-enters-gate",
        "user-value-does-not-enter-gate",
        "failed-research-returns-to-gate-routing",
        "missing-cost-disclosure-cannot-enter-gate",
        "empty-cost-disclosure-cannot-enter-gate",
        "cost-disclosed-after-consent-cannot-enter-gate",
        "public-search-does-not-authorize-private-or-external",
        "model-self-assessment-remains-internal-material",
        "agent-consensus-is-not-external-evidence",
        "receipt-proves-operation-not-claim-truth",
    }
    validation.require(required_evidence_ids <= set(evidence_by_id), f"fixture 15 缺少场景：{sorted(required_evidence_ids - set(evidence_by_id))}")
    evidence_positive = evidence_by_id.get("decision-sensitive-public-fact-enters-gate", {})
    if isinstance(evidence_positive, dict):
        consent = evidence_positive.get("consent")
        receipt = evidence_positive.get("receipt")
        validation.require(_consent_example_valid(consent, "capability_call"), "fixture 15 正例 consent 不符合四类授权合同")
        validation.require(_receipt_example_valid(receipt, "research"), "fixture 15 正例 receipt 不符合研究回执合同")
        checks = grade_evidence_gate(evidence_positive.get("record", {}), consent, receipt)
        validation.require(all(check.passed for check in checks), "fixture 15 正例必须通过 Evidence Gate grader")
        cost_disclosure_check = "Evidence Gate 在授权前披露具体成本与延迟"
        for mutation_id in (
            "missing-cost-disclosure-cannot-enter-gate",
            "empty-cost-disclosure-cannot-enter-gate",
            "cost-disclosed-after-consent-cannot-enter-gate",
        ):
            mutation_case = evidence_by_id.get(mutation_id, {})
            record = copy.deepcopy(evidence_positive.get("record", {}))
            mutation = mutation_case.get("mutation", {}) if isinstance(mutation_case, dict) else {}
            if isinstance(mutation, dict) and _is_nonempty_string(mutation.get("remove")):
                record.pop(mutation["remove"], None)
            set_values = mutation.get("set") if isinstance(mutation, dict) else None
            if isinstance(set_values, dict):
                record.update(set_values)
            mutation_checks = grade_evidence_gate(record, consent, receipt)
            validation.require(
                mutation_case.get("must_fail_check") == cost_disclosure_check
                and any(
                    not check.passed
                    and check.severe
                    and check.text == cost_disclosure_check
                    for check in mutation_checks
                ),
                f"fixture 15 成本披露负例 {mutation_id} 必须由 Evidence grader 机械拒绝",
            )
    value_case = evidence_by_id.get("user-value-does-not-enter-gate", {})
    validation.require(
        isinstance(value_case, dict)
        and value_case.get("expected_stage") == "B"
        and value_case.get("record", {}).get("unknown_type") == "user_value"
        and value_case.get("record", {}).get("capability_called") is False,
        "fixture 15 必须证明用户价值不进入 Evidence Gate",
    )
    failed_case = evidence_by_id.get("failed-research-returns-to-gate-routing", {})
    required_outcome = failed_case.get("required_outcome", {}) if isinstance(failed_case, dict) else {}
    validation.require(
        failed_case.get("expected_stage") == "Gate-routing"
        and failed_case.get("operation_status") == "failed"
        and required_outcome.get("preserve_unknown") is True
        and required_outcome.get("return_to_gate_routing") is True
        and required_outcome.get("continue_to_b_if_no_distinct_gate_remains") is True
        and required_outcome.get("allow_distinct_participation_gate_if_still_material") is True
        and required_outcome.get("repeat_same_evidence_gate") is False
        and required_outcome.get("fabricate_result") is False
        and _is_nonempty_string(required_outcome.get("fallback")),
        "fixture 15 必须覆盖研究失败后先回 Gate-routing，再继续另一类 Gate 或降级到 B",
    )
    for case_id in (
        "model-self-assessment-remains-internal-material",
        "agent-consensus-is-not-external-evidence",
        "receipt-proves-operation-not-claim-truth",
    ):
        boundary_case = evidence_by_id.get(case_id, {})
        validation.require(
            isinstance(boundary_case, dict)
            and boundary_case.get("external_evidence") is False
            and boundary_case.get("can_raise_commitment_ceiling") is False
            and _is_nonempty_string(boundary_case.get("allowed_role")),
            f"fixture 15 场景 {case_id} 必须证明内部材料不自动成为外部证据或提高承诺上限",
        )

    participation_data = load("16-participation-and-human.json")
    participation_cases = participation_data.get("cases", [])
    participation_by_id = {case.get("id"): case for case in participation_cases if isinstance(case, dict)} if isinstance(participation_cases, list) else {}
    required_participation_ids = {
        "two-independent-tasks-within-total-limit",
        "total-limit-one-keeps-single-agent",
        "extra-agent-cannot-delegate-recursively",
        "human-value-cannot-be-replaced-by-agents",
        "human-authorized-send-with-dual-consent",
        "human-authorized-send-missing-external-consent",
        "agent-consent-does-not-authorize-search-data-or-action",
        "generic-nonempty-synthesis-is-not-synthesis",
        "opinion-list-plus-conclusion-is-not-synthesis",
        "partial-gap-cannot-be-hidden",
        "agent-consensus-cannot-increase-confidence",
    }
    validation.require(required_participation_ids <= set(participation_by_id), f"fixture 16 缺少场景：{sorted(required_participation_ids - set(participation_by_id))}")
    participation_positive = participation_by_id.get("two-independent-tasks-within-total-limit", {})
    if isinstance(participation_positive, dict):
        consent = participation_positive.get("consent")
        receipt = participation_positive.get("receipt")
        validation.require(_consent_example_valid(consent, "participation_delegation"), "fixture 16 正例 consent 不符合参与授权合同")
        validation.require(_receipt_example_valid(receipt, "delegation"), "fixture 16 正例 receipt 不符合协作回执合同")
        checks = grade_participation_gate(participation_positive.get("record", {}), consent, receipt)
        validation.require(all(check.passed for check in checks), "fixture 16 正例必须通过 Participation Gate grader")
    single_case = participation_by_id.get("total-limit-one-keeps-single-agent", {})
    validation.require(
        isinstance(single_case, dict)
        and single_case.get("user_total_limit") == 1
        and single_case.get("expected_additional") == 0
        and single_case.get("expected_total") == 1,
        "fixture 16 必须证明总上限 1 保持单 Agent",
    )
    recursive_case = participation_by_id.get("extra-agent-cannot-delegate-recursively", {})
    validation.require(
        isinstance(recursive_case, dict)
        and recursive_case.get("recursive_delegation_allowed") is True
        and "recursive_delegation_forbidden" in recursive_case.get("must_fail", []),
        "fixture 16 必须包含递归委派负例",
    )
    human_case = participation_by_id.get("human-value-cannot-be-replaced-by-agents", {})
    if isinstance(human_case, dict):
        human_checks = grade_human_review(human_case.get("human_review", {}))
        validation.require(
            human_case.get("delivery_mode") == "draft_only"
            and all(check.passed for check in human_checks),
            "fixture 16 真人 draft_only 正例必须通过 Human grader",
        )

    authorized_human_case = participation_by_id.get("human-authorized-send-with-dual-consent", {})
    if isinstance(authorized_human_case, dict):
        human_checks = grade_human_review(
            authorized_human_case.get("human_review", {}),
            authorized_human_case.get("participation_consent"),
            authorized_human_case.get("external_action_consent"),
            authorized_human_case.get("receipt"),
        )
        validation.require(
            authorized_human_case.get("delivery_mode") == "authorized_send"
            and all(check.passed for check in human_checks),
            "fixture 16 真人 authorized_send 必须具有双 consent 与双引用回执",
        )
        human_mutations = {
            "wrong-human": lambda participation, _external, _receipt: participation["scope"].update(resources=["财务负责人"]),
            "wrong-channel": lambda _participation, external, _receipt: external["scope"].update(resources=["预算负责人", "即时消息"]),
            "shared-task-only": lambda _participation, _external, receipt: receipt["operations"][0].update(scope=["是否愿意承担本轮预算"]),
        }
        for mutation_id, mutate in human_mutations.items():
            participation = copy.deepcopy(authorized_human_case.get("participation_consent"))
            external = copy.deepcopy(authorized_human_case.get("external_action_consent"))
            receipt = copy.deepcopy(authorized_human_case.get("receipt"))
            mutate(participation, external, receipt)
            checks = grade_human_review(
                authorized_human_case.get("human_review", {}),
                participation,
                external,
                receipt,
            )
            validation.require(
                any(
                    not check.passed
                    and check.text == "真人实际发送同时具有 participation 与 external-action 授权及双引用回执"
                    for check in checks
                ),
                f"fixture 16 真人 authorized_send 负例 {mutation_id} 必须由 Human grader 拒绝",
            )
    else:
        validation.require(False, "fixture 16 缺少真人 authorized_send 正例")

    missing_human_consent_case = participation_by_id.get("human-authorized-send-missing-external-consent", {})
    if isinstance(authorized_human_case, dict) and isinstance(missing_human_consent_case, dict):
        missing_consent_checks = grade_human_review(
            authorized_human_case.get("human_review", {}),
            authorized_human_case.get("participation_consent"),
            None,
            authorized_human_case.get("receipt"),
        )
        validation.require(
            missing_human_consent_case.get("missing") == "external_action_consent"
            and any(
                not check.passed
                and check.text == "真人实际发送同时具有 participation 与 external-action 授权及双引用回执"
                for check in missing_consent_checks
            ),
            "fixture 16 必须由 Human grader 拒绝缺任一 execution consent 的实际发送",
        )

    partial_gap_case = participation_by_id.get("partial-gap-cannot-be-hidden", {})
    if isinstance(participation_positive, dict) and isinstance(partial_gap_case, dict):
        record = copy.deepcopy(participation_positive.get("record", {}))
        receipt = copy.deepcopy(participation_positive.get("receipt"))
        assigned_questions = partial_gap_case.get("agent_payload_assigned_questions", [])
        if (
            isinstance(assigned_questions, list)
            and isinstance(record.get("agent_payloads"), list)
            and record["agent_payloads"]
            and isinstance(receipt, dict)
            and isinstance(receipt.get("operations"), list)
            and receipt["operations"]
        ):
            payload_template = record["agent_payloads"][0]
            record["agent_payloads"] = [
                {**payload_template, "assigned_question": question}
                for question in assigned_questions
            ]
            receipt["operations"][0]["conflicts_and_gaps"] = partial_gap_case.get("conflicts_and_gaps")
            checks = grade_participation_gate(
                record,
                participation_positive.get("consent"),
                receipt,
            )
            validation.require(
                any(
                    not check.passed
                    and check.text in {
                        "Participation Gate payload 只对应实际完成且唯一的任务",
                        "Participation Gate 协作回执的授权、provider、终态、任务、数量和降级真实一致",
                    }
                    for check in checks
                ),
                "fixture 16 必须由机械 grader 拒绝失败任务伪 payload 和被隐藏的 partial gap",
            )
        else:
            validation.require(False, "fixture 16 partial gap 场景无法基于正例构造机械负例")

    generic_synthesis = participation_by_id.get("generic-nonempty-synthesis-is-not-synthesis", {})
    opinion_collage = participation_by_id.get("opinion-list-plus-conclusion-is-not-synthesis", {})
    consensus_case = participation_by_id.get("agent-consensus-cannot-increase-confidence", {})
    synthesis_check = "Participation Gate 声明 synthesis_not_vote 且结构化综合绑定实际完成任务与判断闭环"
    for synthesis_case in (generic_synthesis, opinion_collage):
        if isinstance(participation_positive, dict) and isinstance(synthesis_case, dict):
            record = copy.deepcopy(participation_positive.get("record", {}))
            record["synthesis"] = copy.deepcopy(synthesis_case.get("synthesis"))
            checks = grade_participation_gate(
                record,
                participation_positive.get("consent"),
                participation_positive.get("receipt"),
            )
            validation.require(
                synthesis_case.get("mutation_target") == "record.synthesis"
                and synthesis_case.get("must_fail_check") == synthesis_check
                and any(
                    not check.passed
                    and check.severe
                    and check.text == synthesis_check
                    for check in checks
                ),
                f"fixture 16 假综合场景 {synthesis_case.get('id')} 必须由 Participation grader 机械拒绝",
            )
        else:
            validation.require(False, "fixture 16 假综合场景无法基于正例构造机械负例")
    validation.require(
        isinstance(consensus_case, dict)
        and consensus_case.get("external_evidence") is False
        and consensus_case.get("can_raise_commitment_ceiling") is False,
        "fixture 16 必须证明 Agent 一致性不能成为外部证据或提高承诺",
    )

    adapter_data = load("17-portable-adapters-and-decision-record.json")
    record = adapter_data.get("decision_record", {})
    record_checks = grade_decision_record(record)
    validation.require(all(check.passed for check in record_checks), "fixture 17 DecisionRecord 正例必须通过当前 grader")
    visible_snapshot = adapter_data.get("visible_snapshot", {})
    required_snapshot_paths = {
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
    snapshot_paths = {
        item.get("path")
        for item in visible_snapshot.values()
        if isinstance(item, dict)
    } if isinstance(visible_snapshot, dict) else set()
    validation.require(
        required_snapshot_paths == snapshot_paths,
        "fixture 17 可见快照必须逐项映射 canonical DecisionRecord，且假设与未知分别保留",
    )
    for label, item in visible_snapshot.items() if isinstance(visible_snapshot, dict) else []:
        path = item.get("path") if isinstance(item, dict) else None
        current = record
        for part in path.split(".") if isinstance(path, str) else []:
            current = current.get(part) if isinstance(current, dict) else None
        validation.require(
            isinstance(item, dict)
            and set(item) == {"path", "value", "rendered"}
            and item.get("value") == current
            and isinstance(item.get("rendered"), str)
            and bool(item["rendered"].strip()),
            f"fixture 17 可见快照字段 {label} 未完整、无损映射 {path}",
        )
    adapters = adapter_data.get("adapter_cases", [])
    adapter_by_id = {case.get("id"): case for case in adapters if isinstance(case, dict)} if isinstance(adapters, list) else {}
    required_adapter_ids = {
        "text-first-class-fallback",
        "claude-code-maps-only-observed-capabilities",
        "chatgpt-skill-only-is-text-contract",
        "authorized-persistence-requires-destination-and-consent",
    }
    validation.require(required_adapter_ids <= set(adapter_by_id), f"fixture 17 缺少场景：{sorted(required_adapter_ids - set(adapter_by_id))}")
    text_case = adapter_by_id.get("text-first-class-fallback", {})
    validation.require(
        isinstance(text_case, dict)
        and {"state_semantics", "formal_method_names", "recommendation_state", "current_value", "consent_boundaries", "decision_record", "b_feedback_routes"} <= set(text_case.get("must_preserve", []))
        and {"native_control_called", "public_search_completed", "agent_started", "record_persisted"} <= set(text_case.get("must_not_claim", [])),
        "fixture 17 纯文本 Adapter 必须完整保真且不虚构能力",
    )
    chatgpt_case = adapter_by_id.get("chatgpt-skill-only-is-text-contract", {})
    validation.require(
        isinstance(chatgpt_case, dict)
        and chatgpt_case.get("status") == "not_run"
        and chatgpt_case.get("guaranteed_surface") == "text"
        and "chatgpt_compatibility_tested" in chatgpt_case.get("must_not_claim", []),
        "fixture 17 ChatGPT Adapter 必须保持 text / not_run 证据边界",
    )
    persistence_case = adapter_by_id.get("authorized-persistence-requires-destination-and-consent", {})
    validation.require(
        isinstance(persistence_case, dict)
        and persistence_case.get("persistence", {}).get("mode") == "authorized_file"
        and {"missing_destination", "missing_consent_id"} <= set(persistence_case.get("must_fail", [])),
        "fixture 17 必须覆盖授权持久化缺少目标或 consent 的负例",
    )

    loop_data = load("18-main-evidence-loop.json")
    loop_cases = loop_data.get("cases", [])
    loop_by_id = {case.get("id"): case for case in loop_cases if isinstance(case, dict)} if isinstance(loop_cases, list) else {}
    positive_loop = loop_by_id.get("one-hypothesis-can-use-required-sequence", {})
    experiment = positive_loop.get("main_experiment", {}) if isinstance(positive_loop, dict) else {}
    validation.require(
        all(_is_nonempty_string(experiment.get(field)) for field in ("core_hypothesis", "action", "observation", "reassessment"))
        and "three_actions" in positive_loop.get("must_not_fail_as", []),
        "fixture 18 必须允许同一假设下的必要连续操作",
    )
    negative_loop = loop_by_id.get("unrelated-projects-are-not-one-loop", {})
    validation.require(
        isinstance(negative_loop, dict)
        and len(negative_loop.get("actions", [])) >= 2
        and len(negative_loop.get("hypotheses", [])) >= 2
        and {"multiple_independent_hypotheses", "multiple_unrelated_projects"} <= set(negative_loop.get("must_fail", [])),
        "fixture 18 必须拒绝把无关项目包装为一个证据闭环",
    )

    checkpoint_data = load("19-contextual-checkpoint.json")
    validation.require(
        checkpoint_data.get("contract_version") == CURRENT_CONTRACT_VERSION,
        "fixture 19 必须使用当前合同版本",
    )
    checkpoint_cases = checkpoint_data.get("cases", [])
    validation.require(isinstance(checkpoint_cases, list) and bool(checkpoint_cases), "fixture 19 必须包含检查点场景")
    if isinstance(checkpoint_cases, list):
        for case in checkpoint_cases:
            if not isinstance(case, dict):
                validation.require(False, "fixture 19 case 必须是对象")
                continue
            try:
                context = CheckpointContext.from_dict(case.get("context", {}))
                observed = case.get("observed_interaction")
                interaction = (
                    InteractionEvidence.from_dict(observed, option_contract="checkpoint")
                    if isinstance(observed, dict)
                    else None
                )
                checks = grade_checkpoint(str(case.get("assistant_text", "")), context, interaction)
            except (TypeError, ValueError) as error:
                validation.require(False, f"fixture 19 case {case.get('id')} 结构非法：{error}")
                continue
            failed = [check for check in checks if not check.passed]
            if case.get("must_pass") is True:
                validation.require(not failed, f"fixture 19 正例 {case.get('id')} 必须通过当前 checkpoint grader")
            else:
                validation.require(
                    bool(case.get("must_fail")) and bool(failed),
                    f"fixture 19 负例 {case.get('id')} 必须由当前 checkpoint grader 拒绝",
                )

    reset_cases = checkpoint_data.get("reset_cases", [])
    required_reset_changes = {
        "new-evidence",
        "purpose-change",
        "commitment-scope-expanded",
        "new-reassessment-node",
        "new-topic",
    }
    reset_changes = {
        case.get("material_change")
        for case in reset_cases
        if isinstance(case, dict)
    } if isinstance(reset_cases, list) else set()
    validation.require(
        reset_changes == required_reset_changes,
        "fixture 19 reset_cases 必须精确覆盖五种 material change",
    )
    checkpoint_positive = next(
        (
            case
            for case in checkpoint_cases
            if isinstance(case, dict) and case.get("id") == "project-initiation-native"
        ),
        None,
    ) if isinstance(checkpoint_cases, list) else None
    for reset_case in reset_cases if isinstance(reset_cases, list) else []:
        if not isinstance(reset_case, dict) or not isinstance(checkpoint_positive, dict):
            validation.require(False, "fixture 19 reset case 或基础正例结构非法")
            continue
        context_data = copy.deepcopy(checkpoint_positive.get("context", {}))
        context_data.update(
            same_decision_cooling_down=True,
            material_change=reset_case.get("material_change"),
        )
        try:
            context = CheckpointContext.from_dict(context_data)
            interaction = InteractionEvidence.from_dict(
                checkpoint_positive.get("observed_interaction", {}),
                option_contract="checkpoint",
            )
            checks = grade_checkpoint(
                str(checkpoint_positive.get("assistant_text", "")),
                context,
                interaction,
            )
        except (TypeError, ValueError) as error:
            validation.require(False, f"fixture 19 reset case {reset_case.get('id')} 结构非法：{error}")
            continue
        validation.require(
            all(check.passed for check in checks),
            f"fixture 19 reset case {reset_case.get('id')} 必须允许重新显示检查点",
        )

    viability_data = load("20-project-viability-falsification.json")
    positive = viability_data.get("positive", {})
    validation.require(
        viability_data.get("contract_version") == CURRENT_CONTRACT_VERSION,
        "fixture 20 必须使用当前合同版本",
    )
    if isinstance(positive, dict):
        checks = grade_project_viability(
            positive.get("record", {}),
            positive.get("consent_bundle"),
            positive.get("receipt_bundle"),
        )
        validation.require(all(check.passed for check in checks), "fixture 20 正例必须通过当前 PROJECT_VIABILITY grader")
    else:
        validation.require(False, "fixture 20 缺少 positive 对象")

    subtractive_cases = viability_data.get("subtractive_path_cases", [])
    expected_subtractive_ids = {
        "do-not-add-new-platform",
        "remove-redundant-approval-step",
        "keep-only-thin-connection",
        "retain-only-critical-local-gap",
        "shrink-formal-build-to-validation",
        "stop-existing-build",
    }
    subtractive_ids = {
        case.get("id")
        for case in subtractive_cases
        if isinstance(case, dict)
    } if isinstance(subtractive_cases, list) else set()
    validation.require(
        subtractive_ids == expected_subtractive_ids
        and len(subtractive_cases) == len(expected_subtractive_ids),
        "fixture 20 必须精确覆盖不新增、删除/简化、薄连接、局部补充、缩小投入和停止路径",
    )
    expected_subtractive_pairs = {
        "do-not-add-new-platform": ("status_quo", "hold"),
        "remove-redundant-approval-step": ("manual_or_process", "adopt"),
        "keep-only-thin-connection": ("plugin_script_or_thin_integration", "thin_integration"),
        "retain-only-critical-local-gap": ("local_supplement", "combine"),
        "shrink-formal-build-to-validation": ("local_supplement", "limited_validation"),
        "stop-existing-build": ("independent_build", "stop"),
    }
    actual_subtractive_pairs = {
        case.get("id"): (
            case.get("mapped_candidate_category"),
            case.get("mapped_direction"),
        )
        for case in subtractive_cases
        if isinstance(case, dict)
    } if isinstance(subtractive_cases, list) else {}
    validation.require(
        isinstance(subtractive_cases, list)
        and "subtractive_solution" not in PROJECT_CANDIDATE_CATEGORIES
        and actual_subtractive_pairs == expected_subtractive_pairs
        and all(
            isinstance(case, dict)
            and case.get("must_not_create_new_category") is True
            for case in subtractive_cases
        ),
        "fixture 20 减法路径必须区分方案机制与投入动作并复用现有类别，不得新增 subtractive_solution",
    )

    mutations = viability_data.get("mutations", [])
    validation.require(isinstance(mutations, list) and bool(mutations), "fixture 20 必须包含单变量负例")
    expected_mutation_ids = {
        "focal-solution-not-candidate",
        "validation-layer-merged-or-missing",
        "search-pass-order-reversed",
        "material-category-missing",
        "completed-search-empty-sources",
        "dangling-evidence-source",
        "strongest-alternative-mismatch",
        "trial-not-performed-but-build",
        "search-provider-mismatch",
        "search-scope-mismatch",
        "search-failed-without-fallback-but-claimed-complete",
        "adversarial-payload-extra-key",
        "adversarial-failed-without-trace-but-build",
        "layer-supported-with-unknown-evidence",
        "layer-supported-with-opposing-evidence",
        "trial-evidence-direction-reversed",
        "commitment-unrelated-source-backed",
        "adversarial-missing-agent-counts",
        "adversarial-wrong-completed-task",
        "adversarial-hidden-failed-task",
        "chosen-rank-over-ceiling",
        "source-less-material-cannot-support-build",
        "dangling-no-go-reference",
        "dangling-reassessment-reference",
    }
    mutation_ids = {
        mutation.get("id")
        for mutation in mutations
        if isinstance(mutation, dict)
    } if isinstance(mutations, list) else set()
    validation.require(
        mutation_ids == expected_mutation_ids and len(mutations) == len(expected_mutation_ids),
        "fixture 20 必须精确保留完整且唯一的单变量 mutation 集合",
    )
    for mutation in mutations if isinstance(mutations, list) else []:
        if not isinstance(mutation, dict) or not isinstance(positive, dict):
            validation.require(False, "fixture 20 mutation 必须是对象")
            continue
        record = copy.deepcopy(positive.get("record", {}))
        consents = copy.deepcopy(positive.get("consent_bundle"))
        receipt = copy.deepcopy(positive.get("receipt_bundle"))
        mutation_id = mutation.get("id")
        mutators = {
            "focal-solution-not-candidate": lambda: record["focal_solution"].update(status="accepted_solution"),
            "validation-layer-merged-or-missing": lambda: record["validation_layers"].pop("alternative_ecosystem"),
            "search-pass-order-reversed": lambda: record["search_passes"].reverse(),
            "material-category-missing": lambda: record["candidates"].pop(),
            "completed-search-empty-sources": lambda: receipt["operations"][0].update(sources=[]),
            "dangling-evidence-source": lambda: record["evidence_items"][0].update(source_ids=["missing-source"]),
            "strongest-alternative-mismatch": lambda: record.update(strongest_alternative_id="candidate-10"),
            "trial-not-performed-but-build": lambda: record["alternative_trial"].update(status="not_performed", result="unknown", consent_ids=[], receipt_ids=[], reason="未执行"),
            "search-provider-mismatch": lambda: receipt["operations"][0].update(provider="other-provider"),
            "search-scope-mismatch": lambda: receipt["operations"][0].update(scope=["unauthorized"]),
            "search-failed-without-fallback-but-claimed-complete": lambda: receipt["operations"][0].update(status="failed"),
            "adversarial-payload-extra-key": lambda: record["adversarial_review"]["payload"].update(main_judgment="自研"),
            "adversarial-failed-without-trace-but-build": lambda: record["adversarial_review"].update(status="failed", payload=None, reason="失败"),
            "layer-supported-with-unknown-evidence": lambda: record["evidence_items"][0].update(state="unknown"),
            "layer-supported-with-opposing-evidence": lambda: record["evidence_items"][0].update(state="opposes"),
            "trial-evidence-direction-reversed": lambda: record["evidence_items"][4].update(state="supports"),
            "commitment-unrelated-source-backed": lambda: record["commitment"].update(evidence_item_ids=["e-fit"]),
            "adversarial-missing-agent-counts": lambda: receipt["operations"][3].pop("agent_counts"),
            "adversarial-wrong-completed-task": lambda: receipt["operations"][3].update(completed_tasks=["其他任务"]),
            "adversarial-hidden-failed-task": lambda: receipt["operations"][3].update(failed_tasks=["独立挑战正式自研必要性"]),
            "chosen-rank-over-ceiling": lambda: record["validation_layers"]["alternative_ecosystem"].update(status="unknown"),
            "source-less-material-cannot-support-build": lambda: record["commitment"].update(evidence_item_ids=["e-trial", "e-adversarial"]),
            "dangling-no-go-reference": lambda: record["no_go_conditions"][0].update(evidence_item_ids=["missing"]),
            "dangling-reassessment-reference": lambda: record["reassessment_triggers"][0].update(evidence_item_ids=["missing"]),
        }
        mutator = mutators.get(mutation_id)
        validation.require(mutator is not None, f"fixture 20 含未知 mutation：{mutation_id}")
        if mutator is None:
            continue
        mutator()
        checks = grade_project_viability(record, consents, receipt)
        validation.require(
            any(not check.passed and check.severe for check in checks),
            f"fixture 20 负例 {mutation_id} 必须产生严重失败",
        )


def validate_evals(validation: Validation) -> None:
    evals_path = SKILL_DIR / "evals" / "evals.json"
    validation.require(evals_path.exists(), "缺少 evals/evals.json")
    if evals_path.exists():
        data = json.loads(evals_path.read_text(encoding="utf-8"))
        validation.require(data.get("skill_name") == "think-it-through", "evals.json 的 skill_name 不匹配")
        validation.require(
            data.get("benchmark_profile") == LEGACY_BEHAVIOR_PROFILE,
            "evals.json 必须明确标记为冻结的 legacy-v0.1 行为评测",
        )
        validation.require(
            CURRENT_CONTRACT_VERSION in str(data.get("notice", "")) and "重解释" in str(data.get("notice", "")),
            f"evals.json 必须说明旧 benchmark 不得由 v{CURRENT_CONTRACT_VERSION} 重解释",
        )
        evals = data.get("evals", [])
        validation.require(bool(evals), "evals.json 至少需要一个行为评测")
        ids = [item.get("id") for item in evals if isinstance(item, dict)]
        validation.require(len(ids) == len(set(ids)), "eval ID 必须唯一")
        for item in evals:
            if not isinstance(item, dict):
                validation.require(False, "eval 项必须是对象")
                continue
            for key in ("id", "prompt", "expected_output", "files", "expectations"):
                validation.require(key in item, f"eval {item.get('id')} 缺少字段 {key}")

    trigger_dir = SKILL_DIR / "evals"
    for name in ("trigger-dev.json", "trigger-holdout.json"):
        path = trigger_dir / name
        validation.require(path.exists(), f"缺少 {name}")
        if path.exists():
            rows = json.loads(path.read_text(encoding="utf-8"))
            validation.require(isinstance(rows, list) and rows, f"{name} 必须是非空数组")
            if isinstance(rows, list):
                positives = sum(row.get("should_trigger") is True for row in rows if isinstance(row, dict))
                negatives = sum(row.get("should_trigger") is False for row in rows if isinstance(row, dict))
                validation.require(
                    positives >= MIN_TRIGGER_EXAMPLES_PER_LABEL,
                    f"{name} 至少需要 {MIN_TRIGGER_EXAMPLES_PER_LABEL} 个正样本，当前为 {positives}",
                )
                validation.require(
                    negatives >= MIN_TRIGGER_EXAMPLES_PER_LABEL,
                    f"{name} 至少需要 {MIN_TRIGGER_EXAMPLES_PER_LABEL} 个负样本，当前为 {negatives}",
                )
                groups = [row.get("group") for row in rows if isinstance(row, dict)]
                validation.require(all(isinstance(group, str) and group for group in groups), f"{name} 每条样本必须有 group")
                queries = [row.get("query") for row in rows if isinstance(row, dict)]
                validation.require(len(queries) == len(set(queries)), f"{name} 不得包含重复 query")

    fixture_paths = sorted((trigger_dir / "fixtures").glob("*.json"))
    expected_fixtures = {f"{index:02d}-{name}" for index, name in (
        (1, "product-misalignment.json"),
        (2, "background-not-confirmation.json"),
        (3, "cancel-method.json"),
        (4, "partnership-safety.json"),
        (5, "direct-and-emergency.json"),
        (6, "authorization-and-degradation.json"),
        (7, "method-routing.json"),
        (8, "interactive-method-adjustment.json"),
        (9, "purpose-text-overrides-choice.json"),
        (10, "a-answer-shapes.json"),
        (11, "b-experiment-and-feedback.json"),
        (12, "native-control-and-fallback.json"),
        (13, "purpose-coexistence-and-priority.json"),
        (14, "inline-method-recommendation.json"),
        (15, "evidence-gate.json"),
        (16, "participation-and-human.json"),
        (17, "portable-adapters-and-decision-record.json"),
        (18, "main-evidence-loop.json"),
        (19, "contextual-checkpoint.json"),
        (20, "project-viability-falsification.json"),
    )}
    actual_fixtures = {path.name for path in fixture_paths}
    validation.require(
        expected_fixtures <= actual_fixtures,
        f"缺少 v{CURRENT_CONTRACT_VERSION} fixture：{sorted(expected_fixtures - actual_fixtures)}",
    )
    for path in fixture_paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        validation.require(
            data.get("contract_version") == CURRENT_CONTRACT_VERSION,
            f"fixture {path.name} 的 contract_version 必须为 {CURRENT_CONTRACT_VERSION}",
        )
        if path.name in SPECIALIZED_FIXTURE_FILES:
            continue
        turns = data.get("turns", data.get("cases", []))
        validation.require(isinstance(turns, list) and bool(turns), f"fixture {path.name} 没有 turns 或 cases")
        if not isinstance(turns, list):
            continue
        for index, turn in enumerate(turns, start=1):
            validation.require(isinstance(turn, dict), f"fixture {path.name} 第 {index} 项必须是对象")
            if not isinstance(turn, dict):
                continue
            stage = turn.get("expected_stage")
            validation.require(stage in EXPECTED_FIXTURE_STAGES, f"fixture {path.name} 含非法阶段：{stage}")
            if stage == "Gate-routing":
                validation.require(
                    turn.get("expected_interaction") is None,
                    f"fixture {path.name} 第 {index} 个 Gate-routing 项不得提前携带 B 反馈交互",
                )
                validation.require(
                    turn.get("next_stage") in {"Evidence Gate", "Participation Gate", "B"},
                    f"fixture {path.name} 第 {index} 个 Gate-routing 项必须给出一个确定 next_stage",
                )
                continue
            if stage not in INTERACTIVE_FIXTURE_STAGES or path.name in {
                "07-method-routing.json",
                "12-native-control-and-fallback.json",
            }:
                continue

            if "invalid_assistant_shape" in turn:
                validation.require(
                    isinstance(turn.get("invalid_assistant_shape"), str)
                    and bool(turn["invalid_assistant_shape"].strip()),
                    f"fixture {path.name} 第 {index} 个负例缺少 invalid_assistant_shape",
                )
                validation.require(
                    isinstance(turn.get("must_fail"), list)
                    and bool(turn["must_fail"]),
                    f"fixture {path.name} 第 {index} 个负例缺少 must_fail",
                )
                continue

            host_capabilities = turn.get("host_capabilities")
            expected_interaction = turn.get("expected_interaction")
            validation.require(
                isinstance(host_capabilities, dict),
                f"fixture {path.name} 第 {index} 个 {stage} 项缺少 host_capabilities",
            )
            validation.require(
                isinstance(expected_interaction, dict),
                f"fixture {path.name} 第 {index} 个 {stage} 项缺少 expected_interaction",
            )
            if not isinstance(host_capabilities, dict) or not isinstance(expected_interaction, dict):
                continue

            selection_control = host_capabilities.get("selection_control")
            host_free_text = host_capabilities.get("host_free_text")
            validation.require(
                selection_control in EXPECTED_HOST_CONTROL_STATUSES,
                f"fixture {path.name} 第 {index} 项 selection_control 非法：{selection_control}",
            )
            validation.require(
                isinstance(host_free_text, bool),
                f"fixture {path.name} 第 {index} 项 host_free_text 必须为布尔值",
            )

            surface = expected_interaction.get("surface")
            selection_mode = expected_interaction.get("selection_mode")
            tool_call_observed = expected_interaction.get("tool_call_observed")
            host_control_status = expected_interaction.get(
                "host_control_status",
                selection_control,
            )
            supplement_mode = expected_interaction.get("supplement_mode", "none")
            validation.require(
                surface in EXPECTED_INTERACTION_SURFACES.get(str(stage), set()),
                f"fixture {path.name} 第 {index} 个 {stage} 项交互 surface 非法：{surface}",
            )
            validation.require(
                selection_mode in EXPECTED_SELECTION_MODES,
                f"fixture {path.name} 第 {index} 项 selection_mode 非法：{selection_mode}",
            )
            validation.require(
                isinstance(tool_call_observed, bool),
                f"fixture {path.name} 第 {index} 项 tool_call_observed 必须为布尔值",
            )
            validation.require(
                host_control_status in EXPECTED_HOST_CONTROL_STATUSES,
                f"fixture {path.name} 第 {index} 项 host_control_status 非法：{host_control_status}",
            )
            validation.require(
                supplement_mode in EXPECTED_SUPPLEMENT_MODES,
                f"fixture {path.name} 第 {index} 项 supplement_mode 非法：{supplement_mode}",
            )
            validation.require(
                host_control_status == selection_control,
                f"fixture {path.name} 第 {index} 项宿主状态与交互证据不一致："
                f"{selection_control} != {host_control_status}",
            )

            if stage in {"R", "A"}:
                answer_shape = turn.get("answer_shape")
                allowed_shapes = set(EXPECTED_ANSWER_SHAPES)
                if stage == "A":
                    allowed_shapes.remove("compatible-set")
                validation.require(
                    answer_shape in allowed_shapes,
                    f"fixture {path.name} 第 {index} 个 {stage} 项 answer_shape 非法：{answer_shape}",
                )
                if answer_shape in EXPECTED_ANSWER_SHAPES:
                    expected_mode, expected_surfaces = EXPECTED_ANSWER_SHAPES[answer_shape]
                    validation.require(
                        selection_mode == expected_mode and surface in expected_surfaces,
                        f"fixture {path.name} 第 {index} 项答案形态 {answer_shape} 应为 "
                        f"{sorted(expected_surfaces)}:{expected_mode}，当前为 {surface}:{selection_mode}",
                    )
                validation.require(
                    expected_interaction.get("semantic_paragraphs") is True,
                    f"fixture {path.name} 第 {index} 个 {stage} 项必须声明 semantic_paragraphs=true",
                )
                validation.require(
                    expected_interaction.get("question_is_last_paragraph") is True,
                    f"fixture {path.name} 第 {index} 个 {stage} 项必须声明 question_is_last_paragraph=true",
                )
                validation.require(
                    supplement_mode == "none",
                    f"fixture {path.name} 第 {index} 个 R/A 项必须使用 supplement_mode=none",
                )
                if surface in {"native-control", "text-fallback"}:
                    validation.require(
                        expected_interaction.get("option_labels_parallel") is True,
                        f"fixture {path.name} 第 {index} 个选择项必须声明 option_labels_parallel=true",
                    )
            elif stage == "B":
                validation.require(
                    selection_mode == "single",
                    f"fixture {path.name} 第 {index} 个 B 项必须使用 single",
                )
                validation.require(
                    expected_interaction.get("semantic_paragraphs") is True,
                    f"fixture {path.name} 第 {index} 个 B 项必须声明 semantic_paragraphs=true",
                )
                validation.require(
                    expected_interaction.get("main_loop_roles_separate_paragraphs") is True,
                    f"fixture {path.name} 第 {index} 个 B 项必须声明主现实闭环的四个语义角色分别成段",
                )
                validation.require(
                    expected_interaction.get("question_is_last_paragraph") is True,
                    f"fixture {path.name} 第 {index} 个 B 项必须声明 question_is_last_paragraph=true",
                )
                validation.require(
                    tuple(expected_interaction.get("options", [])) == FEEDBACK_OPTIONS,
                    f"fixture {path.name} 第 {index} 个 B 项必须使用四个稳定反馈方向",
                )

            if surface == "native-control":
                validation.require(selection_control == "available", f"fixture {path.name} 原生控件必须声明宿主可用")
                validation.require(tool_call_observed is True, f"fixture {path.name} 原生控件必须观察到工具调用")
                validation.require(selection_mode in {"multi", "single"}, f"fixture {path.name} 原生控件必须声明 single 或 multi")
                validation.require(host_free_text is True, f"fixture {path.name} 原生控件场景必须保留宿主自由输入")
                validation.require(
                    expected_interaction.get("host_free_text_available") is True,
                    f"fixture {path.name} 原生控件预期必须声明 host_free_text_available=true",
                )
                if stage in {"R", "A"}:
                    validation.require(
                        expected_interaction.get("product_other_forbidden") is True,
                        f"fixture {path.name} 原生控件预期必须禁止产品自建 Other",
                    )
                else:
                    question_text = expected_interaction.get("question_text", "")
                    validation.require(
                        supplement_mode in {"native-note", "follow-up-message"},
                        f"fixture {path.name} 原生 B 必须声明可观察的补充通道",
                    )
                    validation.require(
                        isinstance(question_text, str)
                        and len(re.findall(r"[?？]", question_text)) == 1
                        and question_text.rstrip().endswith(("?", "？")),
                        f"fixture {path.name} 原生 B 必须只有一个末尾反馈问号",
                    )
                    validation.require(
                        expected_interaction.get("product_option_count") == 4,
                        f"fixture {path.name} 原生 B 必须声明四个产品反馈方向",
                    )
            elif surface == "text-fallback":
                validation.require(
                    selection_control in {"unavailable", "failed", "rejected"},
                    f"fixture {path.name} 文本降级只能发生在控件不可用、失败或被拒绝后",
                )
                expected_call = selection_control in {"failed", "rejected"}
                validation.require(
                    tool_call_observed is expected_call,
                    f"fixture {path.name} 文本降级调用 trace 不真实："
                    f"status={selection_control}，tool_call={tool_call_observed}",
                )
                validation.require(selection_mode in {"multi", "single"}, f"fixture {path.name} 文本降级必须保留选择语义")
                validation.require(
                    supplement_mode == ("inline-text" if stage == "B" else "none"),
                    f"fixture {path.name} 文本降级 supplement_mode 与阶段不匹配",
                )
            elif surface == "free-answer":
                validation.require(stage in {"R", "A"}, f"fixture {path.name} 只有 R/A 可使用 free-answer")
                validation.require(tool_call_observed is False and selection_mode == "none", f"fixture {path.name} 开放 R/A 不得调用选择控件")
                validation.require(turn.get("answer_shape") == "open", f"fixture {path.name} free-answer 必须声明 answer_shape=open")

    method_adjustment_fixture = trigger_dir / "fixtures" / "08-interactive-method-adjustment.json"
    if method_adjustment_fixture.exists():
        method_adjustment_data = json.loads(
            method_adjustment_fixture.read_text(encoding="utf-8")
        )
        fallback_cases = method_adjustment_data.get("fallback_cases", [])
        fallback_by_status = {
            case.get("host_control_status"): case
            for case in fallback_cases
            if isinstance(case, dict)
        } if isinstance(fallback_cases, list) else {}
        validation.require(
            set(fallback_by_status) == {"unavailable", "failed", "rejected"}
            and len(fallback_cases) == 3,
            "fixture 08 必须分别覆盖 unavailable、failed 与 rejected 方法控件降级",
        )
        for status, case in fallback_by_status.items():
            validation.require(
                case.get("surface") == "text-fallback"
                and case.get("selection_mode") == "multi"
                and case.get("supplement_mode") == "none"
                and case.get("tool_call_observed")
                is (status in {"failed", "rejected"})
                and case.get("must_preserve_selection_semantics") is True
                and case.get("must_preserve_structured_method_meaning") is True
                and case.get("must_not_retry_same_call") is True,
                f"fixture 08 的 {status} 降级必须保留真实调用 trace、选择语义且不原样重试",
            )
            try:
                from grade_contracts import InteractionEvidence

                InteractionEvidence.from_dict(case)
            except (ImportError, ValueError) as error:
                validation.require(
                    False,
                    f"fixture 08 的 {status} 降级交互证据不可执行：{error}",
                )

    authorization_fixture = trigger_dir / "fixtures" / "06-authorization-and-degradation.json"
    if authorization_fixture.exists():
        authorization_data = json.loads(authorization_fixture.read_text(encoding="utf-8"))
        authorization_turns = authorization_data.get("turns", [])
        authorization_by_id = {
            turn.get("id"): turn
            for turn in authorization_turns
            if isinstance(turn, dict) and turn.get("id")
        } if isinstance(authorization_turns, list) else {}
        gate_to_evidence = authorization_by_id.get("gate-routing-to-evidence", {})
        gate_to_b = authorization_by_id.get("gate-routing-to-b", {})
        expected_gate = gate_to_evidence.get("expected_gate", {})
        validation.require(
            gate_to_evidence.get("expected_stage") == "Gate-routing"
            and gate_to_evidence.get("next_stage") == "Evidence Gate"
            and gate_to_evidence.get("expected_interaction") is None
            and isinstance(expected_gate, dict)
            and expected_gate.get("consent_type") == "capability_call"
            and expected_gate.get("wait_for_user") is True
            and all(
                isinstance(expected_gate.get(field), str)
                and bool(expected_gate[field].strip())
                for field in (
                    "decision",
                    "evidence_question",
                    "stop_condition",
                    "provider",
                    "cost_and_delay",
                    "fallback",
                )
            ),
            "fixture 06 必须把 Gate-routing→Evidence Gate 定义为具体授权入口，且不得提前显示 B 反馈",
        )
        validation.require(
            gate_to_b.get("expected_stage") == "Gate-routing"
            and gate_to_b.get("next_stage") == "B"
            and gate_to_b.get("expected_interaction") is None
            and {
                "conditional_judgment",
                "one_main_reality_experiment",
                "lossless_decision_snapshot",
                "feedback_only_after-complete-b",
            }
            <= set(gate_to_b.get("b_requirements", [])),
            "fixture 06 必须把 Gate-routing→B 定义为先完成判断、闭环和快照，再进入反馈",
        )

    native_fixture = trigger_dir / "fixtures" / "12-native-control-and-fallback.json"
    snapshot_fixture = trigger_dir / "fixtures" / "17-portable-adapters-and-decision-record.json"
    if native_fixture.exists():
        native_data = json.loads(native_fixture.read_text(encoding="utf-8"))
        snapshot_data = (
            json.loads(snapshot_fixture.read_text(encoding="utf-8"))
            if snapshot_fixture.exists()
            else {}
        )
        canonical_record = snapshot_data.get("decision_record")
        canonical_snapshot = snapshot_data.get("visible_snapshot")
        native_cases = native_data.get("cases", []) if isinstance(native_data, dict) else []
        native_case_ids = {
            case.get("id")
            for case in native_cases
            if isinstance(case, dict)
        }
        required_native_cases = {
            "available-host-rejects-markdown-only",
            "unavailable-host-allows-text-fallback",
            "failed-control-allows-text-fallback",
            "product-created-other-is-invalid",
            "host-native-other-is-valid",
            "selection-does-not-grant-authorization",
            "b-native-follow-up-message",
            "b-native-note-synthetic-contract",
            "b-unavailable-text-fallback",
            "b-failed-text-fallback",
            "b-rejected-text-fallback",
            "b-pseudo-radio-is-invalid",
            "b-host-other-is-not-native-note",
            "b-feedback-does-not-authorize-action",
        }
        validation.require(
            required_native_cases <= native_case_ids,
            f"fixture 12 缺少原生交互边界：{sorted(required_native_cases - native_case_ids)}",
        )
        for case in native_cases:
            if not isinstance(case, dict):
                continue
            observed = case.get("observed_interaction")
            validation.require(isinstance(observed, dict), f"fixture 12 case {case.get('id')} 缺少 observed_interaction")
            if not isinstance(observed, dict):
                continue
            try:
                from grade_contracts import InteractionEvidence

                InteractionEvidence.from_dict(observed)
            except (ImportError, ValueError) as error:
                validation.require(False, f"fixture 12 case {case.get('id')} 的 observed_interaction 非法：{error}")
            else:
                validation.require(True, f"fixture 12 case {case.get('id')} 交互证据可解析")

        b_cases = [
            case
            for case in native_cases
            if isinstance(case, dict) and case.get("expected_stage") == "B"
        ]
        validation.require(len(b_cases) == 8, f"fixture 12 应包含 8 个 B 能力用例，当前为 {len(b_cases)}")
        for case in b_cases:
            case_id = case.get("id")
            observed = case.get("observed_interaction", {})
            assistant_shape = case.get("assistant_shape")
            validation.require(
                isinstance(assistant_shape, list)
                and bool(assistant_shape)
                and all(isinstance(line, str) for line in assistant_shape),
                f"fixture 12 B case {case_id} 缺少可执行 assistant_shape",
            )
            case_record = case.get("decision_record")
            case_snapshot = case.get("visible_snapshot")
            validation.require(
                case_record == canonical_record and case_snapshot == canonical_snapshot,
                f"fixture 12 B case {case_id} 必须绑定 canonical DecisionRecord 与无损可见快照",
            )
            status = observed.get("host_control_status") if isinstance(observed, dict) else None
            surface = observed.get("surface") if isinstance(observed, dict) else None
            tool_call = observed.get("tool_call_observed") if isinstance(observed, dict) else None
            mode = observed.get("selection_mode") if isinstance(observed, dict) else None
            supplement = observed.get("supplement_mode") if isinstance(observed, dict) else None
            validation.require(mode == "single", f"fixture 12 B case {case_id} 必须使用 single")
            if status == "available":
                validation.require(
                    surface == "native-control" and tool_call is True
                    and supplement in {"native-note", "follow-up-message"},
                    f"fixture 12 B case {case_id} 不符合原生反馈能力矩阵",
                )
                validation.require(
                    tuple(observed.get("options", [])) == FEEDBACK_OPTIONS,
                    f"fixture 12 B case {case_id} 缺少四个稳定反馈方向",
                )
            elif status == "unavailable":
                validation.require(
                    surface == "text-fallback" and tool_call is False and supplement == "inline-text",
                    f"fixture 12 B case {case_id} 不符合 unavailable 降级矩阵",
                )
            elif status in {"failed", "rejected"}:
                validation.require(
                    surface == "text-fallback" and tool_call is True and supplement == "inline-text",
                    f"fixture 12 B case {case_id} 不符合 failed/rejected 降级矩阵",
                )
            else:
                validation.require(False, f"fixture 12 B case {case_id} 宿主状态非法：{status}")
            if case.get("must_pass"):
                validation.require(
                    not case.get("must_fail"),
                    f"fixture 12 B case {case_id} 不得同时声明 must_pass 与 must_fail",
                )
            else:
                validation.require(bool(case.get("must_fail")), f"fixture 12 B 负例 {case_id} 缺少 must_fail")

    feedback_fixture = trigger_dir / "fixtures" / "11-b-experiment-and-feedback.json"
    if feedback_fixture.exists():
        feedback_data = json.loads(feedback_fixture.read_text(encoding="utf-8"))
        feedback_routes = feedback_data.get("feedback_routes", []) if isinstance(feedback_data, dict) else []
        try:
            from grade_contracts import resolve_b_feedback_route
        except ImportError as error:
            validation.require(False, f"无法加载 B 反馈 canonical resolver：{error}")
        else:
            route_keys = [
                (route.get("direction_id"), route.get("supplement_type"))
                for route in feedback_routes
                if isinstance(route, dict)
            ]
            required_route_keys = {
                ("accept", "none"),
                ("set-aside", "none"),
                ("adjust-next-step", "none"),
                ("disagree", "none"),
                ("accept", "new-fact"),
                ("accept", "purpose-change"),
            }
            validation.require(
                required_route_keys <= set(route_keys)
                and len(route_keys) == len(set(route_keys)),
                "fixture 11 缺少 B 反馈结束、等待补充、不同意或文字优先转移，或存在重复路由",
            )
            for route in feedback_routes:
                if not isinstance(route, dict):
                    validation.require(False, "fixture 11 的 feedback_routes 必须全部是对象")
                    continue
                try:
                    resolved = resolve_b_feedback_route(
                        route.get("direction_id"),
                        route.get("supplement_type"),
                    )
                except ValueError as error:
                    validation.require(False, f"fixture 11 含非法 B 反馈路由：{error}")
                    continue
                validation.require(
                    (
                        route.get("expected_stage"),
                        route.get("preserve_judgment"),
                        route.get("text_overrode_selection"),
                    )
                    == (
                        resolved.next_stage,
                        resolved.preserve_judgment,
                        resolved.text_overrode_selection,
                    ),
                    "fixture 11 的 B 反馈路由必须与 canonical resolver 一致："
                    f"{route.get('direction_id')}+{route.get('supplement_type')}",
                )
        validation.require(
            all(
                isinstance(route, dict) and route.get("authorization_effect") == "none"
                for route in feedback_routes
            ),
            "fixture 11 的反馈转移不得扩张授权",
        )

    validate_specialized_fixtures(validation, trigger_dir / "fixtures")

    ux_evals_path = trigger_dir / "ux-evals.json"
    ux_rubric_path = trigger_dir / "ux-rubric.md"
    enhancement_rubric_path = trigger_dir / "enhancement-rubric.md"
    checkpoint_evals_path = trigger_dir / "contextual-checkpoint-evals.json"
    validation.require(ux_evals_path.exists(), "缺少 evals/ux-evals.json")
    validation.require(ux_rubric_path.exists(), "缺少 evals/ux-rubric.md")
    validation.require(enhancement_rubric_path.exists(), "缺少 evals/enhancement-rubric.md")
    validation.require(checkpoint_evals_path.exists(), "缺少 evals/contextual-checkpoint-evals.json")
    if checkpoint_evals_path.exists():
        checkpoint_evals = json.loads(checkpoint_evals_path.read_text(encoding="utf-8"))
        validation.require(
            checkpoint_evals.get("contract_version") == CURRENT_CONTRACT_VERSION,
            "contextual-checkpoint-evals.json 版本不匹配",
        )
        validation.require(
            checkpoint_evals.get("status") == "not_run",
            "contextual-checkpoint-evals.json 必须如实保持 not_run",
        )
        validation.require(
            checkpoint_evals.get("fixture") == "fixtures/19-contextual-checkpoint.json",
            "contextual-checkpoint-evals.json 必须绑定 fixture 19",
        )
        tracks = checkpoint_evals.get("tracks", [])
        validation.require(
            isinstance(tracks, list)
            and {track.get("id") for track in tracks if isinstance(track, dict)}
            == {"preloaded-behavior", "natural-discovery"}
            and all(track.get("status") == "not_run" for track in tracks if isinstance(track, dict)),
            "contextual-checkpoint-evals.json 必须精确区分已加载行为与自然发现并保持 not_run",
        )
        episodes = [
            episode
            for track in tracks
            if isinstance(track, dict)
            for episode in track.get("episodes", [])
            if isinstance(episode, dict)
        ] if isinstance(tracks, list) else []
        validation.require(
            {episode.get("id") for episode in episodes}
            == {
                "high-value-node-offer-once",
                "continue-cools-same-decision",
                "material-change-can-reopen",
                "explicit-and-active-flow-bypass",
                "close-negatives-stay-out",
                "natural-language-loading-boundary",
            },
            "contextual-checkpoint-evals.json 场景集合不完整",
        )
        validation.require(
            all(
                isinstance(episode.get("turns"), list)
                and bool(episode["turns"])
                and isinstance(episode.get("must_observe"), list)
                and bool(episode["must_observe"])
                for episode in episodes
            ),
            "contextual-checkpoint-evals.json 每个 episode 都必须定义 turns 与 must_observe",
        )
        validation.require(
            set(checkpoint_evals.get("report_fields", []))
            >= {
                "runtime",
                "runtime_version",
                "skill_revision",
                "loading_observed",
                "interaction_surface",
                "tool_trace",
                "cooldown_observed",
                "reset_reason",
                "unexpected_capability_or_consent",
                "result",
                "reviewer",
            },
            "contextual-checkpoint-evals.json 缺少真实运行报告字段",
        )

    if ux_evals_path.exists():
        ux_data = json.loads(ux_evals_path.read_text(encoding="utf-8"))
        validation.require(ux_data.get("contract_version") == CURRENT_CONTRACT_VERSION, "ux-evals.json 版本不匹配")
        validation.require(ux_data.get("status") == "not_run", "未执行体验评测时 ux-evals.json 必须标记 not_run")
        validation.require(ux_data.get("rubric") == "ux-rubric.md", "ux-evals.json 必须绑定核心 UX rubric")
        validation.require(ux_data.get("enhancement_rubric") == "enhancement-rubric.md", "ux-evals.json 必须绑定增强 UX rubric")
        ux_evals = ux_data.get("evals", [])
        validation.require(isinstance(ux_evals, list) and len(ux_evals) >= 5, "ux-evals.json 至少需要 5 个体验场景")
        if isinstance(ux_evals, list):
            ux_ids = {
                item.get("id")
                for item in ux_evals
                if isinstance(item, dict)
            }
            required_new_ux_ids = {
                "ux-subtractive-alternative",
                "ux-analysis-sufficiency-stop",
                "ux-self-assessment-evidence-boundary",
                "ux-gate-chaining",
                "ux-capability-decline-versus-flow-stop",
                "ux-a-waits-for-answer",
                "ux-zero-method",
                "ux-compact-b",
                "ux-hold-pause-stop-action",
                "ux-subtractive-not-material",
                "ux-human-authorized-send",
            }
            validation.require(
                required_new_ux_ids <= ux_ids,
                f"ux-evals.json 缺少 current UX 边界场景：{sorted(required_new_ux_ids - ux_ids)}",
            )
            validation.require(
                len(ux_ids) == len(ux_evals)
                and all(isinstance(item, dict) and _is_nonempty_string(item.get("id")) for item in ux_evals),
                "ux-evals.json 的 eval ID 必须非空且唯一",
            )
            for item in ux_evals:
                if not isinstance(item, dict):
                    validation.require(False, "UX eval 项必须是对象")
                    continue
                validation.require(
                    _is_nonempty_string(item.get("prompt"))
                    and _is_nonempty_string(item.get("expected_experience")),
                    f"UX eval {item.get('id')} 必须提供非空 prompt 与 expected_experience",
                )
                validation.require(
                    item.get("status") == "not_run",
                    f"UX eval {item.get('id')} 未执行时必须显式标记 status=not_run",
                )
                validation.require(
                    "score" not in item or item.get("score") is None,
                    f"UX eval {item.get('id')} 未执行时不得预填分数",
                )
                fixture = item.get("fixture")
                validation.require(
                    isinstance(fixture, str) and (trigger_dir / fixture).exists(),
                    f"UX eval {item.get('id')} 引用 fixture 不存在：{fixture}",
                )
                expected_interaction = item.get("expected_interaction")
                validation.require(
                    isinstance(expected_interaction, str) and bool(expected_interaction.strip()),
                    f"UX eval {item.get('id')} 缺少 expected_interaction",
                )
        ux_interactions = "\n".join(
            str(item.get("expected_interaction", ""))
            for item in ux_evals
            if isinstance(item, dict)
        ) if isinstance(ux_evals, list) else ""
        for required_interaction in (
            "native-control:multi",
            "native-control:single",
            "free-answer:none",
            "text-fallback:multi",
            "native-control:single+follow-up-message",
            "native-control:single+native-note",
            "text-fallback:single+inline-text",
            "native-control:multi+structured-options",
            "native-control:single+participation-consent",
            "evidence-receipt -> B",
            "delegation-receipt -> synthesis -> B",
            "human-review-draft:none",
            "text:not_run",
        ):
            validation.require(
                required_interaction in ux_interactions,
                f"ux-evals.json 缺少交互形态：{required_interaction}",
            )
        ux_by_id = {
            str(item.get("id")): item
            for item in ux_evals
            if isinstance(item, dict) and _is_nonempty_string(item.get("id"))
        } if isinstance(ux_evals, list) else {}
        expected_case_phrases = {
            "ux-gate-chaining": ("Gate-routing", "同一 Gate 不围绕同一未知重复"),
            "ux-capability-decline-versus-flow-stop": ("只拒绝某项能力", "不输出完整 B"),
            "ux-a-waits-for-answer": ("继续等待 A", "不使用分析停止规则跳过 A"),
            "ux-zero-method": ("不显示空菜单", "直接进入 A"),
            "ux-compact-b": ("紧凑 B", "不输出‘无冲突’‘无搁置’"),
            "ux-hold-pause-stop-action": ("不新增投入", "非空自然动作"),
            "ux-subtractive-not-material": ("不把它作为 material 候选", "不等于每轮必须推荐减法"),
            "ux-human-authorized-send": ("两份 consent", "缺任一授权时不发送"),
            "ux-b-text-overrides-selection": ("回到 A", "不自动重选方法"),
        }
        for eval_id, phrases in expected_case_phrases.items():
            item = ux_by_id.get(eval_id, {})
            experience = str(item.get("expected_experience", "")) if isinstance(item, dict) else ""
            validation.require(
                all(phrase in experience for phrase in phrases),
                f"ux-evals.json 场景 {eval_id} 缺少定向语义：{phrases}",
            )
        ux_experience = "\n".join(
            str(item.get("expected_experience", ""))
            for item in ux_evals
            if isinstance(item, dict)
        ) if isinstance(ux_evals, list) else ""
        for phrase in (
            "合并能够并存的目的",
            "不要求排出唯一第一名",
            "真实排他边界",
            "按语义短段呈现",
            "自然句分别说清核心假设、本轮动作、观察信号和复判条件",
            "四项原生单选",
            "独立附注",
            "普通编号",
            "以补充文字为准",
            "不构成执行或授权",
            "正式名称、推荐状态和当前价值",
            "Evidence Gate",
            "支持、反对、冲突与空白",
            "默认单 Agent",
            "主/额外/总数",
            "不把多数票或模型一致性当事实",
            "对应真人提供",
            "纯文本路径完整保留",
            "Skill-only 的纯文本合同",
            "一个综合判断",
            "判断错误、执行偏差、资源错配与条件变化",
            "候选解法",
            "问题存在、问题强度、方案适配和替代生态",
            "用户结果、任务、痛点、失败机制和约束",
            "产品类别、实现、行业术语、平台和候选术语",
            "同一组真实任务与成功标准",
            "最多允许低成本、可撤回的有限验证",
            "目标用户、核心场景、定位、关键依赖或替代生态",
            "不新增、删除或简化流程、只保留必要增量、缩小投入以及暂停/停止",
            "不创造新的减法模式或候选类型",
            "停止为完整感继续扩张",
            "receipt 只证明操作和返回材料发生",
            "不提高承诺上限",
        ):
            validation.require(
                phrase in ux_experience,
                f"ux-evals.json 缺少 current 核心或项目可行性体验场景：{phrase}",
            )
    if ux_rubric_path.exists():
        rubric = ux_rubric_path.read_text(encoding="utf-8")
        for dimension in (
            "真实目的对齐",
            "可纠错性",
            "认知负担",
            "终端可读性",
            "对话自然度",
            "方法透明度",
            "问题可回答性",
            "信任校准",
            "用户自主权",
            "行动转化",
        ):
            validation.require(dimension in rubric, f"UX rubric 缺少维度：{dimension}")
        for phrase in (
            "十个维度",
            "共 20 分",
            "17/20",
            "未实测 / not_run",
            "普通 Markdown、线框示意或静态文案不能证明控件已实际调用",
            "先合并可并存目的，不默认排序",
            "有限互斥答案使用单选",
            "开放答案直接自由回答",
            "正式问题独立位于最后",
            "要弄清什么、先做什么、看哪些现实信号和何时重新决定",
            "四项单选只表达一个主要反馈方向",
            "未观察到独立附注时不假装存在备注框",
            "文本降级明确使用普通编号",
            "选择与文字冲突时准确采用文字",
            "原生反馈单选 UI：未实测 / not_run",
            "独立附注呈现：未实测 / not_run",
            "真实用户体验：未实测 / not_run",
            "`真实目的对齐`、`终端可读性`、`可纠错性`、`问题可回答性`、`用户自主权` 均不得低于 2",
            "不新增、删除、简化、缩小或停止",
            "不为措辞、背景或报告完整感堆方法、问题、搜索、Agent 或材料",
            "receipt 不冒充外部事实或现实试用",
            "采用/搁置/未决",
        ):
            validation.require(phrase in rubric, f"UX rubric 缺少核心体验或证据规则：{phrase}")

    if enhancement_rubric_path.exists():
        enhancement = enhancement_rubric_path.read_text(encoding="utf-8")
        for dimension in (
            "调研适当性",
            "证据质量",
            "参与适当性",
            "成本与权限透明",
            "综合责任",
            "跨宿主保真",
            "解决方案完整性",
            "复判能力",
        ):
            validation.require(dimension in enhancement, f"增强 UX rubric 缺少维度：{dimension}")
        for phrase in (
            "每个维度按 0～2 分，共 16 分",
            "14/16",
            "未实测 / not_run",
            "四类授权互不继承",
            "额外 Agent 递归委派",
            "不按多数票",
            "ChatGPT 或其他宿主未经真实运行不宣称兼容",
            "一个综合判断",
            "主现实证据闭环",
            "严重失败为 0",
            "真实 transcript、能力 trace 或用户评审证据",
            "用户结果、任务、失败机制和约束",
            "同一组真实任务和成功标准试用最强现实替代",
            "问题存在、问题强度、方案适配和替代生态",
            "证据有缺口时承诺上限随之收紧",
            "没有替代",
            "只能自研",
            "完整后端、数据库、领域模型或正式产品架构",
            "目标用户、核心场景、定位、关键依赖或替代生态实质变化",
            "material 路径主动覆盖不新增、删除或简化、只保留必要增量、缩小投入及暂停/停止",
            "模型自信、自我批判、自我评分、方法输出、Agent 一致性或 receipt",
            "逐方法、逐角色或逐 Agent 罗列观点后追加一句结论",
            "判断、material 路径排序、承诺上限、闭环能否执行及结果区分力已不再会变化",
        ):
            validation.require(
                phrase in enhancement,
                f"增强 UX rubric 缺少 v{CURRENT_CONTRACT_VERSION} 核心或项目可行性规则：{phrase}",
            )

    legacy_rubric_path = trigger_dir / "rubric.md"
    if legacy_rubric_path.exists():
        legacy_rubric = legacy_rubric_path.read_text(encoding="utf-8")
        validation.require("20 分行为评测" in legacy_rubric, "原行为 rubric 必须保留 20 分历史角色")
        validation.require("互不覆盖、互不重解释" in legacy_rubric, "行为与 UX rubric 必须明确互不重解释")


def _svg_root(validation: Validation, path: Path) -> ET.Element | None:
    relative = path.resolve().relative_to(ROOT.resolve())
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except ET.ParseError as error:
        validation.require(False, f"SVG {relative} 无法解析：{error}")
        return None
    validation.require(root.tag.rsplit("}", 1)[-1] == "svg", f"SVG {relative} 根元素必须是 svg")
    return root


def _svg_ids(root: ET.Element) -> set[str]:
    return {element_id for element in root.iter() if (element_id := element.get("id"))}


def _svg_viewbox(root: ET.Element) -> tuple[str | None, str | None, str | None]:
    return root.get("width"), root.get("height"), root.get("viewBox")


def _svg_element_by_id(root: ET.Element, element_id: str) -> ET.Element | None:
    return next((element for element in root.iter() if element.get("id") == element_id), None)


def _svg_subtree_has_path(element: ET.Element | None) -> bool:
    return element is not None and any(child.tag.rsplit("}", 1)[-1] == "path" for child in element.iter())


def _manifest_asset(entries: list[object], asset_id: str) -> dict[str, object] | None:
    matches = [entry for entry in entries if isinstance(entry, dict) and entry.get("id") == asset_id]
    return matches[0] if len(matches) == 1 else None


def _asset_path(validation: Validation, value: object, label: str) -> Path | None:
    if not isinstance(value, str):
        validation.require(False, f"{label} 必须是路径字符串")
        return None
    path = (ROOT / value).resolve()
    root_resolved = ROOT.resolve()
    validation.require(root_resolved in path.parents, f"{label} 不得逃逸仓库：{value}")
    validation.require(path.parent == (ROOT / "assets").resolve(), f"{label} 必须位于 assets/：{value}")
    return path


def validate_assets(validation: Validation, files: list[Path]) -> None:
    manifest_path = ROOT / "assets" / "manifest.json"
    validation.require(manifest_path.exists(), "缺少 assets/manifest.json")
    if not manifest_path.exists():
        return
    try:
        manifest = _load_json(manifest_path)
    except (json.JSONDecodeError, OSError) as error:
        validation.require(False, f"assets/manifest.json 无法读取：{error}")
        return

    entries = manifest.get("assets")
    validation.require(manifest.get("schema_version") == "2", "资产 manifest schema_version 必须是 2")
    validation.require(isinstance(entries, list), "资产 manifest 必须包含 assets 数组")
    if not isinstance(entries, list):
        return
    expected_specs = {
        "social-preview": {
            "role": "social-preview",
            "variants": {("en", "dark")},
            "canvas": {"width": 1280, "height": 640},
            "required_ids": {"social-frame", "wordmark", "positioning", "invocation", "thinking-light-slot"},
            "max_source_bytes": 49152,
            "max_output_bytes": 409600,
        },
    }
    entry_ids = [entry.get("id") for entry in entries if isinstance(entry, dict)]
    validation.require(
        entry_ids == ["readme-invocation-card", "social-preview"],
        "资产 manifest 必须按职责定义 README Invocation Card 和 Social Preview",
    )
    validation.require(len(entry_ids) == len(set(entry_ids)), "资产 manifest 的资产 ID 必须唯一")

    svg_roots: dict[Path, ET.Element] = {}
    variant_paths: dict[str, list[Path]] = {}
    declared_paths: set[Path] = {manifest_path.resolve(), (ROOT / "assets" / "README.md").resolve()}
    output_paths: list[Path] = []
    root_resolved = ROOT.resolve()

    invocation_card = _manifest_asset(entries, "readme-invocation-card")
    validation.require(invocation_card is not None, "资产 manifest 缺少唯一 README Invocation Card")
    if invocation_card is not None:
        validation.require(invocation_card.get("role") == "readme-opening-invocation-card", "README Invocation Card role 不正确")
        validation.require(invocation_card.get("canvas") == {"width": 600, "height": 600}, "README Invocation Card 画布合同不正确")
        validation.require(invocation_card.get("pixel_mode") == "RGBA", "README Invocation Card pixel mode 合同不正确")
        validation.require(invocation_card.get("max_source_bytes") == 160000, "README Invocation Card source 字节预算不正确")
        validation.require(invocation_card.get("max_output_bytes") == 160000, "README Invocation Card output 字节预算不正确")
        validation.require(
            invocation_card.get("composition") == {
                "subject_crop": [168, 78, 434, 448],
                "subject_anchor": [168, 78],
                "scale": 1,
                "resampling": "none",
            },
            "README Invocation Card 必须固定复用 dark 主体的比例与位置",
        )
        validation.require(
            invocation_card.get("generator") == {
                "script": "scripts/render_assets.py",
                "renderer": "Pillow",
                "renderer_version": "11.3.0",
                "pixel_mode": "RGBA",
            },
            "README Invocation Card generator 合同不正确",
        )
        variants = invocation_card.get("variants")
        validation.require(isinstance(variants, list) and len(variants) == 2, "README Invocation Card 必须提供 dark source 和 light output")
        invocation_keys: set[tuple[object, object]] = set()
        card_alpha_masks: dict[str, bytes] = {}
        if isinstance(variants, list):
            for variant in variants:
                if not isinstance(variant, dict):
                    validation.require(False, "README Invocation Card 含无效变体")
                    continue
                key = (variant.get("locale"), variant.get("theme"))
                invocation_keys.add(key)
                theme = variant.get("theme")
                key_name = "source" if theme == "dark" else "output"
                path = _asset_path(validation, variant.get(key_name), f"README Invocation Card {theme} {key_name}")
                validation.require(
                    (theme == "dark" and "output" not in variant) or (theme == "light" and "source" not in variant),
                    "README Invocation Card 必须只有 dark canonical source 与 light generated output",
                )
                if path is None:
                    continue
                validation.require(path not in declared_paths, f"资产路径不得重复声明：{variant.get(key_name)}")
                declared_paths.add(path)
                validation.require(path.name == f"readme-invocation-card-{theme}.png", f"README Invocation Card {theme} 路径不正确")
                validation.require(path.exists(), f"缺少 README Invocation Card {theme}：{variant.get(key_name)}")
                if theme == "light":
                    output_paths.append(path)
                if not path.exists():
                    continue
                data = path.read_bytes()
                limit = invocation_card.get("max_source_bytes" if theme == "dark" else "max_output_bytes")
                validation.require(isinstance(limit, int) and len(data) <= limit, f"README Invocation Card {theme} 超出字节预算")
                if theme == "dark":
                    expected_hash = "33760ccbbf4011f663f1e998ac41f006f31a8888a22945c6e395976c7bda7ff4"
                    validation.require(variant.get("source_sha256") == expected_hash, "README Invocation Card dark SHA-256 合同不正确")
                    validation.require(hashlib.sha256(data).hexdigest() == expected_hash, "README Invocation Card dark SHA-256 不匹配")
                try:
                    size, mode, _ = decoded_image(data)
                    validation.require(size == (600, 600), f"README Invocation Card {theme} 必须是 600×600")
                    validation.require(mode == "RGBA", f"README Invocation Card {theme} pixel mode 必须是 RGBA")
                    with Image.open(path) as image:
                        image.load()
                        alpha = image.getchannel("A")
                        validation.require(alpha.getextrema() == (0, 255), f"README Invocation Card {theme} 必须同时包含透明和不透明像素")
                        card_alpha_masks[str(theme)] = alpha.tobytes()
                except Exception as error:
                    validation.require(False, f"README Invocation Card {theme} 无法完整解码：{error}")
            validation.require(invocation_keys == {("neutral", "light"), ("neutral", "dark")}, "README Invocation Card 语言/主题变体不正确")
        if set(card_alpha_masks) == {"light", "dark"}:
            validation.require(card_alpha_masks["light"] == card_alpha_masks["dark"], "README Invocation Card light/dark 外框 alpha 几何必须完全一致")
        provenance = invocation_card.get("provenance")
        validation.require(
            isinstance(provenance, dict)
            and provenance.get("selection") == "user-selected dark canonical raster source"
            and provenance.get("source_material") == "the repository's canonical Thinking Light 3D subject"
            and "dark variant fixes" in str(provenance.get("geometry_basis"))
            and "no copied composition or brand elements" in str(provenance.get("reference_scope")),
            "README Invocation Card 缺少准确 provenance",
        )

    for entry in entries:
        if isinstance(entry, dict) and entry.get("id") == "readme-invocation-card":
            continue
        if not isinstance(entry, dict):
            validation.require(False, "资产 manifest 的每个条目必须是对象")
            continue
        asset_id = entry.get("id")
        variants = entry.get("variants")
        canvas = entry.get("canvas")
        required_ids = entry.get("required_ids")
        validation.require(isinstance(asset_id, str), "资产条目缺少字符串 ID")
        spec = expected_specs.get(asset_id) if isinstance(asset_id, str) else None
        validation.require(spec is not None, f"资产 manifest 含未知职责：{asset_id}")
        validation.require(isinstance(variants, list) and bool(variants), f"资产 {asset_id} 缺少 variants")
        validation.require(
            isinstance(canvas, dict) and isinstance(canvas.get("width"), int) and isinstance(canvas.get("height"), int),
            f"资产 {asset_id} 缺少有效画布",
        )
        validation.require(
            isinstance(required_ids, list) and all(isinstance(item, str) for item in required_ids),
            f"资产 {asset_id} 缺少 required_ids",
        )
        if not isinstance(asset_id, str) or not isinstance(variants, list) or not isinstance(canvas, dict) or spec is None:
            continue
        validation.require(entry.get("role") == spec["role"], f"资产 {asset_id} role 不正确")
        validation.require(canvas == spec["canvas"], f"资产 {asset_id} 画布合同不正确")
        validation.require(set(required_ids or []) == spec["required_ids"], f"资产 {asset_id} required_ids 合同不正确")
        for key in ("max_bytes", "max_source_bytes", "max_output_bytes"):
            if key in spec:
                validation.require(entry.get(key) == spec[key], f"资产 {asset_id} {key} 预算不正确")
        variant_keys = {
            (variant.get("locale"), variant.get("theme"))
            for variant in variants
            if isinstance(variant, dict)
        }
        validation.require(variant_keys == spec["variants"], f"资产 {asset_id} 语言/主题变体不正确")
        expected_viewbox = (
            str(canvas.get("width")),
            str(canvas.get("height")),
            f"0 0 {canvas.get('width')} {canvas.get('height')}",
        )
        sources: list[Path] = []
        seen_keys: set[tuple[object, object]] = set()
        for variant in variants:
            if not isinstance(variant, dict) or not isinstance(variant.get("source"), str):
                validation.require(False, f"资产 {asset_id} 含无效变体")
                continue
            key = (variant.get("locale"), variant.get("theme"))
            validation.require(key not in seen_keys, f"资产 {asset_id} 含重复 locale/theme 变体：{key}")
            seen_keys.add(key)
            source = (ROOT / variant["source"]).resolve()
            validation.require(source == root_resolved or root_resolved in source.parents, f"资产 {asset_id} source 不得逃逸仓库：{variant['source']}")
            validation.require(source.parent == (ROOT / "assets").resolve(), f"资产 {asset_id} source 必须位于 assets/：{variant['source']}")
            sources.append(source)
            declared_paths.add(source)
            output = variant.get("output")
            if output is not None:
                validation.require(isinstance(output, str), f"资产 {asset_id} output 必须是路径字符串")
                if isinstance(output, str):
                    output_path = (ROOT / output).resolve()
                    validation.require(root_resolved in output_path.parents, f"资产 {asset_id} output 不得逃逸仓库：{output}")
                    validation.require(output_path.parent == (ROOT / "assets").resolve(), f"资产 {asset_id} output 必须位于 assets/：{output}")
                    validation.require(output_path not in declared_paths, f"资产路径不得重复声明：{output}")
                    output_paths.append(output_path)
                    declared_paths.add(output_path)
            validation.require(source.exists(), f"资产 {asset_id} 缺少源文件：{variant['source']}")
            if not source.exists():
                continue
            validation.require(source.suffix == ".svg", f"资产源文件必须是 SVG：{variant['source']}")
            text = source.read_text(encoding="utf-8")
            relative = source.relative_to(root_resolved)
            validation.require("<script" not in text.lower(), f"SVG {relative} 不得包含脚本")
            validation.require("<foreignobject" not in text.lower(), f"SVG {relative} 不得包含 foreignObject")
            validation.require("<style" not in text.lower() and "@import" not in text.lower(), f"SVG {relative} 不得依赖外部 CSS 或字体")
            validation.require(
                not re.search(r"(?:href|src)=[\"'](?:https?:|//)", text, re.IGNORECASE),
                f"SVG {relative} 不得引用远程资源",
            )
            validation.require("data:image" not in text.lower(), f"SVG {relative} 不得包含 data URI raster")
            root = _svg_root(validation, source)
            if root is None:
                continue
            svg_roots[source] = root
            local_tags = {element.tag.rsplit("}", 1)[-1] for element in root.iter()}
            attributes = {
                name.rsplit("}", 1)[-1].lower()
                for element in root.iter()
                for name in element.attrib
            }
            ids = [element.get("id") for element in root.iter() if element.get("id")]
            validation.require("title" in local_tags and "desc" in local_tags, f"SVG {relative} 必须包含 title 和 desc")
            validation.require(len(ids) == len(set(ids)), f"SVG {relative} 的 ID 必须唯一")
            validation.require("script" not in local_tags, f"SVG {relative} 不得包含 script 元素")
            validation.require("image" not in local_tags, f"SVG {relative} 不得嵌入 raster image")
            validation.require("foreignObject" not in local_tags, f"SVG {relative} 不得包含 foreignObject")
            validation.require(not any(name.startswith("on") for name in attributes), f"SVG {relative} 不得包含事件处理器")
            validation.require(_svg_viewbox(root) == expected_viewbox, f"资产 {asset_id} 画布必须是 {canvas.get('width')}×{canvas.get('height')}：{relative}")
            missing_ids = set(required_ids or []) - _svg_ids(root)
            validation.require(not missing_ids, f"资产 {asset_id} 缺少稳定结构 ID：{sorted(missing_ids)}")
            byte_limit = entry.get("max_source_bytes", entry.get("max_bytes"))
            validation.require(isinstance(byte_limit, int), f"资产 {asset_id} 缺少源文件字节预算")
            if isinstance(byte_limit, int):
                validation.require(source.stat().st_size <= byte_limit, f"资产 {relative} 超出 {byte_limit} 字节预算")
        variant_paths[asset_id] = sources

    social_preview = _manifest_asset(entries, "social-preview")
    generator = social_preview.get("generator") if isinstance(social_preview, dict) else None
    validation.require(
        generator == {
            "script": "scripts/render_assets.py",
            "renderer": "resvg-py",
            "renderer_version": "0.5.0",
            "compositor": "Pillow",
            "compositor_version": "11.3.0",
            "skip_system_fonts": True,
            "pixel_mode": "RGBA",
        },
        "Social Preview generator 合同不正确",
    )
    validation.require(
        isinstance(social_preview, dict)
        and social_preview.get("composition") == {
            "canonical_asset": "readme-invocation-card",
            "canonical_theme": "dark",
            "subject_anchor": [914, 100],
            "scale": 1,
            "resampling": "none",
        },
        "Social Preview 必须以固定位置和 1:1 比例复用 dark canonical Thinking Light",
    )

    managed_assets = {
        path.resolve()
        for path in files
        if path.parent.resolve() == (ROOT / "assets").resolve() and path.suffix.lower() in {".svg", ".png"}
    }
    validation.require(
        managed_assets == declared_paths - {manifest_path.resolve(), (ROOT / "assets" / "README.md").resolve()},
        f"assets/ 下 SVG/PNG 必须由 manifest 精确声明：{sorted(path.name for path in managed_assets ^ (declared_paths - {manifest_path.resolve(), (ROOT / 'assets' / 'README.md').resolve()}))}",
    )
    validation.require(len(declared_paths) == len(set(declared_paths)), "资产 source/output 路径必须唯一")

    social_paths = variant_paths.get("social-preview", [])
    validation.require(len(social_paths) == 1, "Social Preview 必须只有一个 dark SVG/PNG 变体")
    if len(social_paths) == 1 and social_paths[0] in svg_roots:
        social_root = svg_roots[social_paths[0]]
        social_tags = {element.tag.rsplit("}", 1)[-1] for element in social_root.iter()}
        social_ids = _svg_ids(social_root)
        validation.require("text" not in social_tags, "Social Preview SVG 不得包含 text 或依赖系统字体")
        validation.require("linearGradient" not in social_tags and "radialGradient" not in social_tags and "filter" not in social_tags, "Social Preview 不得使用 gradient 或 filter")
        positioning = _svg_element_by_id(social_root, "positioning")
        invocation = _svg_element_by_id(social_root, "invocation")
        desc = _svg_element_by_id(social_root, "desc")
        wordmark = _svg_element_by_id(social_root, "wordmark")
        validation.require(_svg_subtree_has_path(wordmark), "Social Preview wordmark 必须包含实际 path")
        validation.require(wordmark is not None and wordmark.get("aria-label") == "Think It Through", "Social Preview wordmark 必须准确表达完整名称")
        validation.require(_svg_subtree_has_path(positioning), "Social Preview positioning 必须包含实际布局 path")
        validation.require(_svg_subtree_has_path(invocation), "Social Preview invocation 必须包含实际布局 path")
        validation.require(positioning is not None and positioning.get("aria-label") == POSITIONING_EN, "Social Preview positioning 必须提供准确的定位 aria-label")
        validation.require(invocation is not None and invocation.get("aria-label") == "Claude Code command /think-it-through", "Social Preview invocation 必须提供准确的调用 aria-label")
        validation.require(desc is not None and POSITIONING_EN in "".join(desc.itertext()), "Social Preview desc 必须包含完整 canonical 英文定位")
        validation.require(
            {"decision-thread", "optional-gate", "reassessment-loop", "tagline"}.isdisjoint(social_ids),
            "Social Preview 不得恢复旧线框流程图或像素 tagline",
        )

    expected_outputs = {
        (ROOT / "assets" / "readme-invocation-card-light.png").resolve(): ((600, 600), "RGBA"),
        (ROOT / "assets" / "social-preview.png").resolve(): ((1280, 640), "RGBA"),
    }
    validation.require(set(output_paths) == set(expected_outputs), "派生 PNG 输出必须精确包含 light Invocation Card 与 Social Preview")
    for output, (expected_size, expected_mode) in expected_outputs.items():
        validation.require(output.exists(), f"缺少派生 PNG：{output.name}")
        if not output.exists():
            continue
        try:
            size, mode, _ = decoded_image(output.read_bytes())
            validation.require(size == expected_size, f"{output.name} 必须是 {expected_size[0]}×{expected_size[1]}")
            validation.require(mode == expected_mode, f"{output.name} pixel mode 必须是 {expected_mode}")
        except Exception as error:
            validation.require(False, f"{output.name} 无法完整解码：{error}")
    try:
        for error in check_generated_assets(ROOT):
            validation.require(False, error)
    except Exception as error:
        validation.require(False, f"派生视觉资产无法重渲染检查：{error}")


def validate_repo_hygiene(validation: Validation, files: list[Path]) -> None:
    home_marker = "/" + "Users" + "/" + "wuweixiang" + "/"
    private_temp_marker = "/" + "private" + "/" + "tmp" + "/"
    generic_temp_marker = "/" + "tmp" + "/"
    absolute_path_markers = (home_marker, private_temp_marker, generic_temp_marker)
    placeholder_words = ("TO" + "DO", "T" + "BD", "FIX" + "ME", "coming" + " soon")
    placeholder_re = re.compile(rf"\b(?:{'|'.join(placeholder_words)})\b", re.IGNORECASE)
    allowed_placeholder_files = {ROOT / "REQUIREMENTS.md", ROOT / "PRODUCT.md"}

    for path in files:
        if path.suffix not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in absolute_path_markers:
            validation.require(marker not in text, f"{path.relative_to(ROOT)} 泄漏本机绝对路径：{marker}")
        if path not in allowed_placeholder_files:
            validation.require(not placeholder_re.search(text), f"{path.relative_to(ROOT)} 含发布占位符")
        validation.require(not re.search(r"(?:api[_-]?key|secret|token)\s*[:=]\s*[\"'][^\"']+[\"']", text, re.IGNORECASE), f"{path.relative_to(ROOT)} 可能包含凭据")
        validation.require(all(not line.rstrip("\n\r").endswith(" ") for line in text.splitlines(keepends=True)), f"{path.relative_to(ROOT)} 含尾随空格")


def validate_examples_and_benchmarks(validation: Validation) -> None:
    benchmark_root = ROOT / "benchmarks" / "behavior-v0.1"
    actual_files = {
        path.relative_to(benchmark_root).as_posix()
        for path in benchmark_root.rglob("*")
        if path.is_file()
    } if benchmark_root.exists() else set()
    validation.require(
        actual_files == set(FROZEN_BEHAVIOR_SHA256),
        f"冻结 behavior benchmark 文件集合发生变化：{sorted(actual_files ^ set(FROZEN_BEHAVIOR_SHA256))}",
    )
    for relative, expected_hash in FROZEN_BEHAVIOR_SHA256.items():
        path = benchmark_root / relative
        validation.require(path.exists(), f"缺少冻结 behavior 证据：{relative}")
        if path.exists():
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            validation.require(actual_hash == expected_hash, f"冻结 behavior 证据被改写：{relative}")

    validation.require((benchmark_root / "README.md").exists(), "缺少公开 behavior benchmark 说明")
    benchmark_json = benchmark_root / "benchmark.json"
    validation.require(benchmark_json.exists(), "缺少公开 behavior benchmark.json")
    if benchmark_json.exists():
        benchmark = json.loads(benchmark_json.read_text(encoding="utf-8"))
        validation.require(benchmark.get("metadata", {}).get("runs_per_configuration") == 1, "benchmark 运行次数必须如实为 1")
        runs = benchmark.get("runs", [])
        validation.require(len(runs) == 6, f"benchmark 应包含 6 份运行，当前为 {len(runs)}")
        for run in runs:
            result = run.get("result", {}) if isinstance(run, dict) else {}
            validation.require("semantic_score" in result and "semantic_passed" in result, "benchmark 每份运行必须包含语义评分")
            if not isinstance(run, dict):
                continue
            eval_id = run.get("eval_id")
            eval_name = run.get("eval_name")
            configuration = run.get("configuration")
            transcript = benchmark_root / f"eval-{eval_id}-{eval_name}" / str(configuration) / "transcript.md"
            semantic = benchmark_root / f"eval-{eval_id}-{eval_name}" / str(configuration) / "semantic-rubric.json"
            validation.require(transcript.exists() and semantic.exists(), f"benchmark 运行缺少 transcript 或语义评分：{eval_id}/{configuration}")
            if transcript.exists() and semantic.exists():
                semantic_data = json.loads(semantic.read_text(encoding="utf-8"))
                actual_hash = hashlib.sha256(transcript.read_bytes()).hexdigest()
                validation.require(
                    semantic_data.get("transcript_sha256") == actual_hash,
                    f"语义评分未绑定当前 transcript：{eval_id}/{configuration}",
                )

    examples_dir = SKILL_DIR / "examples"
    validation.require(
        not examples_dir.exists(),
        "冻结 v0.1 transcript 只保留在 benchmarks/behavior-v0.1，不再复制到分发源 examples/",
    )


def validate_contract_graders(validation: Validation) -> None:
    current_grader = ROOT / "scripts" / "grade_contracts.py"
    legacy_grader = ROOT / "scripts" / "grade_contracts_v0_1.py"
    behavior_grader = ROOT / "scripts" / "grade_behavior_runs.py"
    for path in (current_grader, legacy_grader, behavior_grader):
        validation.require(path.exists(), f"缺少评分器：{path.relative_to(ROOT)}")
    if current_grader.exists():
        current_text = current_grader.read_text(encoding="utf-8")
        validation.require(
            f'"contract_version": "{CURRENT_CONTRACT_VERSION}"' in current_text,
            f"当前评分器必须输出 contract_version {CURRENT_CONTRACT_VERSION}",
        )
        validation.require("class InteractionOption:" in current_text, "当前评分器缺少 InteractionOption")
        validation.require("class InteractionEvidence:" in current_text, "当前评分器缺少 InteractionEvidence")
        validation.require("def parse_interaction_evidence(" in current_text, "当前评分器缺少交互证据解析函数")
        validation.require(
            'parser.add_argument("--interaction-json", type=Path' in current_text
            and 'parser.error("R/A/B 阶段必须提供 --interaction-json")' in current_text,
            "当前评分器必须只对 R/A/B 动态要求 --interaction-json",
        )
        for token in (
            '"native-control"',
            '"text-fallback"',
            '"free-answer"',
            '"multi"',
            '"single"',
            '"none"',
            '"rejected"',
            '"native-note"',
            '"follow-up-message"',
            '"inline-text"',
            '"compatible-set"',
            '"finite-mutually-exclusive"',
            '"open"',
            "ANSWER_SHAPES",
            "A_ANSWER_SHAPES",
            "SUPPLEMENT_MODES",
            "FEEDBACK_DIRECTION_IDS",
            "FEEDBACK_OPTION_SETS",
            "resolve_b_feedback_route",
            "_semantic_paragraphs",
            "_last_paragraph_is_only_question",
            "_selection_question_layout",
            "_text_fallback_layout",
            "_free_answer_interaction_valid",
            "_b_interaction_valid",
            "_b_feedback_layout_valid",
            "PRODUCT_OTHER_RE",
            "host_free_text_available",
            "supplement_mode",
            "_method_option_contract",
            "_method_recommendations_match",
            "_method_descriptions_duplicated_in_body",
            "grade_evidence_gate",
            "grade_participation_gate",
            "grade_human_review",
            "grade_decision_record",
            "CONSENT_TYPES",
            "CAPABILITY_AVAILABILITY",
            "CAPABILITY_READINESS",
            "_agent_counts_valid",
            '"EVIDENCE"',
            '"PARTICIPATION"',
            '"HUMAN"',
            '"DECISION_RECORD"',
            '"阶段 B 的核心假设、本轮动作、观察信号和复判条件以自然句分别成段并后置标记"',
            '"阶段 B 只提出一个反馈问题，不追加决策信息问题"',
        ):
            validation.require(token in current_text, f"当前评分器缺少 v{CURRENT_CONTRACT_VERSION} 合同：{token}")
        validation.require(
            '"declarative-feedback"' not in current_text,
            "当前评分器不得继续接受 declarative-feedback",
        )
        validation.require("method_selection_mode" not in current_text, "当前评分器不得保留重复的 method_selection_mode 分流")
        validation.require(
            '"compatible-set" if stage == "R" else "open"' in current_text,
            "当前评分器必须按阶段默认 R=compatible-set、A=open",
        )
        validation.require("extract_number_phrases" in current_text, "当前评分器缺少决定相关数字提取器")
    if behavior_grader.exists():
        behavior_text = behavior_grader.read_text(encoding="utf-8")
        validation.require(
            "from grade_contracts_v0_1 import Check, grade_a, grade_b, grade_r" in behavior_text,
            "历史行为评分必须显式使用冻结的 grade_contracts_v0_1",
        )
        validation.require("from grade_contracts import" not in behavior_text, "历史行为评分不得导入当前评分合同")
    if legacy_grader.exists():
        legacy_text = legacy_grader.read_text(encoding="utf-8")
        validation.require("自然回显最终确认的方法组合" not in legacy_text, "冻结评分器不得混入当前方法回显合同")
        validation.require("InteractionEvidence" not in legacy_text, "冻结评分器不得混入 v0.1.3 原生交互合同")
        validation.require("contract_version" not in legacy_text, "冻结评分器不得混入当前合同版本输出")


def _markdown_h2(text: str) -> list[str]:
    return re.findall(r"^## (.+)$", text, re.MULTILINE)


def _markdown_h2_section(text: str, heading: str) -> str:
    marker = f"## {heading}\n"
    start = text.find(marker)
    if start < 0:
        return ""
    content_start = start + len(marker)
    next_heading = text.find("\n## ", content_start)
    return text[content_start:] if next_heading < 0 else text[content_start:next_heading]


def _readme_badges(text: str) -> list[tuple[str, str, str]]:
    pattern = re.compile(r"\[!\[([^]]+)\]\((https://[^)]+)\)\]\(([^)]+)\)")
    return pattern.findall(text)


def validate_public_docs(validation: Validation) -> None:
    validation.require(
        not (ROOT / "README.zh-CN.md").exists(),
        "根目录不得保留 README.zh-CN.md；中文默认入口只维护在 README.md",
    )
    current_architecture_path = f"docs/product-architecture-v{CURRENT_ARCHITECTURE_VERSION}.md"
    previous_architecture_path = f"docs/product-architecture-v{PREVIOUS_PUBLISHED_VERSION}.md"
    public_paths = (
        "README.md", "README.en.md", "PRODUCT.md", "REQUIREMENTS.md", "SECURITY.md",
        "CONTRIBUTING.md", "docs/installation.md", "docs/installation.en.md",
        "docs/compatibility-and-evidence.md", "docs/compatibility-and-evidence.en.md",
        ".agents/brand-context.md",
        ".github/ISSUE_TEMPLATE/install-or-runtime-feedback.yml",
        ".github/workflows/validate.yml",
        "docs/product-architecture-v0.2.0.md", previous_architecture_path,
        current_architecture_path, "CLAUDE.md",
    )
    public_docs = {relative: (ROOT / relative).read_text(encoding="utf-8") for relative in public_paths}
    readme_zh = public_docs["README.md"]
    readme_en = public_docs["README.en.md"]
    requirements = public_docs["REQUIREMENTS.md"]
    product = public_docs["PRODUCT.md"]
    claude_md = public_docs["CLAUDE.md"]
    security = public_docs["SECURITY.md"]
    contributing = public_docs["CONTRIBUTING.md"]
    brand_context = public_docs[".agents/brand-context.md"]
    feedback_form = public_docs[".github/ISSUE_TEMPLATE/install-or-runtime-feedback.yml"]
    validate_workflow = public_docs[".github/workflows/validate.yml"]
    stable_architecture = public_docs["docs/product-architecture-v0.2.0.md"]
    previous_architecture = public_docs[previous_architecture_path]
    current_architecture = public_docs[current_architecture_path]
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    feedback_path = "issues/new?template=install-or-runtime-feedback.yml"
    installation_zh = public_docs["docs/installation.md"]
    installation_en = public_docs["docs/installation.en.md"]
    compatibility_zh = public_docs["docs/compatibility-and-evidence.md"]
    compatibility_en = public_docs["docs/compatibility-and-evidence.en.md"]

    method_registry_path = ROOT / "skills" / "think-it-through" / "references" / "methods" / "registry.yaml"
    validation.require(method_registry_path.exists(), "公开 README 方法校验缺少 registry.yaml 事实源")
    method_registry = yaml.safe_load(method_registry_path.read_text(encoding="utf-8")) if method_registry_path.exists() else {}
    registered_methods = method_registry.get("methods", []) if isinstance(method_registry, dict) else []
    registered_methods = [method for method in registered_methods if isinstance(method, dict)]
    registered_method_ids = {method.get("id") for method in registered_methods if isinstance(method.get("id"), str)}
    english_method_labels = {
        "object-calibration": "Object Calibration",
        "system-bottleneck": "System Bottleneck",
        "stage-fit": "Stage Fit",
        "resource-leverage": "Resource Leverage",
        "boundary-contracts": "Boundary Contracts",
        "communication-fit": "Communication Fit",
        "evidence-loop": "Evidence Loop",
    }
    validation.require(
        registered_method_ids == set(english_method_labels),
        "README 英文专项方法本地化映射必须与 registry.yaml ID 完全一致",
    )

    expected_readme_badges = [
        (
            "MIT License",
            "https://img.shields.io/github/license/zemu2718/think-it-through-skill?style=flat-square",
            "LICENSE",
        ),
        (
            "Latest Release",
            "https://img.shields.io/github/v/release/zemu2718/think-it-through-skill?style=flat-square&label=release",
            "https://github.com/zemu2718/think-it-through-skill/releases/latest",
        ),
        (
            "Validate",
            "https://github.com/zemu2718/think-it-through-skill/actions/workflows/validate.yml/badge.svg?branch=main",
            "https://github.com/zemu2718/think-it-through-skill/actions/workflows/validate.yml?query=branch%3Amain",
        ),
    ]

    readme_contracts = (
        {
            "name": "README.en.md",
            "text": readme_en,
            "sections": ["What you get", "When to use it", "How it works", "Install and use", "Safe by default"],
            "navigation": "[When to use it](#when-to-use-it) · [How it works](#how-it-works) · [Install](#install-and-use) · [Safe by default](#safe-by-default)",
            "language_switch": "🌐 [简体中文](README.md)",
            "result_heading": "What you get",
            "result_semantics": ("A clear direction", "existing solution", "critical gap", "validate first", "build", "adjust, pause, or stop", "A small real-world test", "A rationale you can revisit", "what remains unknown"),
            "workflow_heading": "How it works",
            "workflow_semantics": ("real need", "facts, guesses, assumptions, and unknowns", "one question most likely to change", "commitments with the people making them", "what customers actually do", "qualified professional", "existing products", "built-in capabilities", "tool combinations", "process changes", "one small, low-cost test", "no viable existing option", "does not prove you need to build from scratch", "small and reversible"),
            "project_viability_scope": "If you are deciding whether to custom-build a product, feature, or technical system",
            "method_heading": "Methods it may use",
            "base_method": "It always starts with basic analysis",
            "method_recommendation": "it may recommend one or more of the methods below",
            "core_method_intro": "The two core methods are:",
            "automatic_method_execution": r"(?<!not )\b(?:it|the Skill)\s+(?:will\s+)?automatically\s+(?:adds?|uses?|executes?)\b",
            "core_methods": ("Two-sided Steelman", "Pre-mortem"),
            "specialist_methods": tuple(english_method_labels.get(method.get("id"), "") for method in registered_methods),
            "method_boundaries": ("do not need to learn or choose these methods in advance", "only the approaches your current question needs", "asks you to confirm before using them", "someone with relevant knowledge", "explains why each is needed and asks for your consent separately"),
            "removed_phrases": ("## See the shift", "## Say it in your own words", "compressed synthetic illustration", "AI bookkeeping product", "large customer wants to buy my inventory tool", "developer tool for a long time"),
            "install_heading": "Install and use",
            "install_prompt": "Install this Skill for me: https://github.com/zemu2718/think-it-through-skill",
            "install_intro": "Send this message to the Agent you already use",
            "cli_intro": "Or run this command in your terminal",
            "cli_command": "npx skills add zemu2718/think-it-through-skill",
            "installation_link": "docs/installation.en.md",
            "compatibility_link": "docs/compatibility-and-evidence.en.md",
            "safety_heading": "Safe by default",
            "safety_intro": "While you use this Skill, it does not do any of the following unless you explicitly approve that specific action:",
            "safety_phrases": ("access the network", "access private data", "involve additional Agents", "write files or save anything remotely", "take external action"),
            "not_for": ("factual lookup", "low-risk execution", "purely creative work", "does not require a key decision from you", "take protective action first", "qualified professional in the relevant field"),
            "moments": ("Before starting", "Before choosing a path", "Before committing resources", "Before doubling down", "After results or conditions change"),
            "example_phrases": ("I want to build", "whether it is worth doing", "whether an existing or lighter path could meet the same need", "what to validate first"),
            "invocation_alt": "Thinking Light surrounds a clear opening",
            "removed_category": "A **decision-and-evidence Agent Skill** for consequential commitments.",
            "runtime_boundary": "having the files installed does not mean the Skill can run correctly in your current tool.",
            "invocation_intro": "**Get started:** If you use Claude Code, enter this after installation:",
            "consent_boundary": "Agreeing to one action does not mean you agree to any other action.",
            "plain_language": ("Questions you can bring", "achieve the real goal", "understand the real need first", "using the same standards", "ways to limit the damage"),
            "more_heading": "Learn more",
            "detail_groups": ("**Installation and compatibility:**", "**Understand the boundaries:**", "**Help improve it:**"),
            "positioning": POSITIONING_EN,
            "value_statement": VALUE_STATEMENT_EN,
        },
        {
            "name": "README.md",
            "text": readme_zh,
            "sections": ["你会得到什么", "什么时候调用", "它怎样帮你想清楚", "安装与使用", "默认安全"],
            "navigation": "[什么时候调用](#什么时候调用) · [如何工作](#它怎样帮你想清楚) · [安装](#安装与使用) · [默认安全](#默认安全)",
            "language_switch": "🌐 [English](README.en.md)",
            "result_heading": "你会得到什么",
            "result_semantics": ("一个明确方向", "现成方案", "关键能力", "验证", "自己开发", "调整、暂停还是停止", "一次能检验判断的小尝试", "一份可回看的判断依据", "还有哪些未知"),
            "workflow_heading": "它怎样帮你想清楚",
            "workflow_semantics": ("真实需要", "事实、推测、假设和未知", "一个最可能让你改变", "承诺问当事人", "客户需求看真实行为", "具备相应资质的专业人士", "现成产品", "平台能力", "工具组合", "流程调整", "成本可控、随时能停的小测试", "还没找到可行的现成办法", "不能证明必须自己开发", "小范围、可撤回"),
            "project_viability_scope": "如果你正在判断是否自研产品、功能或技术系统",
            "method_heading": "它可能用到的方法",
            "base_method": "它每次都会先做基础分析",
            "method_recommendation": "它可能推荐下面的方法",
            "core_method_intro": "两种核心方法是：",
            "automatic_method_execution": r"(?<!不)(?:会在推荐后自动|会自动|将自动)(?:加入|使用|执行)",
            "core_methods": ("双向钢人", "失败预演"),
            "specialist_methods": tuple(method.get("name", "") for method in registered_methods),
            "method_boundaries": ("不需要提前了解或选择这些方法", "当前问题真正需要的思考角度", "使用前请你确认", "向知情的人了解情况", "先说明原因，再分别征得你的同意"),
            "removed_phrases": ("## 先看它会改变什么", "## 直接说出你的想法", "压缩后的合成示意", "AI 记账产品", "大客户愿意买我的库存工具", "开发者工具已经做了很久"),
            "install_heading": "安装与使用",
            "install_prompt": "帮我安装这个 Skill：https://github.com/zemu2718/think-it-through-skill",
            "install_intro": "把下面这句话发给你正在使用的 Agent",
            "cli_intro": "也可以在终端直接运行",
            "cli_command": "npx skills add zemu2718/think-it-through-skill",
            "installation_link": "docs/installation.md",
            "compatibility_link": "docs/compatibility-and-evidence.md",
            "safety_heading": "默认安全",
            "safety_intro": "使用这个 Skill 时，除非你明确同意某项具体操作，否则它默认：",
            "safety_phrases": ("不联网", "不读取私有数据", "不调用其他 Agent", "不写入文件，也不保存到远端", "不替你执行外部操作"),
            "not_for": ("查事实", "已经决定的低风险任务", "纯创作", "不涉及关键选择", "先采取保护措施", "咨询具备相应资质的专业人士"),
            "moments": ("立项前", "选方向前", "投入资源前", "继续加码前", "结果或条件变化后"),
            "example_phrases": ("我想做", "是否值得做", "有没有现成或更轻的办法", "现在最该验证什么"),
            "invocation_alt": "思考之光围绕清晰开口",
            "removed_category": "一个用于重要投入前后判断的**决策与证据 Agent Skill**。",
            "runtime_boundary": "安装好文件都不代表这个 Skill 已经能在当前工具中正常运行。",
            "invocation_intro": "**开始使用：** 如果你使用 Claude Code，安装完成后输入：",
            "consent_boundary": "你同意一项操作，不代表也同意其他操作。",
            "plain_language": ("适合讨论的问题", "更能实现真正目标", "真实需要的判断", "用同一套标准", "如何控制损失"),
            "more_heading": "更多信息",
            "detail_groups": ("**安装与兼容：**", "**了解边界：**", "**参与改进：**"),
            "positioning": POSITIONING_ZH,
            "value_statement": VALUE_STATEMENT_ZH,
        },
    )
    readme_links = ("PRODUCT.md", "REQUIREMENTS.md", "SECURITY.md", "CONTRIBUTING.md", "LICENSE", "THIRD_PARTY_NOTICES.md")
    readme_forbidden = (
        "npx -y skills", "gh skill install", "git clone", "SHA256SUMS", "git rev-parse HEAD",
        "L0", "L5", "9/16", "approved evidence", "R-align", "R-method", "DecisionRecord",
    )
    old_assets = ("assets/hero-", "assets/product-value-", "assets/demo-flow", "assets/decision-case-")

    for contract in readme_contracts:
        name = contract["name"]
        readme = contract["text"]
        headings = _markdown_h2(readme)
        validation.require(headings == contract["sections"], f"{name} 必须精确包含结果优先的五段普通用户路径")
        first_h2 = readme.find("## ")
        preface = readme[:first_h2] if first_h2 >= 0 else readme
        validation.require(first_h2 > 0, f"{name} 缺少 H2 章节")
        validation.require(
            "assets/readme-invocation-card-dark.png" in preface
            and "assets/readme-invocation-card-light.png" in preface
            and '<img src="assets/readme-invocation-card-light.png"' in preface
            and 'width="200"' in preface,
            f"{name} 首屏缺少正确的 light/dark README Invocation Card、light fallback 或紧凑显示宽度",
        )
        picture_position = preface.find("<picture>")
        picture_end = preface.find("</picture>", picture_position)
        heading_position = preface.find("# ")
        positioning_position = preface.find(contract["positioning"])
        value_position = preface.find(contract["value_statement"])
        navigation_position = preface.find(f"\n{contract['navigation']}\n")
        language_switch_position = preface.find(contract["language_switch"])
        validation.require(
            -1 < picture_position < picture_end < heading_position < positioning_position < value_position < navigation_position < language_switch_position,
            f"{name} 首屏必须保持 Invocation Card → H1 → 主定位 → 价值说明 → 页内导航顺序 → 语言切换",
        )
        picture = preface[picture_position:picture_end + len("</picture>")] if picture_position >= 0 and picture_end >= 0 else ""
        preface_without_picture = preface[:picture_position] + preface[picture_end + len("</picture>"):] if picture else preface
        validation.require(
            re.search(r"(?<![\w-])/think-it-through(?![\w-])", preface_without_picture) is None,
            f"{name} 首屏仅允许 Invocation Card 表达调用入口，不得在卡片之外重复添加文本调用",
        )
        alt_match = re.search(r'<img src="assets/readme-invocation-card-light\.png" alt="([^"]+)" width="200">', picture)
        validation.require(
            alt_match is not None
            and bool(alt_match.group(1).strip())
            and contract["invocation_alt"] in alt_match.group(1)
            and "Claude Code" in alt_match.group(1)
            and "/think-it-through" in alt_match.group(1),
            f"{name} README Invocation Card 必须提供准确的非空本地化 alt，并说明 Claude Code 调用",
        )
        validation.require(contract["removed_category"] not in preface, f"{name} 首屏不得重新加入偏内部的 Agent Skill 品类说明")
        validation.require(contract["positioning"] in preface, f"{name} 首屏缺少 canonical 产品定位")
        validation.require(contract["value_statement"] in preface, f"{name} 首屏缺少想清楚再行动的价值说明")
        badges = _readme_badges(preface)
        validation.require(badges == expected_readme_badges, f"{name} 首屏必须且只能保留 License、Release 与 Validate 三枚可验证徽章")
        validation.require(not any(phrase in readme for phrase in contract["removed_phrases"]), f"{name} 不得重新加入已删除的案例或示例输入")

        result = _markdown_h2_section(readme, contract["result_heading"])
        validation.require(all(phrase in result for phrase in contract["result_semantics"]), f"{name} 缺少明确方向、可验证的下一步和可回看的依据三项用户结果")
        validation.require(
            all(f"| **{moment}** |" in readme for moment in contract["moments"]),
            f"{name} 缺少行动前后五个具体调用时机",
        )
        validation.require(all(phrase in readme for phrase in contract["not_for"]), f"{name} 缺少不必使用完整流程、紧急情况或专业事项的自然说明")
        validation.require(all(phrase in readme for phrase in contract["plain_language"]), f"{name} 仍缺少面向普通用户的自然表达")

        workflow = _markdown_h2_section(readme, contract["workflow_heading"])
        validation.require(all(phrase in workflow for phrase in contract["workflow_semantics"]), f"{name} 缺少从真实决定到现实复判的白话工作原理")
        validation.require(contract["project_viability_scope"] in workflow, f"{name} 必须把自研与现实替代路径限定在对应项目可行性议题")
        validation.require(f"### {contract['method_heading']}" in workflow, f"{name} 缺少按需方法说明")
        validation.require(contract["base_method"] in workflow, f"{name} 必须说明每次先做基础分析")
        validation.require(contract["method_recommendation"] in workflow, f"{name} 必须说明额外方法只会按需推荐，不得写成自动加入")
        validation.require(re.search(contract["automatic_method_execution"], workflow, re.IGNORECASE) is None, f"{name} 不得在保留推荐说明的同时声称自动执行额外方法")
        validation.require(contract["core_method_intro"] in workflow, f"{name} 必须以中性分类说明两种核心方法，不得添加无证据支持的使用频率")
        validation.require(all(method in workflow for method in contract["core_methods"]), f"{name} 缺少双向钢人与失败预演两种核心方法")
        validation.require(all(method and method in workflow for method in contract["specialist_methods"]), f"{name} 专项方法必须完整来自 registry.yaml")
        validation.require(all(phrase in workflow for phrase in contract["method_boundaries"]), f"{name} 缺少方法按需推荐、用户确认或能力征求同意的说明")

        install = _markdown_h2_section(readme, contract["install_heading"])
        validation.require(contract["install_intro"] in install, f"{name} 安装入口必须邀请用户把仓库链接交给当前 Agent")
        validation.require(contract["install_prompt"] in install, f"{name} 缺少可复制的一句话安装请求")
        validation.require(contract["cli_intro"] in install, f"{name} 缺少与 Agent 安装请求衔接的 Skills CLI 入口")
        validation.require(f"```bash\n{contract['cli_command']}\n```" in install, f"{name} 缺少简洁的 Skills CLI GitHub 直装命令")
        validation.require(contract["runtime_boundary"] in install, f"{name} 必须区分文件安装与真实 runtime 验证")
        validation.require(contract["invocation_intro"] in install, f"{name} 必须以面向用户的开始使用步骤把调用方式限定在 Claude Code")
        validation.require("```text\n/think-it-through\n```" in install, f"{name} 缺少可靠显式入口")
        validation.require(
            all(phrase in install for phrase in contract["example_phrases"]),
            f"{name} 缺少体现当前产品价值的可复制使用示例",
        )
        validation.require(contract["installation_link"] in install and contract["compatibility_link"] in install, f"{name} 缺少详细安装或兼容说明链接")

        safety = _markdown_h2_section(readme, contract["safety_heading"])
        validation.require(contract["safety_intro"] in safety, f"{name} 默认安全引导必须准确限定 Skill 使用范围、具体授权和行为极性")
        validation.require(all(phrase in safety for phrase in contract["safety_phrases"]), f"{name} 缺少五项默认安全语义")
        validation.require(contract["consent_boundary"] in safety, f"{name} 缺少单项同意不扩张到其他操作的自然说明")
        validation.require(f"### {contract['more_heading']}" in safety, f"{name} 缺少更多信息入口")
        validation.require(all(group in readme for group in contract["detail_groups"]), f"{name} 缺少安装与兼容、了解边界和参与改进三组详情入口")
        validation.require(all(link in readme for link in readme_links), f"{name} 缺少普通用户所需详情链接")
        validation.require(feedback_path in readme and "Star" in readme, f"{name} 缺少反馈与克制的 Star 入口")
        validation.require(not any(token in readme for token in readme_forbidden), f"{name} 不得重新塞入安装、兼容、benchmark 或正式合同技术细节")
        validation.require(not any(asset in readme for asset in old_assets), f"{name} 不得引用已移除或旧版视觉资产")

    validation.require("[简体中文](README.md)" in readme_en, "英文 README 缺少中文切换")
    validation.require("[English](README.en.md)" in readme_zh, "中文 README 缺少英文切换")

    installation_contracts = (
        {
            "name": "docs/installation.en.md",
            "text": installation_en,
            "language_link": "[简体中文](installation.md)",
            "prompt": "Install this Skill for me: https://github.com/zemu2718/think-it-through-skill",
            "target_boundary": "all target mappings recognized by `skills@1.5.23`",
            "client_boundary": "does **not** mean every AI client",
            "installation_boundary": "installation only places files in a target directory",
        },
        {
            "name": "docs/installation.md",
            "text": installation_zh,
            "language_link": "[English](installation.en.md)",
            "prompt": "帮我安装这个 Skill：https://github.com/zemu2718/think-it-through-skill",
            "target_boundary": "`skills@1.5.23` 认识的全部目标映射",
            "client_boundary": "不表示所有 AI 客户端",
            "installation_boundary": "安装都只说明文件已经进入目标目录",
        },
    )
    for contract in installation_contracts:
        name = contract["name"]
        guide = contract["text"]
        validation.require(contract["language_link"] in guide, f"{name} 缺少双语切换")
        validation.require("不是第二份" in guide if name.endswith("installation.md") else "not a second" in guide, f"{name} 必须说明自身不是第二份合同")
        validation.require(contract["prompt"] in guide, f"{name} 缺少推荐的一句话 Agent 安装")
        validation.require(guide.find(contract["prompt"]) < guide.find("npx -y skills@1.5.23 add"), f"{name} 必须先给普通用户入口，再给技术备用方式")
        validation.require(guide.count("npx -y skills@1.5.23 add") == 2 and "--agent '*'" in guide, f"{name} 缺少固定通用安装器与全部目标入口")
        validation.require(contract["target_boundary"] in guide and contract["client_boundary"] in guide, f"{name} 缺少 --agent '*' 的真实支持边界")
        validation.require(
            "gh skill install" in guide
            and f"think-it-through@v{LATEST_PUBLISHED_VERSION}" in guide,
            f"{name} 缺少 GitHub CLI 固定版本安装",
        )
        validation.require(
            f"git clone --depth 1 --branch v{LATEST_PUBLISHED_VERSION}" in guide,
            f"{name} 缺少不可变 v{LATEST_PUBLISHED_VERSION} tag 手动安装",
        )
        validation.require("cd think-it-through-skill\ngit rev-parse HEAD\ntest ! -e" in guide, f"{name} 缺少准确 revision 与非覆盖式安装")
        validation.require("SHA256SUMS" in guide and "```text\n/think-it-through\n```" in guide, f"{name} 缺少归档核验或可靠调用方式")
        validation.require(contract["installation_boundary"] in guide and "compatibility-and-evidence" in guide, f"{name} 缺少安装不等于 runtime 验证的边界")

    release_tag_url = (
        "https://github.com/zemu2718/think-it-through-skill/releases/tag/"
        f"v{LATEST_PUBLISHED_VERSION}"
    )
    release_asset_url = (
        "https://github.com/zemu2718/think-it-through-skill/releases/download/"
        f"v{LATEST_PUBLISHED_VERSION}/think-it-through.skill"
    )
    release_sums_url = (
        "https://github.com/zemu2718/think-it-through-skill/releases/download/"
        f"v{LATEST_PUBLISHED_VERSION}/SHA256SUMS"
    )
    release_urls = {release_tag_url, release_asset_url, release_sums_url}
    compatibility_contracts = (
        {
            "name": "docs/compatibility-and-evidence.en.md",
            "text": compatibility_en,
            "language_link": "[简体中文](compatibility-and-evidence.md)",
            "release": "backed by an immutable Git tag, a GitHub Release",
            "target": "Eight installer target mappings",
            "checkpoint": "formal contract defines a lightweight contextual checkpoint",
        },
        {
            "name": "docs/compatibility-and-evidence.md",
            "text": compatibility_zh,
            "language_link": "[English](compatibility-and-evidence.en.md)",
            "release": "由不可变 Git tag、GitHub Release",
            "target": "八个安装器目标映射",
            "checkpoint": "正式合同只在 Skill 已经加载",
        },
    )
    release_url_re = re.compile(
        rf"https?://[^\s)]+/releases/(?:download|tag)/v{re.escape(LATEST_PUBLISHED_VERSION)}[^\s)]*",
        re.IGNORECASE,
    )
    for contract in compatibility_contracts:
        name = contract["name"]
        guide = contract["text"]
        validation.require(contract["language_link"] in guide, f"{name} 缺少双语切换")
        validation.require("不是第二份" in guide if name.endswith("evidence.md") else "not a second" in guide, f"{name} 必须说明自身不是第二份合同")
        found_release_urls = {match.rstrip(".,") for match in release_url_re.findall(guide)}
        validation.require(
            found_release_urls == release_urls,
            f"{name} 只能链接准确、已核验的 v{LATEST_PUBLISHED_VERSION} Release 对象",
        )
        validation.require(contract["release"] in guide, f"{name} 缺少已发布的公开对象状态")
        validation.require("not_run" in guide and "L0" in guide and "L5" in guide, f"{name} 缺少当前机器兼容状态摘要")
        validation.require(contract["target"] in guide and "runtime" in guide, f"{name} 缺少安装目标与 runtime 验证的区别")
        validation.require("9/16" in guide and "1/8" in guide and "8/8" in guide, f"{name} 缺少完整自动发现限制")
        validation.require(contract["checkpoint"] in guide, f"{name} 缺少正式上下文检查点与实测边界")
        validation.require("approved evidence" in guide and feedback_path in guide, f"{name} 缺少反馈不得自动提升兼容矩阵的边界")
        validation.require(all(path in guide for path in ("compatibility/profile.json", "compatibility/runtime-support.json", "runtime-support.schema.json", "evidence.schema.json", "benchmarks/trigger-v0.1/", "benchmarks/behavior-v0.1/", "REQUIREMENTS.md")), f"{name} 缺少机器事实源、冻结 benchmark 或正式合同链接")

    trigger_summary = _load_json(ROOT / "benchmarks" / "trigger-v0.1" / "summary.json")
    holdout_summary = trigger_summary.get("holdout", {}).get("summary", {})
    validation.require(holdout_summary == {"total": 16, "passed": 9, "failed": 7}, "冻结 trigger holdout 摘要发生变化")
    holdout = _load_json(ROOT / "benchmarks" / "trigger-v0.1" / "holdout.json")
    holdout_results = holdout.get("results", [])
    positive_passed = sum(item.get("pass") is True for item in holdout_results if item.get("should_trigger") is True)
    negative_passed = sum(item.get("pass") is True for item in holdout_results if item.get("should_trigger") is False)
    validation.require((positive_passed, negative_passed) == (1, 8), "冻结 trigger 正负例摘要发生变化")

    support = _load_json(ROOT / "compatibility" / "runtime-support.json")
    public_claim_text = "\n".join((readme_en, readme_zh, installation_en, installation_zh, compatibility_en, compatibility_zh))
    _validate_runtime_support_claims(validation, public_claim_text, support)

    for phrase in (
        f"本文档是 v{CURRENT_CONTRACT_VERSION} 的唯一正式行为、安全与验收依据",
        "结构化方法 option",
        "推荐不等于确认",
        "Evidence Gate",
        "Participation Gate",
        "用户总参与上限",
        "额外 Agent 不得递归委派",
        "不按多数票",
        "四类授权互不继承",
        "available / unavailable / unknown",
        "ready / requires_approval / requires_auth / failed",
        "主现实证据闭环",
        "DecisionRecord",
        "conversation_only",
        "四项反馈",
        "纯文本协议是跨宿主基线",
        "Skill-only / 纯文本语义映射",
        "原生兼容认证",
        "发布支持范围、内部评测状态和具体会话执行记录必须分层管理",
        "capability observation",
        "trace",
        "receipt",
        "八维 16 分 rubric",
        "14/16",
        "Draft 2020-12",
        "不改变外部世界",
        "distribution/package-manifest.json` 是精确文件集合的唯一机器事实源",
        "普通正文先自然说清",
        "assumptions` 与 `unknowns` 必须分别呈现",
        "L3～L5 只接受绑定准确 runtime version 的 `real_runtime` 证据",
        f"v{CURRENT_CONTRACT_VERSION} 是当前发布候选源码与正式产品合同",
        f"最新真实公开 tag / GitHub Release / `.skill` asset / 校验和仍是 v{LATEST_PUBLISHED_VERSION}",
        "公开发布身份只由已创建并核验的对应对象建立",
        f"v{PREVIOUS_PUBLISHED_VERSION} 继续作为历史发布保留",
        "逐客户端真实加载、纯文本行为和原生能力属于独立兼容观察",
        "不得由此推导“所有 AI 客户端已验证”",
        "PROJECT_VIABILITY",
        "grader-only",
        "问题存在、问题强度、方案适配与替代生态",
        "outcome/problem-first 与 solution/implementation-second",
        "最强现实替代",
        "承诺上限",
    ):
        validation.require(
            phrase in requirements,
            f"REQUIREMENTS.md 缺少 v{CURRENT_CONTRACT_VERSION} 当前合同或发布边界：{phrase}",
        )

    validation.require("思考搭档" in product, "PRODUCT.md 缺少稳定用户体验定位")
    validation.require(POSITIONING_ZH in product, "PRODUCT.md 缺少 canonical 中文产品定位")
    validation.require(VALUE_STATEMENT_ZH in product, "PRODUCT.md 缺少想清楚再行动的价值说明")
    for phrase in (
        "重要行动前后的**决策与证据协议**",
        "首要 ICP",
        "JTBD",
        "四层模型",
        "只有用户本轮提交的集合或明确文字形成唯一最终组合",
        "Evidence Gate",
        "Participation Gate",
        "可用额外上限 = max(0, 用户总参与上限 - 1)",
        "四类，彼此不继承",
        "主现实证据闭环",
        "决策快照",
        "纯文本仍保留完整状态",
        f"v{CURRENT_CONTRACT_VERSION} 是当前发布候选源码与正式产品合同",
        f"最新真实公开发布仍为 v{LATEST_PUBLISHED_VERSION}",
        "由其不可变 Git tag、GitHub Release、可下载 asset 与校验和共同建立身份",
        f"v{PREVIOUS_PUBLISHED_VERSION} 继续作为历史发布保留",
        "实现形态只是候选",
        "自研承担更高举证责任",
        "稳定发布状态不要求逐客户端真实验证先完成",
        "格式、发现、安装、加载、纯文本行为和原生能力分别记录",
        "原生兼容认证",
        "capability observation",
        "trace 与 receipt",
        "未运行保持 `not_run`",
        "用户安装反馈先进入复现、脱敏和审阅闭环",
    ):
        validation.require(
            phrase in product,
            f"PRODUCT.md 缺少 v{CURRENT_CONTRACT_VERSION} 产品或发布边界：{phrase}",
        )

    for phrase in (
        f"当前 v{CURRENT_CONTRACT_VERSION} 状态与交互合同",
        "Evidence Gate",
        "Participation Gate",
        "四类授权互不继承",
        "DecisionRecord",
        f"scripts/grade_contracts.py` 是 v{CURRENT_CONTRACT_VERSION} 当前评分器",
        "版本、发布范围与证据声明",
        f"v{CURRENT_CONTRACT_VERSION} 是当前发布候选源码与正式产品合同，尚未创建同名公开对象",
        f"v{LATEST_PUBLISHED_VERSION} 是最新真实公开 tag / Release / asset / 校验和",
        f"v0.2.0 与 v{PREVIOUS_PUBLISHED_VERSION} 继续作为历史发布保留",
        "PROJECT_VIABILITY` 是 grader-only sidecar stage",
        "稳定源码准入由合同、schema、fixtures、grader",
        "用户 Issue 和安装观察属于发布后反馈线索",
        "distribution/package-manifest.json` 是运行时归档精确文件集合的唯一机器事实源",
        "L3～L5 只能由绑定准确 runtime version 的 `real_runtime` 证据提升",
        "具体能力是否发生只由当前会话 capability observation",
        "文档职责必须保持单一",
        "`README.md` 是 GitHub 默认展示的精简中文用户入口",
        "`README.en.md` 是英文用户入口",
        "`docs/installation.md` 与 `docs/installation.en.md` 承接详细安装和文件核验",
        "`docs/compatibility-and-evidence.md` 与 `docs/compatibility-and-evidence.en.md` 解释公开兼容状态、冻结证据和提升边界，但不是第二份合同",
        "用户可见文档优先使用读者语言",
        "普通正文先说完整含义",
        "canonical key 与用户可见字段分离",
    ):
        validation.require(
            phrase in claude_md,
            f"CLAUDE.md 缺少 v{CURRENT_CONTRACT_VERSION} 维护或发布分层规则：{phrase}",
        )

    for phrase in (
        "普通用户第一次阅读为视角",
        "不逐句孤立修补",
        "英文独立按自然英文重写",
        "不要求逐字直译",
        "公开文档校验优先锁定结构、必要语义、命令、链接和声明边界",
        "mutation test 验证语义缺失或错误声明，而不是阻止自然润色",
    ):
        validation.require(phrase in claude_md, f"CLAUDE.md 缺少双语 README 文案维护规则：{phrase}")

    for phrase in (
        "--stage B",
        "--interaction-json /path/to/interaction-evidence.json",
        "--decision-record-json /path/to/decision-record.json",
        "--visible-snapshot-json /path/to/visible-snapshot.json",
    ):
        validation.require(phrase in claude_md, f"CLAUDE.md 缺少 B CLI 快照参数：{phrase}")

    for phrase in (
        "四类授权彼此独立",
        "无需联网",
        "不读取私有文件",
        "只使用当前主 Agent",
        "不改变外部世界",
        "不包含可执行脚本",
        "持续维护的源码",
    ):
        validation.require(phrase in security, f"SECURITY.md 缺少当前安全模型或维护政策：{phrase}")

    validation.require(
        "文档性质：非规范性架构说明与历史决策记录" in stable_architecture
        and "正式行为、安全与验收只以 [`REQUIREMENTS.md`]" in stable_architecture,
        "v0.2.0 架构文档必须保持非规范性角色和 REQUIREMENTS 唯一合同边界",
    )
    for phrase in (
        "v0.2.0 已正式发布",
        "纯文本协议是跨宿主基线",
        "Adapter 的存在本身不扩大兼容声明",
        "observation、consent、trace 与 receipt",
        "自然语言显示投影",
        "current grader 检查主现实闭环的受控句末标记",
    ):
        validation.require(phrase in stable_architecture, f"v0.2.0 架构文档缺少冻结的发布或声明治理事实：{phrase}")
    for phrase in (
        f"状态：v{PREVIOUS_PUBLISHED_VERSION} 稳定源码的非规范性架构说明",
        "distribution/package-manifest.json",
        "L0",
        "L5",
        "L2 不证明 L3",
        "not_run",
        "real_runtime",
        "普通 CI 不读取模型 provider secret",
        "不以逐客户端真实验证、Git tag、GitHub Release 或可下载 asset 为前置",
        "人工安装观察 → 版本绑定反馈 → 维护者复现",
    ):
        validation.require(
            phrase in previous_architecture,
            f"v{PREVIOUS_PUBLISHED_VERSION} 历史架构文档缺少稳定源码或兼容证据边界：{phrase}",
        )

    for phrase in (
        f"状态：v{CURRENT_ARCHITECTURE_VERSION} 当前稳定源码的非规范性架构说明",
        f"v{CURRENT_ARCHITECTURE_VERSION} 是当前稳定源码、正式产品合同和最新真实公开发布",
        "不提升任何未运行的 runtime 兼容层级",
        "不新增 Veto Gate 或协议状态",
        "四个价值维度与四种认识状态",
        "两遍搜索而不是一次关键词扫描",
        "候选发现、现实核验与试用分层",
        "独立反方为什么是条件能力",
        "承诺上限",
        "grader-only sidecar",
        "静态证据与真实执行边界",
        "references/project-viability.md",
    ):
        validation.require(
            phrase in current_architecture,
            f"v{CURRENT_ARCHITECTURE_VERSION} 架构基线缺少项目可行性或发布边界：{phrase}",
        )

    validation.require("不构成逐项实现或验收规范" in product and "REQUIREMENTS.md" in product, "PRODUCT.md 必须明确只负责产品愿景而非验收合同")
    validation.require("唯一正式行为、安全与验收依据" in requirements, "REQUIREMENTS.md 必须声明唯一正式合同角色")

    for phrase in (
        POSITIONING_ZH,
        POSITIONING_EN,
        VALUE_STATEMENT_ZH,
        VALUE_STATEMENT_EN,
        f"v{CURRENT_CONTRACT_VERSION} is the current release-candidate source and formal product contract, with no same-version public objects yet",
        f"v{LATEST_PUBLISHED_VERSION} remains the latest published immutable Git tag, GitHub Release, downloadable `think-it-through.skill`, and `SHA256SUMS`",
        f"v{PREVIOUS_PUBLISHED_VERSION} remains a historical release",
        "Publication does not promote any unrun runtime compatibility level",
        "real multi-turn behavior, natural-language discovery, external search, alternative trials, and independent-Agent behavior remain `not_run`",
        "use only three compact, verifiable status badges",
        "Do not use badges to claim runtime compatibility",
        "formal method names in everyday terms",
        "canonical 1:1 README Invocation Card at a compact width",
        "cross-host repository-URL request and concise Skills CLI GitHub-source command as parallel installation paths",
        "then the Claude Code invocation as the user-facing start step",
        "Avoid exposing internal protocol language",
        "Installation is explicitly separated from successful real-runtime execution",
        "separate the compact safety section from detail links grouped under installation and compatibility, boundaries, and improvement",
        "state safety defaults during Skill use as concrete user choices",
        "internal protocol vocabulary",
    ):
        validation.require(phrase in brand_context, f"品牌摘要缺少产品定位、README 用户路径、稳定源码或证据边界：{phrase}")

    for phrase in (
        feedback_path,
        "git rev-parse HEAD",
        "canonical compatibility evidence",
        "exact release tag or source commit",
        "API keys, tokens, private conversations",
        "SECURITY.md",
        "dist/local-package",
    ):
        validation.require(phrase in contributing, f"CONTRIBUTING.md 缺少安装反馈或本地包边界：{phrase}")

    for phrase in (
        "Installation or runtime feedback",
        "Exact runtime version",
        "Skill version and source commit",
        "Minimal reproduction steps",
        "Expected result",
        "Actual result",
        "API keys, tokens, private conversations",
        "does not become approved compatibility evidence automatically",
    ):
        validation.require(phrase in feedback_form, f"安装与 runtime Issue form 缺少必要字段或隐私边界：{phrase}")

    validation.require("dist/ci-package" in validate_workflow, "validate workflow 必须使用中性的 ci-package 输出目录")
    validation.require("ci-candidate" not in validate_workflow and "candidate archive" not in validate_workflow.lower(), "validate workflow 不得把稳定分发归档称为 candidate")

    validation.require("## [Unreleased]" in changelog, "CHANGELOG.md 必须保留 Unreleased 节")
    unreleased = changelog.split("## [Unreleased]", 1)[1].split("\n## [", 1)[0]
    validation.require(
        "显示宽度调整为 200px" in unreleased
        and "精简“明确方向”和工作原理第 3、4 步" in unreleased
        and "默认安全只描述 Skill 使用过程" in unreleased,
        "CHANGELOG.md 的 Unreleased 节缺少 README 显示、文案或默认安全范围精修记录",
    )
    validation.require(
        "用户结果 → 调用时机 → 工作原理与最小必要方法 → 安装使用 → 默认安全" in changelog
        and "只在安装区保留 `/think-it-through`" in changelog
        and "MIT License、最新 Release 与 `main` 分支 Validate 三枚可验证状态徽章" in changelog
        and "删除首屏偏内部的 Agent Skill 品类说明" in changelog
        and "将综合判断按立项前与开始后拆分表达" in changelog
        and "内部协议口吻改为普通用户能直接理解的表达" in changelog
        and "以“安装 / 开始使用”两个平行操作步骤区分跨宿主安装请求、Claude Code 调用与真实 runtime 验证" in changelog
        and "将默认安全与更多信息拆开" in changelog
        and "按安装与兼容、了解边界和参与改进分组" in changelog
        and "补充简洁的 Skills CLI GitHub 直装入口" in changelog,
        "CHANGELOG.md 缺少结果优先 README 路径、首屏精简、普通用户表达、安装边界、Skills CLI 入口或详情分组变更",
    )
    validation.require(
        f"将当前源码合同升级为 v{CURRENT_CONTRACT_VERSION} 发布候选" in unreleased
        and "闭合 `A → Gate-routing → 条件 Gate → Gate-routing → B` 回路与显式停止优先级" in unreleased
        and "四个 canonical core schema" in unreleased
        and "执行授权不再接受长期偏好代替本轮同意" in unreleased
        and "真人参与和实际发送、邀请或联系分别需要参与委派与外部行动授权" in unreleased
        and "高投入方向必须引用与现实试用一致的来源和回执" in unreleased
        and "同一次 B 用户可见输出中确定性重建 DecisionRecord 与可见决策快照" in unreleased,
        f"CHANGELOG.md 的 Unreleased 节缺少 v{CURRENT_CONTRACT_VERSION} 发布候选的关键合同、授权、证据链或 runtime smoke 记录",
    )
    validation.require(
        "Python 3.12 完整单元测试 220 项通过" in unreleased
        and "确定性仓库校验 3350 项通过" in unreleased
        and "两个独立空目录构建的 SHA-256 一致" in unreleased
        and "固定 `skills@1.5.23` 在 Node 22.20.0 下" in unreleased
        and "未运行 Claude Code / Codex provider smoke" in unreleased
        and "公开兼容矩阵继续如实保持 `not_run`" in unreleased,
        "CHANGELOG.md 的 Unreleased 节缺少 v0.4.1 发布前验证事实或未运行边界",
    )
    validation.require(
        f"v{LATEST_PUBLISHED_VERSION} 继续作为最新真实公开发布" in unreleased
        and f"v{CURRENT_CONTRACT_VERSION} 的 tag、Release 与 asset 仅在实际创建后声明" in unreleased
        and f"将 v{LATEST_PUBLISHED_VERSION} 设为当前稳定源码、正式产品合同和最新真实公开发布" in changelog
        and "同名不可变 Git tag、GitHub Release、可下载 asset 与校验和共同建立公开发布身份" in changelog
        and f"v{PREVIOUS_PUBLISHED_VERSION} 继续作为历史发布保留" in changelog,
        "CHANGELOG.md 缺少发布候选、最新公开发布与历史发布的分层说明",
    )
    validation.require(
        f"## [{CURRENT_CONTRACT_VERSION}]" not in changelog,
        f"CHANGELOG.md 不得在公开对象创建前预造 v{CURRENT_CONTRACT_VERSION} 发布记录",
    )
    validation.require(
        f"## [{PREVIOUS_PUBLISHED_VERSION}] - 2026-08-31" in changelog,
        f"CHANGELOG.md 缺少 v{PREVIOUS_PUBLISHED_VERSION} 历史发布记录",
    )
    validation.require("## [0.2.0] - 2026-08-29" in changelog, "CHANGELOG.md 缺少 v0.2.0 源码版本记录")
    validation.require("Git tag、GitHub Release 和可下载 asset" in changelog, "CHANGELOG.md 必须区分源码版本与公开 Release 对象")
    validation.require(
        f"建立 v{PREVIOUS_PUBLISHED_VERSION} 开放 Agent Skills 稳定源码" in changelog
        and f"将 v{PREVIOUS_PUBLISHED_VERSION} 设为当前稳定源码和正式产品合同" in changelog,
        f"CHANGELOG.md 缺少 v{PREVIOUS_PUBLISHED_VERSION} 历史稳定源码状态",
    )
    validation.require("反馈只有绑定准确版本、完成复现、脱敏与审阅并形成 approved evidence 后" in changelog, "CHANGELOG.md 缺少发布后反馈提升边界")
    validation.require(
        f"不可变 `v{LATEST_PUBLISHED_VERSION}` Git tag 与 GitHub Release" in changelog
        and "`think-it-through.skill` 和 `SHA256SUMS`" in changelog,
        f"CHANGELOG.md 缺少 v{LATEST_PUBLISHED_VERSION} 正式 Release 对象",
    )
    for phrase in (
        "显式调用 `/think-it-through`",
        "纯文本协议作为跨宿主基线",
        "不构成原生兼容认证",
        "28 个运行时源文件",
        "trace 和 receipt",
        "阶段 B 改为自然语言优先",
        "与稳定的 DecisionRecord schema 无损映射",
    ):
        validation.require(phrase in changelog, f"CHANGELOG.md 缺少 v0.2.0 源码版本事实：{phrase}")

    for legacy_phrase in ("本轮确认：基础分析", "本轮使用：基础分析", "三类授权", "declarative-feedback"):
        validation.require(
            legacy_phrase not in readme_zh and legacy_phrase not in requirements and legacy_phrase not in product,
            f"公开当前规范仍含旧版合同：{legacy_phrase}",
        )

def validate_trigger_benchmark(validation: Validation) -> None:
    benchmark_root = ROOT / "benchmarks" / "trigger-v0.1"
    summary_path = benchmark_root / "summary.json"
    validation.require(summary_path.exists(), "缺少自动触发 benchmark summary.json")
    if not summary_path.exists():
        return

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    validation.require(
        summary.get("final_description_sha256") == DESCRIPTION_SHA256,
        "触发 benchmark 未绑定当前冻结 description",
    )
    validation.require(summary.get("final_description_chars") == 1024, "冻结 description 长度记录不正确")
    for key, expected_file in (("dev", "dev-initial.json"), ("holdout", "holdout.json")):
        data_path = benchmark_root / expected_file
        validation.require(data_path.exists(), f"缺少触发 benchmark 文件：{expected_file}")
        if not data_path.exists():
            continue
        data = json.loads(data_path.read_text(encoding="utf-8"))
        run_summary = data.get("summary", {})
        validation.require(run_summary.get("total") == 16, f"{key} 触发集必须包含 16 条运行")
        validation.require(
            summary.get(key, {}).get("summary") == run_summary,
            f"触发 benchmark 摘要与 {expected_file} 不一致",
        )


def validate_package_source(validation: Validation) -> None:
    actual = {
        path.relative_to(SKILL_DIR).as_posix()
        for path in SKILL_DIR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    forbidden = sorted(
        relative
        for relative in actual
        if "workspace" in relative
        or relative.endswith((".pyc", ".html"))
        or relative.startswith(".claude/")
    )
    validation.require(not forbidden, f"独立 Skill 源目录含禁止分发内容：{forbidden}")
    try:
        _, manifest_files = load_manifest()
        distributable = {
            path.relative_to(SKILL_DIR).as_posix()
            for path in source_files()
        }
    except (ValueError, json.JSONDecodeError) as error:
        validation.require(False, f"分发 manifest 或源码不符合合同：{error}")
        return
    validation.require(distributable == set(manifest_files), "独立分发文件集合必须精确匹配 package manifest")


def validate_required_open_source_files(validation: Validation) -> None:
    required = {
        "README.md",
        "README.en.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "docs/product-architecture-v0.2.0.md",
        "docs/product-architecture-v0.3.0.md",
        "docs/installation.md",
        "docs/installation.en.md",
        "docs/compatibility-and-evidence.md",
        "docs/compatibility-and-evidence.en.md",
        "docs/third-party-audit.md",
        "distribution/package-manifest.json",
        "compatibility/profile.json",
        "compatibility/runtime-support.schema.json",
        "compatibility/runtime-support.json",
        "compatibility/evidence.schema.json",
        "requirements-validation.txt",
        "benchmarks/behavior-v0.1/README.md",
        "benchmarks/trigger-v0.1/README.md",
        "benchmarks/trigger-v0.1/summary.json",
        ".agents/brand-context.md",
        "assets/README.md",
        "assets/manifest.json",
        "scripts/render_assets.py",
        "scripts/test_assets.py",
        ".github/workflows/validate.yml",
        ".github/workflows/runtime-smoke.yml",
        ".github/ISSUE_TEMPLATE/install-or-runtime-feedback.yml",
        "scripts/smoke_installer.py",
        "scripts/run_runtime_smoke.py",
        "scripts/test_runtime_smoke.py",
    }
    manifest_path = ROOT / "assets" / "manifest.json"
    if manifest_path.exists():
        try:
            assets = _load_json(manifest_path).get("assets", [])
            for entry in assets if isinstance(assets, list) else []:
                for variant in entry.get("variants", []) if isinstance(entry, dict) else []:
                    if not isinstance(variant, dict):
                        continue
                    for key in ("source", "output"):
                        value = variant.get(key)
                        if isinstance(value, str):
                            required.add(value)
        except (json.JSONDecodeError, OSError) as error:
            validation.require(False, f"无法从资产 manifest 读取必需文件：{error}")
    for relative in sorted(required):
        validation.require((ROOT / relative).exists(), f"缺少开源交付文件：{relative}")


def main() -> int:
    validation = Validation()
    files = all_repo_files()
    validate_skill(validation)
    validate_json_yaml(validation, files)
    validate_core_schemas(validation)
    validate_compatibility(validation)
    validate_links(validation, files)
    validate_legal(validation)
    validate_methods(validation)
    validate_evals(validation)
    validate_assets(validation, files)
    validate_repo_hygiene(validation, files)
    validate_examples_and_benchmarks(validation)
    validate_contract_graders(validation)
    validate_public_docs(validation)
    validate_trigger_benchmark(validation)
    validate_package_source(validation)
    validate_required_open_source_files(validation)

    print(f"完成 {validation.checks} 项检查")
    if validation.errors:
        print(f"发现 {len(validation.errors)} 个错误：", file=sys.stderr)
        for error in validation.errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("仓库校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
