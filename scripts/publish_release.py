#!/usr/bin/env python3
"""
Publishes the single arm64 APK to GitHub Releases with standard metadata.
"""

import sys
import argparse
import subprocess
from pathlib import Path


def publish_release(apk_path: str, tag: str, title: str, game_ver: str, game_code: str):
    apk = Path(apk_path)
    if not apk.is_file():
        raise FileNotFoundError(f"APK asset not found: {apk_path}")

    notes = (
        f"Patch build {tag}. Game version: {game_ver}. Game version code: `{game_code}`. "
        "Contains standalone arm64 APK with uncompressed resources.arsc (4-byte aligned), "
        "16KiB page alignment, and v2/v3 signatures. Upstream package version remains intact."
    )

    print(f"Publishing release {tag} with {apk.name}...")
    subprocess.run(
        [
            "gh", "release", "create", tag, str(apk),
            "--title", title,
            "--notes", notes,
        ],
        check=True,
    )
    print(f"Successfully published release {tag}")


def main():
    parser = argparse.ArgumentParser(description="Publish patched APK release to GitHub")
    parser.add_argument("--apk", required=True, help="Path to signed APK")
    parser.add_argument("--tag", required=True, help="Git release tag")
    parser.add_argument("--title", required=True, help="Release title")
    parser.add_argument("--game-version", required=True, help="Upstream game version name")
    parser.add_argument("--game-code", required=True, help="Upstream game version code")
    args = parser.parse_args()

    publish_release(
        apk_path=args.apk,
        tag=args.tag,
        title=args.title,
        game_ver=args.game_version,
        game_code=args.game_code,
    )


if __name__ == "__main__":
    main()
