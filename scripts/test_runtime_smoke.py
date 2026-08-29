#!/usr/bin/env python3
"""验证 runtime smoke 的授权、评分证据与脱敏边界。"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from run_runtime_smoke import (
    FEEDBACK_OPTIONS,
    SYSTEM_PROMPT,
    TURN_PROMPTS,
    _activate_prompt,
    _codex_command,
    _grade_outputs,
    _interaction,
    _provider_env,
    _redact_text,
)


class RuntimeSmokeTests(unittest.TestCase):
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

    def test_synthetic_valid_outputs_pass_current_graders(self) -> None:
        outputs = (
            """我目前的暂定理解是，你想做排班工具，但这次真正想得到或保护什么还没说清；你可以直接补充或纠正。\n\n你这次最想通过这件事得到或保护什么？""",
            """你要确认陌生店主是否愿意为现有版本付费，并在证据出现前避免继续投入；本轮真正要决定的是是否值得继续。基本梳理已经足够，不需要额外方法。\n\n当前组合始终包含基本梳理。\n\n可多选，也可以不选，直接加入、取消、替换或纠正；我会等待你的最终组合再继续。\n\n这轮保留哪些思考角度？\n\n[只做基本梳理]\n[加入双向钢人]""",
            """这轮就先做基本梳理。真正的分歧不是工具能否做出来，而是什么现实反应足以推翻继续投入；最关键变量是陌生店主的付费反应。\n\n什么现实结果会让你放弃继续投入？""",
            """按目前信息，更合适的是先用真实付费反应验证，而不是继续投入（当前判断：小步验证）。\n\n陌生店主明确拒付会削弱继续投入的依据；出现真实付款则会反转这个判断。\n\n### 先用现实结果校准方向\n\n这一步要弄清的是，现有版本能否带来足以区分方向的付费反应（核心假设）。\n\n先向符合画像的陌生店主展示现有版本并邀请真实付款（本轮动作）。\n\n真实付款支持继续，明确拒付反对继续（观察信号）。\n\n出现真实付款时重新决定是否推进；持续只有明确拒付时停止新增投入（复判条件）。\n\n## 决策快照\n\n- 议题：是否继续投入排班工具\n- 真正目的：先确认陌生店主的真实付费意愿\n- 本轮决定：先验证，不继续追加投入\n- 判断：小步验证\n- 事实：尚无陌生店主付款\n- 推断：拒付会削弱继续依据\n- 假设：现有版本足以展示核心价值\n- 未知：陌生店主是否付款\n- 来源：本轮对话\n- 反转信号：出现真实付款\n- 主实验：展示现有版本并邀请付款\n- 复判触发：付款或明确拒付\n- 参与与能力：单 Agent、零外部调用\n- 持久化：仅当前对话\n\n### 反馈\n\n当前无法显示原生单选。请回复一个编号或方向，也可以在同一条消息补充说明。\n\n1. 方向符合我\n2. 调整下一步\n3. 不同意这个判断\n4. 暂时先放一放""",
        )
        reports = _grade_outputs(outputs)
        failures = [report for report in reports if not report["passed"]]
        self.assertEqual([], failures)
        self.assertEqual(4, len(FEEDBACK_OPTIONS))

    def test_output_directory_can_be_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate"
            self.assertFalse(path.exists())
            path.mkdir()
            self.assertTrue(path.is_dir())


if __name__ == "__main__":
    unittest.main()
