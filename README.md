# Hololive Dreams Auto-Patcher & Updater

Automated GitHub Actions pipeline to fetch the latest XAPK of **hololive Dreams** (`game.qualiarts.hololive.dreams.com`) from APKPure, patch the Google Play installer & licensing check (PairIP), sign with a permanent key, and publish releases for seamless updates via **Obtainium**.

---

## Why This Repo Exists

When sideloading `game.qualiarts.hololive.dreams.com` without Google Play Store (e.g., via Obtainium or manual install), the app displays a blocking Google Play warning dialog (`LicenseActivity`). Previously, this could only be circumvented by using ADB:
```bash
adb shell pm install-create -i "com.android.vending" -r
```
Because banking apps and security policies often prohibit enabling **Developer Options / USB Debugging**, this repository eliminates the root cause:
- **Bytecode Patch**: Patches `com.pairip.licensecheck.LicenseClient` in `classes.dex` so local installer check and licensing always return `true` / bypass immediately.
- **Standalone APK & Repacked XAPK**: Merges split APKs (`config.arm64_v8a.apk` and `UnityDataAssetPack.apk`) into a single universal APK, or leaves them as a repacked XAPK.
- **Consistent Signing**: Signs every release with a permanent repository keystore (`keystore/release.p12`) so Obtainium can update subsequent releases seamlessly without uninstalling.

---

## ⚠️ Required One-Time GitHub Setting

Before running the workflow, grant GitHub Actions permission to publish Releases:

1. Open your repository on GitHub (`https://github.com/AlexAn75541/holoholo`).
2. Go to **Settings** -> **Actions** -> **General**.
3. Scroll down to **Workflow permissions**.
4. Select **Read and write permissions**.
5. Click **Save**.

---

## How to Trigger the Workflow

### Option 1: Automatic
The workflow runs automatically once daily at 04:00 UTC. If APKPure has released a new version of hololive Dreams, it fetches, patches, and releases it. If the current version is already released, it skips automatically.

### Option 2: Manual Trigger (workflow_dispatch)
1. Go to the **Actions** tab in this repo.
2. Select **Patch and Release Hololive Dreams**.
3. Click **Run workflow**.
4. (Optional) Provide a custom XAPK URL or check `force_release` to rebuild an existing release.

---

## How to Set Up Obtainium

1. Open **Obtainium** on your Android device.
2. Tap **Add App**.
3. Enter your repository URL:
   ```text
   https://github.com/AlexAn75541/holoholo
   ```
4. Optional configurations in Obtainium:
   - **Filter regular expression**: `.*\.apk$` (to download the standalone universal APK) or `.*\.xapk$` (to download the XAPK bundle).
   - **Version detection**: Leave default (GitHub Releases).
5. Tap **Add**.

### First Install Notice
> **Important**: If you already have the game installed with the original Qualiarts Play Store signature, you must **uninstall it once** before installing this patched version. Android enforces that updates share the same signing certificate. All subsequent updates from this repo will update seamlessly.
