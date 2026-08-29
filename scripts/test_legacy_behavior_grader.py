#!/usr/bin/env python3
"""保护冻结的 v0.1 行为评分路径不受当前合同演进影响。"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import grade_behavior_runs
from grade_contracts_v0_1 import grade_a as grade_a_v0_1

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = ROOT / "benchmarks" / "behavior-v0.1"
TRANSCRIPT_HASHES = {
    1: "4531b893b5473dd33560b68e9085e0e1ef77d1ed54dc773f5fee5cb647b3e538",
    2: "652522301b251065c4d85fec8bfbc92d531d39e5cf6a86c91c896e5e47cc832c",
    3: "fc5b3a813051b37132b8fda368e23bc2b9e1f0a4208a2af5aa5392888dd824c1",
}


class LegacyBehaviorGraderTests(unittest.TestCase):
    @staticmethod
    def _eval_dir(eval_id: int) -> Path:
        matches = list(BENCHMARK_DIR.glob(f"eval-{eval_id}-*"))
        if len(matches) != 1:
            raise AssertionError(f"eval {eval_id} 冻结目录数量异常：{matches}")
        return matches[0]

    @staticmethod
    def _copy_run_to_legacy_layout(source: Path, target: Path) -> None:
        for configuration in ("with_skill", "without_skill"):
            source_run = source / configuration
            target_run = target / configuration / "run-1"
            target_outputs = target_run / "outputs"
            target_outputs.mkdir(parents=True)
            (target_outputs / "transcript.md").write_bytes(
                (source_run / "transcript.md").read_bytes()
            )
            grading = source_run / "grading.json"
            if grading.exists():
                (target_run / "grading.json").write_bytes(grading.read_bytes())

    def test_behavior_grader_explicitly_uses_frozen_module(self) -> None:
        self.assertEqual("grade_contracts_v0_1", grade_behavior_runs.grade_a.__module__)

    def test_frozen_grader_does_not_include_current_method_echo_contract(self) -> None:
        names = [check.text for check in grade_a_v0_1("哪个证据会改变决定？")]
        self.assertNotIn("阶段 A 自然回显最终确认的方法组合", names)

    def test_frozen_with_skill_transcript_hashes(self) -> None:
        for eval_id, expected_hash in TRANSCRIPT_HASHES.items():
            path = self._eval_dir(eval_id) / "with_skill" / "transcript.md"
            self.assertEqual(expected_hash, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_legacy_regrade_matches_frozen_expectations(self) -> None:
        for eval_id in (1, 2, 3):
            run_dir = self._eval_dir(eval_id) / "with_skill"
            transcript = (run_dir / "transcript.md").read_text(encoding="utf-8")
            actual = grade_behavior_runs.grade_run(eval_id, transcript)
            frozen = json.loads((run_dir / "grading.json").read_text(encoding="utf-8"))
            self.assertEqual(frozen["expectations"], actual["expectations"], f"eval {eval_id}")
            self.assertEqual(frozen["summary"], actual["summary"], f"eval {eval_id}")

    def test_regrading_writes_only_requested_workspace(self) -> None:
        source = self._eval_dir(1)
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / source.name
            target.mkdir()
            (target / "eval_metadata.json").write_bytes((source / "eval_metadata.json").read_bytes())
            self._copy_run_to_legacy_layout(source, target)
            original_argv = grade_behavior_runs.argparse.ArgumentParser.parse_args
            try:
                grade_behavior_runs.argparse.ArgumentParser.parse_args = lambda _self: type(
                    "Args", (), {"iteration_dir": Path(temp_dir)}
                )()
                self.assertEqual(0, grade_behavior_runs.main())
            finally:
                grade_behavior_runs.argparse.ArgumentParser.parse_args = original_argv
            self.assertTrue((target / "with_skill" / "run-1" / "grading.json").exists())


if __name__ == "__main__":
    unittest.main()
