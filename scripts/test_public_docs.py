#!/usr/bin/env python3
"""验证双语 README 与用户向安装、兼容说明的职责边界。"""

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

    def test_positioning_and_value_statement_fail(self) -> None:
        mutations = (
            (
                "README.en.md",
                "AI can get things done fast, but it can't decide for you what's worth doing.",
                "AI can finish work quickly.",
                "canonical 产品定位",
            ),
            (
                "README.en.md",
                "Before an important commitment, think through the decision you really need to make—then act.",
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
                "重要投入前，先把真正要做的决定想清楚，再行动。",
                "重要投入前后都要仔细考虑。",
                "价值说明",
            ),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, expected=expected):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_readme_user_journey_fail(self) -> None:
        mutations = (
            (
                "README.md",
                "[什么时候调用](#什么时候调用) · [如何工作](#它怎样帮你想清楚) · [安装](#安装与使用) · [默认安全](#默认安全与更多信息)",
                "[你会得到什么](#你会得到什么) · [什么时候调用](#什么时候调用) · [如何工作](#它怎样帮你想清楚) · [安装](#安装与使用) · [默认安全](#默认安全与更多信息)",
                "页内导航顺序",
            ),
            ("README.md", "## 你会得到什么", "## 得到结果", "五段普通用户路径"),
            ("README.en.md", "One integrated judgment", "A long report", "三项用户结果"),
            ("README.md", "先验证", "直接推进", "三项用户结果"),
            ("README.en.md", "already underway", "in every case", "三项用户结果"),
            ("README.md", "| **结果回来后** |", "| **完成以后** |", "五个具体调用时机"),
            ("README.en.md", "what you really need to decide", "what task to execute", "白话工作原理"),
            ("README.md", "成立条件和反转条件", "明确结论", "白话工作原理"),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, expected=expected):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_removed_readme_content_cannot_return(self) -> None:
        mutations = (
            ("README.md", "## 你会得到什么", "## 先看它会改变什么\n\n## 你会得到什么"),
            ("README.en.md", "## What you get", "## Say it in your own words\n\n## What you get"),
            ("README.md", "## 你会得到什么", "压缩后的合成示意\n\n## 你会得到什么"),
            ("README.en.md", "## What you get", "I have an idea for an AI bookkeeping product.\n\n## What you get"),
        )
        for relative, old, new in mutations:
            with self.subTest(relative=relative, new=new):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any("不得重新加入已删除" in error for error in errors), errors)

        errors = self.validate_doc_mutation(
            "README.en.md",
            "[When to use it](#when-to-use-it)",
            "`/think-it-through` · [When to use it](#when-to-use-it)",
        ).errors
        self.assertTrue(any("首屏不得重复显式调用入口" in error for error in errors), errors)

        errors = self.validate_doc_mutation(
            "README.md",
            "**AI 能把事情做得很快，但不能替你决定什么值得做。**",
            "一个用于重要投入前后判断的**决策与证据 Agent Skill**。\n\n**AI 能把事情做得很快，但不能替你决定什么值得做。**",
        ).errors
        self.assertTrue(any("不得重新加入偏内部" in error for error in errors), errors)

    def test_brand_context_and_changelog_follow_readme_path(self) -> None:
        mutations = (
            (
                ".agents/brand-context.md",
                "methods that appear only when useful",
                "a complete method catalog",
                "README 用户路径",
            ),
            (
                "CHANGELOG.md",
                "用户结果 → 调用时机 → 工作原理与最小必要方法 → 安装使用 → 默认安全",
                "先看效果 → 自然输入 → 安装使用",
                "结果优先 README 路径",
            ),
            (
                ".agents/brand-context.md",
                "one cross-host repository-URL installation request",
                "one universal installation path",
                "README 用户路径",
            ),
            (
                "CHANGELOG.md",
                "区分跨宿主安装请求、Claude Code 可靠调用与真实 runtime 验证",
                "支持所有宿主可靠调用",
                "安装边界",
            ),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, expected=expected):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_readme_method_map_fail(self) -> None:
        mutations = (
            ("README.md", "每次都会先做基础分析", "基础分析可以选择", "每次先做基础分析"),
            ("README.en.md", "Two-sided Steelman", "Compare both sides", "两种核心方法"),
            ("README.md", "失败预演", "风险分析", "两种核心方法"),
            ("README.en.md", "Object Calibration", "Audience Check", "registry.yaml"),
            ("README.md", "证据闭环", "结果复盘", "registry.yaml"),
            ("README.en.md", "only the thinking approaches your current question needs", "every available framework", "方法按需推荐"),
            ("README.md", "使用前让你确认", "自动使用", "方法按需推荐"),
            ("README.en.md", "explains why and asks for your consent first", "starts immediately", "能力征求同意"),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, expected=expected):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_readme_install_and_safety_fail(self) -> None:
        mutations = (
            (
                "README.md",
                "帮我安装这个 Skill：https://github.com/zemu2718/think-it-through-skill",
                "帮我安装一个 Skill",
                "一句话安装请求",
            ),
            (
                "README.en.md",
                "according to its capabilities, permissions, and Skill-directory convention",
                "with universal compatibility",
                "安装取决于当前 Agent",
            ),
            (
                "README.md",
                "面向不同宿主的一句话安装请求",
                "适用于所有宿主的通用安装方式",
                "跨宿主一句话安装请求边界",
            ),
            (
                "README.en.md",
                "Installation only means the files reached a target directory; it does not establish real-runtime validation.",
                "Installation proves runtime support.",
                "文件安装与真实 runtime 验证",
            ),
            (
                "README.md",
                "目前有可靠调用说明的入口是 Claude Code。",
                "所有宿主都可以可靠调用。",
                "可靠调用说明限定在 Claude Code",
            ),
            (
                "README.en.md",
                "**Get started:**",
                "**More:**",
                "三组详情入口",
            ),
            (
                "README.md",
                "把下面这句话发给你正在使用的 Agent",
                "选择下列支持的 Agent",
                "把仓库链接交给当前 Agent",
            ),
            ("README.md", "```text\n/think-it-through\n```", "```text\n/wrong\n```", "可靠显式入口"),
            ("README.en.md", "docs/installation.en.md", "docs/missing.md", "详细安装或兼容说明链接"),
            ("README.md", "**不联网**", "**按需联网**", "五项默认安全语义"),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, expected=expected):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_technical_details_cannot_return_to_readme(self) -> None:
        for token in ("npx -y skills", "gh skill install", "git clone", "L0", "9/16", "approved evidence"):
            with self.subTest(token=token):
                errors = self.validate_doc_mutation(
                    "README.en.md",
                    "## Safe by default and more",
                    f"{token}\n\n## Safe by default and more",
                ).errors
                self.assertTrue(any("不得重新塞入" in error for error in errors), errors)

    def test_readme_banner_language_and_badges_fail(self) -> None:
        mutations = (
            ("README.md", "[English](README.en.md)", "[English](README.md)", "中文 README 缺少英文切换"),
            ("README.en.md", "[简体中文](README.md)", "[简体中文](README.en.md)", "英文 README 缺少中文切换"),
            ("README.md", "assets/readme-banner-dark.png", "assets/brand-mark-dark.svg", "README Banner"),
            ("README.en.md", 'width="960"', 'width="1200"', "克制显示宽度"),
            (
                "README.md",
                'alt="多层观察框架逐步对齐成一个清晰开口，并保留一个让判断可以再次修正的小轴点。"',
                'alt=""',
                "本地化 alt",
            ),
            (
                "README.en.md",
                "https://github.com/zemu2718/think-it-through-skill/releases/latest",
                "https://github.com/zemu2718/think-it-through-skill/releases/tag/v0.2.0",
                "三枚可验证徽章",
            ),
            (
                "README.md",
                "badge.svg?branch=main",
                "badge.svg?branch=dev",
                "三枚可验证徽章",
            ),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, expected=expected):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

        compatibility_badge = "[![Compatible](https://img.shields.io/badge/runtime-compatible-brightgreen)](docs/compatibility-and-evidence.en.md)"
        errors = self.validate_doc_mutation(
            "README.en.md", "## What you get", f"{compatibility_badge}\n\n## What you get"
        ).errors
        self.assertTrue(any("三枚可验证徽章" in error for error in errors), errors)

    def test_installation_guide_contract_fail(self) -> None:
        mutations = (
            (
                "docs/installation.en.md",
                "Install this Skill for me: https://github.com/zemu2718/think-it-through-skill",
                "Install a Skill for me",
                "一句话 Agent 安装",
            ),
            (
                "docs/installation.md",
                "npx -y skills@1.5.23 add",
                "npx -y skills@latest add",
                "固定通用安装器",
            ),
            (
                "docs/installation.en.md",
                "all target mappings recognized by `skills@1.5.23`",
                "all supported runtimes",
                "真实支持边界",
            ),
            (
                "docs/installation.md",
                "git clone --depth 1 --branch v0.3.0",
                "git clone",
                "不可变 v0.3.0 tag",
            ),
            (
                "docs/installation.en.md",
                "cd think-it-through-skill\ngit rev-parse HEAD\ntest ! -e",
                "cd think-it-through-skill\ngit status --short\ntest ! -e",
                "准确 revision",
            ),
            (
                "docs/installation.md",
                "[`SHA256SUMS`](https://github.com/zemu2718/think-it-through-skill/releases/download/v0.3.0/SHA256SUMS)",
                "校验和文件",
                "归档核验",
            ),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, expected=expected):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_compatibility_guide_contract_fail(self) -> None:
        mutations = (
            (
                "docs/compatibility-and-evidence.en.md",
                "https://github.com/zemu2718/think-it-through-skill/releases/tag/v0.3.0",
                "https://github.com/other/think-it-through-skill/releases/tag/v0.3.0",
                "准确、已核验",
            ),
            ("docs/compatibility-and-evidence.md", "L5", "LX", "机器兼容状态摘要"),
            (
                "docs/compatibility-and-evidence.en.md",
                "Eight installer target mappings",
                "Many installer mappings",
                "安装目标与 runtime 验证",
            ),
            ("docs/compatibility-and-evidence.md", "9/16", "16/16", "完整自动发现限制"),
            (
                "docs/compatibility-and-evidence.en.md",
                "approved evidence",
                "trusted feedback",
                "反馈不得自动提升",
            ),
            (
                "docs/compatibility-and-evidence.md",
                "[`compatibility/profile.json`](../compatibility/profile.json)",
                "compatibility/profile-v2.json",
                "机器事实源",
            ),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, expected=expected):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_guide_language_switches_fail(self) -> None:
        mutations = (
            ("docs/installation.md", "[English](installation.en.md)", "[English](installation.md)", "缺少双语切换"),
            ("docs/installation.en.md", "[简体中文](installation.md)", "[简体中文](installation.en.md)", "缺少双语切换"),
            (
                "docs/compatibility-and-evidence.md",
                "[English](compatibility-and-evidence.en.md)",
                "[English](compatibility-and-evidence.md)",
                "缺少双语切换",
            ),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_legacy_chinese_readme_path_fails(self) -> None:
        with self.repository_copy() as root:
            shutil.copyfile(root / "README.md", root / "README.zh-CN.md")
            validation = Validation()
            with mock.patch("validate_repo.ROOT", root):
                validate_public_docs(validation)
            self.assertTrue(any("不得保留 README.zh-CN.md" in error for error in validation.errors), validation.errors)

    def test_normative_contract_terms_fail(self) -> None:
        for term in ("R-align", "R-method", "DecisionRecord"):
            with self.subTest(term=term):
                errors = self.validate_doc_mutation(
                    "README.en.md", "## Safe by default and more", f"{term}\n\n## Safe by default and more"
                ).errors
                self.assertTrue(any("不得重新塞入" in error for error in errors), errors)

    def validate_doc_mutation(self, relative: str, old: str, new: str) -> Validation:
        with self.repository_copy() as root:
            path = root / relative
            text = path.read_text(encoding="utf-8")
            self.assertIn(old, text)
            path.write_text(text.replace(old, new), encoding="utf-8")
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
            "docs/installation.md",
            "docs/installation.en.md",
            "docs/compatibility-and-evidence.md",
            "docs/compatibility-and-evidence.en.md",
            "compatibility/profile.json",
            "compatibility/runtime-support.json",
            "compatibility/runtime-support.schema.json",
            "compatibility/evidence.schema.json",
            "benchmarks/trigger-v0.1/summary.json",
            "benchmarks/trigger-v0.1/holdout.json",
            "benchmarks/trigger-v0.1/README.md",
            "benchmarks/behavior-v0.1/README.md",
            "docs/product-architecture-v0.2.0.md",
            "docs/product-architecture-v0.3.0.md",
            "CONTRIBUTING.md",
            ".agents/brand-context.md",
            ".github/ISSUE_TEMPLATE/install-or-runtime-feedback.yml",
            ".github/workflows/validate.yml",
            "skills/think-it-through/references/methods/registry.yaml",
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
