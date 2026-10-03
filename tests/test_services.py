import importlib.util
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

root = Path(__file__).resolve().parents[1]
def load(name):
    spec = importlib.util.spec_from_file_location(name, root / 'addon/globalPlugins/lexico' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
services = load('services')
storage = load('storage')
spelling = load('spelling')

class Checks(unittest.TestCase):
    def test_translation_echo_retries_and_returns_translation(self):
        def response(text):
            return json.dumps({'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': text}]}}]})
        with patch.object(services, 'request', side_effect=[response('Hola'), response('Hello')]) as request:
            self.assertEqual(services.translate('Hola', 'inglés', 'key', 'test'), 'Hello')
            self.assertEqual(request.call_count, 2)
    def test_repeated_echo_reports_target_language(self):
        response = json.dumps({'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'Hola'}]}}]})
        with patch.object(services, 'request', return_value=response) as request:
            with self.assertRaises(services.ServiceError) as error:
                services.translate('Hola', 'inglés', 'key', 'test')
            self.assertIn('sin cambios', str(error.exception))
            self.assertIn('inglés', str(error.exception))
            self.assertEqual(request.call_count, 2)
    def test_utf16_spelling_positions_preserve_emoji(self):
        text = '😀 una prueva.'
        error = {'start': 7, 'length': 6}
        self.assertEqual(spelling.utf16_slice(text, 7, 6), 'prueva')
        self.assertEqual(spelling.apply_change(text, error, 'prueba'), '😀 una prueba.')
    def test_delete_only_selected_occurrence(self):
        text = 'una una prueba'
        error = {'start': 4, 'length': 4}
        self.assertEqual(spelling.apply_change(text, error, ''), 'una prueba')
    def test_question_uses_separate_instruction(self):
        payloads = []
        def request(url, data=None, key=None):
            payloads.append(data)
            return json.dumps({'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'Explicación.'}]}}]})
        with patch.object(services, 'request', request):
            result = services.ask('¿Cuándo se escribe por qué?', 'key', 'gemini-3.5-flash-lite')
        self.assertEqual(result, 'Explicación.')
        self.assertIn('dudas gramaticales', payloads[0]['systemInstruction']['parts'][0]['text'])
        self.assertEqual(payloads[0]['contents'][0]['parts'][0]['text'], '¿Cuándo se escribe por qué?')
    def test_spelling_language_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            storage.Store(directory).save('inglés', storage.RECOMMENDED_MODEL, '', 'es-MX')
            self.assertEqual(storage.Store(directory).values['spelling_language'], 'es-MX')
    def test_dictionary_relations_per_sense(self):
        response = {'ok': True, 'data': {'word': 'bueno', 'meanings': [{'senses': [
            {'meaning_number': 1, 'description': 'De valor positivo', 'synonyms': ['bondadoso'], 'antonyms': ['malo']},
            {'meaning_number': 2, 'description': 'Otra acepción', 'synonyms': None, 'antonyms': None}]}]}}
        with patch.object(services, 'request', return_value=json.dumps(response)):
            result = services.lookup('bueno')
        self.assertIn('Sinónimos: bondadoso', result)
        self.assertIn('Antónimos: malo', result)
        self.assertIn('Antónimos: no se indican', result)
        self.assertIn('no oficial', result)
    def test_unknown_word(self):
        with patch.object(services, 'request', return_value='{"ok":true,"data":{"meanings":[]}}'):
            with self.assertRaises(services.ServiceError):
                services.lookup('xxxx')
    def test_translation_payload_and_key_header(self):
        captured = {}
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size):
                return json.dumps({'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'Hello'}]}}]}).encode()
        def opener(req, timeout):
            captured['req'] = req
            return Response()
        with patch.object(services, 'urlopen', opener):
            result = services.translate('Hola', 'inglés', 'test-key', 'gemini-3.5-flash')
        req = captured['req']
        self.assertEqual(result, 'Hello')
        self.assertNotIn('test-key', req.full_url)
        self.assertEqual(req.get_header('X-goog-api-key'), 'test-key')
        self.assertEqual(json.loads(req.data)['contents'][0]['parts'][0]['text'], 'Hola')
    def test_translation_not_complete(self):
        response = {'candidates': [{'finishReason': 'MAX_TOKENS', 'content': {'parts': [{'text': 'partial'}]}}]}
        with patch.object(services, 'request', return_value=json.dumps(response)):
            with self.assertRaises(services.ServiceError):
                services.translate('Hola', 'inglés', 'key', 'gemini-3.5-flash')
    def test_translation_preconditions(self):
        for text, key, model in [('hola', '', 'test'), ('', 'key', 'test'), ('a' * 30001, 'key', 'test'), ('hola', 'key', '../test')]:
            with self.assertRaises(services.ServiceError):
                services.translate(text, 'inglés', key, model)
    def test_quota_error_does_not_expose_key(self):
        with patch.object(services, 'urlopen', side_effect=HTTPError('url', 429, 'secret-key', {}, None)):
            with self.assertRaises(services.ServiceError) as error:
                services.translate('Hola', 'inglés', 'secret-key', 'test')
        self.assertNotIn('secret-key', str(error.exception))
        self.assertIn('límite', str(error.exception))
    def test_settings_survive_reload_and_key_not_plaintext(self):
        with tempfile.TemporaryDirectory() as directory:
            store = storage.Store(directory)
            def mock_crypt(data, decrypt=False):
                return b'private-test-key' if decrypt else b'encrypted-fixture'
            with patch.object(storage, 'crypt', mock_crypt):
                store.save('francés', 'gemini-3.5-flash', 'private-test-key')
                self.assertNotIn('private-test-key', store.path.read_text(encoding='utf-8'))
                reloaded = storage.Store(directory)
                self.assertEqual(reloaded.values, store.values)
                self.assertEqual(reloaded.warning, '')
    def test_real_settings_without_key(self):
        with tempfile.TemporaryDirectory() as directory:
            storage.Store(directory).save('alemán', 'gemini-3.5-flash', '')
            store = storage.Store(directory)
            self.assertEqual(store.values['language'], 'alemán')
            self.assertEqual(store.values['model'], 'gemini-3.5-flash')
    def test_native_windows_key_protection(self):
        try:
            protected = storage.crypt(b'test-key')
        except OSError as error:
            if error.winerror == 2:
                self.skipTest('DPAPI no tiene acceso al perfil de Windows en este entorno aislado.')
            raise
        self.assertEqual(storage.crypt(protected, True), b'test-key')
    def test_corrupt_settings_recover(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'lexico-settings.json').write_text('invalid', encoding='utf-8')
            store = storage.Store(directory)
            self.assertTrue(store.warning)
            self.assertEqual(store.values['key'], '')

if __name__ == '__main__':
    unittest.main()
