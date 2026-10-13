"""Bounded, cancellable speech translation, without networking on the UI thread."""
from collections import OrderedDict, deque
import threading

class SpeechTranslator:
    def __init__(self, translate, dispatch, emit, notify):
        self.translate, self.dispatch, self.emit, self.notify = translate, dispatch, emit, notify
        self.enabled = False
        self.internal = False
        self.language = ''
        self.epoch = 0
        self.pending = deque()
        self.cache = OrderedDict()
        self.lock = threading.Condition()
        self.closed = False
        threading.Thread(target=self.worker, daemon=True).start()
    def toggle(self, language):
        with self.lock:
            self.enabled = not self.enabled
            self.language = language
            self.epoch += 1
            self.pending.clear()
            self.lock.notify_all()
        return self.enabled
    def cancel(self, **kwargs):
        with self.lock:
            self.epoch += 1
            self.pending.clear()
    def filter(self, sequence, protected=False):
        if not self.enabled or self.internal or protected:
            return sequence
        strings = [s for s in sequence if isinstance(s, str) and s.strip()]
        if not strings or sum(map(len, strings)) > 5000:
            return sequence
        with self.lock:
            if len(self.pending) >= 20:
                return sequence
            self.pending.append((self.epoch, self.language, list(sequence)))
            self.lock.notify()
        return []
    def worker(self):
        while True:
            with self.lock:
                self.lock.wait_for(lambda: self.closed or self.pending)
                if self.closed:
                    return
                epoch, language, sequence = self.pending.popleft()
            output = []
            try:
                for item in sequence:
                    if not isinstance(item, str) or not item.strip():
                        output.append(item)
                        continue
                    with self.lock:
                        if epoch != self.epoch or not self.enabled:
                            break
                    key = (language, item)
                    if key not in self.cache:
                        self.cache[key] = self.translate(item, language)
                        if len(self.cache) > 256:
                            self.cache.popitem(last=False)
                    output.append(self.cache[key])
                else:
                    self.dispatch(self.deliver, epoch, output)
            except Exception:
                self.dispatch(self.failed, epoch, sequence)
    def deliver(self, epoch, sequence):
        if self.closed or not self.enabled or epoch != self.epoch:
            return
        self.internal = True
        try:
            self.emit(sequence)
        finally:
            self.internal = False
    def failed(self, epoch, sequence):
        if self.closed or epoch != self.epoch or not self.enabled:
            return
        self.enabled = False
        self.cancel()
        self.emit(sequence)
        self.notify('La traducción de voz se ha desactivado porque Google Translate no respondió. NVDA vuelve a leer el original.')
    def close(self):
        with self.lock:
            self.closed = True
            self.enabled = False
            self.pending.clear()
            self.lock.notify_all()
