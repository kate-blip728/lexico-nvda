"""Read-only, bounded MediaWiki information sources for Léxico. GPL-2.0-or-later."""
from dataclasses import dataclass, replace
from html import escape
from html.parser import HTMLParser
import json
import re
import socket
import time
from urllib.parse import urlencode, quote, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from .information_html import semantic_html

SOURCES = {'wikipedia':'Wikipedia', 'wiktionary':'Wikcionario', 'wikisource':'Wikisource', 'wikibooks':'Wikilibros', 'wikivoyage':'Wikiviajes'}
MAX_RESPONSE = 4 * 1024 * 1024
MAX_TEXT = 500000
USER_AGENT = 'Lexico/0.6.0 (NVDA add-on; https://github.com/kate-blip728/lexico-nvda)'

class InformationError(ValueError): pass

def language_code(value):
    value = value.strip().lower()
    if not re.fullmatch(r'[a-z]{2,3}(?:-[a-z0-9]{2,8}){0,2}', value):
        raise InformationError('Indica un código de idioma, por ejemplo es, en, fr o pt.')
    return value

def host_for(source, language):
    if source not in SOURCES: raise InformationError('Fuente no admitida.')
    return language_code(language) + '.' + source + '.org'

def allowed_url(url, host):
    try:
        parts = urlsplit(url)
        valid_host = re.fullmatch(r'[a-z]{2,3}(?:-[a-z0-9]{2,8}){0,2}\.(?:wikipedia|wiktionary|wikisource|wikibooks|wikivoyage)\.org', host)
        return bool(valid_host and parts.scheme == 'https' and parts.hostname == host and parts.port in (None,443) and not parts.username and not parts.password)
    except ValueError: return False

class Redirect(HTTPRedirectHandler):
    def __init__(self, host): self.host = host
    def redirect_request(self, request, fp, code, message, headers, newurl):
        if not allowed_url(newurl, self.host): raise InformationError('La fuente redirigió a una dirección no admitida.')
        return super().redirect_request(request, fp, code, message, headers, newurl)

def request_json(host, params):
    url = 'https://' + host + '/w/api.php?' + urlencode(dict(params, format='json',formatversion=2,maxlag=5))
    if not allowed_url(url, host): raise InformationError('Fuente no válida.')
    request = Request(url, headers={'User-Agent':USER_AGENT,'Accept':'application/json'})
    try:
        deadline = time.monotonic() + 15
        with build_opener(Redirect(host)).open(request, timeout=15) as response:
            chunks, size = [], 0
            while True:
                chunk = response.read(min(65536,MAX_RESPONSE+1-size))
                if not chunk: break
                chunks.append(chunk); size += len(chunk)
                if size > MAX_RESPONSE: raise InformationError('La respuesta supera 4 MB. Prueba otro artículo.')
                if time.monotonic() > deadline: raise InformationError('La consulta tardó demasiado. Inténtalo de nuevo.')
        data = json.loads(b''.join(chunks).decode('utf-8'))
    except HTTPError as error:
        if error.code in (429,503): raise InformationError('La fuente está ocupada. Espera y vuelve a intentarlo.') from None
        raise InformationError('La fuente respondió con un error HTTP ' + str(error.code) + '.') from None
    except (URLError,socket.timeout,TimeoutError,OSError):
        raise InformationError('No se pudo conectar con la fuente. Comprueba la conexión.') from None
    except (UnicodeError,json.JSONDecodeError):
        raise InformationError('La respuesta de la fuente no se pudo interpretar.') from None
    if not isinstance(data,dict): raise InformationError('La fuente devolvió una respuesta no válida.')
    if 'error' in data: raise InformationError('La fuente no pudo completar la consulta. Inténtalo más tarde.')
    return data

class Plain(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.parts=[]
    def handle_starttag(self, tag, attrs):
        if tag in ('p','div','tr','br','blockquote','dt','dd'): self.parts.append('\n')
        if tag in ('ul','ol','table'): self.parts.append('\n')
        if tag == 'li': self.parts.append('\n• ')
        if tag in ('td','th'): self.parts.append(' | ')
        if re.fullmatch('h[1-6]',tag): self.parts.append('\n\n'+'#'*int(tag[1])+' ')
    def handle_endtag(self, tag):
        if tag in ('p','div','li','tr','ul','ol','table') or re.fullmatch('h[1-6]',tag): self.parts.append('\n')
    def handle_data(self, data): self.parts.append(data)
    def text(self):
        lines=[re.sub(r'[ \t\r\f\v]+',' ',line).strip() for line in ''.join(self.parts).split('\n')]
        return re.sub('\n{3,}','\n\n','\n'.join(lines)).strip()

def plain(html):
    parser=Plain(); parser.feed(semantic_html(str(html or ''),'')); parser.close(); return parser.text()

@dataclass(frozen=True)
class Result:
    source: str
    language: str
    pageid: int
    title: str
    snippet: str = ''
    @property
    def url(self): return 'https://' + host_for(self.source,self.language) + '/wiki/' + quote(self.title.replace(' ','_'),safe='')

@dataclass(frozen=True)
class Article:
    title: str
    text: str
    html: str
    url: str
    source: str
    language: str

class Client:
    def __init__(self, fetch=request_json): self.fetch=fetch
    def search(self, query, source='wikipedia', language='es', offset=0):
        query=query.strip(); language=language_code(language)
        if not query or len(query)>300: raise InformationError('Escribe una búsqueda de entre 1 y 300 caracteres.')
        if type(offset) is not int or not 0<=offset<=40: raise InformationError('Límite de 50 resultados por consulta.')
        data=self.fetch(host_for(source,language),dict(action='query',list='search',srsearch=query,srnamespace=0,srlimit=10,sroffset=offset,srprop='snippet'))
        rows=[]
        for row in data.get('query',{}).get('search',[]):
            if not isinstance(row,dict) or not isinstance(row.get('title'),str) or type(row.get('pageid')) is not int or row['pageid']<=0: continue
            rows.append(Result(source,language,row['pageid'],row['title'],plain(row.get('snippet',''))))
        return rows[:10]
    def article(self, result):
        host=host_for(result.source,result.language)
        if type(result.pageid) is not int or result.pageid<=0: raise InformationError('Resultado no válido.')
        data=self.fetch(host,dict(action='parse',pageid=result.pageid,prop='text|revid|displaytitle',redirects=1,disableeditsection=1))
        parsed=data.get('parse',{}); raw=parsed.get('text','')
        if isinstance(parsed.get('title'),str) and parsed['title']: result=replace(result,title=parsed['title'])
        if isinstance(raw,dict): raw=raw.get('*','')
        if not isinstance(raw,str): raise InformationError('El artículo no contiene texto legible.')
        html=semantic_html(raw,result.url); body=plain(html)
        if not body: raise InformationError('El artículo no contiene texto legible.')
        if len(body)>MAX_TEXT: raise InformationError('El artículo supera 500.000 caracteres. Abre su fuente original.')
        revision=parsed.get('revid')
        revision_url='https://'+host+'/w/index.php?oldid='+str(revision) if type(revision) is int and revision>0 else result.url
        attribution=('Fuente: '+SOURCES[result.source]+'\n'+result.url+'\nHistorial y autores: '+result.url+'?action=history\nVersión consultada: '+revision_url+'\nConsulta la licencia y las condiciones de reutilización en la fuente original. Texto convertido para lectura en Léxico.')
        footer='<h2>Fuente y atribución</h2><p><a href="'+escape(result.url,quote=True)+'">Abrir fuente original</a></p><p>'+escape(attribution).replace('\n','<br>')+'</p>'
        return Article(result.title,result.title+'\n\n'+body+'\n\n'+attribution,'<h1>'+escape(result.title)+'</h1>'+html+footer,result.url,result.source,result.language)
