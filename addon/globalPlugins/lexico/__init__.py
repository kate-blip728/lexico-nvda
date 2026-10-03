import threading
import webbrowser
import wx
import api
from NVDAState import WritePaths
import globalPluginHandler
import globalVars
import gui
import textInfos
import ui
from scriptHandler import script
from . import services, spelling
from .correction import CorrectionDialog
from .storage import Store, LANGUAGES, MODELS, RECOMMENDED_MODEL, SPELL_LANGUAGES

class Options(wx.Dialog):
    def __init__(self, parent, store):
        super().__init__(parent, title='Opciones de Léxico')
        self.store = store
        layout = wx.BoxSizer(wx.VERTICAL)
        self.controls = {}
        for name, label in [('language', '&Idioma de destino:'),
                             ('model', '&Modelo de Gemini:'),
                             ('spelling_language', 'Idioma del corrector de &Windows:'),
                             ('key', '&Clave de API de Gemini:')]:
            layout.Add(wx.StaticText(self, label=label), 0, wx.ALL, 8)
            if name == 'key':
                control = wx.TextCtrl(self, value=store.values[name], style=wx.TE_PASSWORD)
            else:
                choices = list(LANGUAGES if name == 'language' else SPELL_LANGUAGES if name == 'spelling_language' else MODELS)
                if store.values[name] not in choices:
                    choices.append(store.values[name])
                control = wx.ComboBox(self, value=store.values[name], choices=choices, style=wx.CB_DROPDOWN)
            layout.Add(control, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
            self.controls[name] = control
        layout.Add(wx.StaticText(self, label='Modelo recomendado para traducción: ' + RECOMMENDED_MODEL + '.\n'
            'Puedes elegir de la lista o escribir otro idioma o modelo.'), 0, wx.ALL, 8)
        recommended = wx.Button(self, label='Usar modelo &recomendado')
        recommended.Bind(wx.EVT_BUTTON, self.useRecommended)
        layout.Add(recommended, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        for label, url in [('Crear API de &Gemini en Google AI Studio', 'https://aistudio.google.com/apikey'),
                           ('Abrir credenciales de Google &Cloud', 'https://console.cloud.google.com/apis/credentials')]:
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, lambda event, target=url: self.openLink(target))
            layout.Add(button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        layout.Add(wx.StaticText(self, label='La clave se guarda cifrada para tu usuario de Windows.\n'
            'Al traducir o preguntar, el texto indicado se envía a Google Gemini.\n'
            'La revisión de Windows no utiliza Gemini.\n'
            'Las búsquedas se envían al servicio independiente rae-api.com.'), 0, wx.ALL, 8)
        layout.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALL | wx.ALIGN_RIGHT, 8)
        self.SetSizerAndFit(layout)
        self.Bind(wx.EVT_BUTTON, self.save, id=wx.ID_OK)
        self.controls['language'].SetFocus()
    def useRecommended(self, event):
        self.controls['model'].SetValue(RECOMMENDED_MODEL)
        self.controls['model'].SetFocus()
    def openLink(self, url):
        try:
            if not webbrowser.open(url):
                raise OSError('No browser')
        except (OSError, webbrowser.Error):
            wx.MessageBox('No se pudo abrir el navegador. Enlace: ' + url, 'Léxico', wx.OK | wx.ICON_ERROR, self)
    def save(self, event):
        values = {name: control.GetValue().strip() for name, control in self.controls.items()}
        if not values['language'] or not values['model'] or not values['spelling_language']:
            wx.MessageBox('Escribe el idioma y el modelo.', 'Léxico', wx.OK | wx.ICON_ERROR, self)
            return
        try:
            self.store.save(**values)
        except (OSError, ValueError):
            wx.MessageBox('No se pudo guardar la configuración. Las opciones anteriores se mantienen.',
                          'Léxico', wx.OK | wx.ICON_ERROR, self)
            return
        self.EndModal(wx.ID_OK)

class Window(wx.Dialog):
    def __init__(self, parent, plugin, initial=''):
        super().__init__(parent, title='Léxico 0.3.2: diccionario, escritura y traducción', size=(760, 680))
        self.plugin = plugin
        self.alive = True
        self.busy = False
        self.generation = 0
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(wx.StaticText(self, label='&Palabra o expresión:'), 0, wx.ALL, 8)
        self.word = wx.TextCtrl(self)
        layout.Add(self.word, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.actions = []
        for label, action in [('&Buscar en el DLE', self.lookup), ('Palabra del &día', self.daily)]:
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, action)
            buttons.Add(button, 0, wx.ALL, 4)
            self.actions.append(button)
        layout.Add(buttons, 0, wx.ALL, 4)
        writing = wx.StaticBoxSizer(wx.VERTICAL, self, 'Cómo se escribe')
        writing.Add(wx.StaticText(self, label='Comprueba la palabra escrita arriba con el corrector de Windows.'), 0, wx.ALL, 4)
        how = wx.Button(self, label='Comprobar &escritura')
        how.Bind(wx.EVT_BUTTON, self.howWritten)
        writing.Add(how, 0, wx.ALL, 4)
        self.actions.append(how)
        layout.Add(writing, 0, wx.EXPAND | wx.ALL, 8)
        layout.Add(wx.StaticText(self, label='&Texto para traducir o corregir:'), 0, wx.ALL, 8)
        self.input = wx.TextCtrl(self, value=initial, style=wx.TE_MULTILINE, size=(-1, 90))
        layout.Add(self.input, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for label, action in [('&Traducir', self.translate), ('Traducir porta&papeles', self.translateClipboard), ('&Opciones', self.options)]:
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, action)
            buttons.Add(button, 0, wx.ALL, 4)
            self.actions.append(button)
        layout.Add(buttons, 0, wx.ALL, 4)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for label, action in [('Corregir con &Windows', self.correct), ('&Preguntar a Gemini', self.ask)]:
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, action)
            buttons.Add(button, 0, wx.ALL, 4)
            self.actions.append(button)
        layout.Add(buttons, 0, wx.ALL, 4)
        layout.Add(wx.StaticText(self, label='&Resultado:'), 0, wx.ALL, 8)
        self.result = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP)
        layout.Add(self.result, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        bottom = wx.BoxSizer(wx.HORIZONTAL)
        copy = wx.Button(self, label='&Copiar resultado')
        copy.Bind(wx.EVT_BUTTON, self.copy)
        bottom.Add(copy, 0, wx.ALL, 4)
        close = wx.Button(self, id=wx.ID_CANCEL, label='Cerrar')
        close.Bind(wx.EVT_BUTTON, lambda event: self.Close())
        bottom.Add(close, 0, wx.ALL, 4)
        layout.Add(bottom, 0, wx.ALIGN_RIGHT | wx.ALL, 4)
        self.SetSizer(layout)
        self.Bind(wx.EVT_CLOSE, self.closed)
        self.word.SetFocus()
        if plugin.store.warning:
            self.result.SetValue(plugin.store.warning)
    def closed(self, event):
        self.alive = False
        self.plugin.window = None
        self.Destroy()
    def run(self, operation):
        if self.busy:
            ui.message('Hay una consulta en curso.')
            return
        self.busy = True
        self.generation += 1
        generation = self.generation
        for button in self.actions:
            button.Disable()
        self.result.SetValue('Consultando…')
        ui.message('Consultando')
        def worker():
            try:
                result = operation()
            except (services.ServiceError, spelling.SpellError) as error:
                result = str(error)
            except Exception:
                result = 'No se pudo completar la consulta. Inténtalo de nuevo.'
            wx.CallAfter(self.completed, generation, result)
        threading.Thread(target=worker, daemon=True).start()
    def completed(self, generation, result):
        if not self.alive or not self.plugin.active or generation != self.generation:
            return
        self.busy = False
        for button in self.actions:
            button.Enable()
        self.result.SetValue(result)
        self.result.SetInsertionPoint(0)
        self.result.SetFocus()
        ui.message('Resultado disponible. Puedes leerlo con las flechas.')
    def lookup(self, event=None):
        word = self.word.GetValue()
        self.run(lambda: services.lookup(word))
    def daily(self, event=None):
        self.run(services.daily_word)
    def translate(self, event=None):
        self.translateText(self.input.GetValue())
    def translateText(self, text):
        if self.busy:
            ui.message('Hay una consulta en curso. Espera a que termine.')
            return
        if not isinstance(text, str) or not text.strip():
            ui.message('No hay texto para traducir.')
            return
        self.input.SetValue(text)
        values = self.plugin.store.values.copy()
        self.run(lambda: services.translate(text, values['language'], values['key'], values['model']))
    def translateClipboard(self, event=None):
        try:
            text = api.getClipData()
        except Exception:
            ui.message('El portapapeles no contiene texto.')
            return
        self.translateText(text)
    def howWritten(self, event=None):
        word = self.word.GetValue().strip()
        language = self.plugin.store.values['spelling_language']
        self.run(lambda: spelling.how_written(word, language))
    def correct(self, event=None):
        dialog = CorrectionDialog(self, self.input.GetValue(), self.plugin.store.values['spelling_language'])
        try:
            if dialog.ShowModal() == wx.ID_OK:
                self.input.SetValue(dialog.text.GetValue())
                self.input.SetFocus()
        finally:
            dialog.alive = False
            dialog.Destroy()
    def ask(self, event=None):
        dialog = wx.TextEntryDialog(self, 'Escribe una duda gramatical u otra pregunta.\n'
            'Al aceptar, esta pregunta se enviará a Gemini.', 'Preguntar a Gemini',
            style=wx.OK | wx.CANCEL | wx.TE_MULTILINE)
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            question = dialog.GetValue()
        finally:
            dialog.Destroy()
        values = self.plugin.store.values.copy()
        self.run(lambda: services.ask(question, values['key'], values['model']))
    def paste(self, event):
        try:
            self.input.SetValue(api.getClipData())
            self.input.SetFocus()
        except Exception:
            ui.message('El portapapeles no contiene texto.')
    def copy(self, event):
        value = self.result.GetValue()
        if not value or self.busy:
            ui.message('Todavía no hay un resultado para copiar.')
            return
        api.copyToClip(value)
        ui.message('Resultado copiado.')
    def options(self, event):
        dialog = Options(self, self.plugin.store)
        try:
            dialog.ShowModal()
        finally:
            dialog.Destroy()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = 'Léxico'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active = False
        self.window = None
        self.menu = None
        if globalVars.appArgs.secure:
            return
        self.store = Store(WritePaths.configDir)
        self.active = True
        self.menu = gui.mainFrame.sysTrayIcon.toolsMenu.Append(wx.ID_ANY, 'Léxico: diccionario y traducción…')
        gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onMenu, self.menu)
    def onMenu(self, event):
        self.open()
    def selection(self):
        try:
            focus = api.getFocusObject()
            target = focus.treeInterceptor
            if target is None or target.passThrough:
                target = focus
            return target.makeTextInfo(textInfos.POSITION_SELECTION).text
        except Exception:
            return ''
    def open(self, initial='', action=None):
        if not self.active:
            return
        if self.window is None:
            gui.mainFrame.prePopup()
            try:
                self.window = Window(gui.mainFrame, self, initial)
                self.window.Show()
            finally:
                gui.mainFrame.postPopup()
        else:
            if initial and action != 'translate':
                self.window.input.SetValue(initial)
            self.window.Raise()
        if action == 'translate':
            self.window.translateText(initial)
        elif action:
            getattr(self.window, action)()
    @script(description='Abre Léxico para consultar el DLE o traducir texto.')
    def script_open(self, gesture):
        initial = self.selection()
        wx.CallAfter(self.open, initial)
    @script(description='Consulta la palabra del día dentro de Léxico.')
    def script_daily(self, gesture):
        wx.CallAfter(self.open, '', 'daily')
    @script(description='Traduce el texto seleccionado dentro de Léxico.')
    def script_translateSelection(self, gesture):
        text = self.selection()
        if not text.strip():
            ui.message('Selecciona el texto que quieras traducir.')
            return
        wx.CallAfter(self.open, text, 'translate')
    @script(description='Traduce el texto del portapapeles dentro de Léxico.')
    def script_translateClipboard(self, gesture):
        try:
            text = api.getClipData()
        except Exception:
            ui.message('El portapapeles no contiene texto.')
            return
        wx.CallAfter(self.open, text, 'translate')
    def terminate(self):
        self.active = False
        if self.window:
            self.window.Close()
        if self.menu:
            gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, handler=self.onMenu, source=self.menu)
            gui.mainFrame.sysTrayIcon.toolsMenu.Destroy(self.menu)
        super().terminate()
