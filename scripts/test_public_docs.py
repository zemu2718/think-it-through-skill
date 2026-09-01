#!/usr/bin/env python3
"""验证正式双语 README 的信息架构、事实与声明边界。"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from validate_repo import ROOT, Validation, validate_public_docs


class PublicDocsTests(unittest.TestCase):
    def test_canonical_public_docs_validate(self) -> None:
        validation = Validation()
        validate_public_docs(validation)
        self.assertEqual([], validation.errors)

    def test_required_facts_fail_independently(self) -> None:
        mutations = (
            ("README.en.md", "```text\n/think-it-through\n```", "```text\n/wrong-entry\n```", "可靠显式入口"),
            ("README.en.md", "AI bookkeeping", "AI ledger", "原话画廊第 2 条"),
            ("README.en.md", "polished decision question", "polished prompt", "原话画廊必须说明"),
            ("README.md", "第一版", "初始版本", "原话画廊第 3 条"),
            ("README.en.md", "git clone --depth 1 --branch v0.3.0", "git clone", "不可变 v0.3.0 tag"),
            ("README.en.md", "cd think-it-through-skill\ngit rev-parse HEAD\ntest ! -e", "cd think-it-through-skill\ngit status --short\ntest ! -e", "准确源码 revision"),
            ("README.en.md", "**Stable release:**", "**Source candidate:**", "当前稳定发布状态"),
            ("README.en.md", "gh skill install", "gh extension install", "GitHub CLI 固定版本安装"),
            ("README.en.md", "all target mappings recognized by `skills@1.5.23`", "all AI clients", "--agent '*'"),
            ("README.en.md", "installation or runtime feedback", "general feedback", "反馈入口"),
            ("README.en.md", "no network access", "network access depends on context", "五项默认安全语义"),
            ("README.en.md", "Before starting", "At some point", "五个具体调用时机"),
            ("README.en.md", "not a project-management or task-execution layer", "also executes projects", "决策工具与执行工具边界"),
            ("README.md", "立项前", "开始以后", "五个具体调用时机"),
            ("README.md", "| **结果回来后** |", "| **完成以后** |", "五个具体调用时机"),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, old=old):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_positioning_value_statement_and_preface_order_fail(self) -> None:
        mutations = (
            (
                "README.en.md",
                "AI can get things done fast, but it can't decide for you what's worth doing.",
                "AI can finish work quickly.",
                "canonical 产品定位",
            ),
            (
                "README.en.md",
                "Before an important commitment, clarify what you really need to decide and which unknown could change your course. Once the results come in, decide whether to continue, adjust, pause, or stop.",
                "Before a commitment, think carefully.",
                "价值说明",
            ),
            (
                "README.md",
                "AI 能把事情做得很快，但不能替你决定什么值得做。",
                "AI 能快速执行。",
                "canonical 产品定位",
            ),
            (
                "README.md",
                "重要投入之前，先确认真正要决定什么、哪个未知会改变方向；结果回来之后，再决定继续、调整、暂停还是停止。",
                "重要投入前后都要仔细考虑。",
                "价值说明",
            ),
            (
                "PRODUCT.md",
                "AI 能把事情做得很快，但不能替你决定什么值得做。",
                "AI 能快速执行。",
                "canonical 中文产品定位",
            ),
            (
                "PRODUCT.md",
                "重要投入之前，先确认真正要决定什么、哪个未知会改变方向；结果回来之后，再决定继续、调整、暂停还是停止。",
                "重要投入前后都要仔细考虑。",
                "结果后复判的价值说明",
            ),
            (
                ".agents/brand-context.md",
                "AI can get things done fast, but it can't decide for you what's worth doing.",
                "AI can finish work quickly.",
                "品牌摘要缺少产品定位",
            ),
            (
                ".agents/brand-context.md",
                "Before an important commitment, clarify what you really need to decide and which unknown could change your course. Once the results come in, decide whether to continue, adjust, pause, or stop.",
                "Before a commitment, think carefully.",
                "品牌摘要缺少产品定位",
            ),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, expected=expected):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

        old = (
            "**AI can get things done fast, but it can't decide for you what's worth doing.**\n\n"
            "Before an important commitment, clarify what you really need to decide and which unknown could change your course. Once the results come in, decide whether to continue, adjust, pause, or stop."
        )
        new = (
            "Before an important commitment, clarify what you really need to decide and which unknown could change your course. Once the results come in, decide whether to continue, adjust, pause, or stop.\n\n"
            "**AI can get things done fast, but it can't decide for you what's worth doing.**"
        )
        errors = self.validate_doc_mutation("README.en.md", old, new).errors
        self.assertTrue(any("主定位 → 价值说明" in error for error in errors), errors)

    def test_h2_missing_reordered_and_legacy_heading_fail(self) -> None:
        errors = self.validate_doc_mutation("README.en.md", "## Why it matters", "### Why it matters").errors
        self.assertTrue(any("十个 H2" in error for error in errors), errors)
        errors = self.validate_doc_mutation(
            "README.en.md",
            "## Install and use",
            "## Install and try it",
        ).errors
        self.assertTrue(any("旧版入口章节" in error or "十个 H2" in error for error in errors), errors)
        errors = self.validate_doc_mutation(
            "README.md",
            "## 安装与使用",
            "## 安装并完成第一次体验",
        ).errors
        self.assertTrue(any("旧版入口章节" in error or "十个 H2" in error for error in errors), errors)
        errors = self.validate_doc_mutation("README.en.md", "## What it is", "## Quick Start").errors
        self.assertTrue(any("旧版入口章节" in error or "十个 H2" in error for error in errors), errors)

    def test_install_and_use_journey_fail(self) -> None:
        mutations = (
            (
                "README.en.md",
                "### Invoke it",
                "### Other installation options",
                "依次提供主安装、显式调用、预期行为和其他安装方式",
            ),
            (
                "README.md",
                "### 调用后会先发生什么",
                "### 使用后说明",
                "依次提供主安装、显式调用、预期行为和其他安装方式",
            ),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, old=old):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

        old = "### Invoke it\n\nThe reliable entry is explicit invocation in Claude Code:"
        new = "### Invoke it\n\nnpx -y skills@1.5.23 add placeholder\n\nThe reliable entry is explicit invocation in Claude Code:"
        errors = self.validate_doc_mutation("README.en.md", old, new).errors
        self.assertTrue(any("主路径必须先于其他安装方式" in error for error in errors), errors)

        old = "With [GitHub CLI 2.98.0 or later](https://cli.github.com/), install it for Claude Code at user scope:"
        new = "With [GitHub CLI 2.98.0 or later](https://cli.github.com/), install the pinned v0.3.0 release for Claude Code at user scope:"
        errors = self.validate_doc_mutation("README.en.md", old, new).errors
        self.assertTrue(any("不得突出当前版本号" in error for error in errors), errors)

    def test_language_switch_and_default_readme_contract_fail(self) -> None:
        mutations = (
            ("README.md", "[English](README.en.md)", "[English](README.md)", "中文 README 缺少英文切换"),
            ("README.en.md", "[简体中文](README.md)", "[简体中文](README.en.md)", "英文 README 缺少中文切换"),
            (
                "CLAUDE.md",
                "`README.md` 是 GitHub 默认展示的中文用户入口",
                "`README.md` 是英文用户入口",
                "CLAUDE.md 缺少 v0.3.0 维护规则",
            ),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, old=old):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_legacy_chinese_readme_path_fails(self) -> None:
        with self.repository_copy() as root:
            shutil.copyfile(root / "README.md", root / "README.zh-CN.md")
            validation = Validation()
            with mock.patch("validate_repo.ROOT", root):
                validate_public_docs(validation)
            self.assertTrue(any("不得保留 README.zh-CN.md" in error for error in validation.errors), validation.errors)

    def test_readme_banner_and_text_gallery_fail(self) -> None:
        errors = self.validate_doc_mutation(
            "README.md", "assets/readme-banner-light.png", "assets/brand-mark-light.svg"
        ).errors
        self.assertTrue(any("README Banner" in error or "Brand Mark" in error for error in errors), errors)
        errors = self.validate_doc_mutation(
            "README.en.md",
            "- “I want to build a chat app like QQ. What do you think?”",
            '<img src="assets/decision-case-light.svg" alt="case">',
        ).errors
        self.assertTrue(any("八条用户描述" in error or "纯文本" in error or "已移除" in error for error in errors), errors)

    def test_banner_fallback_width_alt_and_preface_order_fail(self) -> None:
        mutations = (
            ("README.md", '<img src="assets/readme-banner-light.png"', '<img src="assets/readme-banner-dark.png"', "light fallback"),
            ("README.md", 'width="1200"', 'width="104"', "README Banner"),
            (
                "README.md",
                'alt="多层观察框架逐步对齐成一个清晰开口，并保留一个让判断可以再次修正的小轴点。"',
                'alt=""',
                "本地化 alt",
            ),
            ("README.en.md", "# Think It Through · 想清楚", "## What it is", "首屏"),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, expected=expected):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_badge_count_style_workflow_commit_and_license_fail(self) -> None:
        validate_line = "[![Validate](https://img.shields.io/github/actions/workflow/status/zemu2718/think-it-through-skill/validate.yml?branch=main&style=flat-square&label=Validate)](https://github.com/zemu2718/think-it-through-skill/actions/workflows/validate.yml?query=branch%3Amain)"
        errors = self.validate_doc_mutation("README.md", validate_line + "\n", "").errors
        self.assertTrue(any("恰好包含四枚" in error for error in errors), errors)
        errors = self.validate_doc_mutation("README.md", "style=flat-square&label=Validate", "style=plastic&label=Validate").errors
        self.assertTrue(any("flat-square" in error or "徽章职责" in error for error in errors), errors)
        errors = self.validate_doc_mutation("README.md", "validate.yml?branch=main", "other.yml?branch=dev").errors
        self.assertTrue(any("徽章职责" in error for error in errors), errors)
        errors = self.validate_doc_mutation(
            "README.md",
            "tree/v0.3.0/skills/think-it-through",
            "tree/dev/skills/think-it-through",
        ).errors
        self.assertTrue(any("徽章职责" in error for error in errors), errors)
        errors = self.validate_doc_mutation("README.md", "](LICENSE)", "](https://example.com/license)").errors
        self.assertTrue(any("徽章职责" in error for error in errors), errors)

    def test_forbidden_marketing_badges_fail(self) -> None:
        insertion = "[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen?style=flat-square)](https://example.com)\n"
        errors = self.validate_doc_mutation("README.en.md", "**Reliable entry today:**", insertion + "\n**Reliable entry today:**").errors
        self.assertTrue(any("恰好包含四枚" in error or "徽章不得宣称" in error for error in errors), errors)
        insertion = "[![L5 certified](https://img.shields.io/badge/L5-certified-blue?style=flat-square)](https://example.com)\n"
        errors = self.validate_doc_mutation("README.en.md", "**Reliable entry today:**", insertion + "\n**Reliable entry today:**").errors
        self.assertTrue(any("恰好包含四枚" in error or "徽章不得宣称" in error for error in errors), errors)

    def test_inaccurate_release_url_and_runtime_claim_fail(self) -> None:
        errors = self.validate_doc_mutation(
            "README.md",
            "npx -y skills@1.5.23 add",
            "npx -y installer@1.5.22 add",
        ).errors
        self.assertTrue(any("固定通用安装器" in error for error in errors), errors)
        release_mutations = (
            (
                "https://github.com/zemu2718/think-it-through-skill/releases/tag/v0.3.0",
                "https://github.com/other/think-it-through-skill/releases/tag/v0.3.0",
            ),
            (
                "https://github.com/zemu2718/think-it-through-skill/releases/download/v0.3.0/think-it-through.skill",
                "https://github.com/zemu2718/think-it-through-skill/releases/download/v0.3.0/wrong.skill",
            ),
            (
                "https://github.com/zemu2718/think-it-through-skill/releases/download/v0.3.0/SHA256SUMS",
                "https://github.com/zemu2718/think-it-through-skill/releases/download/v0.3.0/checksums.txt",
            ),
        )
        for old, new in release_mutations:
            with self.subTest(new=new):
                errors = self.validate_doc_mutation("README.md", old, new).errors
                self.assertTrue(any("准确" in error or "核验" in error for error in errors), errors)
        errors = self.validate_doc_mutation(
            "README.en.md",
            "Eight installer target mappings",
            "Supports 50+ runtimes; eight installer target mappings",
        ).errors
        self.assertTrue(any("矩阵只有 0 个" in error for error in errors), errors)

    def test_normative_contract_terms_fail(self) -> None:
        for term in ("R-align", "R-method", "DecisionRecord"):
            with self.subTest(term=term):
                errors = self.validate_doc_mutation("README.en.md", "## License", f"{term}\n\n## License").errors
                self.assertTrue(any("正式行为合同术语" in error for error in errors), errors)

    def validate_doc_mutation(self, relative: str, old: str, new: str) -> Validation:
        with self.repository_copy() as root:
            path = root / relative
            text = path.read_text(encoding="utf-8")
            self.assertIn(old, text)
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            validation = Validation()
            with mock.patch("validate_repo.ROOT", root):
                validate_public_docs(validation)
            return validation

    def repository_copy(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        for relative in (
            "README.md",
            "README.en.md",
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
            "CONTRIBUTING.md",
            ".agents/brand-context.md",
            ".github/ISSUE_TEMPLATE/install-or-runtime-feedback.yml",
            ".github/workflows/validate.yml",
        ):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)

        class RepositoryCopy:
            def __enter__(self) -> Path:
                return root

            def __exit__(self, *args: object) -> None:
                temporary.cleanup()

        return RepositoryCopy()


if __name__ == "__main__":
    unittest.main()
