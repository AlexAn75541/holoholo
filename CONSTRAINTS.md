# Constraints

## Release gate

- Publish exactly one arm64 `.apk` per patch release. Do not publish an `.xapk` or describe the APK as universal.
- Preserve the source application's package name, version name, and version code. `scripts/verify_apk.py` compares these to the source XAPK manifest and blocks differences.
- Require zero failures in ZIP integrity, merged Unity assets and arm64 libraries, standalone manifest, 16 KiB ZIP alignment, and Android APK Signature Scheme v2 verification. Zero is required because any one failure can prevent installation. Run `PYTHONPATH=. python3 tests/test_verify_apk.py` locally; CI runs the artifact verifier on the built APK.
- Require an Android API 36+ arm64 device to pass clean install and same-version reinstall in CI before publishing. An unavailable device or missing SDK tool blocks publication; neither static checks nor an x86 emulator establish arm64 Android 16 installation.
- Installation success does not prove gameplay, Play Protect acceptance, or behavior on every Android device. Do not claim these without direct evidence.
- Keep the last published patch release until all gates pass. Prune older patch releases only after a replacement is published. Keep beta tags for patch revision counting; do not change to `1.0` without explicit user approval.

## Scope

- Local checks: Python syntax and the verifier self-check. Device install: CI only.
- No coverage, web performance, or accessibility target: no app UI or existing coverage suite in this repository.
- Do not weaken gates, skip tests, commit signing secrets, or claim a simulated check was a device test to make CI pass.
