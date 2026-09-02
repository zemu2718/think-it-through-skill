#!/usr/bin/env python3
"""按 assets/manifest.json 生成或检查仓库内的派生视觉资产。"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from collections import deque
from pathlib import Path
from typing import Iterable

import resvg_py
from PIL import Image, ImageDraw, ImageFilter, ImageFont

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


def invocation_card_spec(manifest: dict[str, object]) -> dict[str, object]:
    return asset_spec(manifest, "readme-invocation-card")


def social_preview_spec(manifest: dict[str, object]) -> dict[str, object]:
    return asset_spec(manifest, "social-preview")


def _canvas_size(spec: dict[str, object]) -> tuple[int, int]:
    canvas = spec.get("canvas")
    if not isinstance(canvas, dict):
        raise ValueError("资产缺少 canvas")
    width = canvas.get("width")
    height = canvas.get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        raise ValueError("资产 canvas 必须包含整数 width/height")
    return width, height


def _png_bytes(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True, compress_level=9)
    return output.getvalue()


def _load_canonical_card(root: Path, spec: dict[str, object]) -> Image.Image:
    variants = spec.get("variants")
    if not isinstance(variants, list):
        raise ValueError("README Invocation Card 缺少 variants")
    dark = next(
        (variant for variant in variants if isinstance(variant, dict) and variant.get("theme") == "dark"),
        None,
    )
    if not isinstance(dark, dict) or not isinstance(dark.get("source"), str):
        raise ValueError("README Invocation Card 缺少 dark canonical source")
    source = root / dark["source"]
    data = source.read_bytes()
    expected_hash = dark.get("source_sha256")
    if not isinstance(expected_hash, str) or hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError("README Invocation Card dark canonical source SHA-256 不匹配")
    with Image.open(io.BytesIO(data)) as image:
        image.verify()
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        if image.size != _canvas_size(spec) or image.mode != "RGBA":
            raise ValueError("README Invocation Card dark canonical source 尺寸或模式不正确")
        return image.copy()


def _composition(spec: dict[str, object]) -> tuple[tuple[int, int, int, int], tuple[int, int]]:
    composition = spec.get("composition")
    if not isinstance(composition, dict):
        raise ValueError("README Invocation Card 缺少 composition")
    crop = composition.get("subject_crop")
    anchor = composition.get("subject_anchor")
    if (
        not isinstance(crop, list)
        or len(crop) != 4
        or not all(isinstance(value, int) for value in crop)
        or not isinstance(anchor, list)
        or len(anchor) != 2
        or not all(isinstance(value, int) for value in anchor)
        or composition.get("scale") != 1
        or composition.get("resampling") != "none"
    ):
        raise ValueError("README Invocation Card composition 必须使用固定整数 crop/anchor、1:1 比例且不得重采样")
    return (crop[0], crop[1], crop[2], crop[3]), (anchor[0], anchor[1])


def _extract_thinking_light(card: Image.Image, spec: dict[str, object]) -> Image.Image:
    crop_box, _ = _composition(spec)
    subject = card.crop(crop_box)
    width, height = subject.size
    pixels = subject.load()
    connected = [[False] * width for _ in range(height)]
    background_like = [[False] * width for _ in range(height)]
    background = (9, 9, 9)
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            distance = max(abs(red - background[0]), abs(green - background[1]), abs(blue - background[2]))
            background_like[y][x] = alpha > 0 and distance <= 52

    queue: deque[tuple[int, int]] = deque()
    for x in range(width):
        for y in (0, height - 1):
            if background_like[y][x] and not connected[y][x]:
                connected[y][x] = True
                queue.append((x, y))
    for y in range(height):
        for x in (0, width - 1):
            if background_like[y][x] and not connected[y][x]:
                connected[y][x] = True
                queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        for next_x, next_y in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if (
                0 <= next_x < width
                and 0 <= next_y < height
                and background_like[next_y][next_x]
                and not connected[next_y][next_x]
            ):
                connected[next_y][next_x] = True
                queue.append((next_x, next_y))

    alpha = Image.new("L", subject.size, 255)
    alpha_pixels = alpha.load()
    for y in range(height):
        for x in range(width):
            if connected[y][x]:
                red, green, blue, _ = pixels[x, y]
                distance = max(abs(red - background[0]), abs(green - background[1]), abs(blue - background[2]))
                alpha_pixels[x, y] = max(0, min(255, round((distance - 8) * 255 / 44)))
    subject.putalpha(alpha.filter(ImageFilter.GaussianBlur(0.6)))
    return subject


def _light_card_base(card: Image.Image) -> Image.Image:
    surface = (242, 239, 231)
    border = (206, 199, 186)
    output = Image.new("RGBA", card.size, (0, 0, 0, 0))
    source_pixels = card.load()
    output_pixels = output.load()
    for y in range(card.height):
        for x in range(card.width):
            red, green, blue, alpha = source_pixels[x, y]
            if alpha == 0:
                continue
            if x < 72 or x > 528 or y < 72 or y > 528:
                luminance = (red + green + blue) / 3
                amount = max(0.0, min(1.0, (luminance - 12) / 36))
                color = tuple(round(surface[index] * (1 - amount) + border[index] * amount) for index in range(3))
            else:
                color = surface
            output_pixels[x, y] = (*color, alpha)
    return output


def _overlay_invocation(card: Image.Image, source: Image.Image) -> None:
    card_pixels = card.load()
    source_pixels = source.load()
    for y in range(480, 535):
        for x in range(125, 475):
            red, green, blue, alpha = source_pixels[x, y]
            if alpha == 0:
                continue
            if green - red > 18 and green - blue > 18:
                amount = max(0.0, min(1.0, (green - 15) / 215))
                foreground = (47, 125, 74)
            else:
                luminance = (red + green + blue) / 3
                if luminance < 22:
                    continue
                amount = max(0.0, min(1.0, (luminance - 12) / 220))
                foreground = (52, 52, 52)
            background = card_pixels[x, y][:3]
            color = tuple(round(background[index] * (1 - amount) + foreground[index] * amount) for index in range(3))
            card_pixels[x, y] = (*color, alpha)


def render_readme_invocation_card(root: Path = ROOT) -> bytes:
    manifest = load_manifest(root)
    spec = invocation_card_spec(manifest)
    canonical = _load_canonical_card(root, spec)
    subject = _extract_thinking_light(canonical, spec)
    _, anchor = _composition(spec)
    output = _light_card_base(canonical)
    shadow = Image.new("RGBA", canonical.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((208, 408, 392, 452), fill=(40, 40, 40, 38))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    output = Image.alpha_composite(output, shadow)
    output.alpha_composite(subject, dest=anchor)
    _overlay_invocation(output, canonical)
    return _png_bytes(output)


def _single_source_and_output(root: Path, spec: dict[str, object]) -> tuple[Path, Path]:
    variants = spec.get("variants")
    if not isinstance(variants, list) or len(variants) != 1 or not isinstance(variants[0], dict):
        raise ValueError("social-preview 必须只有一个源/输出变体")
    source = variants[0].get("source")
    output = variants[0].get("output")
    if not isinstance(source, str) or not isinstance(output, str):
        raise ValueError("social-preview 变体必须声明 source 与 output")
    return root / source, root / output


def _social_anchor(spec: dict[str, object]) -> tuple[int, int]:
    composition = spec.get("composition")
    if not isinstance(composition, dict):
        raise ValueError("Social Preview 缺少 composition")
    anchor = composition.get("subject_anchor")
    if (
        composition.get("canonical_asset") != "readme-invocation-card"
        or composition.get("canonical_theme") != "dark"
        or composition.get("scale") != 1
        or composition.get("resampling") != "none"
        or not isinstance(anchor, list)
        or len(anchor) != 2
        or not all(isinstance(value, int) for value in anchor)
    ):
        raise ValueError("Social Preview 必须以固定整数 anchor 1:1 复用 dark canonical Thinking Light")
    return anchor[0], anchor[1]


def render_social_preview(root: Path = ROOT) -> bytes:
    manifest = load_manifest(root)
    social_spec = social_preview_spec(manifest)
    source, _ = _single_source_and_output(root, social_spec)
    svg = source.read_text(encoding="utf-8")
    if "<text" in svg.lower():
        raise ValueError("Social Preview 不得依赖 <text> 或系统字体")
    rendered = resvg_py.svg_to_bytes(svg_string=svg, skip_system_fonts=True)
    with Image.open(io.BytesIO(rendered)) as image:
        image.load()
        output = image.convert("RGBA")
    if output.size != _canvas_size(social_spec):
        raise ValueError(f"Social Preview 渲染尺寸错误：{output.size}，预期 {_canvas_size(social_spec)}")

    invocation_spec = invocation_card_spec(manifest)
    canonical = _load_canonical_card(root, invocation_spec)
    subject = _extract_thinking_light(canonical, invocation_spec)
    output.alpha_composite(subject, dest=_social_anchor(social_spec))

    draw = ImageDraw.Draw(output)
    font = ImageFont.load_default(size=27)
    small_font = ImageFont.load_default(size=24)
    draw.text((88, 428), "AI can get things done fast,", font=font, fill=(181, 187, 190, 255))
    draw.text((88, 466), "but what's worth doing is still yours to decide.", font=font, fill=(181, 187, 190, 255))
    draw.text((88, 526), ">", font=small_font, fill=(88, 199, 181, 255))
    draw.text((121, 526), "/think-it-through", font=small_font, fill=(232, 236, 239, 255))
    return _png_bytes(output)


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
        return image.size, image.mode, hashlib.sha256(image.tobytes()).hexdigest()


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


def check_readme_invocation_card(root: Path = ROOT) -> list[str]:
    manifest = load_manifest(root)
    spec = invocation_card_spec(manifest)
    variants = spec.get("variants")
    light = next(
        (variant for variant in variants if isinstance(variant, dict) and variant.get("theme") == "light"),
        None,
    ) if isinstance(variants, list) else None
    if not isinstance(light, dict) or not isinstance(light.get("output"), str):
        raise ValueError("README Invocation Card 缺少 light output")
    return _check_outputs(
        root,
        "README Invocation Card light",
        {light["output"]: render_readme_invocation_card(root)},
        spec.get("max_output_bytes") if isinstance(spec.get("max_output_bytes"), int) else None,
    )


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


def check_generated_assets(root: Path = ROOT) -> list[str]:
    try:
        return check_readme_invocation_card(root) + check_social_preview(root)
    except Exception as error:
        return [f"派生资产无法重渲染检查：{error}"]


def write_readme_invocation_card(root: Path = ROOT) -> Path:
    manifest = load_manifest(root)
    spec = invocation_card_spec(manifest)
    variants = spec.get("variants")
    light = next(
        (variant for variant in variants if isinstance(variant, dict) and variant.get("theme") == "light"),
        None,
    ) if isinstance(variants, list) else None
    if not isinstance(light, dict) or not isinstance(light.get("output"), str):
        raise ValueError("README Invocation Card 缺少 light output")
    output = root / light["output"]
    output.write_bytes(render_readme_invocation_card(root))
    return output


def write_social_preview(root: Path = ROOT) -> Path:
    manifest = load_manifest(root)
    spec = social_preview_spec(manifest)
    _, output = _single_source_and_output(root, spec)
    output.write_bytes(render_social_preview(root))
    return output


def write_generated_assets(root: Path = ROOT) -> list[Path]:
    return [write_readme_invocation_card(root), write_social_preview(root)]


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
        print("README Invocation Card 与 Social Preview 完整解码、尺寸、预算和像素均为最新")
        return 0
    outputs = write_generated_assets()
    print(f"已生成 {_relative_paths(outputs, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
