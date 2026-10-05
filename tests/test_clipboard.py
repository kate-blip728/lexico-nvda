"""Exercise the actual clipboard command methods with NVDA/UI boundaries simulated."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

source = Path(__file__).parents[1] / 'addon/globalPlugins/lexico/__init__.py'
tree = ast.parse(source.read_text(encoding='utf-8'))

def methods(class_name, names, namespace):
    node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    selected = [node for node in node.body if isinstance(node, ast.FunctionDef) and node.name in names]
    for node in selected:
        node.decorator_list = []
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), 'exec'), namespace)
    return {name: namespace[name] for name in names}

class ClipboardChecks(unittest.TestCase):
    def setUp(self):
        self.services = SimpleNamespace(translate=Mock(return_value='Hello'))
        self.api = SimpleNamespace(getClipData=Mock(return_value='Hola'))
        self.ui = SimpleNamespace(message=Mock())
        namespace = {'services': self.services, 'api': self.api, 'ui': self.ui}
        funcs = methods('Window', ['translate', 'translateText', 'translateClipboard'], namespace)
        self.window = SimpleNamespace(busy=False, input=SimpleNamespace(SetValue=Mock(), GetValue=Mock(return_value='texto antiguo')),
            plugin=SimpleNamespace(store=SimpleNamespace(values={'language': 'inglés', 'key': 'test-key', 'model': 'test-model'})),
            result=None)
        def run(operation, history=None):
            self.window.result = operation()
        self.window.run = run
        for name, function in funcs.items():
            setattr(self.window, name, function.__get__(self.window))
    def test_button_translates_clipboard_immediately(self):
        self.window.translateClipboard()
        self.services.translate.assert_called_once_with('Hola', 'inglés', 'test-key', 'test-model')
        self.assertEqual(self.window.result, 'Hello')
        self.window.input.GetValue.assert_not_called()
    def test_empty_clipboard_does_not_send_request(self):
        self.api.getClipData.return_value = '  '
        self.window.translateClipboard()
        self.services.translate.assert_not_called()
    def test_busy_does_not_overwrite_pending_text(self):
        self.window.busy = True
        self.window.translateClipboard()
        self.services.translate.assert_not_called()
        self.window.input.SetValue.assert_not_called()
    def test_global_gesture_dispatches_captured_text(self):
        callbacks = []
        namespace = {'wx': SimpleNamespace(CallAfter=lambda fn, *args: callbacks.append((fn, args))),
                     'api': self.api, 'ui': self.ui}
        funcs = methods('GlobalPlugin', ['script_translateClipboard', 'open'], namespace)
        plugin = SimpleNamespace(active=True, window=self.window)
        self.window.Raise = Mock()
        plugin.open = funcs['open'].__get__(plugin)
        funcs['script_translateClipboard'](plugin, None)
        self.api.getClipData.return_value = 'Otro texto'
        fn, args = callbacks[0]
        fn(*args)
        self.services.translate.assert_called_once_with('Hola', 'inglés', 'test-key', 'test-model')
        self.assertEqual(self.window.result, 'Hello')

if __name__ == '__main__':
    unittest.main()
