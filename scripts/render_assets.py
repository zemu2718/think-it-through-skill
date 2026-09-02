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
from PIL import Image

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


def _canvas_size(spec: dict[str, object]) -> tuple[int, int]:
    canvas = spec.get("canvas")
    if not isinstance(canvas, dict):
        raise ValueError("资产缺少 canvas")
    width = canvas.get("width")
    height = canvas.get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        raise ValueError("资产 canvas 必须包含整数 width/height")
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


def check_generated_assets(root: Path = ROOT) -> list[str]:
    try:
        return check_social_preview(root)
    except Exception as error:
        return [f"派生资产无法重渲染检查：{error}"]


def write_social_preview(root: Path = ROOT) -> Path:
    manifest = load_manifest(root)
    spec = social_preview_spec(manifest)
    _, output = _single_source_and_output(root, spec)
    output.write_bytes(render_social_preview(root))
    return output


def write_generated_assets(root: Path = ROOT) -> list[Path]:
    return [write_social_preview(root)]


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
        print("Social Preview 完整解码、尺寸、预算和像素均为最新")
        return 0
    outputs = write_generated_assets()
    print(f"已生成 {_relative_paths(outputs, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
