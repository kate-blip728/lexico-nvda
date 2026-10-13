import importlib.util
from pathlib import Path
import queue
import threading
import unittest

spec = importlib.util.spec_from_file_location('liveSpeech', Path(__file__).parents[1] / 'addon/globalPlugins/lexico/liveSpeech.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class LiveSpeechChecks(unittest.TestCase):
    def setUp(self):
        self.jobs = queue.Queue()
        self.spoken = []
        self.calls = []
        def translate(text, language):
            self.calls.append((text, language))
            return 'translated:' + text
        self.controller = module.SpeechTranslator(translate, lambda fn, *args: self.jobs.put((fn, args)), self.spoken.append, lambda text: None)
        self.addCleanup(self.controller.close)
    def flush(self):
        fn, args = self.jobs.get(timeout=2)
        fn(*args)
    def test_toggle_translates_preserves_commands_and_caches(self):
        marker = object()
        self.controller.toggle('inglés')
        self.assertEqual(self.controller.filter(['hola', marker]), [])
        self.flush()
        self.assertEqual(self.spoken, [['translated:hola', marker]])
        self.controller.filter(['hola'])
        self.flush()
        self.assertEqual(len(self.calls), 1)
    def test_cancel_discards_late_result(self):
        self.controller.toggle('inglés')
        self.controller.filter(['hola'])
        fn, args = self.jobs.get(timeout=2)
        self.controller.cancel()
        fn(*args)
        self.assertEqual(self.spoken, [])
    def test_off_protected_and_internal_bypass(self):
        original = ['hola']
        self.assertIs(self.controller.filter(original), original)
        self.controller.toggle('inglés')
        self.assertIs(self.controller.filter(original, protected=True), original)
        self.controller.internal = True
        self.assertIs(self.controller.filter(original), original)
        self.assertEqual(self.calls, [])
    def test_error_disables_and_reads_original(self):
        self.controller.translate = lambda *args: (_ for _ in ()).throw(OSError())
        self.controller.toggle('inglés')
        self.controller.filter(['hola'])
        self.flush()
        self.assertFalse(self.controller.enabled)
        self.assertEqual(self.spoken, [['hola']])
    def test_disabling_discards_late_result(self):
        self.controller.toggle('inglés')
        self.controller.filter(['hola'])
        fn, args = self.jobs.get(timeout=2)
        self.controller.toggle('inglés')
        fn(*args)
        self.assertEqual(self.spoken, [])
