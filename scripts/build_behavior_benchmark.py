#!/usr/bin/env python3
"""从行为评分生成诚实、可复核且与官方 viewer 兼容的 benchmark。"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONFIGURATIONS = ("with_skill", "without_skill")


def calculate_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}
    mean = sum(values) / len(values)
    if len(values) > 1:
        variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
        stddev = math.sqrt(variance)
    else:
        stddev = 0.0
    return {
        "mean": round(mean, 4),
        "stddev": round(stddev, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def load_runs(iteration_dir: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for eval_dir in sorted(iteration_dir.glob("eval-*")):
        metadata_path = eval_dir / "eval_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        eval_id = int(metadata["eval_id"])
        eval_name = str(metadata.get("eval_name", eval_dir.name))

        for configuration in CONFIGURATIONS:
            for run_dir in sorted((eval_dir / configuration).glob("run-*")):
                run_number = int(run_dir.name.split("-")[-1])
                grading_path = run_dir / "grading.json"
                grading = json.loads(grading_path.read_text(encoding="utf-8"))
                semantic_path = run_dir / "semantic-rubric.json"
                semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
                summary = grading["summary"]
                metrics = grading.get("execution_metrics", {})
                notes = grading.get("user_notes_summary", {})
                run_notes = [
                    *notes.get("uncertainties", []),
                    *notes.get("needs_review", []),
                    *notes.get("workarounds", []),
                ]
                runs.append({
                    "eval_id": eval_id,
                    "eval_name": eval_name,
                    "configuration": configuration,
                    "run_number": run_number,
                    "result": {
                        "pass_rate": summary["pass_rate"],
                        "passed": summary["passed"],
                        "failed": summary["failed"],
                        "total": summary["total"],
                        "semantic_score": semantic["score"],
                        "semantic_max_score": semantic["max_score"],
                        "semantic_passed": semantic["passed"],
                        "tool_calls": metrics.get("total_tool_calls", 0),
                        "errors": metrics.get("errors_encountered", 0),
                    },
                    "expectations": grading["expectations"],
                    "semantic_rubric": semantic,
                    "notes": run_notes,
                })
    return runs


def summarize(runs: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for configuration in CONFIGURATIONS:
        configuration_runs = [
            run for run in runs if run["configuration"] == configuration
        ]
        rates = [float(run["result"]["pass_rate"]) for run in configuration_runs]
        semantic_rates = [
            float(run["result"]["semantic_score"])
            / float(run["result"]["semantic_max_score"])
            for run in configuration_runs
        ]
        summary[configuration] = {
            "pass_rate": calculate_stats(rates),
            "semantic_score_rate": calculate_stats(semantic_rates),
            "semantic_runs_passed": sum(
                bool(run["result"]["semantic_passed"]) for run in configuration_runs
            ),
            "semantic_runs_total": len(configuration_runs),
        }

    contract_delta = (
        summary["with_skill"]["pass_rate"]["mean"]
        - summary["without_skill"]["pass_rate"]["mean"]
    )
    semantic_delta = (
        summary["with_skill"]["semantic_score_rate"]["mean"]
        - summary["without_skill"]["semantic_score_rate"]["mean"]
    )
    summary["delta"] = {
        "pass_rate": f"{contract_delta:+.2f}",
        "semantic_score_rate": f"{semantic_delta:+.2f}",
    }
    return summary


def render_markdown(benchmark: dict[str, Any]) -> str:
    summary = benchmark["run_summary"]
    with_skill = summary["with_skill"]["pass_rate"]
    without_skill = summary["without_skill"]["pass_rate"]
    semantic_with = summary["with_skill"]["semantic_score_rate"]
    semantic_without = summary["without_skill"]["semantic_score_rate"]
    lines = [
        "# Behavior Benchmark: think-it-through",
        "",
        f"**Date**: {benchmark['metadata']['timestamp']}",
        "**Scope**: 3 paired, three-turn scenarios; one run per scenario and configuration",
        "",
        "| Metric | With Skill | Without Skill | Delta |",
        "| --- | ---: | ---: | ---: |",
        (
            f"| Contract assertion pass rate | {with_skill['mean'] * 100:.1f}% "
            f"| {without_skill['mean'] * 100:.1f}% | {summary['delta']['pass_rate']} |"
        ),
        (
            f"| Semantic rubric score | {semantic_with['mean'] * 100:.1f}% "
            f"| {semantic_without['mean'] * 100:.1f}% "
            f"| {summary['delta']['semantic_score_rate']} |"
        ),
        (
            "| Runs passing the full semantic gate | "
            f"{summary['with_skill']['semantic_runs_passed']}/"
            f"{summary['with_skill']['semantic_runs_total']} | "
            f"{summary['without_skill']['semantic_runs_passed']}/"
            f"{summary['without_skill']['semantic_runs_total']} | — |"
        ),
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {note}" for note in benchmark["notes"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iteration_dir", type=Path)
    parser.add_argument("--timestamp", help="ISO 8601 UTC 时间；省略时使用当前时间")
    args = parser.parse_args()

    runs = load_runs(args.iteration_dir)
    if not runs:
        raise ValueError(f"未找到评分运行：{args.iteration_dir}")

    counts = {
        configuration: sum(run["configuration"] == configuration for run in runs)
        for configuration in CONFIGURATIONS
    }
    if len(set(counts.values())) != 1:
        raise ValueError(f"配置运行数不一致：{counts}")

    timestamp = args.timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    benchmark = {
        "metadata": {
            "skill_name": "think-it-through",
            "skill_path": "skills/think-it-through",
            "executor_model": "session-reported Claude Fable 5",
            "analyzer_model": "deterministic contract checks plus an explicit 20-point rubric review",
            "timestamp": timestamp,
            "evals_run": sorted({run["eval_id"] for run in runs}),
            "runs_per_configuration": 1,
        },
        "runs": runs,
        "run_summary": summarize(runs),
        "notes": [
            "每个场景、每种配置仅运行一次；结果用于合同回归，不表示总体能力或统计显著性。",
            "运行模型名称来自会话运行时报告，未通过独立 API 元数据核验；严格独立 baseline 未读取仓库、Skill、评测定义或既有 transcript。",
            "合同断言由确定性检查和保守场景检查组成；20 分语义 rubric 由主评审逐维度复核，并绑定 transcript SHA-256。",
            "完整语义门槛要求无严重失败、总分至少 18/20，且问题质量、B 判断、用户控制与安全均为 2 分。",
            "运行时未为所有运行暴露可比 token；with_skill 的分段 wall-clock 也不可可靠测量，因此不比较时间或 token。",
            "无 Skill 基线也常能给出有用建议；此 benchmark 只检验 R→A→B 等明确产品合同及对应 rubric，不是笼统回答质量排名。",
        ],
    }

    json_path = args.iteration_dir / "benchmark.json"
    md_path = args.iteration_dir / "benchmark.md"
    json_path.write_text(json.dumps(benchmark, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(benchmark), encoding="utf-8")
    print(f"已生成 {json_path}")
    print(f"已生成 {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
