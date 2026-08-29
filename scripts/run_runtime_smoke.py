#!/usr/bin/env python3
"""在明确授权后运行 Claude Code 或 Codex 的四轮真实 runtime smoke。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_distribution import ROOT, SKILL_DIR, build_archive, load_manifest
from grade_contracts import InteractionEvidence, grade

CONTRACT_VERSION = "0.3.0"
AUTHORIZATION_PHRASE = "I_AUTHORIZE_PROVIDER_CALLS"
OUTPUT_ROOT = ROOT / "dist" / "runtime-smoke"
FEEDBACK_OPTIONS = (
    "方向符合我",
    "调整下一步",
    "不同意这个判断",
    "暂时先放一放",
)
SECRET_ENV_NAMES = {
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "OPENAI_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "AZURE_OPENAI_API_KEY",
}

SYSTEM_PROMPT = """这是已安装 Skill 的隔离 runtime smoke。
必须显式激活当前项目安装的 think-it-through Skill，并遵守其中定义的纯文本交互。
当前是没有原生选择控件和外部工具的 headless 文本界面；不要搜索、读取文件、调用额外 Agent、访问私有数据、持久化或执行外部行动，也不要声称执行过这些能力。
每轮只输出 Skill 在当前对话状态要求的用户可见内容，不解释测试 harness，也不要输出隐藏思维链。
"""

TURN_PROMPTS = (
    """我想做一个面向小商家的排班工具。现在请先帮我想清楚，但我还没说这次最想保护或得到什么。""",
    """我最想确认陌生店主是否真的愿意为现有版本付费；在没有这个证据前，我不想继续投入。""",
    """我确认这轮只做基本梳理，不加入额外方法。""",
    """会让我放弃继续投入的现实结果是：陌生店主明确拒绝为现有版本付费。""",
)

ACTIVATION_PROMPTS = {
    "claude-code": "/think-it-through\n{prompt}",
    "codex": "$think-it-through\n{prompt}",
}


@dataclass(frozen=True)
class RuntimeResult:
    session_id: str
    outputs: tuple[str, ...]
    trace_events: tuple[dict[str, Any], ...]
    commands: tuple[tuple[str, ...], ...]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )
    if completed.returncode:
        raise RuntimeError(
            f"runtime 命令失败（exit={completed.returncode}）：{command[0]}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def _clean_source_commit() -> str:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.strip()
    if status:
        raise RuntimeError("真实 runtime evidence 必须绑定干净且已提交的源码；当前工作区仍有改动")
    return commit


def _runtime_command_name(runtime: str) -> str:
    return "claude" if runtime == "claude-code" else "codex"


def _runtime_executable(runtime: str) -> str:
    executable = shutil.which(_runtime_command_name(runtime))
    if executable is None:
        raise FileNotFoundError(f"找不到 {runtime} CLI")
    return executable


def _activate_prompt(runtime: str, prompt: str, *, first_turn: bool) -> str:
    if not first_turn:
        return prompt
    return ACTIVATION_PROMPTS[runtime].format(prompt=prompt)


def _runtime_version(runtime: str) -> str:
    executable = _runtime_executable(runtime)
    completed = subprocess.run(
        [executable, "--version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )
    return completed.stdout.strip()


def _build_candidate(temporary: Path) -> tuple[Path, str]:
    archive = temporary / "think-it-through.skill"
    build_archive(archive)
    return archive, _sha256(archive)


def _install_candidate(archive: Path, project: Path, runtime: str) -> Path:
    skill_dir = project / (".claude/skills" if runtime == "claude-code" else ".agents/skills") / "think-it-through"
    skill_dir.mkdir(parents=True)
    _, files = load_manifest()
    with zipfile.ZipFile(archive) as package:
        for relative in files:
            destination = skill_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(package.read(f"think-it-through/{relative}"))
    for relative in files:
        if (skill_dir / relative).read_bytes() != (SKILL_DIR / relative).read_bytes():
            raise ValueError(f"runtime candidate 安装内容不一致：{relative}")
    return skill_dir


def _provider_env(runtime: str, home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["NO_COLOR"] = "1"
    if runtime == "claude-code":
        env.pop("OPENAI_API_KEY", None)
        if not any(env.get(name) for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")):
            raise RuntimeError("Claude Code smoke 需要通过环境变量提供 Anthropic provider 凭据")
    else:
        for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
            env.pop(name, None)
        target_home = home / ".codex"
        target_home.mkdir(parents=True)
        if not env.get("OPENAI_API_KEY"):
            raise RuntimeError("Codex smoke 需要通过 OPENAI_API_KEY 环境变量提供 provider 凭据")
        env["CODEX_HOME"] = str(target_home)
    return env


def _claude_turn(
    prompt: str,
    *,
    project: Path,
    env: dict[str, str],
    model: str | None,
    session_id: str | None,
    timeout: int,
    max_budget_usd: str,
) -> tuple[str, str, dict[str, Any], tuple[str, ...]]:
    command = [
        _runtime_executable("claude-code"),
        "--print",
        "--output-format",
        "json",
        "--permission-mode",
        "dontAsk",
        "--tools",
        "",
        "--bare",
        "--no-chrome",
        "--max-budget-usd",
        max_budget_usd,
        "--append-system-prompt",
        SYSTEM_PROMPT,
    ]
    if model:
        command.extend(["--model", model])
    if session_id:
        command.extend(["--resume", session_id])
    command.append(prompt)
    completed = _run(command, cwd=project, env=env, timeout=timeout)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("Claude Code stdout 不是有效 JSON") from error
    output = payload.get("result")
    resolved_session = payload.get("session_id")
    if not isinstance(output, str) or not output.strip():
        raise ValueError("Claude Code JSON 缺少非空 result")
    if not isinstance(resolved_session, str) or not resolved_session:
        raise ValueError("Claude Code JSON 缺少 session_id")
    trace = {
        "turn": 0,
        "session_id": resolved_session,
        "subtype": payload.get("subtype"),
        "is_error": payload.get("is_error"),
        "num_turns": payload.get("num_turns"),
        "duration_ms": payload.get("duration_ms"),
        "total_cost_usd": payload.get("total_cost_usd"),
    }
    recorded_command = tuple(
        _runtime_command_name("claude-code") if index == 0 else "<prompt>" if index == len(command) - 1 else value
        for index, value in enumerate(command)
    )
    return output.strip(), resolved_session, trace, recorded_command


def _codex_session_id(events: list[dict[str, Any]]) -> str:
    for event in events:
        if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
            return str(event["thread_id"])
        if event.get("type") == "session_meta":
            payload = event.get("payload")
            if isinstance(payload, dict):
                candidate = payload.get("session_id") or payload.get("id")
                if isinstance(candidate, str):
                    return candidate
    raise ValueError("Codex JSONL 缺少 thread/session id")


def _codex_command(
    executable: str,
    prompt: str,
    *,
    project: Path,
    output_file: Path,
    model: str | None,
    session_id: str | None,
) -> list[str]:
    shared = [
        "--ignore-user-config",
        "--ignore-rules",
        "--json",
        "--output-last-message",
        str(output_file),
    ]
    if model:
        shared.extend(["--model", model])
    if session_id is None:
        return [
            executable,
            "exec",
            "--sandbox",
            "read-only",
            "--cd",
            str(project),
            *shared,
            prompt,
        ]
    return [executable, "exec", "resume", *shared, session_id, prompt]


def _codex_turn(
    prompt: str,
    *,
    project: Path,
    env: dict[str, str],
    model: str | None,
    session_id: str | None,
    timeout: int,
    turn: int,
) -> tuple[str, str, dict[str, Any], tuple[str, ...]]:
    output_file = project / f".runtime-smoke-turn-{turn}.txt"
    full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}" if session_id is None else prompt
    command = _codex_command(
        _runtime_executable("codex"),
        full_prompt,
        project=project,
        output_file=output_file,
        model=model,
        session_id=session_id,
    )
    completed = _run(command, cwd=project, env=env, timeout=timeout)
    try:
        events = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    except json.JSONDecodeError as error:
        raise ValueError("Codex stdout 不是有效 JSONL") from error
    resolved_session = session_id or _codex_session_id(events)
    output = output_file.read_text(encoding="utf-8").strip()
    output_file.unlink(missing_ok=True)
    if not output:
        raise ValueError("Codex 未生成非空 final message")
    event_types = [str(event.get("type")) for event in events]
    trace = {
        "turn": turn,
        "session_id": resolved_session,
        "event_types": event_types,
        "event_count": len(events),
    }
    redacted_command = tuple(
        _runtime_command_name("codex")
        if index == 0
        else "<project>"
        if value == str(project)
        else "<output>"
        if value == str(output_file)
        else "<prompt>"
        if value == full_prompt
        else value
        for index, value in enumerate(command)
    )
    return output, resolved_session, trace, redacted_command


def _interaction(
    stage: str,
    r_mode: str | None = None,
    answer_shape: str | None = None,
) -> InteractionEvidence:
    if stage == "A" or (stage == "R" and answer_shape == "open"):
        return InteractionEvidence(
            host_control_status="unavailable",
            surface="free-answer",
            tool_call_observed=False,
            selection_mode="none",
            options=(),
            host_free_text_available=True,
            question_text="",
            supplement_mode="none",
        )
    return InteractionEvidence(
        host_control_status="unavailable",
        surface="text-fallback",
        tool_call_observed=False,
        selection_mode="multi" if stage == "R" else "single",
        options=(),
        host_free_text_available=False,
        question_text="",
        supplement_mode="none" if stage == "R" else "inline-text",
    )


def _grade_outputs(outputs: tuple[str, ...]) -> list[dict[str, Any]]:
    specifications = (
        ("R", "align", "open", [], []),
        ("R", "method", "compatible-set", [], []),
        ("A", "method", "open", ["basic-analysis"], []),
        ("B", "method", None, [], []),
    )
    reports: list[dict[str, Any]] = []
    for index, (stage, r_mode, answer_shape, confirmed, recommended) in enumerate(specifications):
        checks = grade(
            stage,
            outputs[index],
            False,
            [],
            confirmed,
            recommended,
            [],
            r_mode,
            _interaction(stage, r_mode, answer_shape),
            answer_shape,
        )
        failed = [check.text for check in checks if not check.passed]
        reports.append(
            {
                "turn": index + 1,
                "stage": "R-align" if index == 0 else "R-method" if index == 1 else stage,
                "passed": not failed,
                "failed_expectations": failed,
                "expectations": [
                    {"text": check.text, "passed": check.passed, "evidence": check.evidence}
                    for check in checks
                ],
            }
        )
    return reports


def _redact_text(text: str, replacements: dict[str, str]) -> str:
    redacted = text
    for value, marker in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        if value:
            redacted = redacted.replace(value, marker)
    for name in SECRET_ENV_NAMES:
        value = os.environ.get(name)
        if value:
            redacted = redacted.replace(value, f"<{name}>")
    redacted = re.sub(r"(?i)(?:sk-ant-|sk-proj-|sk-)[A-Za-z0-9_-]{12,}", "<secret>", redacted)
    return redacted


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _record_artifacts(
    output_dir: Path,
    runtime: str,
    runtime_version: str,
    source_commit: str,
    package_sha: str,
    result: RuntimeResult,
    reports: list[dict[str, Any]],
    recorded_at: str,
) -> None:
    output_dir.mkdir(parents=True)
    replacements = {
        str(ROOT): "<repo>",
        str(Path.home()): "<home>",
        result.session_id: "<session-id>",
    }
    transcript = [
        {
            "turn": index + 1,
            "user": TURN_PROMPTS[index],
            "assistant": output,
        }
        for index, output in enumerate(result.outputs)
    ]
    redacted_transcript = json.loads(_redact_text(json.dumps(transcript, ensure_ascii=False), replacements))
    redacted_trace = json.loads(_redact_text(json.dumps(result.trace_events, ensure_ascii=False), replacements))
    redacted_reports = json.loads(
        _redact_text(json.dumps(reports, ensure_ascii=False), replacements)
    )
    _write_json(output_dir / "transcript.json", redacted_transcript)
    _write_json(output_dir / "grader-report.json", redacted_reports)
    _write_json(output_dir / "trace-summary.json", redacted_trace)
    for index, output in enumerate(result.outputs, 1):
        (output_dir / f"turn-{index}.md").write_text(
            _redact_text(output, replacements).rstrip() + "\n",
            encoding="utf-8",
        )

    artifacts = []
    for name in ("transcript.json", "grader-report.json", "trace-summary.json"):
        media_type = "application/json"
        artifacts.append({"path": name, "media_type": media_type, "sha256": _sha256(output_dir / name)})
    artifacts.extend(
        {
            "path": f"turn-{index}.md",
            "media_type": "text/markdown",
            "sha256": _sha256(output_dir / f"turn-{index}.md"),
        }
        for index in range(1, len(result.outputs) + 1)
    )
    passed = all(report["passed"] for report in reports)
    evidence = {
        "schema_version": "1",
        "evidence_id": f"{runtime}-runtime-smoke-{source_commit[:12]}",
        "kind": "real_runtime",
        "skill": {"id": "think-it-through", "version": CONTRACT_VERSION},
        "source_commit": source_commit,
        "package_sha256": package_sha,
        "runtime": {"id": runtime, "version": runtime_version},
        "environment": {
            "os": platform.system().lower(),
            "arch": platform.machine(),
            "network_used": True,
        },
        "levels": ["L3", "L4"],
        "cases": [
            {
                "id": "explicit-load",
                "level": "L3",
                "status": "passed" if result.outputs else "failed",
                "command_argv": list(result.commands[0]),
                "assertions": [
                    "使用该 runtime 的显式 Skill 语法激活 think-it-through",
                    "首轮输出及后续三轮输出共享同一 session",
                ],
                "notes": "加载结论来自显式激活与同会话行为；candidate evidence 仍需人工审阅 runtime trace。",
            },
            {
                "id": "portable-text-flow",
                "level": "L4",
                "status": "passed" if passed else "failed",
                "command_argv": [runtime, "<same-session-four-turn-smoke>"],
                "assertions": ["R-align、R-method、A、B 均由当前 v0.3.0 grader 评分"],
                "notes": "candidate evidence；人工审阅前不得提升 runtime-support.json",
            },
        ],
        "artifacts": artifacts,
        "redaction": {
            "secrets_removed": True,
            "personal_paths_removed": True,
            "unrelated_data_removed": True,
            "notes": "只保存用户输入、最终回答、非内容 trace 摘要与 grader 报告；不保存隐藏思维链。",
        },
        "review": {
            "status": "candidate",
            "reviewed_by": "runtime-smoke-harness",
            "reviewed_at": recorded_at,
        },
        "recorded_at": recorded_at,
    }
    _write_json(output_dir / "evidence.json", evidence)
    print(f"已生成 candidate evidence：{output_dir / 'evidence.json'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", choices=("claude-code", "codex"), required=True)
    parser.add_argument("--authorize-provider-calls", required=True)
    parser.add_argument("--expected-version")
    parser.add_argument("--model")
    parser.add_argument("--max-budget-usd", default="1.00")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    if args.authorize_provider_calls != AUTHORIZATION_PHRASE:
        parser.error(
            f"真实 provider smoke 需要显式传入 --authorize-provider-calls {AUTHORIZATION_PHRASE}"
        )
    source_commit = _clean_source_commit()
    runtime_version = _runtime_version(args.runtime)
    if args.expected_version and args.expected_version not in runtime_version:
        raise RuntimeError(
            f"runtime version 不匹配：期望包含 {args.expected_version!r}，实际为 {runtime_version!r}"
        )

    recorded_at = _utc_now()
    run_id = f"{args.runtime}-{recorded_at[:19].replace(':', '').replace('-', '')}-{uuid.uuid4().hex[:8]}"
    output_dir = (args.output_dir or OUTPUT_ROOT / run_id).resolve()
    if output_dir.exists():
        raise FileExistsError(f"拒绝覆盖已有 runtime smoke 目录：{output_dir}")

    with tempfile.TemporaryDirectory(prefix=f"think-it-through-{args.runtime}-") as temporary:
        temporary_path = Path(temporary)
        project = temporary_path / "project"
        home = temporary_path / "home"
        project.mkdir()
        home.mkdir()
        subprocess.run(["git", "init", "--quiet"], cwd=project, check=True)
        archive, package_sha = _build_candidate(temporary_path)
        _install_candidate(archive, project, args.runtime)
        env = _provider_env(args.runtime, home)

        outputs: list[str] = []
        traces: list[dict[str, Any]] = []
        commands: list[tuple[str, ...]] = []
        session_id: str | None = None
        for turn, prompt in enumerate(TURN_PROMPTS, 1):
            runtime_prompt = _activate_prompt(args.runtime, prompt, first_turn=turn == 1)
            if args.runtime == "claude-code":
                output, session_id, trace, command = _claude_turn(
                    runtime_prompt,
                    project=project,
                    env=env,
                    model=args.model,
                    session_id=session_id,
                    timeout=args.timeout_seconds,
                    max_budget_usd=args.max_budget_usd,
                )
            else:
                output, session_id, trace, command = _codex_turn(
                    runtime_prompt,
                    project=project,
                    env=env,
                    model=args.model,
                    session_id=session_id,
                    timeout=args.timeout_seconds,
                    turn=turn,
                )
            trace["turn"] = turn
            outputs.append(output)
            traces.append(trace)
            commands.append(command)

        if session_id is None:
            raise RuntimeError("runtime smoke 未建立 session")
        result = RuntimeResult(session_id, tuple(outputs), tuple(traces), tuple(commands))
        reports = _grade_outputs(result.outputs)
        _record_artifacts(
            output_dir,
            args.runtime,
            runtime_version,
            source_commit,
            package_sha,
            result,
            reports,
            recorded_at,
        )
    return 0 if all(report["passed"] for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
