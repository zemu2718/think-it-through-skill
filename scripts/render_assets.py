#!/usr/bin/env python3
"""按 assets/manifest.json 生成或检查仓库内的派生视觉资产。"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
from typing import Iterable

import resvg_py
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "assets" / "manifest.json"


def load_manifest(root: Path = ROOT) -> dict[str, object]:
    manifest = json.loads((root / "assets" / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("assets/manifest.json 顶层必须是对象")
    return manifest


def asset_spec(manifest: dict[str, object], asset_id: str) -> dict[str, object]:
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise ValueError("assets manifest 缺少 assets 数组")
    matches = [item for item in assets if isinstance(item, dict) and item.get("id") == asset_id]
    if len(matches) != 1:
        raise ValueError(f"assets manifest 必须且只能定义一个 {asset_id}")
    return matches[0]


def social_preview_spec(manifest: dict[str, object]) -> dict[str, object]:
    return asset_spec(manifest, "social-preview")


def _canvas_size(spec: dict[str, object], key: str = "canvas") -> tuple[int, int]:
    canvas = spec.get(key)
    if not isinstance(canvas, dict):
        raise ValueError(f"资产缺少 {key}")
    width = canvas.get("width")
    height = canvas.get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        raise ValueError(f"资产 {key} 必须包含整数 width/height")
    return width, height


def _single_source_and_output(root: Path, spec: dict[str, object]) -> tuple[Path, Path]:
    variants = spec.get("variants")
    if not isinstance(variants, list) or len(variants) != 1 or not isinstance(variants[0], dict):
        raise ValueError("social-preview 必须只有一个源/输出变体")
    source = variants[0].get("source")
    output = variants[0].get("output")
    if not isinstance(source, str) or not isinstance(output, str):
        raise ValueError("social-preview 变体必须声明 source 与 output")
    return root / source, root / output


def _png_bytes(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True, compress_level=9)
    return output.getvalue()


def render_social_preview(root: Path = ROOT) -> bytes:
    manifest = load_manifest(root)
    spec = social_preview_spec(manifest)
    source, _ = _single_source_and_output(root, spec)
    svg = source.read_text(encoding="utf-8")
    if "<text" in svg.lower():
        raise ValueError("Social Preview 不得依赖 <text> 或系统字体")
    rendered = resvg_py.svg_to_bytes(svg_string=svg, skip_system_fonts=True)
    with Image.open(io.BytesIO(rendered)) as image:
        image.load()
        rgba = image.convert("RGBA")
        expected_size = _canvas_size(spec)
        if rgba.size != expected_size:
            raise ValueError(f"Social Preview 渲染尺寸错误：{rgba.size}，预期 {expected_size}")
        return _png_bytes(rgba)


def _banner_source(root: Path, spec: dict[str, object]) -> Image.Image:
    source_value = spec.get("source")
    expected_hash = spec.get("source_sha256")
    if not isinstance(source_value, str) or not isinstance(expected_hash, str):
        raise ValueError("README Banner 必须声明 source 与 source_sha256")
    source = root / source_value
    data = source.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError(f"README Banner canonical source SHA-256 不匹配：{actual_hash}")
    with Image.open(io.BytesIO(data)) as image:
        image.verify()
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        if image.size != _canvas_size(spec, "source_canvas"):
            raise ValueError(
                f"README Banner source 尺寸错误：{image.size}，预期 {_canvas_size(spec, 'source_canvas')}"
            )
        if image.mode != "RGB":
            raise ValueError(f"README Banner source 必须是 RGB，实际为 {image.mode}")
        return image.copy()


def _background_mask(image: Image.Image, params: dict[str, object]) -> Image.Image:
    luma_max = params.get("background_luma_max")
    chroma_max = params.get("background_chroma_max")
    aperture_box = params.get("aperture_box")
    feather_radius = params.get("feather_radius")
    if not isinstance(luma_max, int) or not isinstance(chroma_max, int):
        raise ValueError("README Banner light_theme 缺少背景阈值")
    if not isinstance(aperture_box, list) or len(aperture_box) != 4 or not all(isinstance(value, int) for value in aperture_box):
        raise ValueError("README Banner light_theme aperture_box 必须是四个整数")
    if not isinstance(feather_radius, int):
        raise ValueError("README Banner light_theme feather_radius 必须是整数")

    eligible = Image.new("L", image.size)
    eligible.putdata([
        255 if (54 * red + 183 * green + 19 * blue) // 256 <= luma_max and max(red, green, blue) - min(red, green, blue) <= chroma_max else 0
        for red, green, blue in image.getdata()
    ])
    ImageDraw.Draw(eligible).rectangle(tuple(aperture_box), fill=0)

    connected = eligible.copy()
    corners = ((0, 0), (image.width - 1, 0), (0, image.height - 1), (image.width - 1, image.height - 1))
    for corner in corners:
        if connected.getpixel(corner) == 255:
            ImageDraw.floodfill(connected, corner, 128, thresh=0)
    mask = connected.point(lambda value: 255 if value == 128 else 0)
    if feather_radius:
        mask = mask.filter(ImageFilter.GaussianBlur(feather_radius))
    return mask


def _light_banner(source: Image.Image, params: dict[str, object]) -> Image.Image:
    background_rgb = params.get("background_rgb")
    shadow_box = params.get("contact_shadow_box")
    shadow_alpha = params.get("contact_shadow_alpha")
    shadow_blur = params.get("contact_shadow_blur")
    luma_scale = params.get("neutral_luma_scale")
    luma_offset = params.get("neutral_luma_offset")
    if not isinstance(background_rgb, list) or len(background_rgb) != 3 or not all(isinstance(value, int) for value in background_rgb):
        raise ValueError("README Banner light_theme background_rgb 必须是三个整数")
    if not isinstance(shadow_box, list) or len(shadow_box) != 4 or not all(isinstance(value, int) for value in shadow_box):
        raise ValueError("README Banner light_theme contact_shadow_box 必须是四个整数")
    if not isinstance(shadow_alpha, int) or not isinstance(shadow_blur, int):
        raise ValueError("README Banner light_theme 缺少接触阴影参数")
    if not isinstance(luma_scale, (int, float)) or not isinstance(luma_offset, int):
        raise ValueError("README Banner light_theme 缺少主体中性色参数")

    matte = Image.new("RGB", source.size, tuple(background_rgb))
    shadow = Image.new("RGBA", source.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(tuple(shadow_box), fill=(34, 37, 36, shadow_alpha))
    shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur))
    matte = Image.alpha_composite(matte.convert("RGBA"), shadow).convert("RGB")

    toned = source.point(lambda value: max(0, min(255, round(value * float(luma_scale) + luma_offset))))
    toned = ImageEnhance.Color(toned).enhance(0.82)

    chroma = Image.new("L", source.size)
    chroma.putdata([255 if max(pixel) - min(pixel) >= 18 else 0 for pixel in source.getdata()])
    chroma = chroma.filter(ImageFilter.GaussianBlur(1.5))
    subject = Image.composite(source, toned, chroma)
    return Image.composite(matte, subject, _background_mask(source, params))


def render_readme_banners(root: Path = ROOT) -> dict[str, bytes]:
    manifest = load_manifest(root)
    spec = asset_spec(manifest, "readme-banner")
    source = _banner_source(root, spec)
    generator = spec.get("generator")
    if not isinstance(generator, dict) or not isinstance(generator.get("light_theme"), dict):
        raise ValueError("README Banner 缺少 generator.light_theme")
    target_size = _canvas_size(spec, "output_canvas")
    light = _light_banner(source, generator["light_theme"])
    images = {
        "light": light.resize(target_size, Image.Resampling.LANCZOS),
        "dark": source.resize(target_size, Image.Resampling.LANCZOS),
    }

    variants = spec.get("variants")
    if not isinstance(variants, list):
        raise ValueError("README Banner 缺少 variants")
    rendered: dict[str, bytes] = {}
    for variant in variants:
        if not isinstance(variant, dict):
            raise ValueError("README Banner 含无效变体")
        theme = variant.get("theme")
        output = variant.get("output")
        if theme not in images or not isinstance(output, str):
            raise ValueError("README Banner 变体必须声明 light/dark theme 与 output")
        rendered[output] = _png_bytes(images[theme].convert("RGB"))
    return rendered


def decoded_pixels(png: bytes) -> tuple[tuple[int, int], str]:
    with Image.open(io.BytesIO(png)) as image:
        image.verify()
    with Image.open(io.BytesIO(png)) as image:
        image.load()
        rgba = image.convert("RGBA")
        return rgba.size, hashlib.sha256(rgba.tobytes()).hexdigest()


def decoded_image(png: bytes) -> tuple[tuple[int, int], str, str]:
    with Image.open(io.BytesIO(png)) as image:
        image.verify()
    with Image.open(io.BytesIO(png)) as image:
        image.load()
        mode = image.mode
        pixels = hashlib.sha256(image.tobytes()).hexdigest()
        return image.size, mode, pixels


def _check_outputs(root: Path, label: str, rendered: dict[str, bytes], max_bytes: int | None) -> list[str]:
    errors: list[str] = []
    for relative, fresh in rendered.items():
        output = root / relative
        if not output.exists():
            errors.append(f"缺少派生资产：{relative}")
            continue
        tracked = output.read_bytes()
        try:
            fresh_size, fresh_pixels = decoded_pixels(fresh)
        except Exception as error:
            errors.append(f"fresh {label} 无法完整解码：{error}")
            continue
        try:
            tracked_size, tracked_pixels = decoded_pixels(tracked)
        except Exception as error:
            errors.append(f"tracked {label} 无法完整解码：{error}")
            continue
        if tracked_size != fresh_size:
            errors.append(f"{label} 尺寸过期：tracked={tracked_size}，fresh={fresh_size}")
        if tracked_pixels != fresh_pixels:
            errors.append(f"{label} 像素已过期；请运行 python scripts/render_assets.py")
        if isinstance(max_bytes, int) and len(tracked) > max_bytes:
            errors.append(f"{label} 超出字节预算：{len(tracked)} > {max_bytes}")
    return errors


def check_social_preview(root: Path = ROOT) -> list[str]:
    manifest = load_manifest(root)
    spec = social_preview_spec(manifest)
    _, output = _single_source_and_output(root, spec)
    return _check_outputs(
        root,
        "Social Preview",
        {str(output.relative_to(root)): render_social_preview(root)},
        spec.get("max_output_bytes") if isinstance(spec.get("max_output_bytes"), int) else None,
    )


def check_readme_banners(root: Path = ROOT) -> list[str]:
    manifest = load_manifest(root)
    spec = asset_spec(manifest, "readme-banner")
    return _check_outputs(
        root,
        "README Banner",
        render_readme_banners(root),
        spec.get("max_output_bytes") if isinstance(spec.get("max_output_bytes"), int) else None,
    )


def check_generated_assets(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for check in (check_readme_banners, check_social_preview):
        try:
            errors.extend(check(root))
        except Exception as error:
            errors.append(f"派生资产无法重渲染检查：{error}")
    return errors


def write_social_preview(root: Path = ROOT) -> Path:
    manifest = load_manifest(root)
    spec = social_preview_spec(manifest)
    _, output = _single_source_and_output(root, spec)
    output.write_bytes(render_social_preview(root))
    return output


def write_generated_assets(root: Path = ROOT) -> list[Path]:
    outputs: list[Path] = []
    for relative, rendered in render_readme_banners(root).items():
        output = root / relative
        output.write_bytes(rendered)
        outputs.append(output)
    outputs.append(write_social_preview(root))
    return outputs


def _relative_paths(paths: Iterable[Path], root: Path) -> str:
    return ", ".join(str(path.relative_to(root)) for path in paths)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只在内存中重渲染并比较像素，不写文件")
    args = parser.parse_args()
    if args.check:
        errors = check_generated_assets()
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print("README Banner 与 Social Preview 完整解码、尺寸、预算和像素均为最新")
        return 0
    outputs = write_generated_assets()
    print(f"已生成 {_relative_paths(outputs, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
