# hololive Dreams Auto-Patcher & Updater

[![Update & Release](https://github.com/AlexAn75541/holoholo/actions/workflows/patch-and-release.yml/badge.svg)](https://github.com/AlexAn75541/holoholo/actions/workflows/patch-and-release.yml)

Experimental GitHub Actions pipeline for **hololive Dreams** (`game.qualiarts.hololive.dreams.com`). It reads an APKPure XAPK, patches and merges its contents into one signed arm64 APK. The existing `0.1-beta` APK is **known broken**: its `resources.arsc` is compressed, which Android rejects for its target SDK. Later builds store that file uncompressed, but a replacement cannot publish until it passes the Android 16 arm64 device gate. Gameplay remains **unverified**. Read [CONSTRAINTS.md](CONSTRAINTS.md) before changing the release pipeline.

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
2. **Standalone arm64 APK**: Merges `config.arm64_v8a.apk` and `UnityDataAssetPack.apk` into the base APK. It is not universal; it targets arm64 devices.
3. **Artifact and device gates**: CI checks the signed APK, then requires clean installation and same-version reinstallation on an Android 16 arm64 device before releasing. No release is published if the device runner is missing or a check fails. These tests do not prove that the game launches or plays.
4. **Consistent signing**: Beta builds share one repository signing key. **The current signing key and password are public; its signature does not authenticate the publisher.** The upstream package version and version code remain unchanged inside the APK. Android/Obtainium may not offer an in-place update between patch-only revisions with the same version code.
5. **Builds**: Commits to `main` and manual runs produce a patch build. A daily check at 04:00 UTC builds only when APKPure's game version code changes. Older patch releases are pruned only after a successful replacement.

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
   - **Filter regular expression**: `.*\.apk$`. This release now has one APK asset; refresh its entry if Obtainium still shows a cached 2-asset listing.
   - **Version detection**: GitHub Releases tags track patch builds, but Android installation still uses the game's internal version code. Same-game-version beta builds may need manual reinstall; this has not been tested on a device.
5. Tap **Add**, then tap **Install**. If the UI says **2 APKs**, refresh its cached release and check the asset filter; only one `.apk` should be selected. If installation still fails, capture the installer’s detailed error or Android PackageManager log. The generic `failure [holoholo]` message does not identify its cause.

---

## First-Time Installation Note

- If you currently have the official, unpatched game installed, **uninstall it first**.
- Android requires all updates to match the signature of the currently installed app. Because the official game is signed by Qualiarts and this patched release is signed by this repository's key, an existing installation signed with a different key cannot be updated in-place on the first install.
- Later builds use the same signing key, but in-place installation and data preservation are not yet verified. Back up game data before trying a replacement.

---

## Patch Versions

Release tags use `0.1-beta`, then `0.1.1-beta`, `0.1.2-beta`, etc. These identify **patch builds**, not game versions. GitHub marks them as normal releases so Obtainium can discover them without enabling prereleases; the `-beta` tag still means device installation and gameplay are unverified. The original game version stays inside the APK. Tags remain beta until a user verifies installation and gameplay and explicitly requests `1.0`. Only the newest patch release is retained after publication. Older beta tags remain as revision-counter markers; the legacy `v1.2.1-patched` release and tag are removed after the first beta succeeds.

## Device Test Setup

The workflow requires a **self-hosted Linux ARM64 GitHub Actions runner** labeled `android16`, with `adb` installed and exactly one dedicated Android API 36+ arm64 device connected. The device must start without the game installed. Configure it under the repository's **Settings > Actions > Runners**. Keep the device isolated from personal accounts and banking apps. Until it is online, the `android-install` job cannot pass, so new releases will not publish. CI tests Android clean install and same-version reinstall only, not Obtainium UI behavior or game play.

## Manual Workflow Trigger

To build a release on demand:

1. Navigate to the [Actions tab](https://github.com/AlexAn75541/holoholo/actions/workflows/patch-and-release.yml).
2. Select **Patch and Release Hololive Dreams**.
3. Click **Run workflow**.

---

## Disclaimer

This project is an unofficial community tool created for personal backup, regional accessibility, and automation purposes. All game assets, names, and trademarks belong to COVER Corp. and QualiArts, Inc.
