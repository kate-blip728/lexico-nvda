"""Modeless accessible information reader; original articles remain available."""
import wx
import api
import ui
from .information import Client, SOURCES, InformationError, language_code
from .information_html import semantic_html

class InformationWindow(wx.Dialog):
    def __init__(self, parent, jobs):
        super().__init__(parent,title='Léxico — Buscar y leer información',size=(800,740),style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.owner=parent; self.jobs=jobs; self.client=Client(); self.alive=True
        self.results=[]; self.article=None; self.search_state=None; self.next_offset=0; self.has_more=False
        layout=wx.BoxSizer(wx.VERTICAL)
        intro=wx.StaticText(self,label='Busca en una fuente, elige un resultado y ábrelo. No necesitas clave de API. Al buscar se envían la consulta y el idioma a la fuente elegida. Traducir envía el texto al servicio de traducción configurado en Léxico.')
        intro.Wrap(740); layout.Add(intro,0,wx.EXPAND | wx.ALL,8)
        layout.Add(wx.StaticText(self,label='Fuente de información:'),0,wx.LEFT,8)
        self.source=wx.Choice(self,choices=list(SOURCES.values())); self.source.SetSelection(0)
        layout.Add(self.source,0,wx.EXPAND | wx.ALL,8)
        layout.Add(wx.StaticText(self,label='Idioma de búsqueda (código, por ejemplo es o en):'),0,wx.LEFT,8)
        self.language=wx.TextCtrl(self,value='es'); layout.Add(self.language,0,wx.EXPAND | wx.ALL,8)
        layout.Add(wx.StaticText(self,label='Consulta para buscar:'),0,wx.LEFT,8)
        self.query=wx.TextCtrl(self,value=parent.word.GetValue(),style=wx.TE_PROCESS_ENTER)
        layout.Add(self.query,0,wx.EXPAND | wx.ALL,8)
        bar=wx.BoxSizer(wx.HORIZONTAL)
        self.search_button=self.button(bar,'Buscar',self.search)
        self.more_button=self.button(bar,'Más resultados',self.more)
        self.cancel_button=self.button(bar,'Cancelar consulta',self.cancel)
        layout.Add(bar,0,wx.ALL,4)
        layout.Add(wx.StaticText(self,label='Resultados: flechas para elegir; Intro o doble clic abre el artículo.'),0,wx.LEFT,8)
        self.result_list=wx.ListBox(self,size=(-1,95)); layout.Add(self.result_list,0,wx.EXPAND | wx.ALL,8)
        self.result_list.Bind(wx.EVT_LISTBOX,self.preview)
        self.result_list.Bind(wx.EVT_LISTBOX_DCLICK,self.open_result)
        self.result_list.Bind(wx.EVT_KEY_DOWN,self.results_key)
        self.query.Bind(wx.EVT_TEXT_ENTER,self.search)
        self.status=wx.StaticText(self,label='Escribe una consulta y pulsa Buscar.'); layout.Add(self.status,0,wx.EXPAND | wx.ALL,8)
        bar=wx.BoxSizer(wx.HORIZONTAL)
        self.open_button=self.button(bar,'Abrir resultado en texto',self.open_result)
        self.button(bar,'Ver artículo en HTML',self.html_view)
        self.button(bar,'Buscar en el artículo',self.find)
        layout.Add(bar,0,wx.ALL,4)
        layout.Add(wx.StaticText(self,label='Artículo: texto de solo lectura. Selecciona con Mayúsculas y flechas; Control C copia la selección.'),0,wx.LEFT,8)
        self.text=wx.TextCtrl(self,style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        layout.Add(self.text,1,wx.EXPAND | wx.ALL,8)
        bar=wx.BoxSizer(wx.HORIZONTAL)
        self.button(bar,'Copiar selección o artículo',self.copy)
        self.button(bar,'Traducir selección o artículo',self.translate)
        self.button(bar,'Editar una copia en Léxico',self.edit_copy)
        layout.Add(bar,0,wx.ALL,4)
        bar=wx.BoxSizer(wx.HORIZONTAL)
        self.button(bar,'Guardar artículo en historial',self.save_history)
        self.button(bar,'Copiar enlace de la fuente',self.copy_source)
        self.button(bar,'Cerrar',lambda event:self.Close())
        layout.Add(bar,0,wx.ALIGN_RIGHT | wx.ALL,4)
        self.SetSizer(layout); self.Bind(wx.EVT_CLOSE,self.closed)
        self.SetEscapeId(wx.ID_CANCEL)
        self.more_button.Disable(); self.cancel_button.Disable(); self.open_button.Disable()
        self.query.SetFocus()

    def button(self,bar,label,callback):
        button=wx.Button(self,id=wx.ID_CANCEL,label=label) if label=='Cerrar' else wx.Button(self,label=label); button.Bind(wx.EVT_BUTTON,callback); bar.Add(button,0,wx.ALL,4); return button
    def available(self): return self.alive and self.owner.alive and self.owner.plugin.active
    def message(self,text): self.status.SetLabel(text); ui.message(text)
    def busy_ui(self,busy):
        for control in (self.search_button,self.source,self.language,self.query,self.result_list): control.Enable(not busy)
        self.open_button.Enable(not busy and bool(self.results))
        self.more_button.Enable(not busy and self.has_more and len(self.results)<50)
        self.cancel_button.Enable(busy)
    def request(self,operation,completed):
        if self.jobs.busy:
            self.message('Hay una consulta de información pendiente. Espera a que termine.'); return False
        def finish(value,error):
            self.busy_ui(False)
            if error: self.message(error)
            else: completed(value)
        if not self.jobs.start(operation,finish,self.available): return False
        self.busy_ui(True); self.message('Consultando la fuente…'); return True
    def search(self,event=None):
        try:
            source=list(SOURCES)[self.source.GetSelection()]; language=language_code(self.language.GetValue()); query=self.query.GetValue().strip()
            if not query or len(query)>300: raise InformationError('Escribe una búsqueda de entre 1 y 300 caracteres.')
        except InformationError as error: self.message(str(error)); return
        state=(query,source,language)
        def done(rows):
            self.results=rows; self.search_state=state; self.next_offset=10; self.has_more=len(rows)==10; self.show_results()
        self.request(lambda:self.client.search(*state),done)
    def more(self,event=None):
        if not self.search_state or not self.has_more or self.next_offset>40: return
        state=self.search_state; offset=self.next_offset
        def done(rows):
            known={row.pageid for row in self.results}
            self.results.extend(row for row in rows if row.pageid not in known)
            self.next_offset=offset+10; self.has_more=len(rows)==10 and self.next_offset<=40
            self.show_results()
            if not rows: self.more_button.Disable(); self.message('No hay más resultados para esta consulta.')
        self.request(lambda:self.client.search(*state,offset=offset),done)
    def show_results(self):
        self.result_list.Set([row.title for row in self.results])
        self.busy_ui(False)
        if self.results:
            self.result_list.SetSelection(0); self.result_list.SetFocus(); self.preview()
        else: self.message('No se encontraron resultados. Prueba otras palabras, fuente o idioma.')
    def preview(self,event=None):
        index=self.result_list.GetSelection()
        if 0<=index<len(self.results): self.status.SetLabel(self.results[index].snippet or self.results[index].title)
    def results_key(self,event):
        if event.GetKeyCode()==wx.WXK_RETURN: self.open_result()
        else: event.Skip()
    def open_result(self,event=None):
        index=self.result_list.GetSelection()
        if not 0<=index<len(self.results): self.message('Elige un resultado de la lista.'); return
        result=self.results[index]
        def done(article):
            self.article=article; self.text.SetValue(article.text); self.text.SetInsertionPoint(0); self.text.SetFocus()
            self.message('Artículo disponible en texto. Puedes seleccionar, copiar, traducir o abrir su vista HTML.')
        self.request(lambda:self.client.article(result),done)
    def selected_text(self):
        if not self.article: self.message('Abre primero un artículo.'); return ''
        return self.text.GetStringSelection() or self.text.GetValue()
    def copy(self,event=None):
        value=self.selected_text()
        if value:
            if api.copyToClip(value): self.message('Texto copiado.')
            else: self.message('No se pudo copiar el texto.')
    def translate(self,event=None):
        value=self.selected_text()
        if not value: return
        if len(value)>30000:
            self.message('El artículo supera 30.000 caracteres. Selecciona un fragmento para traducirlo.'); return
        if self.owner.busy: self.message('Léxico tiene una traducción o consulta pendiente.'); return
        self.owner.Raise(); self.owner.translateText(value)
    def edit_copy(self,event=None):
        value=self.selected_text()
        if not value: return
        if self.owner.busy: self.message('Espera a que termine la consulta principal de Léxico.'); return
        self.owner.input.SetValue(value); self.owner.Raise(); self.owner.input.SetFocus()
        ui.message('Copia en Texto para traducir o corregir. El artículo original sigue disponible.')
    def copy_source(self,event=None):
        if self.article:
            if api.copyToClip(self.article.url): self.message('Enlace de la fuente copiado.')
            else: self.message('No se pudo copiar el enlace.')
        else: self.message('Abre primero un artículo.')
    def save_history(self,event=None):
        if not self.article: self.message('Abre primero un artículo.'); return
        limit=self.owner.plugin.store.values['history_limit']
        if not limit: self.message('El historial está desactivado en Opciones.'); return
        article=self.article
        try: self.owner.plugin.history.add(kind='Información: '+SOURCES[article.source],text=article.title,result=article.text,language=article.language,limit=limit)
        except (OSError,ValueError): self.message('No se pudo guardar el artículo en el historial.'); return
        self.message('Artículo guardado con fuente y atribución en el historial de Léxico.')
    def html_view(self,event=None):
        if not self.article: self.message('Abre primero un artículo.'); return
        article=self.article
        try:
            ui.browseableMessage(article.html,title=article.title+' — Léxico',isHtml=True,closeButton=True,copyButton=True,sanitizeHtmlFunc=lambda value:semantic_html(value,article.url))
        except Exception: self.message('No se pudo abrir la vista HTML. El texto sigue disponible.')
    def find(self,event=None):
        if not self.article: self.message('Abre primero un artículo.'); return
        with wx.TextEntryDialog(self,'Texto que quieres buscar en el artículo','Buscar en el artículo') as dialog:
            if dialog.ShowModal()!=wx.ID_OK: return
            term=dialog.GetValue()
        if not term: return
        value=self.text.GetValue(); start=self.text.GetSelection()[1]
        # Search original offsets: casefold can change lengths, so use regex instead.
        import re
        matches=list(re.finditer(re.escape(term),value,re.I))
        match=next((m for m in matches if m.start()>=start),matches[0] if matches else None)
        if match is None: self.message('No se encontró ese texto.'); return
        self.text.SetFocus(); self.text.SetSelection(match.start(),match.end()); self.text.ShowPosition(match.start())
    def cancel(self,event=None):
        self.jobs.cancel(); self.busy_ui(False); self.message('Consulta cancelada. Si sigue conectando, espera a que termine antes de buscar de nuevo.')
    def closed(self,event):
        self.alive=False; self.jobs.cancel(); self.owner.informationWindow=None; self.Destroy()
