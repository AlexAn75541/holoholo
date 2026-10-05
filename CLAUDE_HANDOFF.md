# holoholo: session handoff for Claude

## User goal

Install hololive Dreams (`game.qualiarts.hololive.dreams.com`) on a Nothing OS 4.1 / Android 16 phone without leaving Developer Options enabled. Source: APKPure XAPK. Obtainium/ObtainX should recognize one GitHub release APK and support later updates. Preserve the original game package name and Android version code; patch-release labels use `0.1-beta`, `0.1.1-beta`, etc. Do not promote to `1.0` until the user confirms installation and gameplay. No manual signing labor requested.

## What actually happened

- The user installed APKPure's XAPK manually before using `adb shell pm install-create -i com.android.vending` and writing base, arm64 split and Unity asset pack. That avoided the Google Play installer warning but required Developer Options, which conflicts with a banking app.
- This repository's Python patcher modifies PairIP-related DEX methods, merges the APK splits, and signs with `keystore/release.p12`. GitHub Actions builds releases from APKPure's mobile API. Obtainium originally saw APK + XAPK together; the XAPK release asset was removed. The current `0.1-beta` release contains one APK.
- Two Nothing OS screenshots showed only generic Obtainium `failure [holoholo]` with no Android package error. That alone did not identify the defect.
- Direct inspection of the published `0.1-beta` APK found `targetSdkVersion=36` with `resources.arsc` ZIP method 8 (DEFLATED). Android's [official requirement](https://developer.android.com/about/versions/11/behavior-changes-11) says apps targeting API 30+ cannot install if `resources.arsc` is compressed or not 4-byte aligned. The patcher introduced that defect while repacking. Source fix stores the resource table uncompressed and aligns it with `zipalign -P 16 -f 4`. A verifier regression test now rejects compressed `resources.arsc`.
- CI run `37305944947` built the fixed APK but verifier incorrectly rejected `META-INF/RELEASE.RSA` as stale; `apksigner` had validly generated it. Removed that false check. CI run `37306396159` then built again but verifier falsely flagged empty `requiredSplitTypes`. Actual parsed binary manifest has `requiredSplitTypes=''`, no active split metadata; checker now distinguishes empty from nonempty. CI signing output showed v3 true, v2 false; verifier now accepts either valid v2 or v3 for API 36. Explicit v2/v3 signing options were added; **a fresh CI build is still needed**.
- The previous verifier claimed Android 16 installability without device testing. `CONSTRAINTS.md` and workflow now require static checks plus an actual clean install and same-version reinstall on an Android 16 (API 36+) arm64 device before publishing. `gh api repos/AlexAn75541/holoholo/actions/runners` reported zero registered runners; this gate cannot complete until one is registered. Do not describe any build as device-tested or gameplay-tested until proven.

## Signing security

`keystore/release.p12` and its password `holoholo` are committed in a public repository. CI can sign automatically; **this key is not private and the signature does not establish trusted publisher identity**. Rotating it breaks in-place updates from already installed patched APKs, so rotation requires an explicit migration decision. Never call this setup secure against third-party impersonation. Reusing the existing key maintains compatibility among patch releases.

## Current state / next actions

1. Run `PYTHONPATH=. python3 tests/test_verify_apk.py` (WSL `/mnt/c` intermittently returns `OSError [Errno 22]`; copy `scripts/` + `tests/` into `/tmp` to run if needed).
2. Inspect current `git diff`, commit/push the verifier and explicit signing changes, then observe the new CI build. A passing static build is **not** a release while the device job awaits a runner.
3. User may register a dedicated self-hosted Linux ARM64 runner labeled `android16` with `adb` and one clean arm64 API 36+ test device under Settings > Actions > Runners. Avoid personal/banking devices. CI must pass installation before publishing `0.1.1-beta` and pruning the known-broken `0.1-beta` release.
4. Even after install succeeds, verify game launch and login/gameplay separately. Preserve internal game version code per user's request; patch-only releases may not trigger automatic Android update detection in Obtainium.

Key files: `scripts/patcher.py`, `scripts/verify_apk.py`, `tests/test_verify_apk.py`, `.github/workflows/patch-and-release.yml`, `CONSTRAINTS.md`, `README.md`.
