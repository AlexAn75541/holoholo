import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.verify_apk import verify
from scripts.patcher import merge_split_apks, resolve_patch_version

BADGING = "package: name='game.qualiarts.hololive.dreams.com' versionCode='1790677758' versionName='1.2.1'\n"
SIGNATURE = 'Verified using v3 scheme (APK Signature Scheme v3): true\n'


class VerifyApkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.apk = self.root / 'game.apk'
        self.manifest = self.root / 'manifest.json'
        self.manifest.write_text(json.dumps({
            'package_name': 'game.qualiarts.hololive.dreams.com',
            'version_code': '1790677758',
            'version_name': '1.2.1',
        }))
        with zipfile.ZipFile(self.apk, 'w') as archive:
            for name in ('AndroidManifest.xml', 'classes.dex', 'resources.arsc',
                         'lib/arm64-v8a/libunity.so', 'assets/aa/Android/game.bundle'):
                archive.writestr(name, 'sample')

    def test_static_checks_pass_with_required_sdk_tools(self):
        def output(*argv):
            if 'badging' in argv:
                return BADGING
            if 'xmltree' in argv:
                return 'E: manifest\n  A: android:requiredSplitTypes(0x0101064e)="" (Raw: "")\n'
            if 'apksigner' in argv:
                return SIGNATURE
            return ''

        with patch('scripts.verify_apk.shutil.which', return_value='/sdk/tool'), \
             patch('scripts.verify_apk.command', side_effect=output):
            verify(self.apk, self.manifest)

    def test_compressed_resource_table_blocks(self):
        with zipfile.ZipFile(self.apk, 'w') as archive:
            for name in ('AndroidManifest.xml', 'classes.dex',
                         'lib/arm64-v8a/libunity.so', 'assets/aa/Android/game.bundle'):
                archive.writestr(name, 'sample')
            archive.writestr('resources.arsc', 'sample', compress_type=zipfile.ZIP_DEFLATED)
        with patch('scripts.verify_apk.shutil.which', return_value='/sdk/tool'):
            with self.assertRaisesRegex(ValueError, 'resources.arsc'):
                verify(self.apk, self.manifest)

    def test_merged_apk_stores_resource_table(self):
        base = self.root / 'base.apk'
        output = self.root / 'merged.apk'
        with zipfile.ZipFile(base, 'w') as archive:
            archive.writestr('resources.arsc', b'resources', compress_type=zipfile.ZIP_DEFLATED)
            archive.writestr('AndroidManifest.xml', b'manifest')
        with patch('scripts.patcher.clean_manifest_for_standalone', side_effect=lambda data: data):
            merge_split_apks(str(base), [], str(output))
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(archive.getinfo('resources.arsc').compress_type, zipfile.ZIP_STORED)

    def test_missing_tool_blocks(self):
        with patch('scripts.verify_apk.shutil.which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'missing required'):
                verify(self.apk, self.manifest)

    def test_nonempty_required_split_blocks(self):
        with patch('scripts.verify_apk.shutil.which', return_value='/sdk/tool'), \
             patch('scripts.verify_apk.command', side_effect=[
                 BADGING, 'E: manifest\n  A: android:requiredSplitTypes="base__abi"\n']):
            with self.assertRaisesRegex(ValueError, 'split types'):
                verify(self.apk, self.manifest)

    def test_missing_signature_blocks(self):
        with patch('scripts.verify_apk.shutil.which', return_value='/sdk/tool'), \
             patch('scripts.verify_apk.command', side_effect=[
                 BADGING, 'E: manifest\n', '',
                 'Verified using v2 scheme (APK Signature Scheme v2): false\n'
             ]):
            with self.assertRaisesRegex(ValueError, 'neither APK Signature Scheme'):
                verify(self.apk, self.manifest)

    def test_wrong_package_blocks(self):
        self.manifest.write_text(json.dumps({'package_name': 'unexpected'}))
        with self.assertRaisesRegex(ValueError, 'unexpected source package'):
            verify(self.apk, self.manifest)

    def test_resolve_patch_version(self):
        self.assertEqual(resolve_patch_version(None, '1.2.1'), '1.2.1-patched-1')
        self.assertEqual(resolve_patch_version('1', '1.2.1'), '1.2.1-patched-1')
        self.assertEqual(resolve_patch_version('2', '1.2.1'), '1.2.1-patched-2')
        self.assertEqual(resolve_patch_version('1.2.1-patched-1', '1.2.1'), '1.2.1-patched-1')
        with self.assertRaises(ValueError):
            resolve_patch_version('0.3-beta', '1.2.1')
        with self.assertRaises(ValueError):
            resolve_patch_version('bad', '1.2.1')


if __name__ == '__main__':
    unittest.main()
