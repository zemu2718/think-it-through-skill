#!/usr/bin/env python3
"""验证视觉资产 manifest、SVG 合同与可复现 Social Preview 管线。"""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from render_assets import ROOT, check_social_preview, decoded_pixels, load_manifest
from validate_repo import Validation, all_repo_files, validate_assets


class AssetPipelineTests(unittest.TestCase):
    def test_manifest_has_required_roles_variants_and_generator(self) -> None:
        manifest = load_manifest()
        entries = {entry["id"]: entry for entry in manifest["assets"]}
        self.assertEqual({"brand-mark", "decision-case", "social-preview"}, set(entries))
        self.assertEqual("readme-brand-mark", entries["brand-mark"]["role"])
        self.assertEqual(
            {("neutral", "light"), ("neutral", "dark")},
            {(item["locale"], item["theme"]) for item in entries["brand-mark"]["variants"]},
        )
        self.assertEqual("readme-informational-case", entries["decision-case"]["role"])
        self.assertEqual(
            {("en", "light"), ("en", "dark"), ("zh-CN", "light"), ("zh-CN", "dark")},
            {(item["locale"], item["theme"]) for item in entries["decision-case"]["variants"]},
        )
        self.assertEqual({"width": 128, "height": 128}, entries["brand-mark"]["canvas"])
        self.assertEqual({"width": 1200, "height": 680}, entries["decision-case"]["canvas"])
        generator = entries["social-preview"]["generator"]
        self.assertEqual("resvg-py", generator["renderer"])
        self.assertEqual("0.5.0", generator["renderer_version"])
        self.assertEqual("Pillow", generator["decoder"])
        self.assertEqual("11.3.0", generator["decoder_version"])
        self.assertTrue(generator["skip_system_fonts"])
        self.assertEqual("RGBA", generator["pixel_mode"])

    def test_canonical_assets_validate(self) -> None:
        validation = Validation()
        validate_assets(validation, all_repo_files())
        self.assertEqual([], validation.errors)

    def test_missing_theme_or_locale_fails(self) -> None:
        for asset_id, expected in (("brand-mark", "Brand Mark"), ("decision-case", "Decision Case")):
            with self.subTest(asset_id=asset_id), self.repository_copy() as root:
                manifest_path = root / "assets" / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                entry = next(item for item in manifest["assets"] if item["id"] == asset_id)
                entry["variants"].pop()
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                errors = self.validate_copy(root).errors
                self.assertTrue(any(expected in error or "语言/主题变体" in error for error in errors))

    def test_svg_security_and_structure_mutations_fail(self) -> None:
        mutations = (
            ("assets/brand-mark-light.svg", "</svg>", '<script>alert(1)</script></svg>', "不得包含脚本"),
            ("assets/brand-mark-light.svg", "</svg>", '<image href="https://example.com/a.png"/></svg>', "不得引用远程资源"),
            ("assets/brand-mark-light.svg", "</svg>", '<image href="data:image/png;base64,AA=="/></svg>', "不得包含 data URI raster"),
            ("assets/brand-mark-light.svg", "</svg>", '<path onclick="alert(1)"/></svg>', "不得包含事件处理器"),
            ("assets/brand-mark-light.svg", "</svg>", '<foreignObject/></svg>', "不得包含 foreignObject"),
            ("assets/brand-mark-light.svg", "</svg>", '<text>font</text></svg>', "Brand Mark 不得包含 text"),
            ("assets/brand-mark-light.svg", 'id="committed-path"', 'id="missing-path"', "缺少稳定结构 ID"),
            ("assets/brand-mark-dark.svg", 'd="M12 28 C30 28 39 43 54 56"', 'd="M12 27 C30 28 39 43 54 56"', "共享相同非颜色几何"),
            (
                "assets/decision-case-light.svg",
                '<g id="optional-gate" font-family="ui-sans-serif, system-ui, sans-serif" stroke-dasharray="9 9">',
                '<g id="optional-gate" font-family="ui-sans-serif, system-ui, sans-serif">',
                "可选 Gate 必须实际使用虚线",
            ),
            ("assets/social-preview.svg", "</svg>", '<text>font</text></svg>', "Social Preview 不得包含 text"),
            ("assets/social-preview.svg", "</svg>", '<linearGradient id="bad"/></svg>', "不得使用 gradient 或 filter"),
        )
        for relative, old, new, expected in mutations:
            with self.subTest(relative=relative, expected=expected):
                errors = self.validate_asset_mutation(relative, old, new).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_wordmark_and_tagline_require_actual_paths(self) -> None:
        for element_id, expected in (("wordmark", "wordmark 必须包含实际 path"), ("tagline", "tagline 必须包含实际 path")):
            with self.subTest(element_id=element_id), self.repository_copy() as root:
                path = root / "assets" / "social-preview.svg"
                text = path.read_text(encoding="utf-8")
                start = text.index(f'<g id="{element_id}"')
                content_start = text.index(">", start) + 1
                end = text.index("</g>", content_start)
                text = text[:content_start] + "" + text[end:]
                path.write_text(text, encoding="utf-8")
                errors = self.validate_copy(root).errors
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_unmanaged_legacy_asset_fails(self) -> None:
        with self.repository_copy() as root:
            (root / "assets" / "hero-light.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><title>x</title><desc>x</desc></svg>',
                encoding="utf-8",
            )
            errors = self.validate_copy(root).errors
            self.assertTrue(any("必须由 manifest 精确声明" in error for error in errors), errors)

    def test_tracked_social_preview_is_current(self) -> None:
        self.assertEqual([], check_social_preview())

    def test_svg_source_change_makes_png_stale(self) -> None:
        with self.repository_copy() as root:
            source = root / "assets" / "social-preview.svg"
            text = source.read_text(encoding="utf-8")
            source.write_text(text.replace("#0B1117", "#0C1218", 1), encoding="utf-8")
            self.assertTrue(any("像素已过期" in error for error in check_social_preview(root)))

    def test_pixel_change_makes_png_stale(self) -> None:
        with self.repository_copy() as root:
            output = root / "assets" / "social-preview.png"
            with Image.open(output) as image:
                image.load()
                rgba = image.convert("RGBA")
            rgba.putpixel((0, 0), (255, 255, 255, 255))
            rgba.save(output, format="PNG", optimize=True)
            self.assertTrue(any("像素已过期" in error for error in check_social_preview(root)))

    def test_dimension_change_is_rejected(self) -> None:
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
