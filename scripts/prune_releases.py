#!/usr/bin/env python3
"""
Prunes superseded patch releases on GitHub.
Keeps only the current release tag ({game ver}-patched-{rev}).
"""

import sys
import re
import json
import argparse
import subprocess


def prune_releases(current_tag: str):
    print(f"Current release: {current_tag}. Pruning superseded releases...")
    try:
        raw = subprocess.check_output(
            ["gh", "release", "list", "--json", "tagName", "--limit", "100"],
            text=True,
        )
        releases = [r["tagName"] for r in json.loads(raw)]
    except Exception as e:
        print(f"Error listing releases: {e}", file=sys.stderr)
        return

    for tag in releases:
        if tag == current_tag:
            continue
        # Matches {game_ver}-patched-{rev}
        if re.fullmatch(r"[0-9]+(?:\.[0-9]+)*-patched-[0-9]+", tag):
            print(f"Deleting superseded release and tag: {tag}")
            try:
                subprocess.run(
                    ["gh", "release", "delete", tag, "--cleanup-tag", "--yes"],
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to delete {tag}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Prune superseded GitHub releases")
    parser.add_argument("--current-tag", required=True, help="Tag of current release to keep")
    args = parser.parse_args()
    prune_releases(args.current_tag)


if __name__ == "__main__":
    main()
