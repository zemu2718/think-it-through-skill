#!/usr/bin/env python3
"""构建、检查并解包复验最小 `.skill` 分发包。"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "think-it-through"

EXCLUDED_ROOT_DIRS = {"evals"}
EXCLUDED_PARTS = {"__pycache__", ".claude", "think-it-through-workspace"}
EXCLUDED_SUFFIXES = {".pyc", ".html"}
REQUIRED = {
    "SKILL.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "core/protocol.md",
    "core/intents.schema.json",
    "core/consent.schema.json",
    "core/receipts.schema.json",
    "core/decision-record.schema.json",
    "policies/evidence-routing.md",
    "policies/participation-routing.md",
    "adapters/text.md",
    "adapters/claude-code.md",
    "adapters/chatgpt.md",
}


def source_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(SKILL_DIR.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(SKILL_DIR)
        if relative.parts[0] in EXCLUDED_ROOT_DIRS:
            continue
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES or path.name == ".DS_Store":
            continue
        files.append(path)
    return files


def inspect_archive(archive: Path) -> list[str]:
    with zipfile.ZipFile(archive) as package:
        names = sorted(name for name in package.namelist() if not name.endswith("/"))
        expected_prefix = f"{SKILL_DIR.name}/"
        if any(not name.startswith(expected_prefix) for name in names):
            raise ValueError("分发包文件必须统一位于 think-it-through/ 根目录")
        relatives = {name.removeprefix(expected_prefix) for name in names}
        missing = REQUIRED - relatives
        if missing:
            raise ValueError(f"分发包缺少必要文件：{sorted(missing)}")
        forbidden = sorted(
            relative
            for relative in relatives
            if relative.startswith("evals/")
            or any(part in EXCLUDED_PARTS for part in Path(relative).parts)
            or Path(relative).suffix in EXCLUDED_SUFFIXES
        )
        if forbidden:
            raise ValueError(f"分发包包含禁止内容：{forbidden}")
        return names


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / "think-it-through.skill"
    unpacked = output_dir / "unpacked"
    existing = [path for path in (archive, unpacked) if path.exists()]
    if existing:
        raise FileExistsError(
            "为避免覆盖已有产物，请先移走或删除："
            + "、".join(str(path) for path in existing)
        )

    files = source_files()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        for path in files:
            package.write(path, Path(SKILL_DIR.name) / path.relative_to(SKILL_DIR))

    names = inspect_archive(archive)
    with zipfile.ZipFile(archive) as package:
        package.extractall(unpacked)

    extracted = unpacked / SKILL_DIR.name
    extracted_files = {
        path.relative_to(extracted).as_posix()
        for path in extracted.rglob("*")
        if path.is_file()
    }
    source_relatives = {path.relative_to(SKILL_DIR).as_posix() for path in files}
    if extracted_files != source_relatives:
        raise ValueError("解包后的文件集合与打包源不一致")
    for relative in source_relatives:
        if (extracted / relative).read_bytes() != (SKILL_DIR / relative).read_bytes():
            raise ValueError(f"解包后的文件内容不一致：{relative}")

    print(f"已生成 {archive}")
    print(f"已检查 {len(names)} 个包内文件")
    print(f"已解包复验 {extracted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
