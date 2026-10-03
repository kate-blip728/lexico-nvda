import threading
import wx
import ui
from . import spelling

class CorrectionDialog(wx.Dialog):
    def __init__(self, parent, text, language):
        super().__init__(parent, title='Corregir texto con Windows', size=(700, 600))
        self.language = language
        self.errors = []
        self.snapshot = None
        self.alive = True
        self.busy = False
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(wx.StaticText(self, label='&Texto para revisar:'), 0, wx.ALL, 8)
        self.text = wx.TextCtrl(self, value=text, style=wx.TE_MULTILINE)
        layout.Add(self.text, 1, wx.EXPAND | wx.ALL, 8)
        self.checkButton = wx.Button(self, label='&Revisar ortografía')
        self.checkButton.Bind(wx.EVT_BUTTON, self.scan)
        layout.Add(self.checkButton, 0, wx.ALL, 8)
        layout.Add(wx.StaticText(self, label='&Palabras detectadas:'), 0, wx.LEFT, 8)
        self.list = wx.ListBox(self, size=(-1, 100))
        self.list.Bind(wx.EVT_LISTBOX, self.select)
        layout.Add(self.list, 0, wx.EXPAND | wx.ALL, 8)
        layout.Add(wx.StaticText(self, label='&Sugerencia o reemplazo (vacío para eliminar):'), 0, wx.LEFT, 8)
        self.suggestion = wx.ComboBox(self, style=wx.CB_DROPDOWN)
        layout.Add(self.suggestion, 0, wx.EXPAND | wx.ALL, 8)
        self.apply = wx.Button(self, label='&Aplicar a esta aparición')
        self.apply.Bind(wx.EVT_BUTTON, self.replace)
        self.apply.Disable()
        layout.Add(self.apply, 0, wx.ALL, 8)
        layout.Add(wx.StaticText(self, label='Revisión ortográfica local. No se envía este texto a Gemini.\n'
            'Lee las sugerencias antes de aplicarlas; Windows puede marcar nombres propios.'), 0, wx.ALL, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        accept = wx.Button(self, id=wx.ID_OK, label='Usar texto revisado')
        row.Add(accept, 0, wx.ALL, 4)
        row.Add(wx.Button(self, id=wx.ID_CANCEL, label='Cancelar'), 0, wx.ALL, 4)
        layout.Add(row, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(layout)
        self.text.SetFocus()
    def scan(self, event=None):
        if self.busy:
            return
        text = self.text.GetValue()
        self.busy = True
        self.checkButton.Disable()
        self.apply.Disable()
        ui.message('Revisando con Windows')
        def worker():
            try:
                result = spelling.check(text, self.language)
            except spelling.SpellError as error:
                result = str(error)
            except Exception:
                result = 'No se pudo revisar el texto con Windows.'
            wx.CallAfter(self.completed, text, result)
        threading.Thread(target=worker, daemon=True).start()
    def completed(self, text, result):
        if not self.alive:
            return
        self.busy = False
        self.checkButton.Enable()
        self.errors = []
        self.list.Clear()
        self.suggestion.Clear()
        if text != self.text.GetValue():
            ui.message('El texto ha cambiado. Pulsa Revisar de nuevo.')
            return
        if isinstance(result, str):
            wx.MessageBox(result, 'Corrector de Windows', wx.OK | wx.ICON_INFORMATION, self)
            return
        self.snapshot = text
        self.errors = result
        self.list.Set([str(index + 1) + '. ' + error['word'] for index, error in enumerate(result)])
        if result:
            self.list.SetSelection(0)
            self.select()
            self.list.SetFocus()
            ui.message(str(len(result)) + ' posibles errores. Elige una palabra y una sugerencia.')
        else:
            ui.message('Windows no detecta errores ortográficos.')
    def select(self, event=None):
        index = self.list.GetSelection()
        if index == wx.NOT_FOUND:
            return
        values = self.errors[index]['suggestions']
        self.suggestion.SetItems(values)
        self.suggestion.SetValue(values[0] if values else self.errors[index]['word'])
        self.apply.Enable()
    def replace(self, event):
        index = self.list.GetSelection()
        if index == wx.NOT_FOUND or self.text.GetValue() != self.snapshot:
            ui.message('Pulsa Revisar de nuevo antes de aplicar cambios.')
            return
        self.text.SetValue(spelling.apply_change(self.snapshot, self.errors[index], self.suggestion.GetValue()))
        self.apply.Disable()
        self.scan()
