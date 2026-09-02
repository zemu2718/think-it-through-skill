#!/usr/bin/env python3
"""验证 runtime smoke 的授权、评分证据与脱敏边界。"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from run_runtime_smoke import (
    CONTRACT_VERSION,
    FEEDBACK_OPTIONS,
    SYSTEM_PROMPT,
    TURN_PROMPTS,
    _activate_prompt,
    _codex_command,
    _grade_outputs,
    _interaction,
    _parse_visible_snapshot,
    _provider_env,
    _record_artifacts,
    _redact_text,
    RuntimeResult,
)


class RuntimeSmokeTests(unittest.TestCase):
    def test_runtime_smoke_uses_current_contract_version(self) -> None:
        self.assertEqual("0.4.1", CONTRACT_VERSION)

    def test_interaction_evidence_matches_headless_text_surface(self) -> None:
        r_interaction = _interaction("R", "method")
        self.assertEqual("unavailable", r_interaction.host_control_status)
        self.assertEqual("text-fallback", r_interaction.surface)
        self.assertFalse(r_interaction.tool_call_observed)
        self.assertEqual("multi", r_interaction.selection_mode)

        open_r_interaction = _interaction("R", "align", "open")
        self.assertEqual("free-answer", open_r_interaction.surface)
        self.assertEqual("none", open_r_interaction.selection_mode)

        a_interaction = _interaction("A")
        self.assertEqual("free-answer", a_interaction.surface)
        self.assertEqual("none", a_interaction.selection_mode)

        b_interaction = _interaction("B")
        self.assertEqual("text-fallback", b_interaction.surface)
        self.assertEqual("inline-text", b_interaction.supplement_mode)

    def test_prompts_keep_method_confirmation_in_third_turn(self) -> None:
        self.assertNotIn("基本梳理", TURN_PROMPTS[1])
        self.assertIn("基本梳理", TURN_PROMPTS[2])
        self.assertNotIn("R-align", SYSTEM_PROMPT)
        self.assertNotIn("R-method", SYSTEM_PROMPT)
        self.assertEqual(
            "/think-it-through\n" + TURN_PROMPTS[0],
            _activate_prompt("claude-code", TURN_PROMPTS[0], first_turn=True),
        )
        self.assertEqual(
            "$think-it-through\n" + TURN_PROMPTS[0],
            _activate_prompt("codex", TURN_PROMPTS[0], first_turn=True),
        )
        self.assertEqual(
            TURN_PROMPTS[1],
            _activate_prompt("codex", TURN_PROMPTS[1], first_turn=False),
        )

    def test_codex_resume_uses_only_resume_supported_options(self) -> None:
        project = Path("<project>")
        output = project / "last-message.txt"
        initial = _codex_command(
            "codex",
            "first",
            project=project,
            output_file=output,
            model="model-name",
            session_id=None,
        )
        resumed = _codex_command(
            "codex",
            "next",
            project=project,
            output_file=output,
            model="model-name",
            session_id="session-id",
        )
        self.assertEqual(["codex", "exec", "--sandbox", "read-only", "--cd"], initial[:5])
        self.assertEqual(["codex", "exec", "resume"], resumed[:3])
        self.assertNotIn("--sandbox", resumed)
        self.assertNotIn("--cd", resumed)
        self.assertIn("--ignore-user-config", resumed)
        self.assertIn("--ignore-rules", resumed)

    def test_provider_env_keeps_only_selected_provider_secret(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "anthropic-secret",
                "OPENAI_API_KEY": "openai-secret",
            },
            clear=False,
        ):
            home = Path(directory)
            claude_env = _provider_env("claude-code", home)
            codex_env = _provider_env("codex", home)
        self.assertIn("ANTHROPIC_API_KEY", claude_env)
        self.assertNotIn("OPENAI_API_KEY", claude_env)
        self.assertIn("OPENAI_API_KEY", codex_env)
        self.assertNotIn("ANTHROPIC_API_KEY", codex_env)

    def test_redaction_removes_secret_and_personal_paths(self) -> None:
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-secret-value-123456"}):
            text = "/Users/test/repo sk-ant-secret-value-123456"
            redacted = _redact_text(text, {"/Users/test": "<home>"})
        self.assertNotIn("/Users/test", redacted)
        self.assertNotIn("secret-value", redacted)
        self.assertIn("<home>", redacted)

    @staticmethod
    def synthetic_outputs() -> tuple[str, ...]:
        return (
            """我目前的暂定理解是，你想做排班工具，但这次真正想得到或保护什么还没说清；你可以直接补充或纠正。\n\n你这次最想通过这件事得到或保护什么？""",
            """你要确认陌生店主是否愿意为现有版本付费，并在证据出现前避免继续投入；本轮真正要决定的是是否值得继续。基本梳理已经足够，不需要额外方法。\n\n当前组合始终包含基本梳理。\n\n可多选，也可以不选，直接加入、取消、替换或纠正；我会等待你的最终组合再继续。\n\n这轮保留哪些思考角度？\n\n[只做基本梳理]\n[加入双向钢人]""",
            """这轮就先做基本梳理。真正的分歧不是工具能否做出来，而是什么现实反应足以推翻继续投入；最关键变量是陌生店主的付费反应。\n\n什么现实结果会让你放弃继续投入？""",
            """按目前信息，更合适的是先用真实付费反应验证，而不是继续投入（当前判断：小步验证）。

陌生店主明确拒付会削弱继续投入的依据；出现真实付款则会反转这个判断。

### 先用现实结果校准方向

这一步要弄清的是，现有版本能否带来足以区分方向的付费反应（核心假设）。

先向符合画像的陌生店主展示现有版本并邀请真实付款（本轮动作）。

真实付款支持继续，明确拒付反对继续（观察信号）。

出现真实付款时重新决定是否推进；持续只有明确拒付时停止新增投入（复判条件）。

## 决策快照

记录版本："0.4.1"
这次要想清楚的事："是否继续投入面向小商家的排班工具"
真正想得到或保护的结果：["确认陌生店主是否愿意为现有版本付费", "在获得真实付费证据前避免继续投入"]
本轮需要决定什么："是否先验证陌生店主的真实付费反应，再决定是否继续投入"
本轮采用的思考角度：["basic-analysis"]
当前判断："small_test"
目前更合适的方向："先验证真实付款，不继续追加开发投入"
为什么这样判断：["陌生店主的真实付费反应仍是会改变决定的最大未知", "继续开发本身不能消除这个未知"]
判断成立的前提：["现有版本足以让陌生店主判断核心价值"]
已经确认的信息：["用户希望在没有真实付费证据前停止继续投入"]
根据现有信息可以推断：["继续追加功能暂时不能提高对真实付费意愿的判断力"]
当前判断仍依赖：["现有版本足以展示排班工具的核心价值"]
仍不知道的关键问题：["符合画像的陌生店主是否愿意为现有版本真实付款"]
本轮依据来自哪里：[]
什么情况会改变判断：["出现符合画像的陌生店主真实付款"]
要弄清什么："现有版本是否解决了陌生店主愿意付费的排班问题"
先做什么："向符合画像的陌生店主展示现有版本并邀请真实付款"
看哪些现实信号："记录真实付款、明确拒付和拒付理由"
什么时候重新决定："出现真实付款时复判是否推进；持续只有明确拒付时停止新增投入"
用户给定的实验边界：[]
系统建议的实验边界：[]
何时触发复判：["出现真实付款", "持续只有明确拒付"]
本轮参与者与使用的能力：{"main_agents":1,"additional_agents_planned":0,"additional_agents_started":0,"additional_agents_completed":0,"additional_agents_failed":0,"human_participants_requested":[],"capabilities_used":[],"private_data_accessed":false,"external_action_executed":false,"consent_ids":[],"receipt_ids":[],"conflicts_and_gaps":[]}
这份记录保存在哪里：{"mode":"conversation_only","authorized":false}

### 反馈

当前无法显示原生单选。请回复一个编号或方向，也可以在同一条消息补充说明。

1. 方向符合我
2. 调整下一步
3. 不同意这个判断
4. 暂时先放一放""",
        )

    def test_synthetic_valid_outputs_pass_current_graders(self) -> None:
        reports, decision_record, visible_snapshot = _grade_outputs(
            self.synthetic_outputs()
        )
        failures = [report for report in reports if not report["passed"]]
        self.assertEqual([], failures)
        self.assertEqual("是否继续投入面向小商家的排班工具", decision_record["topic"])
        self.assertEqual("basic-analysis", decision_record["confirmed_methods"][0])
        self.assertEqual(decision_record["topic"], visible_snapshot["这次要想清楚的事"]["value"])
        self.assertEqual(4, len(FEEDBACK_OPTIONS))

    def test_grade_outputs_extracts_b_sidecars_from_same_output(self) -> None:
        reports, decision_record, visible_snapshot = _grade_outputs(
            self.synthetic_outputs()
        )
        self.assertTrue(all(report["passed"] for report in reports))
        self.assertEqual("0.4.1", decision_record["contract_version"])
        self.assertEqual(
            decision_record["evidence"]["unknowns"],
            visible_snapshot["仍不知道的关键问题"]["value"],
        )

        missing_snapshot = list(self.synthetic_outputs())
        missing_snapshot[-1] = missing_snapshot[-1].replace(
            '仍不知道的关键问题：["符合画像的陌生店主是否愿意为现有版本真实付款"]\n',
            "",
        )
        with self.assertRaisesRegex(ValueError, "字段不完整"):
            _grade_outputs(tuple(missing_snapshot))

    def test_snapshot_parser_rejects_non_json_or_extra_fields(self) -> None:
        output = self.synthetic_outputs()[-1]
        malformed = output.replace('记录版本："0.4.1"', "记录版本：0.4.1")
        with self.assertRaisesRegex(ValueError, "不是单行 JSON"):
            _parse_visible_snapshot(malformed)

        extra = output.replace(
            "这份记录保存在哪里：{\"mode\":\"conversation_only\",\"authorized\":false}",
            "这份记录保存在哪里：{\"mode\":\"conversation_only\",\"authorized\":false}\n额外字段：\"不允许\"",
        )
        with self.assertRaisesRegex(ValueError, "包含额外内容"):
            _parse_visible_snapshot(extra)

    def test_record_artifacts_preserves_extracted_sidecars(self) -> None:
        outputs = self.synthetic_outputs()
        reports, decision_record, visible_snapshot = _grade_outputs(outputs)
        result = RuntimeResult(
            "session-secret",
            outputs,
            tuple({"turn": turn} for turn in range(1, 5)),
            tuple(("runtime", "<prompt>") for _ in range(4)),
        )
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "candidate"
            _record_artifacts(
                output_dir,
                "claude-code",
                "test-version",
                "a" * 40,
                "b" * 64,
                result,
                reports,
                decision_record,
                visible_snapshot,
                "2026-09-03T00:00:00Z",
            )
            evidence = json.loads((output_dir / "evidence.json").read_text())
            self.assertEqual(
                {
                    "transcript.json",
                    "grader-report.json",
                    "trace-summary.json",
                    "decision-record.json",
                    "visible-snapshot.json",
                    "turn-1.md",
                    "turn-2.md",
                    "turn-3.md",
                    "turn-4.md",
                },
                {artifact["path"] for artifact in evidence["artifacts"]},
            )
            self.assertEqual(
                decision_record,
                json.loads((output_dir / "decision-record.json").read_text()),
            )
            self.assertEqual(
                visible_snapshot,
                json.loads((output_dir / "visible-snapshot.json").read_text()),
            )

    def test_output_directory_can_be_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate"
            self.assertFalse(path.exists())
            path.mkdir()
            self.assertTrue(path.is_dir())


if __name__ == "__main__":
    unittest.main()
