"""One information request slot shared by the Léxico window."""
from threading import Thread
from .information import InformationError

class RequestSlot:
    def __init__(self, dispatch, thread=Thread):
        self.dispatch=dispatch; self.thread=thread; self.busy=False; self.generation=0
    def cancel(self): self.generation+=1
    def start(self, operation, completed, alive):
        if self.busy: return False
        self.busy=True; self.generation+=1; token=self.generation
        def deliver(value,error):
            self.busy=False
            if token==self.generation and alive(): completed(value,error)
        def worker():
            try: value,error=operation(),''
            except InformationError as exc: value,error=None,str(exc)
            except Exception: value,error=None,'No se pudo completar la consulta de información.'
            self.dispatch(deliver,value,error)
        try: self.thread(target=worker,daemon=True,name='LexicoInformacion').start()
        except Exception:
            self.busy=False
            raise
        return True
