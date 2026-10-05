# holoholo: session handoff for Claude

## User goal

Install hololive Dreams (`game.qualiarts.hololive.dreams.com`) on a Nothing OS 4.1 / Android 16 phone without leaving Developer Options enabled. Source: APKPure XAPK. Obtainium/ObtainX should recognize one GitHub release APK and support seamless updates. Preserve the original game package name and Android version code; patch-release labels start at `0.3-beta` (then `0.3.1-beta`, etc.) as requested. Do not promote to `1.0` until the user confirms installation and gameplay. No manual signing labor requested.

## Technical Findings on Google Login vs Sideloading

1. **Why Google Account Link / Google Sign-In Fails on Any Patched APK**:
   - Google Sign-In and Google Play Games use OAuth 2.0. The Google OAuth backend validates client requests by checking the cryptographic SHA-256 fingerprint of the APK's signing certificate against Google Cloud Console.
   - Qualiarts's Google Cloud project authorizes Google's official App Signing Key: `db:f5:a4:12:fc:45:97:a3:e3:5b:dc:c6:1c:37:4e:83:89:ce:6a:05:d5:e5:eb:e0:89:50:28:45:10:6a:8d:1b`.
   - Any re-signed APK has a different SHA-256 fingerprint. Google's server rejects the token request with an OAuth mismatch (`10: DEVELOPER_ERROR`).
   - Sideloaded modified APKs cannot complete Google Sign-In without server-side Google Cloud modifications.
   - **Solution for Sideloaders**: Use the game's built-in **Data Transfer ID & Password (データ引継ぎ)** under the in-game menu. It restores the account across any client without relying on Google servers.

2. **Why ADB Install Works with Google Account Link**:
   - The ADB installation command (`pm install-create -i "com.android.vending" -r`) installs the **unmodified original APKs** signed by Qualiarts/Google.
   - Because the signature is the genuine Google Play signing key and the installer package is set to `com.android.vending`, Google Sign-In and Google Game Dashboard/120Hz work natively.

## Installation & Update Methods Documented in README

1. **Method A (Obtainium Auto-Updates)**:
   - Patched standalone arm64 APK with PairIP checks neutralized, uncompressed `resources.arsc`, 16 KiB alignment, and v2/v3 signatures.
   - Updates via Obtainium with zero Developer Options needed.
   - Uses in-game Data Transfer ID for account sync.
2. **Method B (ADB with Google Play Attribution)**:
   - Full command sequence for initial installation and in-place version updates documented in README.md.
   - Retains official Google account linking and native 120 FPS Game Dashboard attribution.

Key files: `scripts/patcher.py`, `scripts/verify_apk.py`, `tests/test_verify_apk.py`, `.github/workflows/patch-and-release.yml`, `CONSTRAINTS.md`, `README.md`, `CLAUDE_HANDOFF.md`.
