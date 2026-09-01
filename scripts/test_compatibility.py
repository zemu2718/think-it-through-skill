#!/usr/bin/env python3
"""验证兼容矩阵的证据提升、版本与公开声明边界。"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from validate_repo import (
    ROOT,
    RUNTIME_SUPPORT_CLAIM_RE,
    Validation,
    _validate_runtime_support_claims,
    validate_compatibility,
)


class CompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        compatibility = ROOT / "compatibility"
        self.profile = json.loads((compatibility / "profile.json").read_text())
        self.support = json.loads((compatibility / "runtime-support.json").read_text())
        self.schema = json.loads((compatibility / "runtime-support.schema.json").read_text())
        self.evidence_schema = json.loads((compatibility / "evidence.schema.json").read_text())

    def test_canonical_compatibility_files_validate(self) -> None:
        validation = Validation()
        validate_compatibility(validation)
        self.assertEqual([], validation.errors)

    def test_not_run_cannot_reference_evidence(self) -> None:
        from jsonschema import Draft202012Validator

        support = copy.deepcopy(self.support)
        support["runtimes"][0]["levels"]["L3"]["evidence_refs"] = [
            "evidence/claude-code/test/evidence.json"
        ]
        errors = list(Draft202012Validator(self.schema).iter_errors(support))
        self.assertTrue(any("expected to be empty" in error.message for error in errors))

    def test_local_harness_cannot_promote_runtime_levels(self) -> None:
        allowed = {
            level
            for level, kinds in self.profile["evidence_policy"].items()
            if "local_harness" in kinds
        }
        self.assertEqual({"L1", "L2"}, allowed)
        self.assertFalse({"L3", "L4", "L5"} & allowed)

    def test_runtime_version_required_only_after_runtime_execution(self) -> None:
        for runtime in self.support["runtimes"]:
            self.assertIsNone(runtime["runtime_version"])
            self.assertTrue(
                all(runtime["levels"][level]["status"] == "not_run" for level in ("L3", "L4", "L5"))
            )

    def test_codebuddy_and_workbuddy_are_one_family(self) -> None:
        rows = [
            runtime
            for runtime in self.support["runtimes"]
            if "CodeBuddy" in runtime["aliases"] or "WorkBuddy" in runtime["aliases"]
        ]
        self.assertEqual(1, len(rows))
        self.assertEqual("codebuddy-workbuddy", rows[0]["id"])
        self.assertEqual("codebuddy", rows[0]["installer_target"])

    def test_artifact_path_schema_rejects_parent_traversal(self) -> None:
        from jsonschema import Draft202012Validator

        evidence = self._minimal_evidence("static", "L0")
        evidence["artifacts"] = [
            {
                "path": "../transcript.jsonl",
                "media_type": "application/x-ndjson",
                "sha256": "0" * 64,
            }
        ]
        errors = list(Draft202012Validator(self.evidence_schema).iter_errors(evidence))
        self.assertTrue(any("does not match" in error.message for error in errors))

    def test_candidate_evidence_cannot_promote_support_matrix(self) -> None:
        for runtime in self.support["runtimes"]:
            for result in runtime["levels"].values():
                self.assertEqual([], result["evidence_refs"])

    def test_candidate_evidence_reference_is_rejected(self) -> None:
        support = copy.deepcopy(self.support)
        commit = "1" * 40
        package_sha = "2" * 64
        support["source_commit"] = commit
        support["package_sha256"] = package_sha
        runtime = support["runtimes"][0]
        runtime["levels"]["L0"] = {
            "status": "passed",
            "evidence_refs": ["evidence/static/candidate/evidence.json"],
        }
        evidence = self._minimal_evidence("static", "L0")
        evidence["source_commit"] = commit
        evidence["package_sha256"] = package_sha
        evidence["review"]["status"] = "candidate"
        validation = self._validate_mutated_compatibility(support, evidence, "static/candidate")
        self.assertTrue(any("只能引用 approved evidence" in error for error in validation.errors))

    def test_support_status_must_match_evidence_case_status(self) -> None:
        support = copy.deepcopy(self.support)
        commit = "1" * 40
        package_sha = "2" * 64
        support["source_commit"] = commit
        support["package_sha256"] = package_sha
        runtime = support["runtimes"][0]
        runtime["levels"]["L0"] = {
            "status": "failed",
            "evidence_refs": ["evidence/static/mismatch/evidence.json"],
        }
        evidence = self._minimal_evidence("static", "L0")
        evidence["source_commit"] = commit
        evidence["package_sha256"] = package_sha
        validation = self._validate_mutated_compatibility(support, evidence, "static/mismatch")
        self.assertTrue(any("矩阵状态 failed" in error for error in validation.errors))

    def test_unreferenced_historical_evidence_is_preserved(self) -> None:
        evidence = self._minimal_evidence("static", "L0")
        evidence["source_commit"] = "1" * 40
        evidence["package_sha256"] = "2" * 64
        validation = self._validate_mutated_compatibility(
            copy.deepcopy(self.support), evidence, "static/historical"
        )
        self.assertEqual([], validation.errors)

    def test_wrong_artifact_sha_is_detectable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "report.json"
            artifact.write_text("{}")
            expected = "0" * 64
            actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
            self.assertNotEqual(expected, actual)

    def test_forbidden_runtime_claim_patterns(self) -> None:
        for claim in (
            "Supports 50+ runtimes",
            "77 verified runtimes",
            "Compatible with 12 runtimes",
            "已支持 50+ 个 runtime",
            "77 个已验证 runtime",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(RUNTIME_SUPPORT_CLAIM_RE.search(claim))
        self.assertIsNone(
            RUNTIME_SUPPORT_CLAIM_RE.search(
                "八个安装器 target 已做本地安装 smoke；runtime 行为尚未实测"
            )
        )

    def test_runtime_claim_guard_follows_matrix_state(self) -> None:
        validation = Validation()
        _validate_runtime_support_claims(
            validation,
            "Supports 50+ runtimes",
            copy.deepcopy(self.support),
        )
        self.assertTrue(any("矩阵只有 0 个" in error for error in validation.errors))

        support = copy.deepcopy(self.support)
        for level in ("L3", "L4", "L5"):
            support["runtimes"][0]["levels"][level]["status"] = "passed"
        validation = Validation()
        _validate_runtime_support_claims(validation, "Supports 1 runtime", support)
        self.assertEqual([], validation.errors)

        validation = Validation()
        _validate_runtime_support_claims(validation, "Supports 2 runtimes", support)
        self.assertTrue(any("矩阵只有 1 个" in error for error in validation.errors))

    def test_runtime_claim_in_compatibility_guide_is_rejected(self) -> None:
        validation = self._validate_compatibility_doc_mutation(
            "docs/compatibility-and-evidence.en.md",
            "## Machine sources",
            "Supports 50+ runtimes.\n\n## Machine sources",
        )
        self.assertTrue(any("矩阵只有 0 个" in error for error in validation.errors), validation.errors)

    def _validate_mutated_compatibility(
        self,
        support: dict,
        evidence: dict,
        evidence_subdir: str,
    ) -> Validation:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = self._copy_compatibility_fixture(root)
            (target / "runtime-support.json").write_text(
                json.dumps(support, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            evidence_dir = target / "evidence" / evidence_subdir
            evidence_dir.mkdir(parents=True)
            (evidence_dir / "evidence.json").write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            validation = Validation()
            with mock.patch("validate_repo.ROOT", root):
                validate_compatibility(validation)
            return validation

    def _validate_compatibility_doc_mutation(
        self,
        relative: str,
        old: str,
        new: str,
    ) -> Validation:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._copy_compatibility_fixture(root)
            path = root / relative
            text = path.read_text(encoding="utf-8")
            self.assertIn(old, text)
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            validation = Validation()
            with mock.patch("validate_repo.ROOT", root):
                validate_compatibility(validation)
            return validation

    def _copy_compatibility_fixture(self, root: Path) -> Path:
        target = root / "compatibility"
        shutil.copytree(ROOT / "compatibility", target)
        for relative in (
            "README.md",
            "README.en.md",
            "docs/installation.md",
            "docs/installation.en.md",
            "docs/compatibility-and-evidence.md",
            "docs/compatibility-and-evidence.en.md",
        ):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        return target

    def _minimal_evidence(self, kind: str, level: str) -> dict:
        evidence = {
            "schema_version": "1",
            "evidence_id": "format-test",
            "kind": kind,
            "skill": {"id": "think-it-through", "version": "0.3.0"},
            "source_commit": "0" * 40,
            "package_sha256": None,
            "tool": {"name": "skills-ref", "version": "fixed"},
            "environment": {"os": "test", "arch": "test", "network_used": False},
            "levels": [level],
            "cases": [
                {
                    "id": "format-validation",
                    "level": level,
                    "status": "passed",
                    "command_argv": ["skills-ref", "validate", "<skill-root>"],
                    "assertions": ["valid"],
                }
            ],
            "artifacts": [],
            "review": {
                "status": "approved",
                "reviewed_by": "test",
                "reviewed_at": "2026-08-29T00:00:00Z",
            },
            "recorded_at": "2026-08-29T00:00:00Z",
        }
        if kind == "real_runtime":
            evidence["runtime"] = {"id": "claude-code", "version": "test"}
            evidence["redaction"] = {
                "secrets_removed": True,
                "personal_paths_removed": True,
                "unrelated_data_removed": True,
            }
            evidence.pop("tool")
        return evidence


if __name__ == "__main__":
    unittest.main()
