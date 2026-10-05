"""Bounded, atomic local history. No credentials are stored here."""
import json
import os
import threading
from datetime import datetime
from pathlib import Path

class History:
    def __init__(self, directory):
        self.path = Path(directory) / 'lexico-history.json'
        self.warning = ''
        self.entries = []
        self.lock = threading.RLock()
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(raw, list):
                raise ValueError('Invalid history')
            self.entries = [e for e in raw if isinstance(e, dict) and all(
                isinstance(e.get(k), str) for k in ('kind', 'text', 'result', 'date', 'language', 'model'))]
        except FileNotFoundError:
            pass
        except (OSError, ValueError, UnicodeError):
            self.warning = 'No se pudo leer el historial de Léxico.'

    def write(self, entries):
        with self.lock:
            self._write(entries)

    def _write(self, entries):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temporary, self.path)
        self.entries = entries

    def trim(self, limit):
        with self.lock:
            self.write(self.entries[:limit])

    def add(self, kind, text, result, limit, language='', model=''):
        if limit == 0:
            return
        entry = dict(kind=kind, text=text, result=result, language=language,
                     model=model, date=datetime.now().isoformat(timespec='seconds'))
        with self.lock:
            self.write(([entry] + self.entries)[:limit])
