#!/usr/bin/env python3
"""Fail-closed static checks for the single arm64 release APK."""
import argparse
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

PACKAGE = 'game.qualiarts.hololive.dreams.com'


def command(*argv):
    result = subprocess.run(argv, check=True, text=True, capture_output=True)
    return result.stdout


def verify(apk: Path, source_manifest: Path):
    expected = json.loads(source_manifest.read_text(encoding='utf-8'))
    if expected['package_name'] != PACKAGE:
        raise ValueError('unexpected source package')
    for tool in ('aapt', 'apksigner', 'zipalign'):
        if not shutil.which(tool):
            raise RuntimeError(f'missing required Android SDK tool: {tool}')

    with zipfile.ZipFile(apk) as archive:
        if archive.testzip() is not None:
            raise ValueError('corrupt APK ZIP member')
        names = archive.namelist()
        if len(names) != len(set(names)) or 'AndroidManifest.xml' not in names or 'classes.dex' not in names:
            raise ValueError('missing or duplicate APK entry')
        if 'resources.arsc' not in names or archive.getinfo('resources.arsc').compress_type != zipfile.ZIP_STORED:
            raise ValueError('resources.arsc must be stored uncompressed for target SDK 30+')
        libs = [name for name in names if name.startswith('lib/') and name.endswith('.so')]
        if not libs or any(not name.startswith('lib/arm64-v8a/') for name in libs):
            raise ValueError('missing or unexpected native architecture')
        if not any(name.startswith('assets/aa/Android/') for name in names):
            raise ValueError('Unity asset pack not merged')

    badging = command('aapt', 'dump', 'badging', str(apk))
    match = re.search(r"^package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", badging, re.M)
    if not match or match.groups() != (PACKAGE, str(expected['version_code']), str(expected['version_name'])):
        raise ValueError(f'APK package/version differs from source: {match.groups() if match else "missing"}')

    xml = command('aapt', 'dump', 'xmltree', str(apk), 'AndroidManifest.xml')
    if re.search(r'android:requiredSplitTypes[^\n]*"[^"\n]+"', xml):
        raise ValueError('manifest still requires missing split types')
    if re.search(r'com\.android\.vending\.(?:splits(?:\.required)?|derived\.apk\.id)', xml):
        raise ValueError('manifest still declares Play split metadata')
    if re.search(r'^\s*A: split=', xml, re.M):
        raise ValueError('output is a split, not a standalone APK')

    command('zipalign', '-c', '-P', '16', '4', str(apk))
    signature = command('apksigner', 'verify', '--min-sdk-version', '36', '--verbose', str(apk))
    if 'Verified using v2 scheme (APK Signature Scheme v2): true' not in signature:
        raise ValueError('APK Signature Scheme v2 not verified')
    print(f'Static APK checks passed: {apk.name} (not device-install or gameplay proof)')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('apk', type=Path)
    parser.add_argument('source_manifest', type=Path)
    args = parser.parse_args()
    verify(args.apk, args.source_manifest)


if __name__ == '__main__':
    main()
