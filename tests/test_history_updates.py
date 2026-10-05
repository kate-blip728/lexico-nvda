import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from test_services import load

history = load('history')
updates = load('updates')
storage = load('storage')

class HistoryChecks(unittest.TestCase):
    def test_persists_original_result_and_evicts_oldest(self):
        with tempfile.TemporaryDirectory() as directory:
            store = history.History(directory)
            for i in range(3):
                store.add('Traducción', str(i), 'resultado ' + str(i), 2, 'español', 'modelo')
            reopened = history.History(directory)
            self.assertEqual([e['text'] for e in reopened.entries], ['2', '1'])
            self.assertEqual(reopened.entries[0]['result'], 'resultado 2')
            reopened.trim(0)
            reopened.add('Pregunta', 'hola', 'respuesta', 0)
            self.assertEqual(history.History(directory).entries, [])
    def test_corrupt_file_does_not_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'lexico-history.json').write_text('{', encoding='utf-8')
            store = history.History(directory)
            self.assertEqual(store.entries, [])
            self.assertTrue(store.warning)
    def test_failed_save_keeps_previous_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            store = history.History(directory)
            store.add('DLE', 'uno', 'resultado', 10)
            with patch.object(history.os, 'replace', side_effect=OSError('disk')):
                with self.assertRaises(OSError):
                    store.add('DLE', 'dos', 'resultado', 10)
            self.assertEqual(store.entries[0]['text'], 'uno')
    def test_limit_persists_and_old_settings_migrate(self):
        with tempfile.TemporaryDirectory() as directory:
            store = storage.Store(directory)
            self.assertEqual(store.values['history_limit'], 100)
            store.save('español', 'modelo', '', history_limit=5)
            self.assertEqual(storage.Store(directory).values['history_limit'], 5)
            with self.assertRaises(ValueError):
                store.save('español', 'modelo', '', history_limit=-1)

class UpdateChecks(unittest.TestCase):
    def test_version_comparison_and_filename_rejection(self):
        data = dict(version='0.10.0', filename='lexico-0.10.0.nvda-addon', sha256='a'*64)
        with patch.object(updates, 'fetch', return_value=json.dumps(data).encode()):
            self.assertEqual(updates.check(), data)
        data['filename'] = '../evil'
        with patch.object(updates, 'fetch', return_value=json.dumps(data).encode()):
            with self.assertRaises(ValueError):
                updates.check()
        with patch.object(updates, 'fetch', return_value=b'{"version":"0.4.0"}'):
            self.assertIsNone(updates.check())
    def test_hash_and_manifest_verified(self):
        buffer = io.BytesIO()
        with ZipFile(buffer, 'w') as archive:
            archive.writestr('manifest.ini', 'name = lexico\nversion = 0.5.0\n')
        data = buffer.getvalue()
        meta = dict(version='0.5.0', filename='lexico-0.5.0.nvda-addon', sha256=hashlib.sha256(data).hexdigest())
        with tempfile.TemporaryDirectory() as directory, patch.object(updates, 'fetch', return_value=data):
            self.assertTrue(updates.download(meta, directory).exists())
            meta['sha256'] = '0'*64
            with self.assertRaises(ValueError):
                updates.download(meta, directory)
            meta['sha256'] = hashlib.sha256(data).hexdigest()
            meta['version'] = '0.6.0'
            with self.assertRaises(ValueError):
                updates.download(meta, directory)
