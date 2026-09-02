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
                "AI can get things done fast, but what's worth doing is still yours to decide.",
                "AI can finish work quickly.",
                "canonical 产品定位",
            ),
            (
                "README.en.md",
                "Before you start or commit more, think it through—then decide.",
                "Before a commitment, think carefully.",
                "价值说明",
            ),
            (
                "README.md",
                "AI 能把事情做得很快，但什么值得做，仍由你决定。",
                "AI 能快速执行。",
                "canonical 产品定位",
            ),
            (
                "README.md",
                "开始或继续投入前，想清楚再决定。",
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
                "[什么时候调用](#什么时候调用) · [如何工作](#它怎样帮你想清楚) · [安装](#安装与使用) · [默认安全](#默认安全)",
                "[你会得到什么](#你会得到什么) · [什么时候调用](#什么时候调用) · [如何工作](#它怎样帮你想清楚) · [安装](#安装与使用) · [默认安全](#默认安全)",
                "页内导航顺序",
            ),
            ("README.md", "## 你会得到什么", "## 得到结果", "五段普通用户路径"),
            ("README.en.md", "A clear direction", "A long report", "三项用户结果"),
            ("README.md", "一份可回看的判断依据", "一份分析报告", "三项用户结果"),
            ("README.md", "## 默认安全", "## 默认安全与更多信息", "五段普通用户路径"),
            ("README.md", "一次能检验判断的小尝试", "一份分析报告", "三项用户结果"),
            ("README.md", "只补关键能力", "直接全面开发", "三项用户结果"),
            ("README.en.md", "fill only the critical gap", "build immediately", "三项用户结果"),
            ("README.md", "| **结果或条件变化后** |", "| **完成以后** |", "五个具体调用时机"),
            ("README.md", "真实需要", "实现细节", "白话工作原理"),
            ("README.en.md", "That does not prove you need to build from scratch", "You should build it yourself", "白话工作原理"),
            ("README.md", "成本可控、随时能停的小测试", "直接全面建设", "白话工作原理"),
            (
                "README.md",
                "如果你正在判断是否自研产品、功能或技术系统",
                "重大投入前",
                "自研与现实替代路径限定在对应项目可行性议题",
            ),
            (
                "README.en.md",
                "If you are deciding whether to custom-build a product, feature, or technical system",
                "Before a major commitment",
                "自研与现实替代路径限定在对应项目可行性议题",
            ),
            ("README.md", "具备相应资质的专业人士", "相应的专业人士", "白话工作原理"),
            ("README.md", "有没有现成或更轻的办法", "直接设计完整方案", "可复制使用示例"),
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
        self.assertTrue(any("卡片之外重复添加文本调用" in error for error in errors), errors)

        errors = self.validate_doc_mutation(
            "README.md",
            "**AI 能把事情做得很快，但什么值得做，仍由你决定。**",
            "一个用于重要投入前后判断的**决策与证据 Agent Skill**。\n\n**AI 能把事情做得很快，但什么值得做，仍由你决定。**",
        ).errors
        self.assertTrue(any("不得重新加入偏内部" in error for error in errors), errors)

    def test_brand_context_and_changelog_follow_readme_path(self) -> None:
        mutations = (
            (
                ".agents/brand-context.md",
                "formal method names in everyday terms",
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
                "cross-host repository-URL request and concise Skills CLI GitHub-source command as parallel installation paths",
                "one universal installation path",
                "README 用户路径",
            ),
            (
                "CHANGELOG.md",
                "以“安装 / 开始使用”两个平行操作步骤区分跨宿主安装请求、Claude Code 调用与真实 runtime 验证",
                "支持所有宿主可靠调用",
                "安装边界",
            ),
            (
                "CHANGELOG.md",
                "内部协议口吻改为普通用户能直接理解的表达",
                "保留全部内部术语",
                "普通用户表达",
            ),
            (
                ".agents/brand-context.md",
                "separate the compact safety section from detail links",
                "combine safety and maintenance links",
                "README 用户路径",
            ),
            (
                ".agents/brand-context.md",
                "state safety defaults during Skill use as concrete user choices",
                "state safety defaults as global Agent guarantees",
                "README 用户路径",
            ),
            (
                "CHANGELOG.md",
                "默认安全只描述 Skill 使用过程",
                "默认安全适用于整个宿主",
                "README 显示、文案或默认安全范围精修记录",
            ),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, expected=expected):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_bilingual_readme_maintenance_rules_fail(self) -> None:
        mutations = (
            ("普通用户第一次阅读为视角", "维护者视角"),
            ("不逐句孤立修补", "只修改用户指出的单句"),
            ("英文独立按自然英文重写", "英文逐字翻译中文"),
            ("不要求逐字直译", "要求逐字直译"),
            (
                "公开文档校验优先锁定结构、必要语义、命令、链接和声明边界",
                "公开文档校验优先锁定所有完整句子",
            ),
            (
                "mutation test 验证语义缺失或错误声明，而不是阻止自然润色",
                "mutation test 固定全部普通文案",
            ),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                errors = self.validate_doc_mutation("CLAUDE.md", old, new).errors
                self.assertTrue(any("双语 README 文案维护规则" in error for error in errors), errors)

    def test_b_cli_requires_record_and_visible_snapshot(self) -> None:
        mutations = (
            (
                "  --decision-record-json /path/to/decision-record.json \\\n  --visible-snapshot-json /path/to/visible-snapshot.json",
                "  --visible-snapshot-json /path/to/visible-snapshot.json",
            ),
            (
                "  --decision-record-json /path/to/decision-record.json \\\n  --visible-snapshot-json /path/to/visible-snapshot.json",
                "  --decision-record-json /path/to/decision-record.json",
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                errors = self.validate_doc_mutation("CLAUDE.md", old, new).errors
                self.assertTrue(any("B CLI 快照参数" in error for error in errors), errors)

    def test_readme_method_map_fail(self) -> None:
        mutations = (
            ("README.md", "它每次都会先做基础分析", "基础分析可以选择", "每次先做基础分析"),
            ("README.md", "它可能推荐下面的方法", "它会自动加入下面的方法", "只会按需推荐"),
            ("README.en.md", "it may recommend one or more of the methods below", "it automatically adds one or more of the methods below", "只会按需推荐"),
            (
                "README.md",
                "它可能推荐下面的方法。",
                "它可能推荐下面的方法，但会在推荐后自动使用。",
                "不得在保留推荐说明的同时声称自动执行",
            ),
            (
                "README.en.md",
                "it may recommend one or more of the methods below.",
                "it may recommend one or more of the methods below, but the Skill will automatically use them after recommending them.",
                "不得在保留推荐说明的同时声称自动执行",
            ),
            ("README.md", "两种核心方法是：", "两种使用最频繁的核心方法是：", "中性分类说明两种核心方法"),
            ("README.en.md", "The two core methods are:", "The two core methods used most often are:", "中性分类说明两种核心方法"),
            ("README.en.md", "Two-sided Steelman", "Compare both sides", "两种核心方法"),
            ("README.md", "用同一套标准", "用相近的证据标准", "自然表达"),
            ("README.md", "如何控制损失", "保护边界", "自然表达"),
            ("README.md", "失败预演", "风险分析", "两种核心方法"),
            ("README.en.md", "Object Calibration", "Audience Check", "registry.yaml"),
            ("README.md", "证据闭环", "结果复盘", "registry.yaml"),
            ("README.en.md", "only the approaches your current question needs", "every available framework", "方法按需推荐"),
            ("README.md", "使用前请你确认", "自动使用", "方法按需推荐"),
            ("README.en.md", "someone with relevant knowledge", "another person", "方法按需推荐"),
            ("README.en.md", "explains why each is needed and asks for your consent separately", "starts immediately", "能力征求同意"),
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
                "**Install:** Send this message to the Agent you already use:",
                "Send this message:",
                "把仓库链接交给当前 Agent",
            ),
            (
                "README.md",
                "也可以在终端直接运行",
                "也可以手动处理",
                "Skills CLI 入口",
            ),
            (
                "README.en.md",
                "npx skills add zemu2718/think-it-through-skill",
                "npx skills add another/repository",
                "Skills CLI GitHub 直装命令",
            ),
            (
                "README.en.md",
                "having the files installed does not mean the Skill can run correctly in your current tool.",
                "Installation proves runtime support.",
                "文件安装与真实 runtime 验证",
            ),
            (
                "README.md",
                "**开始使用：** 如果你使用 Claude Code，安装完成后输入：",
                "所有宿主都可以可靠调用。",
                "面向用户的开始使用步骤",
            ),
            (
                "README.en.md",
                "**Installation and compatibility:**",
                "**More:**",
                "三组详情入口",
            ),
            (
                "README.md",
                "**安装：** 把下面这句话发给你正在使用的 Agent：",
                "选择下列支持的 Agent：",
                "把仓库链接交给当前 Agent",
            ),
            ("README.md", "```text\n/think-it-through\n```", "```text\n/wrong\n```", "可靠显式入口"),
            ("README.en.md", "docs/installation.en.md", "docs/missing.md", "详细安装或兼容说明链接"),
            ("README.md", "**不联网**", "**按需联网**", "五项默认安全语义"),
            (
                "README.md",
                "使用这个 Skill 时，除非你明确同意某项具体操作，否则它默认：",
                "使用这个 Skill 时，除非你明确同意某项具体操作，否则它默认不是：",
                "行为极性",
            ),
            (
                "README.md",
                "使用这个 Skill 时",
                "在所有情况下",
                "准确限定 Skill 使用范围",
            ),
            (
                "README.en.md",
                "While you use this Skill, it does not do any of the following unless you explicitly approve that specific action:",
                "While you use this Skill, it does every one of the following unless you explicitly approve that specific action:",
                "行为极性",
            ),
            ("README.md", "### 更多信息", "### 其他", "更多信息入口"),
            (
                "README.md",
                "你同意一项操作，不代表也同意其他操作。",
                "你同意一项操作，就视为同意所有操作。",
                "单项同意不扩张",
            ),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, expected=expected):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

        errors = self.validate_doc_mutation(
            "README.md",
            "## 默认安全\n\n使用这个 Skill 时",
            "使用这个 Skill 时\n\n## 默认安全\n\n在所有情况下",
        ).errors
        self.assertTrue(any("准确限定 Skill 使用范围" in error for error in errors), errors)

    def test_technical_details_cannot_return_to_readme(self) -> None:
        for token in ("npx -y skills", "gh skill install", "git clone", "L0", "9/16", "approved evidence"):
            with self.subTest(token=token):
                errors = self.validate_doc_mutation(
                    "README.en.md",
                    "## Safe by default",
                    f"{token}\n\n## Safe by default",
                ).errors
                self.assertTrue(any("不得重新塞入" in error for error in errors), errors)

    def test_readme_invocation_card_language_and_badges_fail(self) -> None:
        mutations = (
            ("README.md", "[English](README.en.md)", "[English](README.md)", "中文 README 缺少英文切换"),
            ("README.en.md", "[简体中文](README.md)", "[简体中文](README.en.md)", "英文 README 缺少中文切换"),
            ("README.md", "assets/readme-invocation-card-dark.png", "assets/social-preview.png", "README Invocation Card"),
            ("README.en.md", 'width="200"', 'width="1200"', "紧凑显示宽度"),
            (
                "README.md",
                'alt="想清楚调用卡片：思考之光围绕清晰开口排列，下方显示 Claude Code 命令 /think-it-through。"',
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
                "git clone --depth 1 --branch v0.4.0",
                "git clone",
                "不可变 v0.4.0 tag",
            ),
            (
                "docs/installation.en.md",
                "cd think-it-through-skill\ngit rev-parse HEAD\ntest ! -e",
                "cd think-it-through-skill\ngit status --short\ntest ! -e",
                "准确 revision",
            ),
            (
                "docs/installation.md",
                "[`SHA256SUMS`](https://github.com/zemu2718/think-it-through-skill/releases/download/v0.4.0/SHA256SUMS)",
                "校验和文件",
                "归档核验",
            ),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, expected=expected):
                errors = self.validate_doc_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_unreleased_release_facts_fail(self) -> None:
        mutations = (
            (
                "同一次 B 用户可见输出中确定性重建 DecisionRecord 与可见决策快照",
                "从静态 fixture 加载 DecisionRecord 与可见决策快照",
                "关键合同、授权、证据链或 runtime smoke 记录",
            ),
            (
                "Python 3.12 完整单元测试 220 项通过",
                "Python 3.12 完整单元测试 219 项通过",
                "发布前验证事实或未运行边界",
            ),
            (
                "未运行 Claude Code / Codex provider smoke",
                "Claude Code / Codex provider smoke 已通过",
                "发布前验证事实或未运行边界",
            ),
        )
        for old, new, expected in mutations:
            with self.subTest(old=old):
                errors = self.validate_doc_mutation(
                    "CHANGELOG.md", old, new
                ).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_current_and_published_version_boundaries_fail(self) -> None:
        mutations = (
            (
                ".agents/brand-context.md",
                "v0.4.1 is the current release-candidate source and formal product contract, with no same-version public objects yet",
                "v0.4.1 is the current stable source, formal product contract, and latest published release",
                "稳定源码或证据边界",
            ),
            (
                ".agents/brand-context.md",
                "v0.4.0 remains the latest published immutable Git tag, GitHub Release, downloadable `think-it-through.skill`, and `SHA256SUMS`",
                "v0.4.1 remains the latest published immutable Git tag, GitHub Release, downloadable `think-it-through.skill`, and `SHA256SUMS`",
                "稳定源码或证据边界",
            ),
            (
                "docs/product-architecture-v0.4.0.md",
                "不新增 Veto Gate 或协议状态",
                "新增 Veto Gate 作为固定阶段",
                "架构基线缺少项目可行性或发布边界",
            ),
            (
                "CHANGELOG.md",
                "v0.4.0 继续作为最新真实公开发布，v0.4.1 的 tag、Release 与 asset 仅在实际创建后声明",
                "v0.4.1 已成为最新真实公开发布",
                "发布候选、最新公开发布与历史发布的分层说明",
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
                "https://github.com/zemu2718/think-it-through-skill/releases/tag/v0.4.0",
                "https://github.com/other/think-it-through-skill/releases/tag/v0.4.0",
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
                    "README.en.md", "## Safe by default", f"{term}\n\n## Safe by default"
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
            "docs/product-architecture-v0.4.0.md",
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
