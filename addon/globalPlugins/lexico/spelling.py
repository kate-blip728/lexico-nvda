"""Windows Spell Checking API; no network calls or third-party dependencies."""
import ctypes as c
from ctypes import wintypes as w
import uuid

class SpellError(Exception):
    pass

P = c.c_void_p
U = w.ULONG
ole = c.OleDLL('ole32')
ole.CoInitializeEx.argtypes = [P, w.DWORD]
ole.CoInitializeEx.restype = c.c_long
ole.CoUninitialize.argtypes = []
ole.CoTaskMemFree.argtypes = [P]
ole.CoCreateInstance.argtypes = [P, P, w.DWORD, P, c.POINTER(P)]
ole.CoCreateInstance.restype = c.c_long

def call(ptr, index, types, *args):
    table = c.cast(ptr, c.POINTER(c.POINTER(P))).contents
    function = c.WINFUNCTYPE(c.c_long, P, *types)(table[index])
    status = function(ptr, *args)
    if status < 0:
        raise SpellError('Windows no pudo completar la revisión ortográfica (código ' + hex(status & 0xffffffff) + ').')
    return status

def release(ptr):
    if ptr:
        call(ptr, 2, [])

def string_values(enum):
    values = []
    try:
        for _ in range(100):
            value, fetched = P(), U()
            status = call(enum, 3, [U, c.POINTER(P), c.POINTER(U)], 1, c.byref(value), c.byref(fetched))
            if not fetched.value:
                break
            try:
                values.append(c.wstring_at(value))
            finally:
                ole.CoTaskMemFree(value)
            if status == 1:
                break
    finally:
        release(enum)
    return values

def utf16_slice(text, start, length):
    raw = text.encode('utf-16-le')
    return raw[start * 2:(start + length) * 2].decode('utf-16-le')

def apply_change(text, error, replacement):
    raw = text.encode('utf-16-le')
    start, end = error['start'] * 2, (error['start'] + error['length']) * 2
    return (raw[:start] + replacement.encode('utf-16-le') + raw[end:]).decode('utf-16-le')

def check(text, language='es-ES'):
    if not text.strip():
        raise SpellError('Escribe una palabra o un texto para revisar.')
    if len(text) > 30000:
        raise SpellError('Revisa una parte del texto: el límite es de 30.000 caracteres.')
    if '\x00' in text:
        raise SpellError('El texto contiene caracteres nulos que Windows no puede revisar.')
    initialized = ole.CoInitializeEx(None, 2)
    if initialized < 0:
        raise SpellError('No se pudo iniciar el corrector de Windows.')
    factory, checker, errors = P(), P(), P()
    try:
        clsid = c.create_string_buffer(uuid.UUID('7AB36653-1796-484B-BDFA-E74F1DB7C1DC').bytes_le)
        iid = c.create_string_buffer(uuid.UUID('8E018A9D-2415-4677-BF08-794EA61F94BB').bytes_le)
        status = ole.CoCreateInstance(clsid, None, 1, iid, c.byref(factory))
        if status < 0:
            raise SpellError('El corrector ortográfico de Windows no está disponible.')
        supported = w.BOOL()
        call(factory, 4, [w.LPCWSTR, c.POINTER(w.BOOL)], language, c.byref(supported))
        if not supported.value:
            raise SpellError('Windows no tiene un diccionario para ' + language + '. Instala las funciones de escritura de ese idioma en Configuración de Windows.')
        call(factory, 5, [w.LPCWSTR, c.POINTER(P)], language, c.byref(checker))
        call(checker, 4, [w.LPCWSTR, c.POINTER(P)], text, c.byref(errors))
        result = []
        for _ in range(30000):
            error = P()
            status = call(errors, 3, [c.POINTER(P)], c.byref(error))
            if not error:
                break
            try:
                start, length, action = U(), U(), c.c_int()
                for index, value in [(3, start), (4, length)]:
                    call(error, index, [c.POINTER(U)], c.byref(value))
                call(error, 5, [c.POINTER(c.c_int)], c.byref(action))
                if action.value == 0:
                    continue
                word = utf16_slice(text, start.value, length.value)
                suggestions = []
                if action.value == 2:
                    replacement = P()
                    call(error, 6, [c.POINTER(P)], c.byref(replacement))
                    if replacement:
                        try:
                            suggestions = [c.wstring_at(replacement)]
                        finally:
                            ole.CoTaskMemFree(replacement)
                elif action.value == 3:
                    suggestions = ['']
                else:
                    enum = P()
                    call(checker, 5, [w.LPCWSTR, c.POINTER(P)], word, c.byref(enum))
                    suggestions = string_values(enum)
                result.append({'start': start.value, 'length': length.value, 'word': word,
                               'suggestions': suggestions, 'action': action.value})
            finally:
                release(error)
            if status == 1:
                break
        return result
    finally:
        release(errors)
        release(checker)
        release(factory)
        ole.CoUninitialize()

def how_written(word, language='es-ES'):
    if len(word.strip().split()) != 1:
        raise SpellError('Escribe una sola palabra en Cómo se escribe.')
    errors = check(word, language)
    if not errors:
        return 'Windows no detecta errores en «' + word + '». Esto no garantiza que sea la palabra adecuada en cada contexto.'
    return '\n'.join('Palabra: ' + error['word'] + '\nSugerencias: ' +
        (', '.join(error['suggestions']) or 'Windows no ofrece sugerencias.') for error in errors)
