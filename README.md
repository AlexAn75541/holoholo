# hololive Dreams Auto-Patcher & Updater

[![Update & Release](https://github.com/AlexAn75541/holoholo/actions/workflows/patch-and-release.yml/badge.svg)](https://github.com/AlexAn75541/holoholo/actions/workflows/patch-and-release.yml)

Automated GitHub Actions pipeline that fetches the latest release of **hololive Dreams** (`game.qualiarts.hololive.dreams.com`) from APKPure, removes the Google Play licensing/installer lock (PairIP), signs the binaries with a permanent key, and publishes ready-to-install releases for auto-updating via **Obtainium**.

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

---

## The Solution

This repository automates the entire patching and packaging pipeline via GitHub Actions:

1. **DEX Bytecode Patch**: Directly patches `com.pairip.licensecheck.LicenseClient` inside `classes.dex`:
   - `performLocalInstallerCheck` -> returns `true` (skips installer verification).
   - `isLocalCheckPassed` -> returns `true`.
   - `checkLicense` -> returns early (`return-void`).
   - `attachBaseContext` -> nops out the `checkLicense` call.
2. **Standalone Merged APK**: Merges split APK components (`config.arm64_v8a.apk` and `UnityDataAssetPack.apk`) into a single universal APK. No split-installer needed.
3. **Repacked XAPK**: Also builds a signed, repacked `.xapk` containing all split APKs and original manifest for users preferring XAPK installers.
4. **Permanent Keystore Signing**: All releases are signed with a persistent repository keystore. Android allows seamless in-place updates without uninstalling or wiping user data.
5. **Scheduled Checks**: Checks APKPure daily at 04:00 UTC. When a new game version drops, it builds and releases the update automatically.

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
   - **Filter regular expression**: `.*\.apk$` (downloads the standalone APK; recommended) or `.*\.xapk$` (if using an XAPK installer).
   - **Version detection**: Default (GitHub Releases).
5. Tap **Add**, then tap **Install**.

---

## First-Time Installation Note

- If you currently have the official, unpatched game installed, **uninstall it first**.
- Android requires all updates to match the signature of the currently installed app. Because the official game is signed by Qualiarts and this patched release is signed by this repository's key, an existing installation signed with a different key cannot be updated in-place on the first install.
- **All future updates from this repository share the same key and update seamlessly without losing data.**

---

## Manual Workflow Trigger

To build a release on demand:

1. Navigate to the [Actions tab](https://github.com/AlexAn75541/holoholo/actions/workflows/patch-and-release.yml).
2. Select **Patch and Release Hololive Dreams**.
3. Click **Run workflow**.

---

## Disclaimer

This project is an unofficial community tool created for personal backup, regional accessibility, and automation purposes. All game assets, names, and trademarks belong to COVER Corp. and QualiArts, Inc.
