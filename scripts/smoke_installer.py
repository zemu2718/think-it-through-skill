#!/usr/bin/env python3
"""对固定安装器执行隔离的 archive 发现与八 target 安装 smoke。"""

from __future__ import annotations

import argparse
import functools
import http.server
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from build_distribution import SKILL_DIR, inspect_archive, load_manifest, verify_archive_bytes

INSTALLER_PACKAGE = "skills@1.5.23"
SKILL_NAME = "think-it-through"
TARGET_DIRS = {
    "claude-code": ".claude/skills",
    "codex": ".agents/skills",
    "cursor": ".agents/skills",
    "openclaw": "skills",
    "hermes-agent": ".hermes/skills",
    "codebuddy": ".codebuddy/skills",
    "gemini-cli": ".agents/skills",
    "opencode": ".agents/skills",
}


class QuietRequestHandler(http.server.SimpleHTTPRequestHandler):
    """CI 中隐藏安装器的预探测 404，只保留 smoke 断言。"""

    def log_message(self, format: str, *args: object) -> None:
        return


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            f"命令失败（exit={completed.returncode}）：{' '.join(command)}\n{completed.stdout}"
        )
    return completed


def _assert_install(installed: Path) -> None:
    _, manifest_files = load_manifest()
    symlinks = [path.relative_to(installed).as_posix() for path in installed.rglob("*") if path.is_symlink()]
    if symlinks:
        raise ValueError(f"安装结果不得包含 symlink：{sorted(symlinks)}")
    actual = {
        path.relative_to(installed).as_posix()
        for path in installed.rglob("*")
        if path.is_file()
    }
    expected = set(manifest_files)
    if actual != expected:
        raise ValueError(
            f"安装文件集合与 manifest 不一致：缺少={sorted(expected - actual)}，"
            f"多出={sorted(actual - expected)}"
        )
    for relative in manifest_files:
        if (installed / relative).read_bytes() != (SKILL_DIR / relative).read_bytes():
            raise ValueError(f"安装文件内容与源码不一致：{relative}")


def _smoke_archive(archive: Path, *, npx: str) -> None:
    archive = archive.resolve()
    inspect_archive(archive)
    verify_archive_bytes(archive)

    with tempfile.TemporaryDirectory(prefix="think-it-through-installer-") as temporary:
        root = Path(temporary)
        serve = root / "serve"
        serve.mkdir()
        served_archive = serve / archive.name
        shutil.copyfile(archive, served_archive)

        handler = functools.partial(QuietRequestHandler, directory=str(serve))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        archive_url = f"http://127.0.0.1:{server.server_port}/{served_archive.name}"
        try:
            discovery = root / "discovery"
            discovery.mkdir()
            discovery_home = root / "discovery-home"
            discovery_home.mkdir()
            discovery_env = os.environ.copy()
            discovery_env.update(
                {
                    "HOME": str(discovery_home),
                    "XDG_CONFIG_HOME": str(discovery_home / ".config"),
                    "XDG_STATE_HOME": str(discovery_home / ".state"),
                    "DISABLE_TELEMETRY": "1",
                    "NO_COLOR": "1",
                }
            )
            listed = _run(
                [npx, "--yes", INSTALLER_PACKAGE, "add", archive_url, "--list"],
                cwd=discovery,
                env=discovery_env,
            )
            if SKILL_NAME not in listed.stdout:
                raise ValueError("固定安装器未从 archive 发现 think-it-through")
            print("L1 archive-discovery: passed")

            for target, relative_dir in TARGET_DIRS.items():
                project = root / f"project-{target}"
                home = root / f"home-{target}"
                project.mkdir()
                home.mkdir()
                env = os.environ.copy()
                env.update(
                    {
                        "HOME": str(home),
                        "XDG_CONFIG_HOME": str(home / ".config"),
                        "XDG_STATE_HOME": str(home / ".state"),
                        "DISABLE_TELEMETRY": "1",
                        "NO_COLOR": "1",
                    }
                )
                _run(
                    [
                        npx,
                        "--yes",
                        INSTALLER_PACKAGE,
                        "add",
                        archive_url,
                        "--skill",
                        SKILL_NAME,
                        "--agent",
                        target,
                        "--copy",
                        "--yes",
                    ],
                    cwd=project,
                    env=env,
                )
                installed = project / relative_dir / SKILL_NAME
                if not installed.is_dir():
                    raise FileNotFoundError(f"{target} 未生成预期安装目录：{installed}")
                _assert_install(installed)
                print(f"L2 archive-install [{target}]: passed")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--npx", default="npx")
    args = parser.parse_args()
    _smoke_archive(args.archive, npx=args.npx)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
