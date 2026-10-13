import json
import unittest
from test_services import services

def event(text='', finish=None, thought=False):
    candidate = {'content': {'parts': [{'text': text, 'thought': thought}]}}
    if finish:
        candidate['finishReason'] = finish
    return ('data: ' + json.dumps({'candidates': [candidate]}) + '\n\n').encode()

class StreamChecks(unittest.TestCase):
    def test_incremental_text_without_thoughts(self):
        updates = []
        result = json.loads(services.read_stream(iter([event('internal', thought=True), event('Good '), event('morning', 'STOP')]), updates.append))
        self.assertEqual(updates, ['Good ', 'Good morning'])
        self.assertEqual(result['candidates'][0]['finishReason'], 'STOP')
        self.assertNotIn('internal', json.dumps(result))
    def test_incomplete_stream_is_not_success(self):
        with self.assertRaises(services.ServiceError):
            services.read_stream(iter([event('Partial')]), lambda text: None)
    def test_stream_error_does_not_expose_server_message(self):
        with self.assertRaises(services.ServiceError) as raised:
            services.read_stream(iter([b'data: {"error":{"message":"secret-key"}}\n']), lambda text: None)
        self.assertNotIn('secret-key', str(raised.exception))
    def test_non_stop_reason_preserved(self):
        result = json.loads(services.read_stream(iter([event('Partial', 'MAX_TOKENS')]), lambda text: None))
        self.assertEqual(result['candidates'][0]['finishReason'], 'MAX_TOKENS')
