import os
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
from . import services, spelling, updates
from .history import History
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
            'Las búsquedas del DLE se envían a rae-api.com; las del DPD a www.rae.es.'), 0, wx.ALL, 8)
        layout.Add(wx.StaticText(self, label='Número máximo de entradas del historial (0 lo desactiva):'), 0, wx.ALL, 8)
        self.limit = wx.SpinCtrl(self, min=0, max=10000, initial=store.values['history_limit'])
        layout.Add(self.limit, 0, wx.ALL, 8)
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
            self.store.save(**values, history_limit=self.limit.GetValue())
        except (OSError, ValueError):
            wx.MessageBox('No se pudo guardar la configuración. Las opciones anteriores se mantienen.',
                          'Léxico', wx.OK | wx.ICON_ERROR, self)
            return
        self.EndModal(wx.ID_OK)

class Window(wx.Dialog):
    def __init__(self, parent, plugin, initial=''):
        super().__init__(parent, title='Léxico 0.5.0: diccionario, escritura y traducción', size=(760, 680))
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
        dictionary = wx.BoxSizer(wx.HORIZONTAL)
        for label, action in [('Definición del porta&papeles', self.lookupClipboard), ('Consultar &DPD', self.dpd)]:
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, action)
            dictionary.Add(button, 0, wx.ALL, 4)
            self.actions.append(button)
        layout.Add(dictionary, 0, wx.ALL, 4)
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
        for label, action in [('Corregir con &Windows', self.correct), ('&Preguntar a Gemini', self.ask), ('&Historial', self.history), ('Buscar &actualizaciones', self.update)]:
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
    def run(self, operation, history=None):
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
                if history is not None:
                    try:
                        self.plugin.history.add(result=result, limit=self.plugin.store.values['history_limit'], **history)
                    except (OSError, ValueError):
                        result += '\n\nNo se pudo guardar esta consulta en el historial.'
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
        self.run(lambda: services.lookup(word), dict(kind='DLE', text=word))
    def lookupText(self, word):
        if self.busy:
            ui.message('Hay una consulta en curso. Espera a que termine.')
            return
        if not isinstance(word, str) or not word.strip():
            ui.message('El portapapeles no contiene una palabra o expresión.')
            return
        word = word.strip()
        if len(word) > 150 or '\n' in word or '\r' in word:
            ui.message('Copia una palabra o expresión de una sola línea y hasta 150 caracteres.')
            return
        self.word.SetValue(word)
        self.lookup()
    def lookupClipboard(self, event=None):
        try:
            word = api.getClipData()
        except Exception:
            ui.message('El portapapeles no contiene texto.')
            return
        self.lookupText(word)
    def dpd(self, event=None):
        word = self.word.GetValue()
        self.run(lambda: services.lookup_dpd(word), dict(kind='DPD', text=word))
    def daily(self, event=None):
        self.run(services.daily_word, dict(kind='Palabra del día', text=''))
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
        self.run(lambda: services.translate(text, values['language'], values['key'], values['model']),
                 dict(kind='Traducción', text=text, language=values['language'], model=values['model']))
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
        self.run(lambda: spelling.how_written(word, language), dict(kind='Escritura', text=word, language=language))
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
        self.run(lambda: services.ask(question, values['key'], values['model']),
                 dict(kind='Pregunta', text=question, model=values['model']))
    def history(self, event):
        dialog = HistoryDialog(self, self.plugin.history)
        try:
            if dialog.ShowModal() == wx.ID_OK:
                entry = dialog.selected()
                if entry:
                    self.input.SetValue(entry['text'])
                    self.word.SetValue(entry['text'] if entry['kind'] in ('DLE', 'DPD', 'Escritura') else '')
                    self.result.SetValue(entry['result'])
                    self.result.SetInsertionPoint(0)
                    self.result.SetFocus()
        finally:
            dialog.Destroy()

    def update(self, event):
        if self.busy:
            ui.message('Hay una consulta en curso.')
            return
        def checked(metadata, error):
            if not self.alive or not self.plugin.active:
                return
            self.busy = False
            for button in self.actions:
                button.Enable()
            if error:
                wx.MessageBox('No se pudo buscar la actualización. ' + error, 'Léxico', wx.OK | wx.ICON_ERROR, self)
            elif metadata is None:
                wx.MessageBox('Léxico ya está actualizado.', 'Léxico', wx.OK, self)
            elif wx.MessageBox('Está disponible Léxico ' + metadata['version'] + '. ¿Descargar y abrir el instalador de NVDA?',
                               'Actualizar Léxico', wx.YES_NO | wx.ICON_QUESTION, self) == wx.YES:
                start(lambda: updates.download(metadata, self.plugin.store.path.parent / 'lexico-updates'), installed)
        def installed(path, error):
            if not self.alive or not self.plugin.active:
                return
            self.busy = False
            for button in self.actions:
                button.Enable()
            try:
                if error:
                    raise OSError(error)
                os.startfile(str(path))
                self.result.SetValue('Instalador abierto. Sigue las instrucciones de NVDA y reinicia NVDA al terminar.')
            except OSError as exc:
                wx.MessageBox('No se pudo abrir el instalador. ' + str(exc), 'Léxico', wx.OK | wx.ICON_ERROR, self)
        def start(operation, callback):
            self.busy = True
            for button in self.actions:
                button.Disable()
            self.result.SetValue('Consultando GitHub…')
            def worker():
                try:
                    value, error = operation(), ''
                except Exception as exc:
                    value, error = None, str(exc)
                wx.CallAfter(callback, value, error)
            threading.Thread(target=worker, daemon=True).start()
        start(updates.check, checked)

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
            if dialog.ShowModal() == wx.ID_OK:
                try:
                    self.plugin.history.trim(self.plugin.store.values['history_limit'])
                except OSError:
                    wx.MessageBox('Opciones guardadas, pero no se pudo reducir el historial.', 'Léxico', wx.OK | wx.ICON_ERROR, self)
        finally:
            dialog.Destroy()

class HistoryDialog(wx.Dialog):
    def __init__(self, parent, history):
        super().__init__(parent, title='Historial de Léxico', size=(700, 550))
        self.history = history
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(wx.StaticText(self, label='Consultas guardadas, de más reciente a más antigua:'), 0, wx.ALL, 8)
        self.items = wx.ListBox(self)
        layout.Add(self.items, 1, wx.EXPAND | wx.ALL, 8)
        self.preview = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        layout.Add(self.preview, 1, wx.EXPAND | wx.ALL, 8)
        self.items.Bind(wx.EVT_LISTBOX, self.showEntry)
        self.items.Bind(wx.EVT_LISTBOX_DCLICK, lambda event: self.EndModal(wx.ID_OK) if self.selected() else None)
        for label, action in [('Copiar resultado', self.copy), ('Eliminar entrada', self.delete), ('Vaciar historial', self.clear)]:
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, action)
            layout.Add(button, 0, wx.ALL, 4)
        layout.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALL, 8)
        self.SetSizer(layout)
        self.FindWindowById(wx.ID_OK).SetLabel('Recuperar texto y resultado')
        self.refresh()
        self.items.SetFocus()
    def selected(self):
        index = self.items.GetSelection()
        return self.history.entries[index] if 0 <= index < len(self.history.entries) else None
    def refresh(self):
        self.items.Set([e['date'] + ' · ' + e['kind'] + (' · ' + e['language'] if e['language'] else '') + ' · ' + e['text'][:80].replace('\n', ' ') for e in self.history.entries])
        self.FindWindowById(wx.ID_OK).Enable(bool(self.history.entries))
        if self.history.entries:
            self.items.SetSelection(0)
        self.showEntry()
    def showEntry(self, event=None):
        entry = self.selected()
        self.preview.SetValue('Original:\n' + entry['text'] + '\n\nResultado:\n' + entry['result'] if entry else 'El historial está vacío.')
    def copy(self, event):
        entry = self.selected()
        if entry:
            api.copyToClip(entry['result'])
            ui.message('Resultado copiado.')
    def persist(self, entries):
        try:
            self.history.write(entries)
            self.refresh()
        except OSError:
            wx.MessageBox('No se pudo guardar el cambio en el historial.', 'Léxico', wx.OK | wx.ICON_ERROR, self)
    def delete(self, event):
        if self.selected():
            index = self.items.GetSelection()
            self.persist(self.history.entries[:index] + self.history.entries[index + 1:])
    def clear(self, event):
        if wx.MessageBox('¿Eliminar todo el historial guardado?', 'Léxico', wx.YES_NO | wx.ICON_QUESTION, self) == wx.YES:
            self.persist([])

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
        self.history = History(WritePaths.configDir)
        try:
            if not self.history.warning:
                self.history.trim(self.store.values['history_limit'])
        except OSError:
            self.store.warning += '\nNo se pudo aplicar el límite del historial.'
        self.store.warning += self.history.warning
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
            if initial and action not in ('translate', 'lookupText'):
                self.window.input.SetValue(initial)
            self.window.Raise()
        if action == 'translate':
            self.window.translateText(initial)
        elif action == 'lookupText':
            self.window.lookupText(initial)
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
    @script(description='Consulta la definición de la palabra del portapapeles en el DLE dentro de Léxico.',
            gesture='kb:NVDA+control+shift+d')
    def script_lookupClipboard(self, gesture):
        try:
            word = api.getClipData()
        except Exception:
            ui.message('El portapapeles no contiene texto.')
            return
        if not isinstance(word, str) or not word.strip():
            ui.message('El portapapeles no contiene una palabra o expresión.')
            return
        wx.CallAfter(self.open, word, 'lookupText')
    def terminate(self):
        self.active = False
        if self.window:
            self.window.Close()
        if self.menu:
            gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, handler=self.onMenu, source=self.menu)
            gui.mainFrame.sysTrayIcon.toolsMenu.Destroy(self.menu)
        super().terminate()
