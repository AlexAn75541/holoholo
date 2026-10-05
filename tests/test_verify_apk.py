import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.verify_apk import verify

BADGING = "package: name='game.qualiarts.hololive.dreams.com' versionCode='1790677758' versionName='1.2.1'\n"
SIGNATURE = 'Verified using v2 scheme (APK Signature Scheme v2): true\n'


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
            for name in ('AndroidManifest.xml', 'classes.dex',
                         'lib/arm64-v8a/libunity.so', 'assets/aa/Android/game.bundle'):
                archive.writestr(name, 'sample')

    def test_static_checks_pass_with_required_sdk_tools(self):
        def output(*argv):
            if 'badging' in argv:
                return BADGING
            if 'xmltree' in argv:
                return 'E: manifest\n  A: android:requiredSplitTypes(0x0101064e)=""\n'
            if 'apksigner' in argv:
                return SIGNATURE
            return ''

        with patch('scripts.verify_apk.shutil.which', return_value='/sdk/tool'), \
             patch('scripts.verify_apk.command', side_effect=output):
            verify(self.apk, self.manifest)

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

    def test_wrong_package_blocks(self):
        self.manifest.write_text(json.dumps({'package_name': 'unexpected'}))
        with self.assertRaisesRegex(ValueError, 'unexpected source package'):
            verify(self.apk, self.manifest)


if __name__ == '__main__':
    unittest.main()
