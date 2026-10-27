# Buscar y leer información — Léxico 0.6.0

En la ventana principal pulsa **Buscar información…**. También aparece una orden nueva en Preferencias, Gestos de entrada, Léxico, sin atajo global inicial. Se mantiene el mismo complemento y sus funciones de DLE, DPD, escritura de Windows, historial, preguntas y traducción.

1. Elige **Wikipedia, Wikcionario, Wikisource, Wikilibros o Wikiviajes**.
2. Escribe el código del idioma de esa fuente, por ejemplo **es**, **en**, **fr** o **pt**. No es el idioma de destino de traducción.
3. Escribe la consulta y pulsa Intro o **Buscar**.
4. Recorre los resultados con flechas y pulsa Intro, doble clic o **Abrir resultado en texto**. Más resultados añade hasta diez cada vez, con un máximo de cincuenta por consulta.

## Dos vistas para leer

El cuadro **Artículo** es de solo lectura, con cursor y selección normales. Puedes leer con NVDA, seleccionar con Mayúsculas y flechas y copiar con Control+C. **Buscar en el artículo** encuentra texto sin distinguir mayúsculas y vuelve al principio si hace falta.

**Ver artículo en HTML** abre una vista de lectura con encabezados, listas, tablas, enlaces y atribución. Usa los comandos habituales de NVDA, por ejemplo H, L y T. La vista conserva la estructura que devuelve la fuente; las fórmulas, tablas complejas o artículos sin contenido textual pueden no representarse completamente. Se eliminan scripts, imágenes, marcos, estilos y recursos que se cargarían automáticamente. Seguir un enlace puede abrir su destino mediante el comportamiento normal de la vista de NVDA.

Cerrar la vista HTML mantiene el artículo en la ventana de información. Escape cierra la ventana de información; la ventana principal de Léxico sigue disponible.

## Copiar, editar, traducir y guardar

- **Copiar selección o artículo** usa la selección del cuadro Artículo; si no hay selección, copia todo el artículo, incluida la fuente y su atribución.
- **Copiar enlace de la fuente** copia la dirección original, no una dirección del traductor.
- **Traducir selección o artículo** lleva ese texto al traductor habitual de Léxico, con el servicio y el idioma que hayas elegido en Opciones. Google Translate y Gemini conservan sus requisitos y límites. No cambia silenciosamente de servicio. El artículo original permanece abierto en la ventana de información; el resultado de la traducción aparece en la ventana principal y puede copiarse con Copiar resultado.
- Si el texto supera **30.000 caracteres**, se solicita seleccionar un fragmento. No se recorta ni se traduce solo el principio sin avisar.
- **Editar una copia en Léxico** lleva la selección, o todo el artículo si no hay selección, al cuadro Texto para traducir o corregir. Allí puedes editar y usar el corrector de Windows. El original no cambia ni se escribe en el sitio web.
- **Guardar artículo en historial** conserva el texto original y su fuente en el historial local habitual, respetando el límite de Opciones. No se guardan automáticamente todos los artículos ni las listas de resultados. Con el historial desactivado no se guarda. El historial recupera la versión de texto; no almacena la vista HTML. Las traducciones siguen usando el historial de traducción existente.

Buscar otra consulta o encontrar un error no borra el último artículo abierto. Para volver a la ventana de información, pulsa Buscar información en la principal; se reutiliza la ventana que ya existe.

## Conexiones y límites

La búsqueda no necesita clave. Se consultan las API oficiales de MediaWiki por HTTPS, con diez resultados por petición y un límite de 4 MB por respuesta. Se admite hasta 500.000 caracteres de cuerpo del artículo. La petición tiene límites de espera y no se reintenta automáticamente si la fuente está ocupada. La búsqueda no cubre toda la web ni sitios arbitrarios: se limita a las cinco fuentes indicadas. Algunas ediciones por idioma pueden no existir o no contener el término.

Al buscar se envían consulta, fuente e idioma al proyecto elegido, junto con los datos habituales de conexión. Al abrir un artículo se consulta su identificador. **Copiar, seleccionar o editar una copia no envían una traducción**. Al pulsar Traducir se envía el texto elegido al servicio de Opciones. Si tienes activada la traducción de los anuncios de NVDA, se mantienen sus propias reglas de envío de voz a Google; el nuevo buscador no activa ese modo.

**Cancelar consulta** descarta su entrega; no interrumpe de forma insegura la conexión nativa. Solo hay una petición de información en curso y no se lanza otra hasta que termine, incluso si cancelas o cierras y vuelves a abrir la ventana. Las respuestas de ventanas cerradas o consultas canceladas no se muestran. El artículo ya abierto sigue disponible.

Los artículos se convierten para leerlos dentro de Léxico. Se incluyen la fuente original, el historial de autores, la revisión cuando está disponible y una indicación de consultar la licencia en el original. Las condiciones dependen del proyecto y del contenido: no se atribuye a todos los textos la misma licencia. Esta función no genera resúmenes con IA ni edita Wikipedia.

## Comprobación

84 pruebas automáticas correctas, incluidas las 53 anteriores: cinco fuentes, idiomas, búsquedas, límites, errores de conexión, HTML, citas, cancelación, cierre de ventanas, copia, selección, traducción, historial y conservación del original. Las respuestas de las fuentes y NVDA se simularon. No se ha confirmado una consulta real desde la aplicación ni la escucha y navegación con NVDA real; la ayuda y las pruebas no afirman lo contrario.

Referencias: [búsqueda de MediaWiki](https://www.mediawiki.org/wiki/API:Search), [lectura de artículos](https://www.mediawiki.org/wiki/API:Parsing_wikitext). El saneador HTML se adapta del Editor Invisible del mismo proyecto, conservando GPL-2.0-or-later. No requiere tener instalado Editor Invisible ni otro complemento.
