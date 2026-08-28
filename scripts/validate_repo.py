#!/usr/bin/env python3
"""执行“想清楚”仓库的确定性发布前校验。"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "think-it-through"
SKILL_MD = SKILL_DIR / "SKILL.md"

TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".svg", ".txt"}
IGNORED_SCAN_PARTS = {".git", ".claude", "dist", "review", "think-it-through-workspace", "__pycache__"}
CURRENT_CONTRACT_VERSION = "0.1.3"
LEGACY_BEHAVIOR_PROFILE = "legacy-v0.1"
EXPECTED_FIXTURE_STAGES = {"R", "A", "B", "direct", "emergency"}
INTERACTIVE_FIXTURE_STAGES = {"R", "A", "B"}
EXPECTED_INTERACTION_SURFACES = {
    "R": {"native-control", "text-fallback"},
    "A": {"native-control", "text-fallback", "free-answer"},
    "B": {"declarative-feedback"},
}
EXPECTED_SELECTION_MODES = {"multi", "single", "none"}
DESCRIPTION_SHA256 = "f89f3d1fca11641e925a6f2e27b487ddd182789a0bea4f7ae3a3d197e4c6f3d3"
EXPECTED_PACKAGE_FILES = {
    "LICENSE",
    "SKILL.md",
    "THIRD_PARTY_NOTICES.md",
    "examples/partnership-boundary.md",
    "examples/saas-validation.md",
    "references/core-analysis.md",
    "references/external-validation.md",
    "references/interaction-ux.md",
    "references/method-selection.md",
    "references/pre-mortem.md",
    "references/safety-boundaries.md",
    "references/two-sided-steelman.md",
    "references/methods/boundary-contracts.md",
    "references/methods/communication-fit.md",
    "references/methods/evidence-loop.md",
    "references/methods/object-calibration.md",
    "references/methods/registry.yaml",
    "references/methods/resource-leverage.md",
    "references/methods/stage-fit.md",
    "references/methods/system-bottleneck.md",
}
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
    skill_metadata = metadata.get("metadata")
    validation.require(isinstance(skill_metadata, dict), "Skill metadata 必须是对象")
    if isinstance(skill_metadata, dict):
        validation.require(
            str(skill_metadata.get("version")) == CURRENT_CONTRACT_VERSION,
            f"Skill 版本必须为 {CURRENT_CONTRACT_VERSION}",
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
        "优先实际调用原生控件",
        "不得仅因 Markdown",
        "自由文字为准",
        "原生控件使用多选",
        "使用原生多选提交最终组合",
        "原生单选",
        "开放答案不得调用选择控件",
        "不使用 `AskUserQuestion`",
        "产品不得自行创建“其他”或 `Other` 选项",
        "加入 X",
        "自然回显",
        "一个答案槽",
        "不得自行植入",
        "先做这一件事",
        "动作 / 观察 / 复判",
        "建议边界",
        "不自称朋友、导师或教练",
    ):
        validation.require(phrase in body, f"SKILL.md 缺少 v0.1.3 原生交互合同：{phrase}")
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
            "不得仅因为 Markdown",
            "R-align 的目的可能并存，使用多选",
            "R-method 的方法天然可组合",
            "A 的答案天然有限且互斥时使用单选",
            "开放答案不调用选择控件",
            "B 不使用问题型控件",
            "产品不得自行创建名为“其他”或 `Other`",
            "宿主自动提供的 `Other` 是自由输入能力",
            "选择和自由文字冲突时，以自由文字为准",
            "不形成第四阶段",
        ):
            validation.require(phrase in interaction, f"interaction-ux.md 缺少 v0.1.3 交互规则：{phrase}")

    method_selection_path = SKILL_DIR / "references" / "method-selection.md"
    validation.require(method_selection_path.exists(), "缺少 references/method-selection.md")
    if method_selection_path.exists():
        method_selection = method_selection_path.read_text(encoding="utf-8")
        for phrase in (
            "优先实际调用该工具提交最终组合",
            "2～4 个相关方法作为原生多选候选",
            "基础分析是唯一有效路径",
            "工具不可用、调用失败或被拒绝时不重试",
            "宿主自动提供的 `Other` 是自由输入能力",
        ):
            validation.require(phrase in method_selection, f"method-selection.md 缺少 v0.1.3 规则：{phrase}")


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


def validate_links(validation: Validation, files: list[Path]) -> None:
    link_re = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    for path in files:
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        for target in link_re.findall(text):
            target = target.strip().split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
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
                selection_control in {"available", "unavailable", "failed"},
                f"fixture {path.name} 第 {index} 项 selection_control 非法：{selection_control}",
            )
            validation.require(
                isinstance(host_free_text, bool),
                f"fixture {path.name} 第 {index} 项 host_free_text 必须为布尔值",
            )

            surface = expected_interaction.get("surface")
            selection_mode = expected_interaction.get("selection_mode")
            tool_call_observed = expected_interaction.get("tool_call_observed")
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
            if surface == "native-control":
                validation.require(selection_control == "available", f"fixture {path.name} 原生控件必须声明宿主可用")
                validation.require(tool_call_observed is True, f"fixture {path.name} 原生控件必须观察到工具调用")
                validation.require(selection_mode in {"multi", "single"}, f"fixture {path.name} 原生控件必须声明 single 或 multi")
                validation.require(host_free_text is True, f"fixture {path.name} 原生控件场景必须保留宿主自由输入")
                validation.require(
                    expected_interaction.get("host_free_text_available") is True,
                    f"fixture {path.name} 原生控件预期必须声明 host_free_text_available=true",
                )
                validation.require(
                    expected_interaction.get("product_other_forbidden") is True,
                    f"fixture {path.name} 原生控件预期必须禁止产品自建 Other",
                )
            elif surface == "text-fallback":
                validation.require(
                    selection_control in {"unavailable", "failed"},
                    f"fixture {path.name} 文本降级只能发生在控件不可用或失败后",
                )
                validation.require(tool_call_observed is False, f"fixture {path.name} 文本降级不得声称工具调用成功")
                validation.require(selection_mode in {"multi", "single"}, f"fixture {path.name} 文本降级必须保留选择语义")
            elif surface == "free-answer":
                validation.require(stage == "A", f"fixture {path.name} 只有 A 可使用 free-answer")
                validation.require(tool_call_observed is False and selection_mode == "none", f"fixture {path.name} 开放 A 不得调用选择控件")
                validation.require(turn.get("answer_shape") == "open", f"fixture {path.name} free-answer 必须声明 answer_shape=open")
            elif surface == "declarative-feedback":
                validation.require(stage == "B", f"fixture {path.name} 只有 B 可使用 declarative-feedback")
                validation.require(tool_call_observed is False and selection_mode == "none", f"fixture {path.name} B 不得调用问题型控件")
                validation.require(not expected_interaction.get("question_text", ""), f"fixture {path.name} B 不得包含问题文本")

            if stage == "R":
                expected_r_mode = "multi" if turn.get("r_mode") == "align" else turn.get("method_selection_mode", "multi")
                validation.require(
                    selection_mode == expected_r_mode,
                    f"fixture {path.name} 的 R 选择形态应为 {expected_r_mode}，当前为 {selection_mode}",
                )
            elif stage == "A" and turn.get("answer_shape") == "finite-mutually-exclusive":
                validation.require(surface in {"native-control", "text-fallback"} and selection_mode == "single", f"fixture {path.name} 有限互斥 A 必须使用单选")
            elif stage == "B":
                validation.require(surface == "declarative-feedback" and selection_mode == "none", f"fixture {path.name} 的 B 必须是陈述式反馈")

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

    ux_evals_path = trigger_dir / "ux-evals.json"
    ux_rubric_path = trigger_dir / "ux-rubric.md"
    validation.require(ux_evals_path.exists(), "缺少 evals/ux-evals.json")
    validation.require(ux_rubric_path.exists(), "缺少 evals/ux-rubric.md")
    if ux_evals_path.exists():
        ux_data = json.loads(ux_evals_path.read_text(encoding="utf-8"))
        validation.require(ux_data.get("contract_version") == CURRENT_CONTRACT_VERSION, "ux-evals.json 版本不匹配")
        validation.require(ux_data.get("status") == "not_run", "未执行体验评测时 ux-evals.json 必须标记 not_run")
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
            "declarative-feedback:none",
        ):
            validation.require(
                required_interaction in ux_interactions,
                f"ux-evals.json 缺少交互形态：{required_interaction}",
            )
    if ux_rubric_path.exists():
        rubric = ux_rubric_path.read_text(encoding="utf-8")
        for dimension in (
            "真实目的对齐",
            "可纠错性",
            "认知负担",
            "对话自然度",
            "方法透明度",
            "问题可回答性",
            "信任校准",
            "用户自主权",
            "行动转化",
        ):
            validation.require(dimension in rubric, f"UX rubric 缺少维度：{dimension}")
        validation.require("18" in rubric and "not_run" in rubric, "UX rubric 必须保留 18 分门槛与 not_run 边界")
        for phrase in (
            "普通 Markdown、线框示意或静态文案不能证明控件已实际调用",
            "R-align 与可组合的 R-method 使用多选",
            "有限互斥的 A 使用单选",
            "开放 A 直接自由回答",
            "B 给一个阶段匹配的判断和一个现实实验",
        ):
            validation.require(phrase in rubric, f"UX rubric 缺少 v0.1.3 证据或分流规则：{phrase}")

    legacy_rubric_path = trigger_dir / "rubric.md"
    if legacy_rubric_path.exists():
        legacy_rubric = legacy_rubric_path.read_text(encoding="utf-8")
        validation.require("20 分行为评测" in legacy_rubric, "原行为 rubric 必须保留 20 分历史角色")
        validation.require("互不覆盖、互不重解释" in legacy_rubric, "行为与 UX rubric 必须明确互不重解释")


def validate_assets(validation: Validation, files: list[Path]) -> None:
    for path in files:
        if path.suffix != ".svg":
            continue
        text = path.read_text(encoding="utf-8")
        validation.require("<script" not in text.lower(), f"SVG {path.relative_to(ROOT)} 不得包含脚本")
        validation.require(not re.search(r"(?:href|src)=[\"']https?://", text, re.IGNORECASE), f"SVG {path.relative_to(ROOT)} 不得引用远程资源")
        validation.require("<title" in text and "<desc" in text, f"SVG {path.relative_to(ROOT)} 必须包含 title 和 desc")


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

    for example_name, eval_name in (
        ("saas-validation.md", "eval-1-saas-misalignment"),
        ("partnership-boundary.md", "eval-3-partnership-safety"),
    ):
        example = SKILL_DIR / "examples" / example_name
        transcript = benchmark_root / eval_name / "with_skill" / "transcript.md"
        validation.require(example.exists() and transcript.exists(), f"缺少示例或原始 transcript：{example_name}")
        if example.exists() and transcript.exists():
            example_text = example.read_text(encoding="utf-8")
            transcript_text = transcript.read_text(encoding="utf-8").strip()
            validation.require(transcript_text in example_text, f"示例 {example_name} 必须包含逐字评测 transcript")


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
        validation.require("class InteractionEvidence:" in current_text, "当前评分器缺少 InteractionEvidence")
        validation.require("def parse_interaction_evidence(" in current_text, "当前评分器缺少交互证据解析函数")
        validation.require(
            'parser.add_argument("--interaction-json", type=Path, required=True' in current_text,
            "当前评分器必须把 --interaction-json 设为必填",
        )
        for token in (
            '"native-control"',
            '"text-fallback"',
            '"free-answer"',
            '"declarative-feedback"',
            '"multi"',
            '"single"',
            '"none"',
            '"finite-mutually-exclusive"',
            '"open"',
            "PRODUCT_OTHER_RE",
            "host_free_text_available",
        ):
            validation.require(token in current_text, f"当前评分器缺少 v0.1.3 交互合同：{token}")
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


def validate_public_docs(validation: Validation) -> None:
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    requirements = (ROOT / "REQUIREMENTS.md").read_text(encoding="utf-8")
    product = (ROOT / "PRODUCT.md").read_text(encoding="utf-8")
    for name, text in (("README.md", readme_en), ("README.zh-CN.md", readme_zh)):
        validation.require(f"v{CURRENT_CONTRACT_VERSION}" in text, f"{name} 缺少当前版本说明")
        validation.require("not_run" in text, f"{name} 必须如实说明 v{CURRENT_CONTRACT_VERSION} 体验未实测")
        validation.require("/think-it-through" in text, f"{name} 缺少显式调用命令")
        validation.require("assets/demo-flow.svg" in text, f"{name} 缺少用户流程图")
        validation.require("R-align" in text and "R-method" in text, f"{name} 缺少后台状态边界")
    for phrase in (
        "原生控件",
        "Markdown",
        "多选",
        "单选",
        "开放",
        "Other",
        "一个现实实验",
    ):
        validation.require(phrase in requirements, f"REQUIREMENTS.md 缺少 v0.1.3 规则：{phrase}")
    validation.require("先接住我" in product and "思考搭档" in product, "PRODUCT.md 缺少用户可感知体验与稳定身份")
    for phrase in (
        "优先实际调用",
        "原生多选",
        "原生单选",
        "不调用选择控件",
        "问题型控件",
        "宿主自动提供的 `Other`",
        "未实测 / not_run",
    ):
        validation.require(phrase in product, f"PRODUCT.md 缺少 v0.1.3 原生交互或证据边界：{phrase}")
    for legacy_phrase in ("本轮确认：基础分析", "本轮使用：基础分析"):
        validation.require(legacy_phrase not in readme_zh and legacy_phrase not in requirements, f"公开当前规范仍含旧版回显：{legacy_phrase}")


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
    distributable = actual - {relative for relative in actual if relative.startswith("evals/")}
    validation.require(distributable == EXPECTED_PACKAGE_FILES, f"独立分发文件集合不匹配：{sorted(distributable ^ EXPECTED_PACKAGE_FILES)}")


def validate_required_open_source_files(validation: Validation) -> None:
    for relative in (
        "README.md",
        "README.zh-CN.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "docs/third-party-audit.md",
        "benchmarks/behavior-v0.1/README.md",
        "benchmarks/trigger-v0.1/README.md",
        "benchmarks/trigger-v0.1/summary.json",
        "assets/hero.png",
        "assets/demo-flow.svg",
        "assets/social-preview.png",
        ".github/workflows/validate.yml",
    ):
        validation.require((ROOT / relative).exists(), f"缺少开源交付文件：{relative}")


def main() -> int:
    validation = Validation()
    files = all_repo_files()
    validate_skill(validation)
    validate_json_yaml(validation, files)
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
