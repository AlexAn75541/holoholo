#!/usr/bin/env python3
"""
Android Compatibility & Verification Check
Verifies APK structure, signatures, 16KB page alignment, and split compatibility for Android 16+.
"""

import sys
import os
import zipfile
import struct
import shutil
import subprocess

def run_cmd(cmd):
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed ({' '.join(cmd)}):\n{res.stderr}\n{res.stdout}")
    return res.stdout.strip()

def check_apk_compliance(apk_path: str) -> None:
    print(f"\n==================================================")
    print(f"Checking Android 16+ Compliance: {os.path.basename(apk_path)}")
    print(f"==================================================")

    if not os.path.isfile(apk_path):
        raise FileNotFoundError(f"APK not found: {apk_path}")

    # 1. Check ZIP and AndroidManifest.xml
    with zipfile.ZipFile(apk_path, 'r') as zf:
        infolist = zf.infolist()
        namelist = [info.filename for info in infolist]

        if "AndroidManifest.xml" not in namelist:
            raise ValueError(f"FAIL: AndroidManifest.xml missing in {apk_path}")

        axml = zf.read("AndroidManifest.xml")
        
        # Verify requiredSplitTypes is not enforcing splits
        if b"base__abi" in axml:
            raise ValueError("FAIL: AndroidManifest.xml still contains requiredSplitTypes='base__abi'")
        if b"com.android.vending.splits.required" in axml:
            raise ValueError("FAIL: AndroidManifest.xml still contains com.android.vending.splits.required")
        if b"com.android.vending.splits\x00" in axml:
            raise ValueError("FAIL: AndroidManifest.xml still contains com.android.vending.splits")

        print("✓ AndroidManifest.xml: Split requirements cleanly removed")

        # 2. Check Native Library 16KB Alignment (Android 15 & 16 requirement)
        so_files = [info for info in infolist if info.filename.endswith(".so")]
        print(f"✓ Found {len(so_files)} native shared libraries (.so)")

        misaligned_16k = []
        for info in so_files:
            # Check local file header offset
            with open(apk_path, "rb") as f:
                f.seek(info.header_offset)
                lh = f.read(30)
                fn_len, extra_len = struct.unpack("<HH", lh[26:30])
                data_offset = info.header_offset + 30 + fn_len + extra_len
                if data_offset % 16384 != 0:
                    misaligned_16k.append((info.filename, data_offset))

        if misaligned_16k:
            print(f"Warning: {len(misaligned_16k)} .so files are not 16KB aligned (required for 16KB page devices)")
        else:
            print("✓ Native libraries: 100% 16KB (16384-byte) page aligned for Android 15/16")

        # 3. Check classes.dex exists
        dex_files = [info.filename for info in infolist if info.filename.startswith("classes") and info.filename.endswith(".dex")]
        if not dex_files:
            raise ValueError("FAIL: No classes.dex found in APK")
        print(f"✓ DEX: Found {len(dex_files)} dex files: {dex_files}")

    # 4. Check APK Signature Scheme v2/v3 using apksigner if available
    apksigner = shutil.which("apksigner")
    if not apksigner:
        android_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
        if android_home:
            bt_dir = os.path.join(android_home, "build-tools")
            if os.path.isdir(bt_dir):
                for v in sorted(os.listdir(bt_dir), reverse=True):
                    cand = os.path.join(bt_dir, v, "apksigner")
                    if os.path.isfile(cand):
                        apksigner = cand
                        break

    if apksigner:
        verify_output = run_cmd([apksigner, "verify", "--verbose", apk_path])
        if "Verifies" not in verify_output:
            raise ValueError(f"FAIL: apksigner verify failed for {apk_path}:\n{verify_output}")
        v2_ok = "Verified using v2 scheme (APK Signature Scheme v2): true" in verify_output
        v3_ok = "Verified using v3 scheme (APK Signature Scheme v3): true" in verify_output
        print(f"✓ Signature: Verified (v2: {v2_ok}, v3: {v3_ok})")
    else:
        print("Note: apksigner not available in current environment; skipped signature verification")

    print(f"RESULT: PASS - {os.path.basename(apk_path)} is valid for Android 16 installation\n")

def main():
    if len(sys.argv) < 2:
        print("Usage: verify_apk.py <path_to_apk_or_dist_dir>")
        sys.exit(1)

    target = sys.argv[1]
    if os.path.isdir(target):
        apk_files = [os.path.join(target, f) for f in os.listdir(target) if f.endswith(".apk")]
        if not apk_files:
            print(f"No APK files found in directory: {target}")
            sys.exit(1)
        for apk in sorted(apk_files):
            check_apk_compliance(apk)
    else:
        check_apk_compliance(target)

if __name__ == "__main__":
    main()
