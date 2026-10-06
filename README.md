# holoholo 

Automated GitHub Actions pipeline for **hololive Dreams** (`game.qualiarts.hololive.dreams.com`). It fetches the official APKPure XAPK, patches the Google Play licensing/installer lock (PairIP), properly packages and signs a standalone arm64 APK, and publishes apks to releases.

> [!WARNING]
> **ONLY LOGIN WITH ID AND PASSWORD. GOOGLE SIGN IN NOT SUPPORTED.**
> If you wanted to have Google Sign in for whatever reasons, just go to [method B](https://github.com/AlexAn75541/holoholo#method-b-adb-sideload-with-google-play-attribution-you-can-use-this-instead-of-the-apk-in-this-repo-if-you-still-wanted-to-have-google-sign-in)

[![Update & Release](https://github.com/AlexAn75541/holoholo/actions/workflows/patch-and-release.yml/badge.svg)](https://github.com/AlexAn75541/holoholo/actions/workflows/patch-and-release.yml)


# Methods to actually install da game

---

## Method A: just use Obtainium/ObtainX for the apks in this repo or APKPure

## Method B: ADB Sideload with Google Play Attribution (You can use this instead of the apk in this repo, if you still wanted to have google sign in)

This method installs the **unmodified official split APKs** while setting Google Play (`com.android.vending`) as the installer. This bypasses the Google Play licensing check without patching the binary, allowing **official Google Account login** to work.

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
   *(This outputs a session ID that you have to note it down for the next 3 commands, e.g. `Success: created install session [12345678]`)*
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
7. *(Optional)* Turn off Developer Options once installed if required by security-aware apps like banking apps and shit.

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

# Unlocking 120 FPS / Game Dashboard

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

I'm creating this repo for the sole purpose of playing hololive dream wthout having to deal with xapk manual sideloading, and i'm not gonna advertise this shit because people will find it eventually.
