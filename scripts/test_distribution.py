#!/usr/bin/env python3
"""验证 manifest 驱动的 `.skill` 分发构建与归档安全。"""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from build_distribution import (
    MANIFEST_PATH,
    SKILL_DIR,
    build_archive,
    inspect_archive,
    load_manifest,
    source_files,
    verify_archive_bytes,
)


class DistributionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_root, self.manifest_files = load_manifest()

    def _write_manifest_archive(self, archive: Path) -> None:
        with zipfile.ZipFile(archive, "w") as package:
            for relative in self.manifest_files:
                package.writestr(f"{self.skill_root}/{relative}", (SKILL_DIR / relative).read_bytes())

    def test_source_files_exactly_match_manifest(self) -> None:
        relatives = tuple(path.relative_to(SKILL_DIR).as_posix() for path in source_files())
        self.assertEqual(self.manifest_files, relatives)
        self.assertFalse(any(relative.startswith("evals/") for relative in relatives))

    def test_build_archive_matches_source_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "valid.skill"
            build_archive(archive)
            self.assertEqual(len(self.manifest_files), len(inspect_archive(archive)))
            verify_archive_bytes(archive)

    def test_inspect_archive_rejects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "missing.skill"
            with zipfile.ZipFile(archive, "w") as package:
                for relative in self.manifest_files[:-1]:
                    package.writestr(f"{self.skill_root}/{relative}", relative)
            with self.assertRaisesRegex(ValueError, "文件集合"):
                inspect_archive(archive)

    def test_inspect_archive_rejects_unexpected_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "extra.skill"
            self._write_manifest_archive(archive)
            with zipfile.ZipFile(archive, "a") as package:
                package.writestr(f"{self.skill_root}/evals/evals.json", "{}")
            with self.assertRaisesRegex(ValueError, "禁止目录|文件集合"):
                inspect_archive(archive)

    def test_inspect_archive_rejects_wrong_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "wrong-root.skill"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("wrong/SKILL.md", "invalid")
            with self.assertRaisesRegex(ValueError, "根目录"):
                inspect_archive(archive)

    def test_inspect_archive_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "traversal.skill"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr(f"{self.skill_root}/../outside", "invalid")
            with self.assertRaisesRegex(ValueError, "不安全路径"):
                inspect_archive(archive)

    def test_inspect_archive_rejects_duplicate_member(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "duplicate.skill"
            self._write_manifest_archive(archive)
            with self.assertWarns(UserWarning):
                with zipfile.ZipFile(archive, "a") as package:
                    package.writestr(f"{self.skill_root}/{self.manifest_files[0]}", "duplicate")
            with self.assertRaisesRegex(ValueError, "重复 member"):
                inspect_archive(archive)

    def test_inspect_archive_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "symlink.skill"
            self._write_manifest_archive(archive)
            info = zipfile.ZipInfo(f"{self.skill_root}/link")
            info.create_system = 3
            info.external_attr = (0o120777 & 0xFFFF) << 16
            with zipfile.ZipFile(archive, "a") as package:
                package.writestr(info, "SKILL.md")
            with self.assertRaisesRegex(ValueError, "符号链接"):
                inspect_archive(archive)

    def test_load_manifest_rejects_duplicates_and_unsorted_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(
                '{"schema_version":"1","skill_root":"think-it-through",'
                '"files":["SKILL.md","SKILL.md"]}'
            )
            with self.assertRaisesRegex(ValueError, "重复"):
                load_manifest(path)

            path.write_text(
                '{"schema_version":"1","skill_root":"think-it-through",'
                '"files":["SKILL.md","LICENSE"]}'
            )
            with self.assertRaisesRegex(ValueError, "字典序"):
                load_manifest(path)

    def test_load_manifest_rejects_unsafe_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(
                '{"schema_version":"1","skill_root":"think-it-through",'
                '"files":["../secret"]}'
            )
            with self.assertRaisesRegex(ValueError, "非法路径段"):
                load_manifest(path)

    def test_source_files_reject_unlisted_runtime_file(self) -> None:
        eligible = set(self.manifest_files) | {"references/unlisted.md"}
        with mock.patch("build_distribution._eligible_source_relatives", return_value=eligible):
            with self.assertRaisesRegex(ValueError, "未列入 manifest"):
                source_files()

    def test_manifest_path_is_repository_owned(self) -> None:
        self.assertTrue(MANIFEST_PATH.is_file())
        self.assertEqual("distribution/package-manifest.json", MANIFEST_PATH.relative_to(MANIFEST_PATH.parents[1]).as_posix())


if __name__ == "__main__":
    unittest.main()
