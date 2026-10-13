import json
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs
from test_services import services, storage

class GoogleChecks(unittest.TestCase):
    def test_translation_no_key_and_correct_target(self):
        with patch.object(services, 'request', return_value=json.dumps({'sentences': [{'trans': 'Hello'}, {'trans': '!'}]})) as request:
            self.assertEqual(services.google_translate('Hola', 'inglés'), 'Hello!')
            args = request.call_args.args
            self.assertEqual(len(args), 1)
            query = parse_qs(urlsplit(args[0]).query)
            self.assertEqual(query['tl'], ['en'])
            self.assertEqual(query['q'], ['Hola'])
    def test_chunks_preserve_all_input(self):
        inputs, updates = [], []
        def request(url):
            chunk = parse_qs(urlsplit(url).query, keep_blank_values=True)['q'][0]
            inputs.append(chunk)
            return json.dumps({'sentences': [{'trans': chunk}]})
        text = 'Una frase. ' * 220
        with patch.object(services, 'request', side_effect=request):
            self.assertEqual(services.google_translate(text, 'en', updates.append), text)
        self.assertEqual(''.join(inputs), text)
        self.assertTrue(all(len(chunk) <= 1000 for chunk in inputs))
        self.assertEqual(updates[-1], text)
    def test_provider_persists_and_old_settings_preserve_gemini(self):
        with tempfile.TemporaryDirectory() as directory:
            store = storage.Store(directory)
            store.save('inglés', 'test', '', provider='Google Translate')
            self.assertEqual(storage.Store(directory).values['provider'], 'Google Translate')
            data = json.loads(store.path.read_text(encoding='utf-8'))
            del data['provider']
            store.path.write_text(json.dumps(data), encoding='utf-8')
            self.assertEqual(storage.Store(directory).values['provider'], 'Gemini')
    def test_bad_response_and_language(self):
        with patch.object(services, 'request', return_value='{}'):
            with self.assertRaises(services.ServiceError):
                services.google_translate('Hola', 'inglés')
        with self.assertRaises(services.ServiceError):
            services.google_translate('Hola', 'idioma inexistente')
