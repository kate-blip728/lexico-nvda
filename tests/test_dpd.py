import unittest
from unittest.mock import patch
from test_services import services

class DPDChecks(unittest.TestCase):
    def test_article_only_preserves_inline_text_and_multiple_entries(self):
        page = ('<nav>Menú</nav><link rel="canonical" href="https://www.rae.es/dpd/tilde">'
                '<entry><header>tilde<sup>1</sup></header>'
                '<p>La <em>acentuación</em> y las dudas &amp; usos.</p>'
                '<script>no mostrar</script><p>Segundo apartado.</p></entry>'
                '<entry><header>tilde<sup>2</sup></header><p>Otro significado.</p></entry><footer>Redes</footer>')
        with patch.object(services, 'request', return_value=page) as request:
            result = services.lookup_dpd(' sólo ')
        request.assert_called_once_with('https://www.rae.es/dpd/s%C3%B3lo')
        self.assertIn('La acentuación y las dudas & usos.', result)
        self.assertIn('tilde^1', result)
        self.assertIn('tilde^2', result)
        self.assertIn('\n\nSegundo apartado.', result)
        self.assertTrue(result.endswith('https://www.rae.es/dpd/tilde'))
        for excluded in ['Menú', 'Redes', 'no mostrar']:
            self.assertNotIn(excluded, result)
    def test_missing_article_is_not_site_navigation_result(self):
        for page in ['<nav>Diccionario panhispánico de dudas</nav>', '<entry></entry>', '<h1>Access denied</h1>']:
            with self.subTest(page=page), patch.object(services, 'request', return_value=page):
                with self.assertRaises(services.ServiceError):
                    services.lookup_dpd('noexiste')
    def test_invalid_input_never_requests(self):
        with patch.object(services, 'request') as request:
            for word in ['', ' ', 'a'*151, 'una\notra']:
                with self.assertRaises(services.ServiceError):
                    services.lookup_dpd(word)
            request.assert_not_called()
    def test_service_error_remains_visible(self):
        with patch.object(services, 'request', side_effect=services.ServiceError('No se pudo conectar.')):
            with self.assertRaisesRegex(services.ServiceError, 'No se pudo conectar'):
                services.lookup_dpd('haber')

    def test_examples_have_separate_paragraphs_with_their_citations(self):
        parser = services.DPDParser()
        parser.feed('<entry><p>Explicación: <span class="cita">«Un <em>ejemplo</em>» '
                    '<span class="bib">(Autor 2025)</span></span>; '
                    '<span class="cita">«Otro ejemplo»</span>. Más explicación.</p></entry>')
        text = parser.text()
        self.assertIn('Explicación:\n\n«Un ejemplo» (Autor 2025);\n\n«Otro ejemplo».', text)

    def test_long_results_have_short_lines_and_blank_separators_without_word_loss(self):
        original = ' '.join(['Esta frase mantiene todas sus palabras y su puntuación.'] * 15)
        formatted = services.format_result(original)
        self.assertEqual(formatted.split(), original.split())
        self.assertIn('\n\n', formatted)
        self.assertTrue(all(len(line) <= 90 for line in formatted.splitlines()))
        self.assertTrue(all(len(block.splitlines()) <= 3 for block in formatted.split('\n\n')))

    def test_existing_headings_and_paragraphs_are_preserved(self):
        text = 'Apartado 1\r\n\r\nTexto breve.\r\n\r\nApartado 2\r\nEjemplo.'
        self.assertEqual(services.format_result(text), 'Apartado 1\n\nTexto breve.\n\nApartado 2\nEjemplo.')
