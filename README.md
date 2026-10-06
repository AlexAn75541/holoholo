# hololive Dreams Auto-Patcher & Updater

[![Update & Release](https://github.com/AlexAn75541/holoholo/actions/workflows/patch-and-release.yml/badge.svg)](https://github.com/AlexAn75541/holoholo/actions/workflows/patch-and-release.yml)

Automated GitHub Actions pipeline for **hololive Dreams** (`game.qualiarts.hololive.dreams.com`). It fetches the official APKPure XAPK, patches the Google Play licensing/installer lock (PairIP), properly packages and signs a standalone arm64 APK, and publishes releases for auto-updating via **Obtainium**.

---

## Sideloading vs. Account Linking / Google Login: The Reality

When sideloading this game, there are two distinct installation paths depending on your priorities:

| Feature / Goal | Method A: Sideload Patched APK (Obtainium) | Method B: ADB Install as Google Play (`-i com.android.vending`) |
| :--- | :--- | :--- |
| **Google Account Linking** | ❌ Fails (Google OAuth server checks SHA-256 fingerprint) | ✅ Works (Uses official Play Store signature) |
| **In-Game Data Transfer ID (引継ぎ)** | ✅ Works completely | ✅ Works completely |
| **Google / OEM Game Dashboard & 120 FPS** | ⚠️ Generic profile unless set in OS Display settings | ✅ Works natively (installer attributed to Play Store) |
| **Developer Options / USB Debugging Required** | ❌ **No** (Safe for banking apps) | ⚠️ **Yes** (During initial install & updates) |
| **Update Process** | Seamless 1-tap in Obtainium | Connect USB, enable ADB, run shell commands |

> **Why Google Login / Play Games fails on any patched APK:**
> Google's OAuth 2.0 servers verify client requests by checking the cryptographic SHA-256 certificate fingerprint of the running app against Google Cloud Console. Qualiarts's server only authorizes Google's official App Signing Key (`db:f5:a4:...`). Any modified or re-signed APK has a different signature, so Google's backend unconditionally rejects Google Sign-In with an OAuth mismatch (`10: DEVELOPER_ERROR`).
>
> **Recommended Solution:** Use the publisher's built-in **Data Transfer ID & Password (データ引継ぎ)** system under the game's menu. It works identically across all devices and clients without relying on Google servers.

---

## Method A: Clean Obtainium Setup (No Developer Options)

Use this method if banking apps or security profiles prohibit keeping Developer Options enabled.

### First-Time Installation
1. If you previously had the official app installed, back up your account with a **Data Transfer ID & Password** (引継ぎ) first.
2. Cleanly uninstall the existing app:
   - Go to **Settings -> Apps -> hololive Dreams**.
   - Tap **Storage & cache -> Clear storage**.
   - Tap **Uninstall**. Ensure the popup checkbox *"Keep app data"* is **UNCHECKED** (prevents `failureConflict`).
3. In **Obtainium**, tap **Add App**:
   - URL: `https://github.com/AlexAn75541/holoholo`
   - Filter regular expression: `.*\.apk$`
4. Tap **Add**, then tap **Install**.
5. Open the game and restore your account using your Data Transfer ID. Future updates from Obtainium will update in-place without data loss.

---

## Method B: ADB Sideload with Google Play Attribution

This method installs the **unmodified official split APKs** while setting Google Play (`com.android.vending`) as the installer. This bypasses the Google Play licensing check without patching the binary, allowing **official Google Account login** and **Game Dashboard / 120 FPS** to work.

### Initial Installation via ADB

1. Download and extract the official XAPK (e.g. from APKPure):
   - `game.qualiarts.hololive.dreams.com.apk` (Base APK)
   - `config.arm64_v8a.apk` (ABI split)
   - `UnityDataAssetPack.apk` (Asset split)
2. Connect your phone via USB and enable USB Debugging.
3. Push files to temporary device storage:
   ```bash
   adb push game.qualiarts.hololive.dreams.com.apk /data/local/tmp/base.apk
   adb push config.arm64_v8a.apk /data/local/tmp/config.apk
   adb push UnityDataAssetPack.apk /data/local/tmp/asset.apk
   ```
4. Create an installation session attributed to Google Play:
   ```bash
   adb shell pm install-create -i "com.android.vending" -r
   ```
   *(This outputs a session ID, e.g. `Success: created install session [12345678]`)*
5. Stage the APKs into the session:
   ```bash
   adb shell pm install-write 12345678 base.apk /data/local/tmp/base.apk
   adb shell pm install-write 12345678 config.apk /data/local/tmp/config.apk
   adb shell pm install-write 12345678 asset.apk /data/local/tmp/asset.apk
   ```
6. Commit the installation and clean up:
   ```bash
   adb shell pm install-commit 12345678
   adb shell rm /data/local/tmp/*.apk
   ```
7. *(Optional)* Turn off Developer Options once installed if required by banking apps.

---

### Updating the Game via ADB (When a New Version Drops)

When a new game version is released, you can update without losing any save data or account links:

1. Download the new version's XAPK and extract the updated APKs (`base.apk`, `config.arm64_v8a.apk`, `UnityDataAssetPack.apk`).
2. Connect phone via USB and enable USB Debugging.
3. Push the new APKs:
   ```bash
   adb push game.qualiarts.hololive.dreams.com.apk /data/local/tmp/base.apk
   adb push config.arm64_v8a.apk /data/local/tmp/config.apk
   adb push UnityDataAssetPack.apk /data/local/tmp/asset.apk
   ```
4. Create an update session (the `-r` flag preserves existing app data):
   ```bash
   adb shell pm install-create -i "com.android.vending" -r -d
   ```
   *(Note the returned session ID, e.g. `87654321`)*
5. Write the split files to the update session:
   ```bash
   adb shell pm install-write 87654321 base.apk /data/local/tmp/base.apk
   adb shell pm install-write 87654321 config.apk /data/local/tmp/config.apk
   adb shell pm install-write 87654321 asset.apk /data/local/tmp/asset.apk
   ```
6. Commit the update:
   ```bash
   adb shell pm install-commit 87654321
   adb shell rm /data/local/tmp/*.apk
   ```
7. The game updates in-place. All user data, logins, and configurations are preserved.

---

## Unlocking 120 FPS / Game Dashboard

**Package ID:** `game.qualiarts.hololive.dreams.com`  
**App List Name:** `hololive Dreams` (or `ホロライブドリームス`)

### Option 1: Game Dashboard overlay
1. Open **Settings -> Special features -> Game Mode / Game Dashboard**.
2. Tap **Add Apps** and ensure `hololive Dreams` (`game.qualiarts.hololive.dreams.com`) is enabled.
3. Open **Settings -> Display -> Refresh rate** -> set to **High (120 Hz)**.
4. If available, open **Apps with high refresh rate** and toggle `hololive Dreams` to 120 Hz.
5. In-game, open **メニュー -> ライブ設定 / 動作設定** and set quality/framerate to **High (高)**.

### Option 2: Force Game Mode & 120 Hz via ADB
If the app does not show up in the Game Dashboard list:

1. Force Android Game Mode performance profile:
   ```bash
   adb shell cmd game set --fps 120 --mode 2 game.qualiarts.hololive.dreams.com
   ```
2. Force display refresh rate to 120 Hz:
   ```bash
   adb shell settings put system peak_refresh_rate 120.0
   adb shell settings put system min_refresh_rate 120.0
   ```

---

## Disclaimer

This project is an unofficial community tool created for personal backup, regional accessibility, and automation purposes. All game assets, names, and trademarks belong to COVER Corp. and QualiArts, Inc.
