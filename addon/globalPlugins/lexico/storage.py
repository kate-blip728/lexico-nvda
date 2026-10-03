"""Persist preferences and protect the API key with Windows user-bound DPAPI."""
import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path

RECOMMENDED_MODEL = 'gemini-3.5-flash-lite'
MODELS = [RECOMMENDED_MODEL, 'gemini-3.8-flash', 'gemini-3.5-flash', 'gemini-3.1-flash-lite']
LANGUAGES = ['español', 'inglés', 'francés', 'alemán', 'italiano', 'portugués',
             'catalán', 'gallego', 'euskera', 'árabe', 'búlgaro', 'checo', 'chino simplificado',
             'chino tradicional', 'coreano', 'danés', 'finés', 'griego', 'hebreo', 'hindi',
             'húngaro', 'indonesio', 'japonés', 'neerlandés', 'noruego', 'polaco', 'rumano',
             'ruso', 'sueco', 'tailandés', 'turco', 'ucraniano', 'vietnamita']
SPELL_LANGUAGES = ['es-ES', 'es-MX', 'en-US', 'en-GB', 'fr-FR', 'de-DE', 'it-IT', 'pt-PT', 'pt-BR', 'ca-ES']
DEFAULTS = {'language': 'inglés', 'model': RECOMMENDED_MODEL, 'key': '', 'spelling_language': 'es-ES'}

class Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]

def crypt(data, decrypt=False):
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    library = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if decrypt:
        function = library.CryptUnprotectData
        second = None
    else:
        function = library.CryptProtectData
        second = 'Léxico Gemini'
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p if decrypt else wintypes.LPCWSTR,
                         ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), second, None, None, None, 1, ctypes.byref(target)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(ctypes.cast(target.data, ctypes.c_void_p))

class Store:
    def __init__(self, directory):
        self.path = Path(directory) / 'lexico-settings.json'
        self.values = DEFAULTS.copy()
        self.warning = ''
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding='utf-8'))
                for name in ('language', 'model', 'spelling_language'):
                    if isinstance(raw.get(name), str):
                        self.values[name] = raw[name]
                if raw.get('protectedKey'):
                    self.values['key'] = crypt(base64.b64decode(raw['protectedKey']), True).decode('utf-8')
            except (OSError, ValueError, TypeError, UnicodeError):
                self.warning = 'No se pudo leer la configuración o descifrar la clave. Revisa las opciones de Léxico.'
    def save(self, language, model, key, spelling_language='es-ES'):
        raw = {'language': language, 'model': model, 'spelling_language': spelling_language,
               'protectedKey': base64.b64encode(crypt(key.encode('utf-8'))).decode('ascii') if key else ''}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temporary, self.path)
        self.values = {'language': language, 'model': model, 'key': key, 'spelling_language': spelling_language}
        self.warning = ''
