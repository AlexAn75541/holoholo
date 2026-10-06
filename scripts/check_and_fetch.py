#!/usr/bin/env python3
"""
Fetch source XAPK, inspect APK version with aapt/manifest, and check against published releases.
Outputs GITHUB_OUTPUT variables:
  should_build: 'true' | 'false'
  game_version: e.g. '1.2.1'
  game_code: e.g. '1790677758'
  patch_version: e.g. '1.2.1-patched-5'
  xapk_path: path to downloaded source XAPK
"""

import os
import sys
from pathlib import Path

# Ensure repo root is in sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import re
import json
import argparse
import subprocess
from typing import Optional, List, Tuple
from scripts.patcher import (
    DEFAULT_PACKAGE,
    download_file,
    get_apkpure_download_info,
    inspect_apk_version,
)


def parse_version_tuple(v: str) -> Tuple[int, ...]:
    """Parse version string into integer tuple for comparison (e.g. '1.2.1' -> (1, 2, 1))."""
    return tuple(int(x) if x.isdigit() else 0 for x in re.findall(r"\d+", v))


def get_published_releases() -> List[str]:
    """Retrieve list of release tag names via gh CLI."""
    try:
        raw = subprocess.check_output(
            ["gh", "release", "list", "--json", "tagName", "--limit", "100"],
            text=True,
        )
        return [r["tagName"] for r in json.loads(raw)]
    except Exception as e:
        print(f"Warning: Failed to fetch releases via gh: {e}", file=sys.stderr)
        return []


def get_git_tags() -> List[str]:
    """Retrieve list of local/remote git tags."""
    try:
        return subprocess.check_output(["git", "tag", "--list"], text=True).splitlines()
    except Exception as e:
        print(f"Warning: Failed to fetch git tags: {e}", file=sys.stderr)
        return []


def get_latest_patched_game_version(tags: List[str]) -> Optional[str]:
    """
    Finds the highest/latest game version among existing {game_ver}-patched-{rev} tags.
    Returns e.g. '1.2.1' or None if no patched tags exist.
    """
    versions = []
    for t in tags:
        m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)*)-patched-[1-9][0-9]*", t)
        if m:
            versions.append(m.group(1))
    if not versions:
        return None
    versions.sort(key=parse_version_tuple)
    return versions[-1]


def compute_next_patch_version(game_ver: str, all_tags: List[str]) -> str:
    """Calculates next {game_ver}-patched-{rev} tag."""
    pattern = rf"^{re.escape(game_ver)}-patched-(\d+)$"
    revs = [int(m.group(1)) for t in set(all_tags) if (m := re.fullmatch(pattern, t))]
    next_rev = max([0] + revs) + 1
    return f"{game_ver}-patched-{next_rev}"


def check_and_fetch(
    output_xapk: str = "source.xapk",
    custom_url: Optional[str] = None,
    force_build: bool = False,
) -> dict:
    release_tags = get_published_releases()
    git_tags = get_git_tags()
    all_tags = list(set(release_tags + git_tags))

    latest_patched_ver = get_latest_patched_game_version(all_tags)
    print(f"Latest published patched game version: {latest_patched_ver or 'None'}")

    # Determine download URL
    url = (custom_url or "").strip()
    if not url:
        print("Querying APKPure mobile API for latest XAPK...")
        url, api_ver_name, api_ver_code = get_apkpure_download_info(DEFAULT_PACKAGE)
        print(f"APKPure upstream version: {api_ver_name} (code: {api_ver_code})")

        # Early check before downloading ~600MB if not forced and not custom URL
        if not force_build and latest_patched_ver:
            if parse_version_tuple(api_ver_name) <= parse_version_tuple(latest_patched_ver):
                # Also check version code from latest release body if available
                latest_tag = next((t for t in release_tags if t.startswith(f"{api_ver_name}-patched-")), None)
                if latest_tag:
                    try:
                        body = subprocess.check_output(
                            ["gh", "release", "view", latest_tag, "--json", "body", "--jq", ".body"],
                            text=True,
                        )
                        if f"Game version code: `{api_ver_code}`" in body:
                            print(f"Upstream game version {api_ver_name} ({api_ver_code}) is already patched in {latest_tag}. Skipping build to save compute.")
                            return {
                                "should_build": False,
                                "game_version": api_ver_name,
                                "game_code": api_ver_code,
                                "patch_version": "",
                                "xapk_path": "",
                            }
                    except Exception as e:
                        print(f"Notice: Could not read release notes: {e}")

    # Download source XAPK
    print(f"Downloading source XAPK into {output_xapk}...")
    download_file(url, output_xapk)

    # Decompile/inspect downloaded APK
    pkg_name, game_ver, game_code = inspect_apk_version(output_xapk)
    print(f"Inspected APK: package={pkg_name}, version={game_ver}, code={game_code}")

    # Version comparison against published version
    should_build = True
    if not force_build and latest_patched_ver:
        if parse_version_tuple(game_ver) < parse_version_tuple(latest_patched_ver):
            print(f"Downloaded game version {game_ver} is older than published {latest_patched_ver}. Skipping.")
            should_build = False
        elif parse_version_tuple(game_ver) == parse_version_tuple(latest_patched_ver):
            # Same version: check if latest release has matching version code
            latest_tag = next((t for t in release_tags if t.startswith(f"{game_ver}-patched-")), None)
            if latest_tag:
                try:
                    body = subprocess.check_output(
                        ["gh", "release", "view", latest_tag, "--json", "body", "--jq", ".body"],
                        text=True,
                    )
                    if f"Game version code: `{game_code}`" in body:
                        print(f"Game version {game_ver} (code {game_code}) is already patched in release {latest_tag}. Skipping build.")
                        should_build = False
                except Exception as e:
                    print(f"Notice: Could not inspect release body: {e}")

    patch_version = compute_next_patch_version(game_ver, all_tags) if should_build else ""
    if should_build:
        print(f"New or updated version detected ({game_ver} vs published {latest_patched_ver}). Inferred patch tag: {patch_version}")

    return {
        "should_build": should_build,
        "game_version": game_ver,
        "game_code": game_code,
        "patch_version": patch_version,
        "xapk_path": output_xapk if should_build else "",
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch and check game APK version")
    parser.add_argument("--output-xapk", default="source.xapk", help="Output path for downloaded XAPK")
    parser.add_argument("--custom-url", default=os.environ.get("XAPK_URL", ""), help="Optional direct XAPK URL")
    parser.add_argument("--force", action="store_true", help="Force build regardless of version match")
    args = parser.parse_args()

    # Manual dispatch or push on main with inputs might force build
    force = args.force or os.environ.get("FORCE_BUILD", "").lower() in ("true", "1", "yes")

    result = check_and_fetch(
        output_xapk=args.output_xapk,
        custom_url=args.custom_url,
        force_build=force,
    )

    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write(f"should_build={'true' if result['should_build'] else 'false'}\n")
            f.write(f"game_version={result['game_version']}\n")
            f.write(f"game_code={result['game_code']}\n")
            f.write(f"patch_version={result['patch_version']}\n")
            f.write(f"xapk_path={result['xapk_path']}\n")

    print("\nSummary:")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
