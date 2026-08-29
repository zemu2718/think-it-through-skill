#!/usr/bin/env python3
"""根据唯一 manifest 构建并复验最小 `.skill` 分发包。"""

from __future__ import annotations

import argparse
import json
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "think-it-through"
MANIFEST_PATH = ROOT / "distribution" / "package-manifest.json"

EXCLUDED_ROOT_DIRS = {"evals"}
EXCLUDED_PARTS = {"__pycache__", ".claude", "think-it-through-workspace"}
EXCLUDED_SUFFIXES = {".pyc", ".html"}


def _validate_relative_path(relative: str) -> None:
    path = PurePosixPath(relative)
    if not relative or path.is_absolute() or relative != path.as_posix():
        raise ValueError(f"manifest 包含非法相对路径：{relative!r}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"manifest 包含非法路径段：{relative!r}")
    if path.parts[0] in EXCLUDED_ROOT_DIRS:
        raise ValueError(f"manifest 包含禁止目录：{relative}")
    if any(part in EXCLUDED_PARTS for part in path.parts):
        raise ValueError(f"manifest 包含本地或缓存目录：{relative}")
    if path.suffix in EXCLUDED_SUFFIXES or path.name == ".DS_Store":
        raise ValueError(f"manifest 包含禁止文件：{relative}")


def load_manifest(path: Path = MANIFEST_PATH) -> tuple[str, tuple[str, ...]]:
    data = json.loads(path.read_text())
    if set(data) != {"schema_version", "skill_root", "files"}:
        raise ValueError("package manifest 根字段不符合合同")
    if data["schema_version"] != "1" or data["skill_root"] != SKILL_DIR.name:
        raise ValueError("package manifest 版本或 Skill 根目录不符合合同")
    files = data["files"]
    if not isinstance(files, list) or not files or not all(isinstance(item, str) for item in files):
        raise ValueError("package manifest files 必须是非空字符串数组")
    if files != sorted(files):
        raise ValueError("package manifest files 必须按字典序排列")
    if len(files) != len(set(files)):
        raise ValueError("package manifest files 不得重复")
    for relative in files:
        _validate_relative_path(relative)
    return data["skill_root"], tuple(files)


def _eligible_source_relatives() -> set[str]:
    relatives: set[str] = set()
    for path in SKILL_DIR.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(SKILL_DIR)
        if relative.parts[0] in EXCLUDED_ROOT_DIRS:
            continue
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES or path.name == ".DS_Store":
            continue
        relatives.add(relative.as_posix())
    return relatives


def source_files() -> list[Path]:
    _, manifest_files = load_manifest()
    manifest_set = set(manifest_files)
    eligible = _eligible_source_relatives()
    missing = sorted(manifest_set - eligible)
    unexpected = sorted(eligible - manifest_set)
    if missing:
        raise ValueError(f"manifest 文件在源码中缺失：{missing}")
    if unexpected:
        raise ValueError(f"源码存在未列入 manifest 的运行时文件：{unexpected}")
    paths = [SKILL_DIR / relative for relative in manifest_files]
    symlinks = [relative for relative, path in zip(manifest_files, paths) if path.is_symlink()]
    if symlinks:
        raise ValueError(f"运行时源码不得使用符号链接：{symlinks}")
    return paths


def _archive_member_relative(info: zipfile.ZipInfo, skill_root: str) -> str | None:
    name = info.filename
    if "\\" in name:
        raise ValueError(f"分发包 member 使用反斜杠：{name}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"分发包包含不安全路径：{name}")
    if not path.parts or path.parts[0] != skill_root:
        raise ValueError(f"分发包文件必须统一位于 {skill_root}/ 根目录")
    mode = info.external_attr >> 16
    if stat.S_ISLNK(mode):
        raise ValueError(f"分发包不得包含符号链接：{name}")
    if info.is_dir():
        return None
    if len(path.parts) < 2:
        raise ValueError(f"分发包根目录下缺少文件相对路径：{name}")
    relative = PurePosixPath(*path.parts[1:]).as_posix()
    _validate_relative_path(relative)
    return relative


def inspect_archive(archive: Path) -> list[str]:
    skill_root, manifest_files = load_manifest()
    expected = set(manifest_files)
    with zipfile.ZipFile(archive) as package:
        relatives: list[str] = []
        names: list[str] = []
        for info in package.infolist():
            relative = _archive_member_relative(info, skill_root)
            if relative is None:
                continue
            relatives.append(relative)
            names.append(info.filename)
        if len(relatives) != len(set(relatives)):
            duplicates = sorted({item for item in relatives if relatives.count(item) > 1})
            raise ValueError(f"分发包包含重复 member：{duplicates}")
        actual = set(relatives)
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        if missing or unexpected:
            raise ValueError(f"分发包文件集合与 manifest 不一致：缺少={missing}，多出={unexpected}")
        return sorted(names)


def verify_archive_bytes(archive: Path) -> None:
    skill_root, manifest_files = load_manifest()
    with zipfile.ZipFile(archive) as package:
        for relative in manifest_files:
            archived = package.read(f"{skill_root}/{relative}")
            source = (SKILL_DIR / relative).read_bytes()
            if archived != source:
                raise ValueError(f"归档文件内容与源码不一致：{relative}")


def build_archive(archive: Path) -> None:
    files = source_files()
    skill_root, _ = load_manifest()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        for path in files:
            arcname = f"{skill_root}/{path.relative_to(SKILL_DIR).as_posix()}"
            info = zipfile.ZipInfo.from_file(path, arcname)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            package.writestr(info, path.read_bytes())
    inspect_archive(archive)
    verify_archive_bytes(archive)


def verify_extracted(extracted_root: Path) -> None:
    skill_root, manifest_files = load_manifest()
    extracted = extracted_root / skill_root
    actual = {
        path.relative_to(extracted).as_posix()
        for path in extracted.rglob("*")
        if path.is_file()
    }
    expected = set(manifest_files)
    if actual != expected:
        raise ValueError(f"解包后的文件集合与 manifest 不一致：{sorted(actual ^ expected)}")
    for relative in manifest_files:
        if (extracted / relative).read_bytes() != (SKILL_DIR / relative).read_bytes():
            raise ValueError(f"解包后的文件内容不一致：{relative}")


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

    build_archive(archive)
    unpacked.mkdir()
    with zipfile.ZipFile(archive) as package:
        for info in package.infolist():
            _archive_member_relative(info, SKILL_DIR.name)
        package.extractall(unpacked)
    verify_extracted(unpacked)

    _, manifest_files = load_manifest()
    print(f"已生成 {archive}")
    print(f"已检查 {len(manifest_files)} 个 manifest 文件")
    print(f"已解包复验 {unpacked / SKILL_DIR.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
