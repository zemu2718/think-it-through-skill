#!/usr/bin/env python3
"""验证最小 `.skill` 分发文件筛选与归档检查。"""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from build_distribution import REQUIRED, SKILL_DIR, inspect_archive, source_files


class DistributionTests(unittest.TestCase):
    def test_source_files_exclude_evals_and_local_artifacts(self) -> None:
        relatives = {
            path.relative_to(SKILL_DIR).as_posix()
            for path in source_files()
        }

        self.assertTrue(REQUIRED <= relatives)
        self.assertFalse(any(relative.startswith("evals/") for relative in relatives))
        self.assertFalse(any(relative.endswith((".pyc", ".html")) for relative in relatives))
        self.assertFalse(any("__pycache__" in Path(relative).parts for relative in relatives))

    def test_inspect_archive_accepts_minimum_valid_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "valid.skill"
            with zipfile.ZipFile(archive, "w") as package:
                for relative in sorted(REQUIRED):
                    package.writestr(f"think-it-through/{relative}", relative)

            self.assertEqual(len(REQUIRED), len(inspect_archive(archive)))

    def test_inspect_archive_rejects_evals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "invalid.skill"
            with zipfile.ZipFile(archive, "w") as package:
                for relative in sorted(REQUIRED):
                    package.writestr(f"think-it-through/{relative}", relative)
                package.writestr("think-it-through/evals/evals.json", "{}")

            with self.assertRaisesRegex(ValueError, "禁止内容"):
                inspect_archive(archive)


if __name__ == "__main__":
    unittest.main()
