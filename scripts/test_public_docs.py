#!/usr/bin/env python3
"""验证发布级 README 与视觉资产的事实和职责边界。"""

from __future__ import annotations

import shutil
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from validate_repo import ROOT, Validation, all_repo_files, validate_assets, validate_public_docs


class PublicDocsTests(unittest.TestCase):
    def test_canonical_public_docs_and_assets_validate(self) -> None:
        validation = Validation()
        validate_public_docs(validation)
        validate_assets(validation, all_repo_files())
        self.assertEqual([], validation.errors)

    def test_readme_required_facts_fail_independently(self) -> None:
        mutations = (
            ("/think-it-through", "/wrong-entry", "可靠显式入口"),
            ("synthetic, not a runtime transcript", "illustrative example", "合成示例边界"),
            ("3b9320b8890d36e592e86e89bf98e5103d4cf7d1", "3b9320b", "固定 v0.2.0"),
            ("no network access", "network access depends on context", "五项默认安全语义"),
            ("Before starting", "At some point", "五个具体调用时机"),
            (
                "not a project-management or task-execution layer",
                "a project-management and task-execution layer",
                "决策工具与执行工具边界",
            ),
        )
        for old, new, expected in mutations:
            with self.subTest(old=old):
                validation = self._validate_doc_mutation("README.md", old, new)
                self.assertTrue(any(expected in error for error in validation.errors))

    def test_chinese_readme_requires_project_start_and_reassessment_moments(self) -> None:
        validation = self._validate_doc_mutation(
            "README.zh-CN.md",
            "立项前",
            "开始以后",
        )
        self.assertTrue(any("五个具体调用时机" in error for error in validation.errors))

        validation = self._validate_doc_mutation(
            "README.zh-CN.md",
            "结果回来后",
            "完成以后",
        )
        self.assertTrue(any("五个具体调用时机" in error for error in validation.errors))

    def test_candidate_release_url_and_runtime_claim_fail(self) -> None:
        validation = self._validate_doc_mutation(
            "README.md",
            "## FAQ",
            "[Download](https://example.com/releases/download/v0.3.0/think-it-through.skill)\n\n## FAQ",
        )
        self.assertTrue(any("候选 Release" in error for error in validation.errors))

        validation = self._validate_doc_mutation(
            "README.md",
            "Eight mappings are defined",
            "Supports 50+ runtimes; eight mappings are defined",
        )
        self.assertTrue(any("矩阵只有 0 个" in error for error in validation.errors))

    def test_quick_start_position_and_flow_language_fail(self) -> None:
        validation = self._validate_doc_mutation(
            "README.md",
            "## Quick Start",
            "<!-- " + ("x" * 5000) + " -->\n\n## Quick Start",
        )
        self.assertTrue(any("Quick Start 出现过晚" in error for error in validation.errors))

        validation = self._validate_doc_mutation(
            "README.md",
            "assets/demo-flow.svg",
            "assets/demo-flow.zh-CN.svg",
        )
        self.assertTrue(any("错误语言流程图" in error for error in validation.errors))

    def test_readme_does_not_repeat_normative_contract(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("R-align", readme)
        self.assertNotIn("DecisionRecord", readme)
        self.assertNotIn("（核心假设）", readme)
        validation = Validation()
        validate_public_docs(validation)
        self.assertEqual([], validation.errors)

    def test_svg_security_structure_and_dimensions_fail(self) -> None:
        mutations = (
            (
                "assets/hero-light.svg",
                "<rect width=\"1200\"",
                "<script>alert(1)</script><rect width=\"1200\"",
                "不得包含脚本",
            ),
            (
                "assets/hero-light.svg",
                "</svg>",
                '<image href="https://example.com/a.png"/></svg>',
                "不得引用远程资源",
            ),
            (
                "assets/hero-light.svg",
                "</svg>",
                '<image href="data:image/png;base64,AA=="/></svg>',
                "不得嵌入 raster image",
            ),
            (
                "assets/demo-flow.svg",
                'id="step-4"',
                'id="missing-step"',
                "英文流程图缺少稳定结构 ID",
            ),
            (
                "assets/hero-dark.svg",
                'height="480" viewBox="0 0 1200 480"',
                'height="481" viewBox="0 0 1200 481"',
                "dark Hero 必须是 1200×480",
            ),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, expected=expected):
                validation = self._validate_asset_mutation(relative, old, new)
                self.assertTrue(any(expected in error for error in validation.errors))

    def test_social_preview_png_dimensions_fail(self) -> None:
        with self._repository_copy() as root:
            png = root / "assets" / "social-preview.png"
            data = bytearray(png.read_bytes())
            data[16:24] = struct.pack(">II", 640, 320)
            png.write_bytes(data)
            validation = self._validate_assets(root)
            self.assertTrue(any("Social Preview PNG 必须是 1280×640" in error for error in validation.errors))

    def _validate_doc_mutation(self, relative: str, old: str, new: str) -> Validation:
        with self._repository_copy() as root:
            path = root / relative
            text = path.read_text(encoding="utf-8")
            self.assertIn(old, text)
            path.write_text(text.replace(old, new), encoding="utf-8")
            validation = Validation()
            with mock.patch("validate_repo.ROOT", root):
                validate_public_docs(validation)
            return validation

    def _validate_asset_mutation(self, relative: str, old: str, new: str) -> Validation:
        with self._repository_copy() as root:
            path = root / relative
            text = path.read_text(encoding="utf-8")
            self.assertIn(old, text)
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            return self._validate_assets(root)

    def _validate_assets(self, root: Path) -> Validation:
        validation = Validation()
        with mock.patch("validate_repo.ROOT", root):
            validate_assets(validation, all_repo_files())
        return validation

    def _repository_copy(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        for relative in (
            "README.md",
            "README.zh-CN.md",
            "PRODUCT.md",
            "REQUIREMENTS.md",
            "SECURITY.md",
            "CHANGELOG.md",
            "CLAUDE.md",
            "compatibility/runtime-support.json",
            "benchmarks/trigger-v0.1/summary.json",
            "benchmarks/trigger-v0.1/holdout.json",
            "docs/product-architecture-v0.2.0.md",
            "docs/product-architecture-v0.3.0.md",
        ):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        shutil.copytree(ROOT / "assets", root / "assets")

        class RepositoryCopy:
            def __enter__(self) -> Path:
                return root

            def __exit__(self, *args: object) -> None:
                temporary.cleanup()

        return RepositoryCopy()


if __name__ == "__main__":
    unittest.main()
