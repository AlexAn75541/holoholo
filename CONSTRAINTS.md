# Constraints

## Release gate

- Publish exactly one arm64 `.apk` per patch release. Do not publish an `.xapk` or describe the APK as universal.
- Preserve the source application's package name, version name, and version code. `scripts/verify_apk.py` compares these to the source XAPK manifest and blocks differences.
- Require zero failures in ZIP integrity, uncompressed `resources.arsc` (mandatory for target SDK 30+), merged Unity assets and arm64 libraries, standalone manifest (split requirements neutralized), 16 KiB ZIP alignment, and Android APK Signature Scheme v2 or v3 verification. Zero is required because any one failure prevents installation. Run `PYTHONPATH=. python3 tests/test_verify_apk.py` locally; CI runs `verify_apk.py` on the built APK.
- Releases use patch version tags starting at `0.3-beta` (then `0.3.1-beta`, etc.).
- Prune older patch releases only after a replacement is published. Do not change to `1.0` without explicit user approval.
- Static APK checks prove package format compliance, but do not guarantee runtime gameplay, Play Protect acceptance, or device-specific OS quirks.

## Scope

- Local checks: Python syntax and the verifier self-check (`tests/test_verify_apk.py`).
- CI/CD checks: full build, alignment, v2/v3 signing, and static verification before release publication.
- Do not weaken gates, skip tests, commit private signing secrets, or claim an unverified build is gameplay-tested.
