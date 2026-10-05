# holoholo: session handoff for Claude

## User goal

Install hololive Dreams (`game.qualiarts.hololive.dreams.com`) on a Nothing OS 4.1 / Android 16 phone without leaving Developer Options enabled. Source: APKPure XAPK. Obtainium/ObtainX should recognize one GitHub release APK and support seamless updates. Preserve the original game package name and Android version code; patch-release labels start at `0.2-beta` (then `0.2.1-beta`, etc.) as requested. Do not promote to `1.0` until the user confirms installation and gameplay. No manual signing labor requested.

## Root cause of earlier installation failures

1. **Compressed `resources.arsc`**: Direct inspection of the `0.1-beta` APK revealed that `resources.arsc` was stored using ZIP method 8 (DEFLATED). Android's official PackageInstaller specification for `targetSdkVersion >= 30` (this game targets 36) strictly forbids compressed `resources.arsc` or unaligned resources, rejecting installation with error code -124 (`STATUS_FAILURE_INCOMPATIBLE` / failure).
2. **Missing uncompressed packaging in patcher**: `scripts/patcher.py` was compressing all non-`.so` files with `zipfile.ZIP_DEFLATED`. Fixed to explicitly store `resources.arsc` uncompressed (`ZIP_STORED`) and align it on 4-byte boundaries.
3. **Workflow blockage that delayed releasing the fix**: When the `resources.arsc` fix was originally created in commit `bfe243e`, a `[self-hosted, linux, ARM64, android16]` runner job was placed between `build` and `publish`. Because no self-hosted runner was registered, the job was queued indefinitely and cancelled. As a result, GitHub Releases was never updated, and the user's phone continued attempting to install the old broken `0.1-beta` APK from earlier.
4. **Resolution**: The workflow was consolidated to run end-to-end on GitHub-hosted `ubuntu-latest`. Run `37315724893` built the APK, verified it with `scripts/verify_apk.py`, published the `0.2-beta` release, and pruned the superseded `0.1-beta` release.

## Applied APK packaging & fixes

- **PairIP License Check Bypass**: Patched `com.pairip.licensecheck.LicenseClient` in `classes.dex` (`performLocalInstallerCheck`, `isLocalCheckPassed`, `checkLicense`, and `attachBaseContext`). Sideloaded installs will no longer trigger the Google Play error screen.
- **Uncompressed `resources.arsc`**: `resources.arsc` is stored `ZIP_STORED` and 4-byte aligned (verified in released binary: `compress_type=0`).
- **16 KiB Page Alignment**: All 22 native `.so` files are aligned to 16 KiB boundaries using `zipalign -P 16 -f 4` (mandatory for Android 15/16).
- **Split Requirements Neutralized**: `requiredSplitTypes="base__abi"` and Play split metadata tags (`com.android.vending.splits.required`, etc.) are stripped from `AndroidManifest.xml` during standalone APK creation.
- **Automated Signing**: APK is aligned and signed using `apksigner` with `--v2-signing-enabled true --v3-signing-enabled true` using `keystore/release.p12`.
- **Single APK Release**: Only one `.apk` (`hololive-dreams-1.2.1-0.2-beta.apk`) is published per release (no `.xapk`) to prevent Obtainium from downloading multiple conflicting assets.

## Signing security note

`keystore/release.p12` and its password `holoholo` are committed in the repository so GitHub Actions can sign automatically with zero manual labor. **This key is public and does not establish trusted third-party publisher identity**, but using this consistent key enables seamless in-place updates across patch versions without uninstalling or wiping user data.

## Current live release state

- **Latest Release**: [`0.2-beta`](https://github.com/AlexAn75541/holoholo/releases/tag/0.2-beta) (Normal release, `isPrerelease: false`).
- **Asset**: `hololive-dreams-1.2.1-0.2-beta.apk` (636,127,649 bytes).
- **Obtainium instructions**: Refresh the app in Obtainium; it will detect `0.2-beta` with 1 APK asset. Tap Install.

Key files: `scripts/patcher.py`, `scripts/verify_apk.py`, `tests/test_verify_apk.py`, `.github/workflows/patch-and-release.yml`, `CONSTRAINTS.md`, `README.md`, `CLAUDE_HANDOFF.md`.
