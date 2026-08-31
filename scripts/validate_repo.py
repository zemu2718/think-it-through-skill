#!/usr/bin/env python3
"""执行“想清楚”仓库的确定性发布前校验。"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError
from referencing import Registry, Resource

from build_distribution import load_manifest, source_files
from render_assets import check_social_preview, decoded_pixels

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "think-it-through"
SKILL_MD = SKILL_DIR / "SKILL.md"

TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".svg", ".txt"}
IGNORED_SCAN_PARTS = {".git", ".claude", "dist", "review", "think-it-through-workspace", "__pycache__"}
CURRENT_CONTRACT_VERSION = "0.3.0"
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
    ):
        validation.require(phrase in body, f"SKILL.md 缺少 v0.3.0 合同：{phrase}")
    for forbidden in (
        "本轮确认：基础分析",
        "本轮使用：基础分析",
        "可选择：按推荐继续 / 调整方法 / 只做基础分析 / 补充背景",
    ):
        validation.require(forbidden not in body, f"SKILL.md 仍包含旧版固定合同：{forbidden}")

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
        "saved_preference" in json.dumps(consent.get("allOf", []), ensure_ascii=False)
        and "private_data_access" not in json.dumps(consent.get("allOf", []), ensure_ascii=False)
        and "external_action" not in json.dumps(consent.get("allOf", []), ensure_ascii=False),
        "saved_preference 只能适用于能力或参与授权",
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
            f"README 宣称支持或验证 {claimed} 个 runtime，但矩阵只有 {fully_supported_count} 个 runtime 的 L3～L5 全部通过",
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

    readmes = (ROOT / "README.md").read_text(encoding="utf-8") + "\n" + (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    _validate_runtime_support_claims(validation, readmes, support)


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
            InteractionEvidence,
            grade_decision_record,
            grade_evidence_gate,
            grade_human_review,
            grade_participation_gate,
            grade_r,
        )
    except ImportError as error:
        validation.require(False, f"无法导入 v0.3.0 当前评分器：{error}")
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
        "failed-research-degrades-to-b",
        "public-search-does-not-authorize-private-or-external",
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
    value_case = evidence_by_id.get("user-value-does-not-enter-gate", {})
    validation.require(
        isinstance(value_case, dict)
        and value_case.get("expected_stage") == "B"
        and value_case.get("record", {}).get("unknown_type") == "user_value"
        and value_case.get("record", {}).get("capability_called") is False,
        "fixture 15 必须证明用户价值不进入 Evidence Gate",
    )
    failed_case = evidence_by_id.get("failed-research-degrades-to-b", {})
    required_outcome = failed_case.get("required_outcome", {}) if isinstance(failed_case, dict) else {}
    validation.require(
        failed_case.get("expected_stage") == "B"
        and failed_case.get("operation_status") == "failed"
        and required_outcome.get("preserve_unknown") is True
        and required_outcome.get("continue_to_b") is True
        and required_outcome.get("fabricate_result") is False
        and _is_nonempty_string(required_outcome.get("fallback")),
        "fixture 15 必须覆盖研究失败后保留未知并降级到 B",
    )

    participation_data = load("16-participation-and-human.json")
    participation_cases = participation_data.get("cases", [])
    participation_by_id = {case.get("id"): case for case in participation_cases if isinstance(case, dict)} if isinstance(participation_cases, list) else {}
    required_participation_ids = {
        "two-independent-tasks-within-total-limit",
        "total-limit-one-keeps-single-agent",
        "extra-agent-cannot-delegate-recursively",
        "human-value-cannot-be-replaced-by-agents",
        "agent-consent-does-not-authorize-search-data-or-action",
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
        validation.require(all(check.passed for check in human_checks), "fixture 16 真人参与正例必须通过 Human grader")

    adapter_data = load("17-portable-adapters-and-decision-record.json")
    record = adapter_data.get("decision_record", {})
    record_checks = grade_decision_record(record)
    validation.require(all(check.passed for check in record_checks), "fixture 17 DecisionRecord 正例必须通过当前 grader")
    visible_snapshot = adapter_data.get("visible_snapshot", {})
    required_snapshot_paths = {
        "topic",
        "true_objectives",
        "decision",
        "confirmed_methods",
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
            isinstance(item, dict) and item.get("value") == current,
            f"fixture 17 可见快照字段 {label} 未无损映射 {path}",
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

    native_fixture = trigger_dir / "fixtures" / "12-native-control-and-fallback.json"
    if native_fixture.exists():
        native_data = json.loads(native_fixture.read_text(encoding="utf-8"))
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
        expected_routes = {
            ("accept", "none"): ("end", True, False),
            ("set-aside", "none"): ("end", True, False),
            ("adjust-next-step", "none"): ("R-method", True, False),
            ("disagree", "none"): ("R-method", False, False),
            ("accept", "new-fact"): ("R-method", False, True),
            ("accept", "purpose-change"): ("R-align", False, True),
        }
        actual_routes = {
            (route.get("direction_id"), route.get("supplement_type")): (
                route.get("expected_stage"),
                route.get("preserve_judgment"),
                route.get("text_overrode_selection"),
            )
            for route in feedback_routes
            if isinstance(route, dict)
        }
        validation.require(
            expected_routes.items() <= actual_routes.items(),
            "fixture 11 缺少 B 反馈结束、调整、不同意或文字优先转移",
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
    validation.require(ux_evals_path.exists(), "缺少 evals/ux-evals.json")
    validation.require(ux_rubric_path.exists(), "缺少 evals/ux-rubric.md")
    validation.require(enhancement_rubric_path.exists(), "缺少 evals/enhancement-rubric.md")
    if ux_evals_path.exists():
        ux_data = json.loads(ux_evals_path.read_text(encoding="utf-8"))
        validation.require(ux_data.get("contract_version") == CURRENT_CONTRACT_VERSION, "ux-evals.json 版本不匹配")
        validation.require(ux_data.get("status") == "not_run", "未执行体验评测时 ux-evals.json 必须标记 not_run")
        validation.require(ux_data.get("rubric") == "ux-rubric.md", "ux-evals.json 必须绑定核心 UX rubric")
        validation.require(ux_data.get("enhancement_rubric") == "enhancement-rubric.md", "ux-evals.json 必须绑定增强 UX rubric")
        ux_evals = ux_data.get("evals", [])
        validation.require(isinstance(ux_evals, list) and len(ux_evals) >= 5, "ux-evals.json 至少需要 5 个体验场景")
        if isinstance(ux_evals, list):
            for item in ux_evals:
                if not isinstance(item, dict):
                    validation.require(False, "UX eval 项必须是对象")
                    continue
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
        ):
            validation.require(phrase in ux_experience, f"ux-evals.json 缺少 v0.2.0 体验场景：{phrase}")
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
            "B 用四项单选表达一个主要反馈方向",
            "未观察到独立附注时不假装存在备注框",
            "文本降级明确使用普通编号",
            "选择与文字冲突时准确采用文字",
            "原生反馈单选 UI：未实测 / not_run",
            "独立附注呈现：未实测 / not_run",
            "真实用户体验：未实测 / not_run",
            "`真实目的对齐`、`终端可读性`、`可纠错性`、`问题可回答性`、`用户自主权` 均不得低于 2",
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
        ):
            validation.require(phrase in enhancement, f"增强 UX rubric 缺少 v0.3.0 规则：{phrase}")

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


def _svg_structure_signature(root: ET.Element) -> tuple[tuple[str, str | None, tuple[tuple[str, str], ...]], ...]:
    geometry_attributes = {
        "cx", "cy", "d", "height", "points", "r", "rx", "ry", "viewBox", "width", "x", "x1", "x2", "y", "y1", "y2",
    }
    return tuple(
        (
            element.tag.rsplit("}", 1)[-1],
            element.get("id"),
            tuple(sorted((name, value) for name, value in element.attrib.items() if name in geometry_attributes)),
        )
        for element in root.iter()
    )


def _svg_subtree_has_attribute(element: ET.Element | None, attribute: str) -> bool:
    return element is not None and any(attribute in child.attrib for child in element.iter())


def _svg_subtree_has_path(element: ET.Element | None) -> bool:
    return element is not None and any(child.tag.rsplit("}", 1)[-1] == "path" for child in element.iter())


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
    validation.require(manifest.get("schema_version") == "1", "资产 manifest schema_version 必须是 1")
    validation.require(isinstance(entries, list), "资产 manifest 必须包含 assets 数组")
    if not isinstance(entries, list):
        return
    expected_specs = {
        "brand-mark": {
            "role": "readme-brand-mark",
            "variants": {("neutral", "light"), ("neutral", "dark")},
            "canvas": {"width": 128, "height": 128},
            "required_ids": {"input-paths", "decision-hinge", "committed-path", "reassessment-loop"},
            "max_bytes": 16384,
        },
        "decision-case": {
            "role": "readme-informational-case",
            "variants": {("en", "light"), ("en", "dark"), ("zh-CN", "light"), ("zh-CN", "dark")},
            "canvas": {"width": 1200, "height": 680},
            "required_ids": {
                "surface-request", "execution-first-path", "decision-hinge", "decision-first-path",
                "optional-gate", "outcome-set", "reassessment-loop", "synthetic-label",
            },
            "max_bytes": 65536,
        },
        "social-preview": {
            "role": "social-preview",
            "variants": {("bilingual", "dark")},
            "canvas": {"width": 1280, "height": 640},
            "required_ids": {
                "wordmark", "tagline", "input-paths", "decision-hinge", "committed-path",
                "optional-gate", "reassessment-loop",
            },
            "max_source_bytes": 49152,
            "max_output_bytes": 409600,
        },
    }
    entry_ids = [entry.get("id") for entry in entries if isinstance(entry, dict)]
    validation.require(
        entry_ids == ["brand-mark", "decision-case", "social-preview"],
        "资产 manifest 必须按职责定义 Brand Mark、Decision Case 和 Social Preview",
    )
    validation.require(len(entry_ids) == len(set(entry_ids)), "资产 manifest 的资产 ID 必须唯一")

    svg_roots: dict[Path, ET.Element] = {}
    variant_paths: dict[str, list[Path]] = {}
    declared_paths: set[Path] = {manifest_path.resolve(), (ROOT / "assets" / "README.md").resolve()}
    output_paths: list[Path] = []
    root_resolved = ROOT.resolve()
    for entry in entries:
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

    generator = next((entry.get("generator") for entry in entries if isinstance(entry, dict) and entry.get("id") == "social-preview"), None)
    validation.require(
        generator == {
            "script": "scripts/render_assets.py", "renderer": "resvg-py", "renderer_version": "0.5.0",
            "decoder": "Pillow", "decoder_version": "11.3.0", "skip_system_fonts": True, "pixel_mode": "RGBA",
        },
        "Social Preview generator 合同不正确",
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

    brand_paths = variant_paths.get("brand-mark", [])
    validation.require(len(brand_paths) == 2, "Brand Mark 必须提供 light/dark 两个变体")
    if len(brand_paths) == 2 and all(path in svg_roots for path in brand_paths):
        signatures = [_svg_structure_signature(svg_roots[path]) for path in brand_paths]
        validation.require(signatures[0] == signatures[1], "Brand Mark light/dark 必须共享相同非颜色几何")
        for path in brand_paths:
            validation.require(
                not any(element.tag.rsplit("}", 1)[-1] == "text" for element in svg_roots[path].iter()),
                "Brand Mark 不得包含 text 或依赖系统字体",
            )

    case_paths = variant_paths.get("decision-case", [])
    validation.require(len(case_paths) == 4, "Decision Case 必须提供中英文 light/dark 四个变体")
    if len(case_paths) == 4 and all(path in svg_roots for path in case_paths):
        signatures = [_svg_structure_signature(svg_roots[path]) for path in case_paths]
        validation.require(all(signature == signatures[0] for signature in signatures[1:]), "Decision Case 四个变体必须共享相同非文本几何")
        for path in case_paths:
            gate = _svg_element_by_id(svg_roots[path], "optional-gate")
            validation.require(gate is not None and "stroke-dasharray" in gate.attrib, "Decision Case 的可选 Gate 必须实际使用虚线")

    social_paths = variant_paths.get("social-preview", [])
    validation.require(len(social_paths) == 1, "Social Preview 必须只有一个 dark SVG/PNG 变体")
    if len(social_paths) == 1 and social_paths[0] in svg_roots:
        social_root = svg_roots[social_paths[0]]
        social_tags = {element.tag.rsplit("}", 1)[-1] for element in social_root.iter()}
        validation.require("text" not in social_tags, "Social Preview 不得包含 text 或依赖系统字体")
        validation.require("linearGradient" not in social_tags and "radialGradient" not in social_tags and "filter" not in social_tags, "Social Preview 不得使用 gradient 或 filter")
        validation.require(_svg_subtree_has_path(_svg_element_by_id(social_root, "wordmark")), "Social Preview wordmark 必须包含实际 path")
        validation.require(_svg_subtree_has_path(_svg_element_by_id(social_root, "tagline")), "Social Preview tagline 必须包含实际 path")
        validation.require(_svg_subtree_has_attribute(_svg_element_by_id(social_root, "optional-gate"), "stroke-dasharray"), "Social Preview 的可选 Gate 必须实际使用虚线")

    social_png = output_paths[0] if len(output_paths) == 1 else ROOT / "assets" / "social-preview.png"
    validation.require(len(output_paths) == 1, "Social Preview manifest 必须且只能声明一个 PNG 输出")
    validation.require(social_png.exists(), "缺少 Social Preview PNG")
    if social_png.exists():
        try:
            size, _ = decoded_pixels(social_png.read_bytes())
            validation.require(size == (1280, 640), "Social Preview PNG 必须是 1280×640")
        except Exception as error:
            validation.require(False, f"Social Preview PNG 无法完整解码：{error}")
    try:
        for error in check_social_preview(ROOT):
            validation.require(False, error)
    except Exception as error:
        validation.require(False, f"Social Preview 无法重渲染检查：{error}")


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
            validation.require(token in current_text, f"当前评分器缺少 v0.3.0 合同：{token}")
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


def _readme_badges(text: str) -> list[tuple[str, str, str]]:
    pattern = re.compile(r"\[!\[([^]]+)\]\((https://img\.shields\.io/[^)]+)\)\]\(([^)]+)\)")
    return pattern.findall(text)


def validate_public_docs(validation: Validation) -> None:
    current_architecture_path = f"docs/product-architecture-v{CURRENT_CONTRACT_VERSION}.md"
    public_paths = (
        "README.md", "README.zh-CN.md", "PRODUCT.md", "REQUIREMENTS.md", "SECURITY.md",
        "CONTRIBUTING.md", ".agents/brand-context.md",
        ".github/ISSUE_TEMPLATE/install-or-runtime-feedback.yml",
        ".github/workflows/validate.yml",
        "docs/product-architecture-v0.2.0.md", current_architecture_path, "CLAUDE.md",
    )
    public_docs = {relative: (ROOT / relative).read_text(encoding="utf-8") for relative in public_paths}
    readme_en = public_docs["README.md"]
    readme_zh = public_docs["README.zh-CN.md"]
    requirements = public_docs["REQUIREMENTS.md"]
    product = public_docs["PRODUCT.md"]
    claude_md = public_docs["CLAUDE.md"]
    security = public_docs["SECURITY.md"]
    contributing = public_docs["CONTRIBUTING.md"]
    brand_context = public_docs[".agents/brand-context.md"]
    feedback_form = public_docs[".github/ISSUE_TEMPLATE/install-or-runtime-feedback.yml"]
    validate_workflow = public_docs[".github/workflows/validate.yml"]
    stable_architecture = public_docs["docs/product-architecture-v0.2.0.md"]
    current_architecture = public_docs[current_architecture_path]
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    feedback_path = "issues/new?template=install-or-runtime-feedback.yml"
    shared_links = (
        "PRODUCT.md", "REQUIREMENTS.md", "skills/think-it-through/SKILL.md",
        "distribution/package-manifest.json", "compatibility/runtime-support.json",
        "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md",
    )
    readme_contracts = (
        {
            "name": "README.md",
            "text": readme_en,
            "sections": [
                "What it is", "Why it matters", "A concrete case", "When to use it", "Install and try it",
                "What happens in a full check", "Safe by default", "Version, compatibility, and evidence",
                "Documentation and contributing", "License",
            ],
            "case_assets": ("assets/decision-case-light.svg", "assets/decision-case-dark.svg"),
            "wrong_case_assets": ("assets/decision-case-light.zh-CN.svg", "assets/decision-case-dark.zh-CN.svg"),
            "case_phrases": ("Illustrative synthetic case", "not a runtime transcript", "defines no result", "reassess"),
            "safety_phrases": ("no network access", "no private-data access", "one current main agent", "no file or remote persistence", "no external action"),
            "moments": ("Before starting", "Before choosing a path", "Before committing resources", "Before doubling down", "After results arrive"),
            "boundary": ("decision layer", "not a project-management or task-execution layer"),
            "stable": "v0.3.0 is the current stable source",
            "no_release": "no public Git tag, GitHub Release",
            "checkpoint": "formal contract defines a lightweight contextual checkpoint",
            "feedback": "installation or runtime feedback",
        },
        {
            "name": "README.zh-CN.md",
            "text": readme_zh,
            "sections": [
                "这是什么", "为什么需要它", "一个具体案例", "什么时候调用", "安装并完成第一次体验",
                "一次完整检查会发生什么", "默认安全与隐私", "版本、兼容性与证据", "文档与参与", "许可证",
            ],
            "case_assets": ("assets/decision-case-light.zh-CN.svg", "assets/decision-case-dark.zh-CN.svg"),
            "wrong_case_assets": ("assets/decision-case-light.svg", "assets/decision-case-dark.svg"),
            "case_phrases": ("说明性合成案例", "不是真实 runtime transcript", "没有预设结果", "复判"),
            "safety_phrases": ("不联网", "不读取私有数据", "只使用当前主 Agent", "不写入文件或远端保存", "不执行外部行动"),
            "moments": ("立项前", "选方向前", "投入资源前", "继续加码前", "结果回来后"),
            "boundary": ("决策层", "不是项目管理或任务执行层"),
            "stable": "v0.3.0 是维护分支 `main` 上的当前稳定源码",
            "no_release": "没有公开 Git tag、GitHub Release",
            "checkpoint": "正式合同只在 Skill 已经加载",
            "feedback": "反馈安装或 runtime 问题",
        },
    )
    old_sections = {
        "A 30-second walkthrough", "Quick Start", "How it works", "What you receive", "FAQ",
        "30 秒说明性演示", "快速开始", "它如何工作", "你会得到什么", "常见问题",
    }
    old_assets = ("assets/hero-", "assets/product-value-", "assets/demo-flow")
    expected_badges = (
        ("Validate", "validate.yml?branch=main&style=flat-square&label=Validate", "actions/workflows/validate.yml?query=branch%3Amain"),
        ("Agent Skill", "type-Agent%20Skill-0F766E?style=flat-square", "skills/think-it-through/SKILL.md"),
        ("Stable source v0.3.0", "stable%20source-v0.3.0-172033?style=flat-square", "tree/main/skills/think-it-through"),
        ("MIT License", "license-MIT-172033?style=flat-square", "LICENSE"),
    )
    forbidden_badge_terms = re.compile(r"(?:release|latest|download|coverage|stars?|runtime|compatib|certif|L5|auto.?discovery)", re.IGNORECASE)

    for contract in readme_contracts:
        name = contract["name"]
        readme = contract["text"]
        sections = contract["sections"]
        headings = _markdown_h2(readme)
        validation.require(headings == sections, f"{name} 必须精确包含正式首次访问路径的十个 H2")
        validation.require(not old_sections.intersection(headings), f"{name} 不得保留旧版入口章节")
        first_h2 = readme.find("## ")
        preface = readme[:first_h2] if first_h2 >= 0 else readme
        validation.require(first_h2 > 0, f"{name} 缺少 H2 章节")
        validation.require("assets/brand-mark-light.svg" in preface and "assets/brand-mark-dark.svg" in preface, f"{name} 首屏缺少 light/dark Brand Mark")
        validation.require(all(asset in readme for asset in contract["case_assets"]), f"{name} 缺少对应语言/主题 Decision Case")
        validation.require(all(asset not in readme for asset in contract["wrong_case_assets"]), f"{name} 引用了错误语言 Decision Case")
        validation.require(not any(asset in readme for asset in old_assets), f"{name} 不得引用旧视觉资产")
        validation.require("git clone --depth 1 --branch main" in readme, f"{name} 缺少稳定 main 源码安装")
        validation.require("cd think-it-through-skill\ngit rev-parse HEAD\ntest ! -e" in readme, f"{name} 缺少安装时记录准确源码 revision 的命令")
        validation.require("```text\n/think-it-through\n```" in readme, f"{name} 缺少可靠显式入口")
        validation.require("test ! -e" in readme, f"{name} 缺少非覆盖式源码安装")
        validation.require(all(phrase in readme for phrase in contract["case_phrases"]), f"{name} 缺少合成示例、非实测、无虚构结果或现实复判边界")
        validation.require(all(phrase in readme for phrase in contract["safety_phrases"]), f"{name} 缺少五项默认安全语义")
        validation.require(
            all(f"| **{moment}** |" in readme for moment in contract["moments"]),
            f"{name} 缺少行动前后五个具体调用时机",
        )
        validation.require(all(phrase in readme for phrase in contract["boundary"]), f"{name} 缺少决策工具与执行工具边界")
        validation.require(all(link in readme for link in shared_links), f"{name} 缺少任务导向文档链接")
        validation.require(contract["stable"] in readme, f"{name} 缺少 v0.3.0 稳定源码状态")
        validation.require(contract["no_release"] in readme, f"{name} 必须诚实说明无公开 Release")
        validation.require("not_run" in readme and "L0" in readme and "L5" in readme, f"{name} 缺少当前机器兼容状态摘要")
        validation.require("9/16" in readme and "1/8" in readme and "8/8" in readme, f"{name} 缺少完整自动发现限制")
        validation.require(contract["checkpoint"] in readme, f"{name} 缺少正式上下文检查点与实测边界")
        validation.require(contract["feedback"] in readme and feedback_path in readme, f"{name} 缺少安装与 runtime 反馈入口")
        validation.require("approved evidence" in readme, f"{name} 缺少反馈不得自动提升兼容矩阵的边界")
        validation.require("Star" in readme, f"{name} 缺少克制的 Star 入口")
        validation.require("scripts/build_distribution.py" not in readme and "unzip -t" not in readme, f"{name} 不应复制维护者构建命令")
        validation.require("feat/v0.3.0-agent-skills" not in readme, f"{name} 不得引用不存在的候选分支")
        validation.require("R-align" not in readme and "R-method" not in readme and "DecisionRecord" not in readme, f"{name} 不得复制正式行为合同术语")
        badges = _readme_badges(preface)
        validation.require(len(badges) == 4, f"{name} 首屏必须恰好包含四枚功能徽章")
        if len(badges) == 4:
            for actual, expected in zip(badges, expected_badges):
                label, image, target = actual
                expected_label, image_fragment, target_fragment = expected
                validation.require(label == expected_label and image_fragment in image and target_fragment in target, f"{name} 徽章职责、URL 或目标不正确：{label}")
                validation.require("style=flat-square" in image, f"{name} 所有徽章必须使用 flat-square")
            validation.require(not any(forbidden_badge_terms.search(image + " " + label) for label, image, _ in badges), f"{name} 徽章不得宣称 Release、下载、coverage、stars、runtime、兼容认证、L5 或自动发现")
        validation.require(
            ("committed `main`" in readme and "uncommitted local work" in readme)
            if name == "README.md"
            else ("已提交 `main`" in readme and "本地未提交工作区" in readme),
            f"{name} 缺少 Validate 徽章状态边界",
        )

    validation.require("[简体中文](README.zh-CN.md)" in readme_en, "英文 README 缺少中文切换")
    validation.require("[English](README.md)" in readme_zh, "中文 README 缺少英文切换")

    trigger_summary = _load_json(ROOT / "benchmarks" / "trigger-v0.1" / "summary.json")
    holdout_summary = trigger_summary.get("holdout", {}).get("summary", {})
    validation.require(holdout_summary == {"total": 16, "passed": 9, "failed": 7}, "冻结 trigger holdout 摘要发生变化")
    holdout = _load_json(ROOT / "benchmarks" / "trigger-v0.1" / "holdout.json")
    holdout_results = holdout.get("results", [])
    positive_passed = sum(item.get("pass") is True for item in holdout_results if item.get("should_trigger") is True)
    negative_passed = sum(item.get("pass") is True for item in holdout_results if item.get("should_trigger") is False)
    validation.require((positive_passed, negative_passed) == (1, 8), "冻结 trigger 正负例摘要发生变化")

    release_asset_re = re.compile(r"https?://[^\s)]+/releases/(?:download|tag)/v0\.3\.0", re.IGNORECASE)
    validation.require(not release_asset_re.search(readme_en) and not release_asset_re.search(readme_zh), "README 不得链接不存在或未经核验的 v0.3.0 Release 对象")
    support = _load_json(ROOT / "compatibility" / "runtime-support.json")
    _validate_runtime_support_claims(validation, readme_en + "\n" + readme_zh, support)

    for phrase in (
        "本文档是 v0.3.0 的唯一正式行为、安全与验收依据",
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
        "v0.3.0 是当前稳定源码版本与正式产品合同",
        "逐客户端真实加载、纯文本行为和原生能力属于发布后的兼容观察",
        "不得由此推导“所有 AI 客户端已验证”",
    ):
        validation.require(phrase in requirements, f"REQUIREMENTS.md 缺少 v0.3.0 规则：{phrase}")

    validation.require("思考搭档" in product, "PRODUCT.md 缺少稳定用户体验定位")
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
        "v0.3.0 是当前稳定源码版本与正式产品合同",
        "稳定源码状态不要求逐客户端真实验证先完成",
        "格式、发现、安装、加载、纯文本行为和原生能力分别记录",
        "原生兼容认证",
        "capability observation",
        "trace 与 receipt",
        "未运行保持 `not_run`",
        "用户安装反馈先进入复现、脱敏和审阅闭环",
    ):
        validation.require(phrase in product, f"PRODUCT.md 缺少 v0.3.0 产品或声明边界：{phrase}")

    for phrase in (
        "当前 v0.3.0 状态与交互合同",
        "Evidence Gate",
        "Participation Gate",
        "四类授权互不继承",
        "DecisionRecord",
        "scripts/grade_contracts.py` 是 v0.3.0 当前评分器",
        "版本、发布范围与证据声明",
        "v0.3.0 是当前稳定源码版本与正式产品合同",
        "稳定源码准入由合同、schema、fixtures、grader",
        "用户 Issue 和安装观察属于发布后反馈线索",
        "distribution/package-manifest.json` 是运行时归档精确文件集合的唯一机器事实源",
        "L3～L5 只能由绑定准确 runtime version 的 `real_runtime` 证据提升",
        "具体能力是否发生只由当前会话 capability observation",
        "文档职责必须保持单一",
        "用户可见文档优先使用读者语言",
        "普通正文先说完整含义",
        "canonical key 与用户可见字段分离",
    ):
        validation.require(phrase in claude_md, f"CLAUDE.md 缺少 v0.3.0 维护规则：{phrase}")

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
        "状态：v0.3.0 稳定源码的非规范性架构说明",
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
        validation.require(phrase in current_architecture, f"v0.3.0 架构文档缺少稳定源码或兼容证据边界：{phrase}")

    validation.require("不构成逐项实现或验收规范" in product and "REQUIREMENTS.md" in product, "PRODUCT.md 必须明确只负责产品愿景而非验收合同")
    validation.require("唯一正式行为、安全与验收依据" in requirements, "REQUIREMENTS.md 必须声明唯一正式合同角色")

    for phrase in (
        "v0.3.0 is the current stable source and formal product contract",
        "no Git tag, GitHub Release, or downloadable asset is currently claimed",
        "real multi-turn behavior and natural-language discovery remain `not_run`",
    ):
        validation.require(phrase in brand_context, f"品牌摘要缺少稳定源码或证据边界：{phrase}")

    for phrase in (
        feedback_path,
        "git rev-parse HEAD",
        "canonical compatibility evidence",
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
    validation.require(f"## [{CURRENT_CONTRACT_VERSION}] - 2026-08-31" in changelog, "CHANGELOG.md 缺少 v0.3.0 稳定源码版本记录")
    validation.require("## [0.2.0] - 2026-08-29" in changelog, "CHANGELOG.md 缺少 v0.2.0 源码版本记录")
    validation.require("Git tag、GitHub Release 和可下载 asset" in changelog, "CHANGELOG.md 必须区分源码版本与公开 Release 对象")
    validation.require(
        f"建立 v{CURRENT_CONTRACT_VERSION} 开放 Agent Skills 稳定源码" in changelog
        and f"将 v{CURRENT_CONTRACT_VERSION} 设为当前稳定源码和正式产品合同" in changelog,
        "CHANGELOG.md 缺少 v0.3.0 稳定源码状态",
    )
    validation.require("反馈只有绑定准确版本、完成复现、脱敏与审阅并形成 approved evidence 后" in changelog, "CHANGELOG.md 缺少发布后反馈提升边界")
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
        "README.zh-CN.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "docs/product-architecture-v0.2.0.md",
        "docs/product-architecture-v0.3.0.md",
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
