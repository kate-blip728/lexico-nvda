import ast
import importlib
import io
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

ROOT=Path(__file__).parents[1]
PACKAGE=ROOT/'addon/globalPlugins/lexico'
package=types.ModuleType('lexico_information_tests'); package.__path__=[str(PACKAGE)]; sys.modules[package.__name__]=package
info=importlib.import_module(package.__name__+'.information')
jobs=importlib.import_module(package.__name__+'.information_jobs')
html_module=importlib.import_module(package.__name__+'.information_html')

class ClientTests(unittest.TestCase):
    def test_all_five_sources_and_languages(self):
        for source in info.SOURCES:
            fetch=Mock(return_value={'query':{'search':[{'pageid':1,'title':'Luna','snippet':'La <b>Luna</b>'}]}})
            rows=info.Client(fetch).search('Luna',source,'en')
            self.assertEqual(fetch.call_args.args[0],'en.'+source+'.org')
            self.assertEqual(rows[0].snippet,'La Luna')
            self.assertEqual(fetch.call_args.args[1]['srnamespace'],0)
    def test_no_fetch_for_invalid_query_language_source_offset(self):
        fetch=Mock(); client=info.Client(fetch)
        for kwargs in ({'query':''},{'query':'x'*301},{'query':'x','source':'example.com'},{'query':'x','language':'es/evil'},{'query':'x','offset':50}):
            with self.assertRaises(info.InformationError): client.search(**kwargs)
        fetch.assert_not_called()
    def test_safe_source_urls_and_redirects(self):
        host='es.wikipedia.org'
        for value in ('http://es.wikipedia.org/a','https://evil.org/a','https://u:p@es.wikipedia.org/a','https://es.wikipedia.org:444/a','file:///etc/passwd'):
            self.assertFalse(info.allowed_url(value,host))
            with self.assertRaises(info.InformationError): info.Redirect(host).redirect_request(None,None,302,'',{},value)
        self.assertTrue(info.allowed_url('https://es.wikipedia.org/w/api.php',host))
    def test_invalid_result_rows_ignored(self):
        fetch=lambda *a:{'query':{'search':[{'pageid':-1,'title':'X'},{'pageid':'1','title':'X'},{'pageid':1,'title':None},'bad']}}
        self.assertEqual(info.Client(fetch).search('x'),[])
    def article(self, html='<h2>Tema</h2><ul><li>Uno</li></ul><table><tr><th>Nombre</th><td>Dato</td></tr></table>'):
        return info.Client(lambda *a:{'parse':{'text':html,'revid':123,'title':'Título canónico'}}).article(info.Result('wikipedia','es',1,'Redirección'))
    def test_article_preserves_semantics_and_canonical_source(self):
        article=self.article()
        for value in ('<h2>','<ul>','<table>','<th>','<td>'): self.assertIn(value,article.html)
        for value in ('Título canónico','oldid=123','Historial y autores:','Consulta la licencia'): self.assertIn(value,article.text)
        self.assertIn('T%C3%ADtulo_can%C3%B3nico',article.url)
    def test_html_has_no_scripts_images_styles_or_remote_resources(self):
        article=self.article('<h1 onclick="x()">Tema</h1><img src="https://evil/x"><script>evil()</script><iframe src="https://evil">oculto</iframe><style>body{}</style><a href="javascript:x()">Texto</a>')
        for value in ('<script','<img','<iframe','onclick','javascript:','evil()','oculto','body{}'): self.assertNotIn(value,article.html)
    def test_literal_markup_is_escaped(self):
        self.assertIn('&lt;script&gt;',self.article('<p>&lt;script&gt;</p>').html)
    def test_hidden_and_malformed_structure(self):
        html=html_module.semantic_html('<ul><li>Uno</ul><p hidden>Oculto</p><table><tr><td>A</td></tr></table>','https://es.wikipedia.org/')
        self.assertIn('<ul><li>Uno</li></ul>',html); self.assertNotIn('Oculto',html)
    def test_external_links_and_table_headers_sanitized(self):
        html=html_module.semantic_html('<a href="/wiki/Sol">Sol</a><a href="https://:secret@evil/a">X</a><th scope="col" rowspan="2" style="x">H</th>','https://es.wikipedia.org/wiki/Luna')
        self.assertIn('https://es.wikipedia.org/wiki/Sol',html); self.assertNotIn('secret',html)
        self.assertIn('scope="col"',html); self.assertIn('rowspan="2"',html); self.assertNotIn('style=',html)
    def test_empty_and_oversized_article_are_explicit_errors(self):
        with self.assertRaises(info.InformationError): self.article('<script>Solo oculto</script>')
        with patch.object(info,'MAX_TEXT',5):
            with self.assertRaises(info.InformationError): self.article('<p>Demasiado texto</p>')
    def test_transport_headers_limits_and_api_errors(self):
        opener=Mock(); opener.open.return_value=io.BytesIO(b'{"query":{}}')
        with patch.object(info,'build_opener',return_value=opener):
            self.assertEqual(info.request_json('es.wikipedia.org',{'action':'query'}),{'query':{}})
            request=opener.open.call_args.args[0]
            self.assertIn('Lexico/0.6.0',request.get_header('User-agent'))
            self.assertEqual(opener.open.call_args.kwargs['timeout'],15)
        for raw in (b'invalid',b'[]',b'{"error":{"code":"maxlag"}}'):
            opener.open.return_value=io.BytesIO(raw)
            with patch.object(info,'build_opener',return_value=opener):
                with self.assertRaises(info.InformationError): info.request_json('es.wikipedia.org',{})
    def test_response_size_is_bounded(self):
        opener=Mock(); opener.open.return_value=io.BytesIO(b'x'*100)
        with patch.object(info,'build_opener',return_value=opener),patch.object(info,'MAX_RESPONSE',8):
            with self.assertRaisesRegex(info.InformationError,'4 MB'): info.request_json('es.wikipedia.org',{})
    def test_network_errors_do_not_expose_query_or_credentials(self):
        for error in (URLError('private query'),HTTPError('https://x/?q=private',429,'',{},None)):
            opener=Mock(); opener.open.side_effect=error
            with patch.object(info,'build_opener',return_value=opener):
                with self.assertRaises(info.InformationError) as caught: info.request_json('es.wikipedia.org',{'query':'private'})
            self.assertNotIn('private',str(caught.exception))

class SlotTests(unittest.TestCase):
    def setUp(self):
        self.work=[]; self.queue=[]
        owner=self
        class Deferred:
            def __init__(self,target,**kwargs): self.target=target
            def start(self): owner.work.append(self.target)
        self.slot=jobs.RequestSlot(lambda fn,*args:self.queue.append((fn,args)),Deferred)
        self.done=Mock()
    def deliver(self):
        self.work.pop(0)(); fn,args=self.queue.pop(0); fn(*args)
    def test_one_request_and_gui_delivery(self):
        self.assertTrue(self.slot.start(lambda:'ok',self.done,lambda:True))
        self.assertFalse(self.slot.start(lambda:'new',self.done,lambda:True))
        self.work.pop(0)(); self.done.assert_not_called()
        fn,args=self.queue.pop(0); fn(*args)
        self.done.assert_called_once_with('ok',''); self.assertFalse(self.slot.busy)
    def test_cancel_holds_slot_until_native_request_finishes(self):
        self.slot.start(lambda:'old',self.done,lambda:True); self.slot.cancel()
        self.assertFalse(self.slot.start(lambda:'new',self.done,lambda:True))
        self.deliver(); self.done.assert_not_called(); self.assertFalse(self.slot.busy)
    def test_closed_window_never_receives_result(self):
        self.slot.start(lambda:'old',self.done,lambda:False); self.deliver(); self.done.assert_not_called()
    def test_unexpected_error_is_not_leaked(self):
        def fail(): raise RuntimeError('secret-key-and-private-text')
        self.slot.start(fail,self.done,lambda:True); self.deliver()
        self.assertNotIn('secret',self.done.call_args.args[1])
    def test_thread_start_failure_frees_slot(self):
        slot=jobs.RequestSlot(lambda *a:None,Mock(side_effect=RuntimeError('start')))
        with self.assertRaises(RuntimeError): slot.start(lambda:1,self.done,lambda:True)
        self.assertFalse(slot.busy)

class UIActionTests(unittest.TestCase):
    def setUp(self):
        tree=ast.parse((PACKAGE/'information_ui.py').read_text(encoding='utf-8'))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
        names=('selected_text','copy','translate','edit_copy','save_history','copy_source','html_view','request','cancel','closed','search','more','show_results')
        methods=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in names]
        self.api=types.SimpleNamespace(copyToClip=Mock(return_value=True))
        self.ui=types.SimpleNamespace(message=Mock(),browseableMessage=Mock())
        namespace=dict(api=self.api,ui=self.ui,SOURCES=info.SOURCES,InformationError=info.InformationError,language_code=info.language_code,semantic_html=html_module.semantic_html)
        exec(compile(ast.Module(body=methods,type_ignores=[]),'information_ui.py','exec'),namespace)
        self.owner=types.SimpleNamespace(alive=True,busy=False,Raise=Mock(),translateText=Mock(),input=types.SimpleNamespace(SetValue=Mock(),SetFocus=Mock()),plugin=types.SimpleNamespace(active=True,history=Mock(),store=types.SimpleNamespace(values={'history_limit':100})))
        self.window=types.SimpleNamespace(owner=self.owner,article=info.Article('Tema','Texto completo','<h2>Tema</h2>','https://es.wikipedia.org/wiki/Tema','wikipedia','es'),text=types.SimpleNamespace(GetStringSelection=Mock(return_value='Parte seleccionada'),GetValue=Mock(return_value='Texto completo')),message=Mock(),busy_ui=Mock(),available=lambda:True,alive=True,Destroy=Mock())
        for name in names: setattr(self.window,name,namespace[name].__get__(self.window))
    def test_selection_translates_through_existing_service_without_losing_article(self):
        article=self.window.article; self.window.translate()
        self.owner.translateText.assert_called_once_with('Parte seleccionada'); self.assertIs(self.window.article,article)
    def test_no_selection_translates_full_text(self):
        self.window.text.GetStringSelection.return_value=''; self.window.translate()
        self.owner.translateText.assert_called_once_with('Texto completo')
    def test_long_article_is_not_silently_truncated(self):
        self.window.text.GetStringSelection.return_value='x'*30001; self.window.translate()
        self.owner.translateText.assert_not_called(); self.assertIn('30.000',self.window.message.call_args.args[0])
    def test_busy_parent_preserves_translation_input(self):
        self.owner.busy=True; self.window.translate(); self.window.edit_copy()
        self.owner.translateText.assert_not_called(); self.owner.input.SetValue.assert_not_called()
    def test_copy_selection_full_text_and_failed_copy(self):
        self.window.copy(); self.api.copyToClip.assert_called_with('Parte seleccionada')
        self.window.text.GetStringSelection.return_value=''; self.window.copy(); self.api.copyToClip.assert_called_with('Texto completo')
        self.api.copyToClip.return_value=False; self.window.copy(); self.assertIn('No se pudo',self.window.message.call_args.args[0])
    def test_edit_copy_does_not_mutate_original(self):
        original=self.window.article; self.window.edit_copy()
        self.owner.input.SetValue.assert_called_once_with('Parte seleccionada'); self.assertIs(self.window.article,original)
    def test_history_is_explicit_and_respects_off_switch(self):
        self.window.save_history(); self.owner.plugin.history.add.assert_called_once()
        self.assertEqual(self.owner.plugin.history.add.call_args.kwargs['result'],'Texto completo')
        self.owner.plugin.history.reset_mock(); self.owner.plugin.store.values['history_limit']=0
        self.window.save_history(); self.owner.plugin.history.add.assert_not_called()
    def test_html_uses_separate_safe_view_and_preserves_text(self):
        self.window.html_view(); options=self.ui.browseableMessage.call_args.kwargs
        self.assertTrue(options['isHtml']); self.assertNotIn('<img',options['sanitizeHtmlFunc']('<img src="x"><h2>H</h2>'))
        self.window.text.GetValue.assert_not_called()
    def test_source_link_is_original_not_translation_service(self):
        self.window.copy_source(); self.api.copyToClip.assert_called_once_with(self.window.article.url)
    def test_empty_article_does_not_copy_or_translate(self):
        self.window.article=None; self.window.copy(); self.window.translate()
        self.api.copyToClip.assert_not_called(); self.owner.translateText.assert_not_called()
    def test_close_invalidates_callbacks(self):
        self.window.jobs=types.SimpleNamespace(cancel=Mock()); self.window.closed(None)
        self.assertFalse(self.window.alive); self.window.jobs.cancel.assert_called_once(); self.window.Destroy.assert_called_once()
    def test_search_captures_source_and_language(self):
        self.window.source=types.SimpleNamespace(GetSelection=lambda:1)
        self.window.language=types.SimpleNamespace(GetValue=lambda:'en')
        self.window.query=types.SimpleNamespace(GetValue=lambda:'moon'); self.window.client=Mock(); self.window.request=Mock()
        self.window.search(); operation,done=self.window.request.call_args.args
        operation(); self.window.client.search.assert_called_once_with('moon','wiktionary','en')
    def test_more_uses_captured_query_and_stops_at_fifty(self):
        self.window.search_state=('moon','wikipedia','en'); self.window.next_offset=40; self.window.has_more=True
        self.window.results=[]; self.window.client=Mock(); self.window.request=Mock()
        self.window.more(); operation,done=self.window.request.call_args.args; operation()
        self.window.client.search.assert_called_once_with('moon','wikipedia','en',offset=40)
        self.window.show_results=Mock(); self.window.more_button=Mock(); done([]); self.assertFalse(self.window.has_more)
        self.window.request.reset_mock(); self.window.more(); self.window.request.assert_not_called()

if __name__=='__main__': unittest.main()
