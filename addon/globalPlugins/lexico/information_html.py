"""Conservative HTML reader, adapted from this project's Editor Invisible. GPL-2.0-or-later."""
from html import escape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

class SemanticHTML(HTMLParser):
    tags = set('p div span h1 h2 h3 h4 h5 h6 ul ol li dl dt dd table caption thead tbody tfoot tr th td a strong em b i blockquote br sup sub hr'.split())
    void = {'br', 'hr', 'img', 'input', 'meta', 'link', 'source', 'wbr', 'area', 'embed', 'param', 'track', 'col'}
    blocked = {'script', 'style', 'iframe', 'object', 'svg', 'math', 'canvas', 'video', 'audio', 'picture', 'figure', 'form', 'head'}

    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.stack, self.output = base, [], []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        hidden = any(entry[2] for entry in self.stack) or tag in self.blocked or 'hidden' in attrs or attrs.get('aria-hidden') == 'true'
        hidden |= bool(set(attrs.get('class', '').split()) & {'mw-editsection', 'noprint', 'navbox', 'metadata'})
        emitted = not hidden and tag in self.tags
        if tag not in self.void:
            self.stack.append((tag, emitted, hidden))
        if not emitted: return
        safe = []
        for name in ('id', 'title', 'lang'):
            if attrs.get(name): safe.append((name, attrs[name]))
        if tag == 'a' and attrs.get('href'):
            href = attrs['href'] if attrs['href'].startswith('#') else urljoin(self.base, attrs['href'])
            try:
                parts = urlsplit(href)
                if href.startswith('#') or (parts.scheme in ('http', 'https') and parts.hostname and not parts.username and not parts.password):
                    safe.append(('href', href))
            except ValueError: pass
        if tag in ('th', 'td'):
            for name in ('colspan', 'rowspan'):
                if attrs.get(name, '').isdigit() and 0 < int(attrs[name]) <= 100:
                    safe.append((name, attrs[name]))
            if attrs.get('scope') in ('row', 'col', 'rowgroup', 'colgroup'): safe.append(('scope', attrs['scope']))
        self.output.append('<' + tag + ''.join(' '+k+'="'+escape(v, quote=True)+'"' for k,v in safe) + '>')

    def handle_endtag(self, tag):
        for index in range(len(self.stack)-1, -1, -1):
            if self.stack[index][0] == tag:
                for name, emitted, hidden in reversed(self.stack[index:]):
                    if emitted: self.output.append('</'+name+'>')
                del self.stack[index:]
                break

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.void: self.handle_endtag(tag)

    def handle_data(self, text):
        if not any(entry[2] for entry in self.stack): self.output.append(escape(text))

    def finish(self):
        for name, emitted, hidden in reversed(self.stack):
            if emitted: self.output.append('</'+name+'>')
        self.stack.clear()
        return ''.join(self.output)


def semantic_html(html, base):
    parser = SemanticHTML(base)
    parser.feed(html)
    parser.close()
    return parser.finish()

