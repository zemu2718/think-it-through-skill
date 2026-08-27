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
EXPECTED_FIXTURE_STAGES = {"R", "A", "B", "direct", "emergency"}
DESCRIPTION_SHA256 = "f89f3d1fca11641e925a6f2e27b487ddd182789a0bea4f7ae3a3d197e4c6f3d3"
EXPECTED_PACKAGE_FILES = {
    "LICENSE",
    "SKILL.md",
    "THIRD_PARTY_NOTICES.md",
    "examples/partnership-boundary.md",
    "examples/saas-validation.md",
    "references/core-analysis.md",
    "references/external-validation.md",
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
    "use_when",
    "do_not_use_when",
    "inputs",
    "outputs",
    "relationships",
    "provenance",
    "test_status",
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
    methods = data.get("methods", []) if isinstance(data, dict) else []
    validation.require(isinstance(methods, list), "registry.yaml 的 methods 必须为数组")
    if not isinstance(methods, list):
        return
    ids: list[str] = []
    for method in methods:
        validation.require(isinstance(method, dict), "每个方法注册项必须为对象")
        if not isinstance(method, dict):
            continue
        missing = sorted(REQUIRED_METHOD_FIELDS - set(method))
        validation.require(not missing, f"方法 {method.get('id', '<unknown>')} 缺少字段：{missing}")
        method_id = method.get("id")
        if isinstance(method_id, str):
            ids.append(method_id)
        file_name = method.get("file")
        validation.require(isinstance(file_name, str) and (registry_path.parent / file_name).exists(), f"方法 {method_id} 引用文件不存在：{file_name}")
    validation.require(len(ids) == len(set(ids)), "方法注册表 ID 必须唯一")

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

    for path in sorted((trigger_dir / "fixtures").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        turns = data.get("turns", data.get("cases", []))
        validation.require(bool(turns), f"fixture {path.name} 没有 turns 或 cases")
        for turn in turns:
            stage = turn.get("expected_stage") if isinstance(turn, dict) else None
            validation.require(stage in EXPECTED_FIXTURE_STAGES, f"fixture {path.name} 含非法阶段：{stage}")


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
