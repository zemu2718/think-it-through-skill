#!/usr/bin/env python3
"""验证视觉资产 manifest、SVG 合同与可复现派生 raster 管线。"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from render_assets import (
    ROOT,
    check_generated_assets,
    check_readme_invocation_card,
    check_social_preview,
    decoded_pixels,
    load_manifest,
    write_generated_assets,
)
from validate_repo import Validation, all_repo_files, validate_assets


class AssetPipelineTests(unittest.TestCase):
    def test_manifest_has_single_canonical_subject_and_two_outputs(self) -> None:
        manifest = load_manifest()
        entries = {entry["id"]: entry for entry in manifest["assets"]}
        self.assertEqual({"readme-invocation-card", "social-preview"}, set(entries))

        invocation = entries["readme-invocation-card"]
        self.assertEqual("readme-opening-invocation-card", invocation["role"])
        self.assertEqual({"width": 600, "height": 600}, invocation["canvas"])
        self.assertEqual("RGBA", invocation["pixel_mode"])
        self.assertEqual(160000, invocation["max_source_bytes"])
        self.assertEqual(160000, invocation["max_output_bytes"])
        variants = {item["theme"]: item for item in invocation["variants"]}
        self.assertEqual(
            {
                "locale": "neutral",
                "theme": "dark",
                "source": "assets/readme-invocation-card-dark.png",
                "source_sha256": "33760ccbbf4011f663f1e998ac41f006f31a8888a22945c6e395976c7bda7ff4",
            },
            variants["dark"],
        )
        self.assertEqual(
            {
                "locale": "neutral",
                "theme": "light",
                "output": "assets/readme-invocation-card-light.png",
            },
            variants["light"],
        )
        self.assertEqual("Pillow", invocation["generator"]["renderer"])
        self.assertEqual(1, invocation["composition"]["scale"])
        self.assertEqual("none", invocation["composition"]["resampling"])

        social = entries["social-preview"]
        self.assertEqual(
            {
                "canonical_asset": "readme-invocation-card",
                "canonical_theme": "dark",
                "subject_anchor": [914, 100],
                "scale": 1,
                "resampling": "none",
            },
            social["composition"],
        )
        generator = social["generator"]
        self.assertEqual("resvg-py", generator["renderer"])
        self.assertEqual("0.5.0", generator["renderer_version"])
        self.assertEqual("Pillow", generator["compositor"])
        self.assertEqual("11.3.0", generator["compositor_version"])
        self.assertTrue(generator["skip_system_fonts"])
        self.assertEqual("RGBA", generator["pixel_mode"])

    def test_canonical_assets_validate(self) -> None:
        validation = Validation()
        validate_assets(validation, all_repo_files())
        self.assertEqual([], validation.errors)

    def test_missing_theme_or_locale_fails(self) -> None:
        with self.repository_copy() as root:
            manifest_path = root / "assets" / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entry = next(item for item in manifest["assets"] if item["id"] == "readme-invocation-card")
            entry["variants"].pop()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            errors = self.validate_copy(root).errors
            self.assertTrue(any("README Invocation Card" in error or "语言/主题变体" in error for error in errors))

    def test_svg_security_and_structure_mutations_fail(self) -> None:
        mutations = (
            ("</svg>", '<script>alert(1)</script></svg>', "不得包含脚本"),
            ("</svg>", '<image href="https://example.com/a.png"/></svg>', "不得引用远程资源"),
            ("</svg>", '<image href="data:image/png;base64,AA=="/></svg>', "不得包含 data URI raster"),
            ("</svg>", '<path onclick="alert(1)"/></svg>', "不得包含事件处理器"),
            ("</svg>", "<foreignObject/></svg>", "不得包含 foreignObject"),
            ("</svg>", "<text>font</text></svg>", "不得包含 text"),
            ('id="thinking-light-slot"', 'id="missing-light-slot"', "缺少稳定结构 ID"),
            ("</svg>", '<linearGradient id="bad"/></svg>', "不得使用 gradient 或 filter"),
        )
        for old, new, expected in mutations:
            with self.subTest(expected=expected):
                errors = self.validate_asset_mutation("assets/social-preview.svg", old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_social_preview_metadata_mutations_fail(self) -> None:
        mutations = (
            (
                'aria-label="Think It Through"',
                'aria-label="Think Through"',
                "wordmark 必须准确表达完整名称",
            ),
            (
                "AI can get things done fast, but what's worth doing is still yours to decide.",
                "AI can finish work quickly.",
                "desc 必须包含完整 canonical 英文定位",
            ),
            (
                'aria-label="AI can get things done fast, but what\'s worth doing is still yours to decide."',
                'aria-label="AI works quickly."',
                "positioning 必须提供准确的定位 aria-label",
            ),
            (
                'aria-label="Claude Code command /think-it-through"',
                'aria-label="Run the skill"',
                "invocation 必须提供准确的调用 aria-label",
            ),
        )
        for old, new, expected in mutations:
            with self.subTest(expected=expected):
                errors = self.validate_asset_mutation("assets/social-preview.svg", old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_social_preview_required_groups_contain_paths(self) -> None:
        groups = (
            ("wordmark", "wordmark 必须包含实际 path"),
            ("positioning", "positioning 必须包含实际布局 path"),
            ("invocation", "invocation 必须包含实际布局 path"),
        )
        for element_id, expected in groups:
            with self.subTest(element_id=element_id), self.repository_copy() as root:
                path = root / "assets" / "social-preview.svg"
                text = path.read_text(encoding="utf-8")
                start = text.index(f'<g id="{element_id}"')
                content_start = text.index(">", start) + 1
                end = text.index("</g>", content_start)
                path.write_text(text[:content_start] + text[end:], encoding="utf-8")
                errors = self.validate_copy(root).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_legacy_social_structure_is_rejected(self) -> None:
        for legacy_id in ("decision-thread", "optional-gate", "reassessment-loop", "tagline"):
            with self.subTest(legacy_id=legacy_id):
                errors = self.validate_asset_mutation(
                    "assets/social-preview.svg",
                    "</svg>",
                    f'<g id="{legacy_id}"><path d="M0 0"/></g></svg>',
                ).errors
                self.assertTrue(any("不得恢复旧线框流程图或像素 tagline" in error for error in errors), errors)

    def test_unmanaged_legacy_asset_fails(self) -> None:
        with self.repository_copy() as root:
            (root / "assets" / "hero-light.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><title>x</title><desc>x</desc></svg>',
                encoding="utf-8",
            )
            errors = self.validate_copy(root).errors
            self.assertTrue(any("必须由 manifest 精确声明" in error for error in errors), errors)

    def test_tracked_generated_assets_are_current(self) -> None:
        self.assertEqual([], check_generated_assets())

    def test_canonical_dark_byte_change_is_rejected(self) -> None:
        with self.repository_copy() as root:
            source = root / "assets" / "readme-invocation-card-dark.png"
            source.write_bytes(source.read_bytes() + b"changed")
            errors = self.validate_copy(root).errors
            self.assertTrue(any("Invocation Card dark SHA-256 不匹配" in error for error in errors), errors)

    def test_dark_subject_change_makes_both_outputs_stale(self) -> None:
        with self.repository_copy() as root:
            source = root / "assets" / "readme-invocation-card-dark.png"
            with Image.open(source) as image:
                image.load()
                changed = image.convert("RGBA")
            red, green, blue, alpha = changed.getpixel((300, 180))
            changed.putpixel((300, 180), ((red + 64) % 256, green, blue, alpha))
            changed.save(source, format="PNG", optimize=True)
            manifest_path = root / "assets" / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            invocation = next(item for item in manifest["assets"] if item["id"] == "readme-invocation-card")
            dark = next(item for item in invocation["variants"] if item["theme"] == "dark")
            dark["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertTrue(any("像素已过期" in error for error in check_readme_invocation_card(root)))
            self.assertTrue(any("像素已过期" in error for error in check_social_preview(root)))

    def test_light_output_pixel_change_is_stale(self) -> None:
        with self.repository_copy() as root:
            output = root / "assets" / "readme-invocation-card-light.png"
            with Image.open(output) as image:
                image.load()
                changed = image.convert("RGBA")
            changed.putpixel((300, 300), (255, 0, 255, 255))
            changed.save(output, format="PNG", optimize=True)
            self.assertTrue(any("像素已过期" in error for error in check_readme_invocation_card(root)))

    def test_light_output_dimension_mode_or_alpha_change_is_rejected(self) -> None:
        changes = (
            ("RGBA", (300, 300), False, "必须是 600×600"),
            ("RGB", (600, 600), False, "pixel mode 必须是 RGBA"),
            ("RGBA", (600, 600), True, "必须同时包含透明和不透明像素"),
        )
        for mode, size, opaque, expected in changes:
            with self.subTest(mode=mode, size=size, opaque=opaque), self.repository_copy() as root:
                output = root / "assets" / "readme-invocation-card-light.png"
                with Image.open(output) as image:
                    image.load()
                    changed = image.convert(mode).resize(size)
                if opaque:
                    changed.putalpha(255)
                changed.save(output, format="PNG", optimize=True)
                errors = self.validate_copy(root).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_composition_mutations_fail(self) -> None:
        with self.repository_copy() as root:
            manifest_path = root / "assets" / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            invocation = next(item for item in manifest["assets"] if item["id"] == "readme-invocation-card")
            invocation["composition"]["scale"] = 0.9
            social = next(item for item in manifest["assets"] if item["id"] == "social-preview")
            social["composition"]["canonical_theme"] = "light"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            errors = self.validate_copy(root).errors
            self.assertTrue(any("固定复用 dark 主体" in error for error in errors), errors)
            self.assertTrue(any("复用 dark canonical Thinking Light" in error for error in errors), errors)

    def test_svg_source_change_makes_png_stale(self) -> None:
        with self.repository_copy() as root:
            source = root / "assets" / "social-preview.svg"
            text = source.read_text(encoding="utf-8")
            source.write_text(text.replace("#090909", "#0A0A0A", 1), encoding="utf-8")
            self.assertTrue(any("像素已过期" in error for error in check_social_preview(root)))

    def test_social_output_pixel_change_is_stale(self) -> None:
        with self.repository_copy() as root:
            output = root / "assets" / "social-preview.png"
            with Image.open(output) as image:
                image.load()
                rgba = image.convert("RGBA")
            rgba.putpixel((0, 0), (255, 255, 255, 255))
            rgba.save(output, format="PNG", optimize=True)
            self.assertTrue(any("像素已过期" in error for error in check_social_preview(root)))

    def test_social_output_dimension_change_is_rejected(self) -> None:
        with self.repository_copy() as root:
            output = root / "assets" / "social-preview.png"
            with Image.open(output) as image:
                image.load()
                resized = image.convert("RGBA").resize((640, 320))
            resized.save(output, format="PNG", optimize=True)
            self.assertTrue(any("尺寸过期" in error for error in check_social_preview(root)))

    def test_corrupted_idat_is_rejected_by_full_decode(self) -> None:
        with self.repository_copy() as root:
            output = root / "assets" / "social-preview.png"
            data = bytearray(output.read_bytes())
            marker = data.find(b"IDAT")
            self.assertGreater(marker, 0)
            data[marker + 12] ^= 0xFF
            output.write_bytes(data)
            self.assertTrue(any("无法完整解码" in error for error in check_social_preview(root)))

    def test_same_pixels_with_different_compression_are_current(self) -> None:
        with self.repository_copy() as root:
            output = root / "assets" / "social-preview.png"
            original = output.read_bytes()
            with Image.open(io.BytesIO(original)) as image:
                image.load()
                rgba = image.convert("RGBA")
            buffer = io.BytesIO()
            rgba.save(buffer, format="PNG", optimize=False, compress_level=6)
            rewritten = buffer.getvalue()
            self.assertNotEqual(original, rewritten)
            self.assertEqual(decoded_pixels(original), decoded_pixels(rewritten))
            output.write_bytes(rewritten)
            self.assertEqual([], check_social_preview(root))

    def test_generation_writes_expected_outputs_only(self) -> None:
        with self.repository_copy() as root:
            output_names = {"readme-invocation-card-light.png", "social-preview.png"}
            before = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file() and path.name not in output_names
            }
            dark_before = (root / "assets" / "readme-invocation-card-dark.png").read_bytes()
            outputs = write_generated_assets(root)
            self.assertEqual(
                {"assets/readme-invocation-card-light.png", "assets/social-preview.png"},
                {path.relative_to(root).as_posix() for path in outputs},
            )
            after = {relative: (root / relative).read_bytes() for relative in before}
            self.assertEqual(before, after)
            self.assertEqual(dark_before, (root / "assets" / "readme-invocation-card-dark.png").read_bytes())
            self.assertEqual([], check_generated_assets(root))

    def validate_asset_mutation(self, relative: str, old: str, new: str) -> Validation:
        with self.repository_copy() as root:
            path = root / relative
            text = path.read_text(encoding="utf-8")
            self.assertIn(old, text)
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            return self.validate_copy(root)

    def validate_copy(self, root: Path) -> Validation:
        validation = Validation()
        with mock.patch("validate_repo.ROOT", root):
            validate_assets(validation, [path for path in root.rglob("*") if path.is_file()])
        return validation

    def repository_copy(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        shutil.copytree(ROOT / "assets", root / "assets")

        class RepositoryCopy:
            def __enter__(self) -> Path:
                return root

            def __exit__(self, *args: object) -> None:
                temporary.cleanup()

        return RepositoryCopy()


if __name__ == "__main__":
    unittest.main()
