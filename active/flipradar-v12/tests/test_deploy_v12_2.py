import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PKG=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('v12_deploy_under_test',PKG/'deploy_v12.py')
deploy=importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)

class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='v12-2-')
        self.addCleanup(self.tmp.cleanup)
        self.d=Path(self.tmp.name)
        self.root=self.d/'v12';self.root.mkdir()
        self.overlay=self.d/'overlay';self.overlay.mkdir()
        self.entry=self.overlay/'flip_v2_overlay_dev.py'
        self.entry.write_text('app = object()\n')
        (self.root/'v12_bridge.py').write_text('# actual bridge fixture\n')
        self.dist=self.root/'dist'; self.dist.mkdir()
        for name in ('index.html','account.html'):
            (self.dist/name).write_text('<html>FlipRadar original</html>')
        j=(self.dist/'_expo/static/js/web');j.mkdir(parents=True)
        (j/'bundle.js').write_text('a'*2000)
        with sqlite3.connect(self.overlay/'data.sqlite3') as conn:
            conn.execute('CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)')
            conn.execute("INSERT INTO users(name) VALUES('keep')")
        self.snapshot=(self.overlay/'data.sqlite3').read_bytes()
        self.patches=[
            patch.object(deploy,'ROOT',self.root),
            patch.object(deploy,'DIST',self.dist),
            patch.object(deploy,'OVERLAY',self.overlay),
            patch.object(deploy,'ENTRY',self.entry),
            patch.object(deploy,'BACKUPS',self.overlay/'backups'),
            patch.object(deploy,'FLAG',self.overlay/'.v12_live'),
            patch.object(deploy,'_prepublish_check',return_value=None),
            patch.object(deploy,'_wait',return_value=True),
        ]
        for p in self.patches:p.start();self.addCleanup(p.stop)

    def test_original_root_and_csp_static_contract(self):
        source=(PKG/'v12_bridge.py').read_text()
        self.assertIn("if path == '/':\n            return _asset('index.html')",source)
        self.assertIn('Content-Security-Policy',source)
        self.assertIn("'/admin/uzytkownicy'",source)
        self.assertIn("'/rejestracja'",source)

    def test_successful_publish_preserves_data_and_publishes_code(self):
        with patch.object(deploy,'run',return_value=None) as run:
            deploy.publish()
        self.assertIn('install_v12_original(app)',self.entry.read_text())
        self.assertTrue(deploy.FLAG.is_file())
        self.assertEqual((self.overlay/'v12_bridge.py').read_text(),'# actual bridge fixture\n')
        self.assertEqual((self.overlay/'data.sqlite3').read_bytes(),self.snapshot)
        self.assertTrue((self.root/'last_backup').exists())
        self.assertEqual(run.call_count,1)
        with patch.object(deploy,'run',return_value=None):
            deploy.rollback()
        self.assertFalse(deploy.FLAG.exists())

    def test_restart_failure_rolls_back_without_touching_data(self):
        original=self.entry.read_text()
        calls=[]
        def fake_run(command,**kw):
            calls.append(command)
            if len(calls)==1: raise RuntimeError('simulated restart failure')
        with patch.object(deploy,'run',side_effect=fake_run):
            with self.assertRaisesRegex(RuntimeError,'simulated'):
                deploy.publish()
        self.assertEqual(self.entry.read_text(),original)
        self.assertFalse(deploy.FLAG.exists())
        self.assertFalse((self.overlay/'v12_bridge.py').exists())
        self.assertEqual((self.overlay/'data.sqlite3').read_bytes(),self.snapshot)
        self.assertEqual(len(calls),2)

    def test_missing_preview_stops_before_changes(self):
        with patch.object(deploy,'_wait',return_value=False), patch.object(deploy,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'Podglad'):
                deploy.publish()
            run.assert_not_called()
        self.assertEqual(self.entry.read_text(),'app = object()\n')
        self.assertFalse(deploy.FLAG.exists())

if __name__=='__main__': unittest.main(verbosity=2)
