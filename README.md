# hololive Dreams Auto-Patcher & Updater

[![Update & Release](https://github.com/AlexAn75541/holoholo/actions/workflows/patch-and-release.yml/badge.svg)](https://github.com/AlexAn75541/holoholo/actions/workflows/patch-and-release.yml)

Automated GitHub Actions pipeline for **hololive Dreams** (`game.qualiarts.hololive.dreams.com`). It fetches an APKPure XAPK, patches the Google Play licensing/installer lock (PairIP), properly packages and signs a standalone arm64 APK, and publishes releases for auto-updating via **Obtainium**.

---

## The Problem

When sideloading `game.qualiarts.hololive.dreams.com` outside of Google Play (or in unsupported regions), the game launches into a blocking Google Play error screen (`com.pairip.licensecheck.LicenseActivity`).

Normally, bypassing this check requires manual ADB installation commands:
```bash
adb shell pm install-create -i "com.android.vending" -r
adb shell pm install-write <session> ...
adb shell pm install-commit <session>
```

However, many users cannot enable **Developer Options** or **USB Debugging** because banking apps, work profiles, and integrity checks refuse to run when Developer Mode is active.

Furthermore, on **Android 11 through Android 16 (API 30–36+)**, Android's `PackageInstaller` strictly enforces:
1. `resources.arsc` must be **stored uncompressed** and 4-byte aligned.
2. Native `.so` libraries must be **16 KiB page aligned** (mandatory for Android 15/16).
3. Split-requirement tags (`requiredSplitTypes="base__abi"`, `com.android.vending.splits.required`) must be stripped if merged into a standalone APK, or PackageInstaller throws `STATUS_FAILURE_INCOMPATIBLE`.

---

## The Solution

This repository automates the complete patching, packaging, and signing pipeline via GitHub Actions:

1. **DEX Bytecode Patch**: Directly patches `com.pairip.licensecheck.LicenseClient` inside `classes.dex`:
   - `performLocalInstallerCheck` -> returns `true` (skips installer verification).
   - `isLocalCheckPassed` -> returns `true`.
   - `checkLicense` -> returns early (`return-void`).
   - `attachBaseContext` -> nops out the `checkLicense` call.
2. **Standalone arm64 APK Packaging**:
   - Merges `config.arm64_v8a.apk` native libraries and `UnityDataAssetPack.apk` assets into the base APK.
   - Strips split metadata from `AndroidManifest.xml`.
   - Stores `resources.arsc` **uncompressed** to comply with Android 11+ requirements.
   - Aligns all 22 native `.so` files to **16 KiB boundaries** (`zipalign -P 16 -f 4`) for Android 15/16 devices.
3. **Automated Verification**: CI runs `scripts/verify_apk.py` verifying ZIP integrity, uncompressed resources, manifest cleaning, 16 KiB library alignment, and v2/v3 signatures before publishing.
4. **Single APK Release**: Releases contain only the standalone `.apk` (no confusing multi-asset downloads in Obtainium).
5. **Continuous Releases**: Starts at `0.2-beta` (advancing to `0.2.1-beta`, etc.). Supreseded beta releases are pruned automatically.

---

## Quick Start (Obtainium Setup)

To receive automatic game updates on your Android phone:

1. Install [Obtainium](https://github.com/ImranR98/Obtainium) on your device.
2. Open Obtainium, tap **Add App**.
3. Paste this repository URL:
   ```text
   https://github.com/AlexAn75541/holoholo
   ```
4. Configure options:
   - **Filter regular expression**: `.*\.apk$` (ensures only the standalone APK is downloaded).
   - **Version detection**: Default (GitHub Releases).
5. Tap **Add**, then tap **Install**.

---

## First-Time Installation Note

- If you currently have the official, unpatched game installed, **uninstall it first**.
- Android requires all updates to match the signature of the currently installed app. Because the official game is signed by Qualiarts and this patched release is signed by this repository's key, an existing installation signed with a different key cannot be updated in-place on the first install.
- All subsequent updates from this repo use the exact same key.

---

## Patch Versions

Release tags use `0.2-beta`, then `0.2.1-beta`, `0.2.2-beta`, etc. These identify **patch builds**, not game versions. The original game version stays inside the APK. Tags remain beta until a user verifies installation and gameplay and explicitly requests `1.0`. Only the newest patch release is retained after publication.

## Manual Workflow Trigger

To build a release on demand:

1. Navigate to the [Actions tab](https://github.com/AlexAn75541/holoholo/actions/workflows/patch-and-release.yml).
2. Select **Patch and Release Hololive Dreams**.
3. Click **Run workflow**.

---

## Disclaimer

This project is an unofficial community tool created for personal backup, regional accessibility, and automation purposes. All game assets, names, and trademarks belong to COVER Corp. and QualiArts, Inc.
