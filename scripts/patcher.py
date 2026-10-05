#!/usr/bin/env python3
"""
Hololive Dreams APK / XAPK Patcher & Builder
Patches PairIP (Google Play licensing / installer check) in classes.dex,
merges split APKs into a standalone APK, and repacks signed XAPK and APK for Obtainium.
"""

import os
import sys
import re
import json
import zlib
import shutil
import struct
import hashlib
import zipfile
import argparse
import subprocess
import urllib.request
from typing import Dict, List, Tuple, Optional

DEFAULT_PACKAGE = "game.qualiarts.hololive.dreams.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def get_apkpure_download_info(package_name: str = DEFAULT_PACKAGE) -> Tuple[str, str, str]:
    """
    Queries APKPure mobile API (same as Obtainium) to fetch direct CDN download URL and metadata.
    Returns (download_url, version_name, version_code).
    """
    api_url = f"https://tapi.pureapk.com/v3/get_app_his_version?package_name={package_name}&hl=en"
    headers = {
        "Ual-Access-Businessid": "projecta",
        "Ual-Access-ProjectA": '{"device_info":{"os_ver":"34"}}',
        "User-Agent": USER_AGENT,
    }
    req = urllib.request.Request(api_url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    version_list = data.get("version_list", [])
    if not version_list:
        raise RuntimeError(f"No versions found for package: {package_name}")

    latest = version_list[0]
    ver_name = str(latest.get("version_name", "1.0.0"))
    ver_code = str(latest.get("version_code", "0"))
    asset = latest.get("asset", {})
    download_url = asset.get("url")
    if not download_url:
        urls = asset.get("urls", [])
        if urls:
            download_url = urls[0]

    if not download_url:
        raise RuntimeError(f"Download URL missing in APKPure asset: {asset}")

    return download_url, ver_name, ver_code


def read_uleb128(data: bytes, p: int) -> Tuple[int, int]:
    val = 0
    shift = 0
    while True:
        b = data[p]
        p += 1
        val |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            break
        shift += 7
    return val, p


def patch_dex_bytes(dex: bytearray) -> Tuple[bytearray, List[str]]:
    """
    Patches classes.dex in-place to bypass PairIP Google Play checks.
    """
    if len(dex) < 0x70 or dex[:4] != b'dex\n':
        return dex, []

    string_ids_size, string_ids_off = struct.unpack('<II', dex[0x38:0x40])
    type_ids_size, type_ids_off = struct.unpack('<II', dex[0x40:0x48])
    method_ids_size, method_ids_off = struct.unpack('<II', dex[0x58:0x60])
    class_defs_size, class_defs_off = struct.unpack('<II', dex[0x60:0x68])

    def get_string(idx: int) -> str:
        if idx >= string_ids_size:
            return ""
        off = struct.unpack('<I', dex[string_ids_off + idx * 4 : string_ids_off + (idx + 1) * 4])[0]
        length, p = read_uleb128(dex, off)
        return dex[p : p + length].decode('utf-8', errors='replace')

    def get_type(idx: int) -> str:
        if idx >= type_ids_size:
            return ""
        str_idx = struct.unpack('<I', dex[type_ids_off + idx * 4 : type_ids_off + (idx + 1) * 4])[0]
        return get_string(str_idx)

    methods_to_patch = {
        ('Lcom/pairip/licensecheck/LicenseClient;', 'performLocalInstallerCheck'): 'return_true',
        ('Lcom/pairip/licensecheck/LicenseClient;', 'isLocalCheckPassed'): 'return_true',
        ('Lcom/pairip/licensecheck/LicenseClient;', 'checkLicense'): 'return_void',
        ('Lcom/pairip/application/Application;', 'attachBaseContext'): 'nop_first_invoke',
    }

    found: Dict[Tuple[str, str], int] = {}
    for i in range(class_defs_size):
        c_idx = struct.unpack('<I', dex[class_defs_off + i * 32 : class_defs_off + i * 32 + 4])[0]
        cname = get_type(c_idx)
        data_off = struct.unpack('<I', dex[class_defs_off + i * 32 + 24 : class_defs_off + i * 32 + 28])[0]
        if not data_off:
            continue
        p = data_off
        sf, p = read_uleb128(dex, p)
        inf, p = read_uleb128(dex, p)
        dm, p = read_uleb128(dex, p)
        vm, p = read_uleb128(dex, p)
        for _ in range(sf):
            _, p = read_uleb128(dex, p)
            _, p = read_uleb128(dex, p)
        for _ in range(inf):
            _, p = read_uleb128(dex, p)
            _, p = read_uleb128(dex, p)

        for count in (dm, vm):
            mid = 0
            for _ in range(count):
                diff, p = read_uleb128(dex, p)
                flags, p = read_uleb128(dex, p)
                code_off, p = read_uleb128(dex, p)
                mid += diff
                if mid < method_ids_size:
                    c_idx_m, p_idx_m, n_idx_m = struct.unpack('<HHI', dex[method_ids_off + mid * 8 : method_ids_off + (mid + 1) * 8])
                    mname = get_string(n_idx_m)
                    key = (cname, mname)
                    if key in methods_to_patch and code_off:
                        found[key] = code_off

    patched_actions = []
    for key, action in methods_to_patch.items():
        if key not in found:
            continue
        code_off = found[key]
        r_sz, i_sz, o_sz, t_sz, d_off, insns_sz = struct.unpack('<HHHHII', dex[code_off : code_off + 16])
        ins_byte_start = code_off + 16
        ins_byte_len = insns_sz * 2

        if action == 'return_true' and ins_byte_len >= 4:
            # const/4 v0, 1 (0x1012), return v0 (0x000f), pad nop (0x0000)
            patch = bytes([0x12, 0x10, 0x0F, 0x00]) + b'\x00' * (ins_byte_len - 4)
            dex[ins_byte_start : ins_byte_start + ins_byte_len] = patch
            patched_actions.append(f'{key[0]}->{key[1]}: return_true')
        elif action == 'return_void' and ins_byte_len >= 2:
            # return-void (0x000e), pad nop (0x0000)
            patch = bytes([0x0E, 0x00]) + b'\x00' * (ins_byte_len - 2)
            dex[ins_byte_start : ins_byte_start + ins_byte_len] = patch
            patched_actions.append(f'{key[0]}->{key[1]}: return_void')
        elif action == 'nop_first_invoke' and ins_byte_len >= 6:
            # nop out 3-word invoke-static (6 bytes)
            dex[ins_byte_start : ins_byte_start + 6] = b'\x00\x00\x00\x00\x00\x00'
            patched_actions.append(f'{key[0]}->{key[1]}: nop_checkLicense_invoke')

    if patched_actions:
        # Recompute SHA-1
        sha1 = hashlib.sha1(dex[32:]).digest()
        dex[12:32] = sha1

        # Recompute Adler-32
        adler = zlib.adler32(dex[12:]) & 0xFFFFFFFF
        dex[8:12] = struct.pack('<I', adler)

    return dex, patched_actions


def is_signature_file(filename: str) -> bool:
    fn = filename.upper()
    return (
        fn.startswith("META-INF/")
        and (
            fn.endswith(".SF")
            or fn.endswith(".RSA")
            or fn.endswith(".DSA")
            or fn.endswith(".EC")
            or fn.endswith(".MF")
            or "SIG-" in fn
        )
    )


def patch_apk(input_apk_path: str, output_apk_path: str) -> List[str]:
    """
    Extracts, patches DEX files, strips old signatures, and repacks APK.
    """
    all_patched_actions = []
    with zipfile.ZipFile(input_apk_path, 'r') as in_zip:
        with zipfile.ZipFile(output_apk_path, 'w', compression=zipfile.ZIP_DEFLATED) as out_zip:
            for item in in_zip.infolist():
                if is_signature_file(item.filename):
                    continue
                data = in_zip.read(item.filename)
                if item.filename.startswith("classes") and item.filename.endswith(".dex"):
                    patched_dex, actions = patch_dex_bytes(bytearray(data))
                    if actions:
                        all_patched_actions.extend([f"[{item.filename}] {a}" for a in actions])
                        data = bytes(patched_dex)
                # Store uncompressed for .so and audio/assets if wanted, or standard deflate
                compress_type = zipfile.ZIP_STORED if item.filename.endswith(".so") else zipfile.ZIP_DEFLATED
                out_zip.writestr(item.filename, data, compress_type=compress_type)
    return all_patched_actions


def clean_manifest_for_standalone(axml_bytes: bytes) -> bytes:
    """
    Cleans AndroidManifest.xml binary XML for standalone single APK install:
    1. Removes Google Play split-requirement meta-data tags (com.android.vending.splits.required, etc.)
       which cause Android 14/15/16 PackageInstaller to fail with STATUS_FAILURE_INCOMPATIBLE.
    2. Clears requiredSplitTypes='base__abi' attribute on <manifest>.
    """
    axml = bytearray(axml_bytes)
    chunk_type, chunk_size = struct.unpack('<II', axml[8:16])
    string_count, style_count, flags, strings_start, styles_start = struct.unpack('<IIIII', axml[16:36])
    offsets = struct.unpack(f'<{string_count}I', axml[36 : 36 + string_count * 4])
    pool_data = axml[8 + strings_start :]
    strings = []
    for off in offsets:
        u16_len = struct.unpack('<H', pool_data[off : off + 2])[0]
        s = pool_data[off + 2 : off + 2 + u16_len * 2].decode('utf-16le', errors='replace')
        strings.append(s)

    empty_idx = strings.index('') if '' in strings else None
    req_split_idx = strings.index('requiredSplitTypes') if 'requiredSplitTypes' in strings else None

    res_type, res_size = struct.unpack('<II', axml[8 + chunk_size : 8 + chunk_size + 8])
    chunks = []
    p = 8 + chunk_size
    if res_type == 0x00080180:
        chunks.append(('res_map', p, res_size))
        p += res_size

    while p < len(axml):
        ctype, csize = struct.unpack('<II', axml[p : p + 8])
        chunks.append((ctype, p, csize))
        p += csize

    to_remove = set()
    for i, (ctype, cpos, csize) in enumerate(chunks):
        if ctype == 0x00100102:  # START_TAG
            name_idx = struct.unpack('<I', axml[cpos + 20 : cpos + 24])[0]
            tag_name = strings[name_idx]
            if tag_name == 'meta-data':
                attr_count = struct.unpack('<H', axml[cpos + 28 : cpos + 30])[0]
                ap = cpos + 36
                m_name = None
                for _ in range(attr_count):
                    aname = struct.unpack('<I', axml[ap + 4 : ap + 8])[0]
                    aval_str = struct.unpack('<I', axml[ap + 8 : ap + 12])[0]
                    if strings[aname] == 'name' and aval_str < len(strings):
                        m_name = strings[aval_str]
                    ap += 20
                if m_name in ('com.android.vending.splits.required', 'com.android.vending.splits', 'com.android.vending.derived.apk.id'):
                    to_remove.add(i)
                    to_remove.add(i + 1)  # Matching END_TAG

    new_axml = bytearray(axml[: chunks[0][1]])
    for i, (ctype, cpos, csize) in enumerate(chunks):
        if i in to_remove:
            continue
        chunk_bytes = axml[cpos : cpos + csize]
        if ctype == 0x00100102:
            name_idx = struct.unpack('<I', chunk_bytes[20:24])[0]
            if strings[name_idx] == 'manifest' and req_split_idx is not None and empty_idx is not None:
                attr_count = struct.unpack('<H', chunk_bytes[28:30])[0]
                ap = 36
                for _ in range(attr_count):
                    aname = struct.unpack('<I', chunk_bytes[ap + 4 : ap + 8])[0]
                    if aname == req_split_idx:
                        chunk_bytes[ap + 8 : ap + 12] = struct.pack('<I', empty_idx)
                        chunk_bytes[ap + 16 : ap + 20] = struct.pack('<i', empty_idx)
                    ap += 20
        new_axml.extend(chunk_bytes)

    new_axml[4:8] = struct.pack('<I', len(new_axml))
    return bytes(new_axml)


def merge_split_apks(patched_base_apk: str, split_apk_paths: List[str], output_merged_apk: str) -> None:
    """
    Merges native libraries (config.*.apk) and assets (UnityDataAssetPack.apk) into base APK,
    and strips split requirements from AndroidManifest.xml.
    """
    seen_entries = set()
    with zipfile.ZipFile(output_merged_apk, 'w', compression=zipfile.ZIP_DEFLATED) as out_zip:
        # 1. Write patched base APK entries (with cleaned AndroidManifest.xml)
        with zipfile.ZipFile(patched_base_apk, 'r') as base_zip:
            for item in base_zip.infolist():
                if is_signature_file(item.filename):
                    continue
                seen_entries.add(item.filename)
                data = base_zip.read(item.filename)
                if item.filename == "AndroidManifest.xml":
                    print("Cleaning AndroidManifest.xml split requirements for standalone APK...")
                    data = clean_manifest_for_standalone(data)
                compress_type = zipfile.ZIP_STORED if item.filename.endswith(".so") else item.compress_type
                out_zip.writestr(item.filename, data, compress_type=compress_type)

        # 2. Merge entries from split APKs
        for split_path in split_apk_paths:
            with zipfile.ZipFile(split_path, 'r') as split_zip:
                for item in split_zip.infolist():
                    if is_signature_file(item.filename):
                        continue
                    if item.filename in ("AndroidManifest.xml", "resources.arsc"):
                        continue
                    if item.filename in seen_entries:
                        continue
                    seen_entries.add(item.filename)
                    data = split_zip.read(item.filename)
                    compress_type = zipfile.ZIP_STORED if item.filename.endswith(".so") else item.compress_type
                    out_zip.writestr(item.filename, data, compress_type=compress_type)


def strip_apk_signatures(input_apk_path: str, output_apk_path: str) -> None:
    with zipfile.ZipFile(input_apk_path, 'r') as in_zip:
        with zipfile.ZipFile(output_apk_path, 'w', compression=zipfile.ZIP_DEFLATED) as out_zip:
            for item in in_zip.infolist():
                if is_signature_file(item.filename):
                    continue
                compress_type = zipfile.ZIP_STORED if item.filename.endswith(".so") else item.compress_type
                out_zip.writestr(item.filename, in_zip.read(item.filename), compress_type=compress_type)


def run_cmd(cmd: List[str]) -> str:
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed ({' '.join(cmd)}):\n{res.stderr}\n{res.stdout}")
    return res.stdout.strip()


def zipalign_and_sign(
    apk_path: str,
    output_path: str,
    keystore_path: str,
    key_pass: str = "holoholo",
    key_alias: str = "release"
) -> None:
    # Find zipalign and apksigner
    zipalign_bin = shutil.which("zipalign")
    apksigner_bin = shutil.which("apksigner")

    if not zipalign_bin or not apksigner_bin:
        android_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
        if android_home:
            bt_dir = os.path.join(android_home, "build-tools")
            if os.path.isdir(bt_dir):
                versions = sorted(os.listdir(bt_dir), reverse=True)
                for v in versions:
                    cand_zip = os.path.join(bt_dir, v, "zipalign")
                    cand_sign = os.path.join(bt_dir, v, "apksigner")
                    if os.path.isfile(cand_zip) and not zipalign_bin:
                        zipalign_bin = cand_zip
                    if os.path.isfile(cand_sign) and not apksigner_bin:
                        apksigner_bin = cand_sign

    temp_aligned = output_path + ".aligned.tmp"
    if zipalign_bin:
        print(f"Aligning {apk_path} with {zipalign_bin}...")
        run_cmd([zipalign_bin, "-p", "-f", "4", apk_path, temp_aligned])
    else:
        print("Warning: zipalign not found, copying directly...")
        shutil.copy2(apk_path, temp_aligned)

    if apksigner_bin and os.path.isfile(keystore_path):
        print(f"Signing {temp_aligned} with apksigner...")
        # Determine keystore type (PKCS12 vs JKS)
        ks_type = "PKCS12" if keystore_path.endswith(".p12") else "JKS"
        run_cmd([
            apksigner_bin, "sign",
            "--ks", keystore_path,
            "--ks-type", ks_type,
            "--ks-pass", f"pass:{key_pass}",
            "--ks-key-alias", key_alias,
            "--out", output_path,
            temp_aligned
        ])
        verify_out = run_cmd([apksigner_bin, "verify", "--verbose", output_path])
        print(f"Signature verified:\n{verify_out}")
    else:
        print("Warning: apksigner or keystore not found, outputting unsigned APK...")
        shutil.move(temp_aligned, output_path)

    if os.path.exists(temp_aligned):
        os.remove(temp_aligned)


def download_file(url: str, dest_path: str) -> None:
    print(f"Downloading from {url} to {dest_path}...")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as out_file:
        total_size = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 1024 * 2  # 2MB
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                percent = (downloaded / total_size) * 100
                print(f"\r  [{downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB] ({percent:.1f}%)", end="")
            else:
                print(f"\r  [{downloaded / (1024*1024):.1f} MB]", end="")
    print()


def main():
    parser = argparse.ArgumentParser(description="Hololive Dreams APK/XAPK Patcher")
    parser.add_argument("--input", default=None, help="Input XAPK path or direct download URL")
    parser.add_argument("--keystore", default="keystore/release.p12", help="Keystore path")
    parser.add_argument("--keystore-pass", default="holoholo", help="Keystore password")
    parser.add_argument("--keystore-alias", default="release", help="Keystore key alias")
    parser.add_argument("--dist-dir", default="dist", help="Output directory")
    parser.add_argument("--patch-version", required=True, help="Release version, e.g. 0.1-beta")
    args = parser.parse_args()

    os.makedirs(args.dist_dir, exist_ok=True)
    work_dir = os.path.join(args.dist_dir, "work")
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)

    input_source = args.input
    xapk_path = os.path.join(work_dir, "source.xapk")

    # Priority 1: Check for input file in input/ folder
    input_dir = "input"
    if not input_source and os.path.isdir(input_dir):
        candidates = [
            os.path.join(input_dir, f)
            for f in os.listdir(input_dir)
            if f.lower().endswith((".xapk", ".zip"))
        ]
        if candidates:
            input_source = candidates[0]
            print(f"Found local XAPK in input directory: {input_source}")

    # Priority 2: Use provided local file
    if input_source and os.path.isfile(input_source):
        print(f"Using local XAPK: {input_source}")
        shutil.copy2(input_source, xapk_path)
    # Priority 3: Download from custom URL
    elif input_source and input_source.startswith(("http://", "https://")):
        print(f"Downloading from custom URL: {input_source}")
        download_file(input_source, xapk_path)
    # Priority 4: Query APKPure API directly (CDN link)
    else:
        print("Querying APKPure mobile API for direct CDN link...")
        cdn_url, api_ver_name, api_ver_code = get_apkpure_download_info(DEFAULT_PACKAGE)
        print(f"APKPure latest version: {api_ver_name} ({api_ver_code})")
        download_file(cdn_url, xapk_path)

    # Extract XAPK
    extract_dir = os.path.join(work_dir, "extracted")
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(xapk_path, 'r') as zf:
        zf.extractall(extract_dir)

    manifest_path = os.path.join(extract_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        raise FileNotFoundError(f"manifest.json not found in XAPK: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    package_name = manifest.get("package_name", "game.qualiarts.hololive.dreams.com")
    version_name = manifest.get("version_name", "1.0.0")
    version_code = manifest.get("version_code", "0")
    print(f"Target: {package_name} | Version Name: {version_name} | Version Code: {version_code}")

    # Identify base APK and split APKs
    base_apk_name = f"{package_name}.apk"
    base_apk_path = os.path.join(extract_dir, base_apk_name)
    if not os.path.isfile(base_apk_path):
        # Fallback to search in manifest split_apks
        for sp in manifest.get("split_apks", []):
            if sp.get("id") == "base":
                base_apk_name = sp.get("file")
                base_apk_path = os.path.join(extract_dir, base_apk_name)
                break

    if not os.path.isfile(base_apk_path):
        raise FileNotFoundError(f"Base APK not found in XAPK: {base_apk_name}")

    split_apk_paths = [
        os.path.join(extract_dir, f)
        for f in os.listdir(extract_dir)
        if f.endswith(".apk") and f != base_apk_name
    ]

    print(f"Base APK: {base_apk_name}")
    print(f"Split APKs: {[os.path.basename(p) for p in split_apk_paths]}")

    # Patch Base APK
    patched_base_apk = os.path.join(work_dir, "base_patched.apk")
    actions = patch_apk(base_apk_path, patched_base_apk)
    print("Patched methods:")
    for a in actions:
        print(f"  + {a}")

    # Build Standalone Merged APK
    merged_apk_unsigned = os.path.join(work_dir, "merged_unsigned.apk")
    print("Merging split APKs into standalone APK...")
    merge_split_apks(patched_base_apk, split_apk_paths, merged_apk_unsigned)

    # Cosmetic names
    if not re.fullmatch(r"0\.1(?:\.[1-9][0-9]*)?-beta", args.patch_version):
        raise ValueError("Patch version must be 0.1-beta or 0.1.X-beta (X >= 1)")
    cosmetic_base = f"hololive-dreams-{version_name}-{args.patch_version}"
    output_standalone_apk = os.path.join(args.dist_dir, f"{cosmetic_base}.apk")
    output_xapk = os.path.join(args.dist_dir, f"{cosmetic_base}.xapk")

    # Sign standalone APK
    print(f"Creating signed standalone APK: {output_standalone_apk}...")
    zipalign_and_sign(
        merged_apk_unsigned,
        output_standalone_apk,
        keystore_path=args.keystore,
        key_pass=args.keystore_pass,
        key_alias=args.keystore_alias
    )

    # Sign individual APKs for XAPK repacking
    signed_base_apk = os.path.join(work_dir, base_apk_name)
    zipalign_and_sign(
        patched_base_apk,
        signed_base_apk,
        keystore_path=args.keystore,
        key_pass=args.keystore_pass,
        key_alias=args.keystore_alias
    )

    signed_splits = []
    for split_path in split_apk_paths:
        fname = os.path.basename(split_path)
        stripped_split = os.path.join(work_dir, f"stripped_{fname}")
        strip_apk_signatures(split_path, stripped_split)
        signed_split = os.path.join(work_dir, fname)
        zipalign_and_sign(
            stripped_split,
            signed_split,
            keystore_path=args.keystore,
            key_pass=args.keystore_pass,
            key_alias=args.keystore_alias
        )
        signed_splits.append(signed_split)

    # Repack XAPK
    print(f"Repacking XAPK: {output_xapk}...")
    with zipfile.ZipFile(output_xapk, 'w', compression=zipfile.ZIP_STORED) as out_xapk:
        out_xapk.write(manifest_path, "manifest.json")
        out_xapk.write(signed_base_apk, base_apk_name)
        for s in signed_splits:
            out_xapk.write(s, os.path.basename(s))

    print("\nSUCCESS! Generated artifacts:")
    print(f"  1. Standalone Universal APK: {output_standalone_apk} ({os.path.getsize(output_standalone_apk) / (1024*1024):.1f} MB)")
    print(f"  2. Signed Repacked XAPK:     {output_xapk} ({os.path.getsize(output_xapk) / (1024*1024):.1f} MB)")

    # Set GitHub Actions output environment variables if running in CI
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write(f"package_name={package_name}\n")
            f.write(f"version_name={version_name}\n")
            f.write(f"version_code={version_code}\n")
            f.write(f"tag_name={args.patch_version}\n")
            f.write(f"release_title=hololive Dreams patch {args.patch_version} (game {version_name})\n")
            f.write(f"standalone_apk={output_standalone_apk}\n")
            f.write(f"repacked_xapk={output_xapk}\n")


if __name__ == "__main__":
    main()
