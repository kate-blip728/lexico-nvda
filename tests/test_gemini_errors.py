import io
import json
import socket
import ssl
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from test_services import services

class GeminiErrors(unittest.TestCase):
    def test_http_reasons_are_safe_and_actionable(self):
        for code, reason, expected in [(400, 'API_KEY_INVALID', 'clave'),
                (403, 'SERVICE_DISABLED', 'deshabilitada'),
                (403, 'API_KEY_HTTP_REFERRER_BLOCKED', 'restricciones'),
                (402, '', 'facturación'), (429, '', 'cuota'), (503, '', 'saturado')]:
            body = {'error': {'message': 'secret-key private text', 'details': [{'reason': reason}]}}
            error = HTTPError('secret-key', code, 'secret-key', {}, io.BytesIO(json.dumps(body).encode()))
            with self.subTest(code=code), patch.object(services, 'urlopen', side_effect=error):
                with self.assertRaises(services.ServiceError) as raised:
                    services.translate('Hola', 'inglés', 'secret-key', 'test')
                message = str(raised.exception)
                self.assertIn(expected, message)
                self.assertIn('HTTP ' + str(code), message)
                self.assertNotIn('secret-key', message)
                self.assertNotIn('private text', message)

    def test_network_failures_are_distinct(self):
        for reason, expected in [(socket.gaierror(), 'DNS'), (ssl.SSLCertVerificationError(), 'TLS'),
                                 (TimeoutError(), 'tiempo de espera')]:
            with self.subTest(expected=expected), patch.object(services, 'urlopen', side_effect=URLError(reason)):
                with self.assertRaises(services.ServiceError) as raised:
                    services.translate('Hola', 'inglés', 'key', 'test')
                self.assertIn(expected, str(raised.exception))

    def test_key_whitespace_and_new_model_payload(self):
        response = json.dumps({'candidates': [{'content': {'parts': [{'text': 'Hello'}]}}]})
        with patch.object(services, 'request', return_value=response) as request:
            services.translate('Hola', 'inglés', ' key ', ' models/gemini-3.5-flash-lite ')
            args = request.call_args.args
            self.assertEqual(args[2], 'key')
            self.assertNotIn('generationConfig', args[1])
            self.assertIn('/gemini-3.5-flash-lite:', args[0])
        with patch.object(services, 'urlopen') as opener:
            with self.assertRaises(services.ServiceError):
                services.translate('Hola', 'inglés', 'key\nother', 'test')
            opener.assert_not_called()
