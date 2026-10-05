# Léxico para NVDA — versión 0.5.1

[Descargar Léxico 0.5.1 para NVDA](https://github.com/kate-blip728/lexico-nvda/raw/refs/heads/main/lexico-0.5.1.nvda-addon)

Repositorio público con el código fuente, las pruebas y el generador del paquete. Versión inicial: consulta las limitaciones de validación antes de instalar.

Preparado para NVDA 2026.2, la versión estable oficial publicada el 31 de agosto de 2026.

## Instalación y uso

1. Abre `lexico-0.5.1.nvda-addon` con NVDA y acepta la instalación. Reinicia NVDA cuando lo solicite.
2. En el menú NVDA, abre Herramientas → Léxico: diccionario y traducción.
3. Escribe una palabra y pulsa Buscar en el DLE, o pulsa Palabra del día.
4. Lee el resultado con las flechas en el campo Resultado. Incluye definiciones, ejemplos cuando existen y sinónimos y antónimos por acepción. Si el servicio no los indica, se comunica expresamente; no se inventan.
5. Para traducir, abre Opciones, introduce tu clave de API de Gemini, el idioma de destino y el modelo. El modelo inicial es `gemini-3.5-flash-lite`; puedes cambiarlo por uno al que tenga acceso tu cuenta.
6. Escribe o pega el texto, y pulsa Traducir. El resultado aparece en la misma ventana. Copiar resultado solo modifica el portapapeles al pulsar ese botón.

Tab y Mayús+Tab recorren los controles; Escape cierra la ventana. El gesto NVDA+Control+Mayús+D consulta la definición del portapapeles; puede cambiarse en Gestos de entrada. Los demás comandos no tienen atajos globales de fábrica. Puedes asignarlos en NVDA → Preferencias → Gestos de entrada → Léxico: abrir, palabra del día, traducir selección y traducir portapapeles.

## Configuración que se conserva

Al aceptar Opciones se guardan inmediatamente el idioma, el modelo y la clave en `lexico-settings.json`, dentro del directorio de configuración de la copia de NVDA que estás utilizando. No depende de la opción general de guardar NVDA al salir. Cambiar perfiles no cambia estas preferencias. Los gestos asignados se guardan mediante NVDA.

La clave se protege mediante DPAPI de Windows, vinculada al usuario de Windows. Si llevas la configuración a otro usuario o equipo, tendrás que volver a introducirla. Los textos y resultados se guardan en el historial local con el límite elegido en Opciones.

## Servicios y privacidad

Las consultas de palabras se envían a https://rae-api.com, un intermediario independiente **no oficial**, que proporciona datos del DLE de la RAE y ASALE. La conexión directa a https://dle.rae.es devolvió HTTP 403 en las pruebas, por lo que no se usa para obtener resultados. No se abre un navegador para las consultas. El intermediario puede aplicar límites y sus datos pueden diferir de la actualización más reciente del DLE. La ausencia de sinónimos o antónimos significa que el servicio no los devuelve para esa acepción.

La traducción envía a Google Gemini el texto que indiques y el idioma elegido. La clave solo se envía a la API de Google. Necesitas una clave de API; una sesión abierta en la aplicación Gemini no la sustituye. Google puede aplicar cuotas o costes de acuerdo con tu cuenta. Puedes obtenerla en https://aistudio.google.com/apikey.

No se realizan consultas automáticas al iniciar NVDA. El complemento no se activa en modo seguro.

## Estado de validación

Se han comprobado conexiones reales al diccionario, sinónimos, antónimos y palabra del día, la persistencia del idioma y modelo en Windows, el almacenamiento de una clave con cifrado simulado, errores y respuestas simuladas de Gemini, y la estructura del paquete. **No se ha probado la interfaz ejecutándose dentro de NVDA ni una traducción real con una clave de Gemini.** La prueba del cifrado nativo DPAPI no pudo ejecutarse porque el entorno aislado no permite acceder al perfil de Windows necesario; su funcionamiento dentro de NVDA queda pendiente. Si Windows no permite cifrar, el complemento avisa y no guarda la clave en texto plano. Es una versión inicial para probar, no una compatibilidad certificada. `lastTestedNVDAVersion` del manifiesto indica el objetivo del paquete, no una prueba manual completada.

## Proyecto para GitHub

Repositorio: https://github.com/kate-blip728/lexico-nvda . Contiene el código fuente del complemento, pruebas, un generador del paquete y el instalable en la raíz del repositorio.

Para generar el archivo instalable: `python build.py`.
Para ejecutar pruebas: `python -m unittest discover -s tests -v`.
Para comprobar el servicio real: `python tests/live_check.py`.

Referencias: https://www.nvaccess.org/post/nvda-2026-2/ ; https://rae-api.com/docs/ ; https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite .

## Cambios de la versión 0.2.0

Idioma y modelo ahora son cuadros combinados editables: puedes recorrer las opciones con las flechas o escribir una opción distinta. Se mantienen los valores previamente guardados. Usa «Usar modelo recomendado» para seleccionar Gemini 3.5 Flash-Lite y acepta Opciones para guardar el cambio. En una instalación nueva es el modelo predeterminado.

Gemini 3.5 Flash-Lite se recomienda aquí para traducciones de texto por su rapidez y menor coste; Google lo incluye entre las opciones para proyectos nuevos: https://ai.google.dev/gemini-api/docs/models . No hay una prueba comparativa de calidad de traducción propia.

En Opciones hay botones para crear la clave de Gemini en Google AI Studio (https://aistudio.google.com/apikey) y para abrir las credenciales de Google Cloud (https://console.cloud.google.com/apis/credentials). AI Studio permite crear la clave para Gemini vinculada a un proyecto de Google Cloud. El complemento utiliza Gemini Developer API; el botón de Cloud abre la gestión de credenciales, no configura Vertex AI ni otras APIs de Google.

La versión 0.2.0 sigue pendiente de verificación interactiva dentro de NVDA y de una traducción real con una clave de Gemini.

## Escritura, corrección y preguntas — versión 0.3.0

### Cómo se escribe

Escribe una sola palabra en el campo Palabra o expresión y pulsa Comprobar escritura, en la sección Cómo se escribe. Usa el corrector de Windows y muestra las sugerencias en Resultado. No utiliza Gemini. Que Windows no marque una palabra no garantiza que sea adecuada en el contexto; por ejemplo, las dudas entre «haber» y «a ver» requieren considerar la frase.

### Corregir con Windows

Escribe o pega el texto en Texto para traducir o corregir y pulsa Corregir con Windows. En la ventana de revisión:

1. Pulsa Revisar ortografía.
2. Elige una aparición en Palabras detectadas.
3. Elige una sugerencia en el cuadro combinado o escribe el reemplazo. Un reemplazo vacío elimina esa aparición.
4. Pulsa Aplicar a esta aparición. Se aplica solo ese cambio y vuelve a revisar el texto.
5. Pulsa Usar texto revisado para llevarlo al campo de texto de Léxico, o Cancelar para descartar la revisión.

El complemento llama a Windows Spell Checking API (ISpellChecker), sin realizar peticiones de red para esta función y sin utilizar Gemini. Revisa ortografía; no ofrece una revisión gramatical completa. Las sugerencias no se aplican automáticamente. No modifica el documento de otra aplicación ni el portapapeles; puedes copiar el texto revisado manualmente.

El idioma del corrector se elige en Opciones mediante un cuadro combinado editable y se guarda junto con las demás preferencias. Inicialmente es es-ES y es independiente del idioma de traducción. Windows necesita tener instalado un diccionario para el idioma elegido. Si no está disponible, se muestra un mensaje; el complemento no lo sustituye por Gemini.

### Preguntar a Gemini

Pulsa Preguntar a Gemini y escribe una duda gramatical u otra consulta. Al aceptar, solo se envía esa pregunta a Gemini. La respuesta aparece en Resultado. Usa la clave y el modelo configurados, y solicita una respuesta en español. No envía automáticamente el texto que estés revisando.

### Verificación de esta versión

Pruebas automáticas: 13 aprobadas y una omitida (cifrado nativo DPAPI). Se comprobaron la aplicación de reemplazos con posiciones UTF-16 de Windows, la conservación de emoji, la eliminación de una aparición, el idioma del corrector guardado y la solicitud separada de preguntas a Gemini mediante una respuesta simulada.

La llamada real a CreateSpellChecker en este entorno devuelve 0x80070005 (acceso denegado), por lo que la revisión nativa y las sugerencias **quedan pendientes de verificar dentro de NVDA**, igual que la interfaz, el cifrado nativo de la clave y una petición real a Gemini. No se presenta esta versión inicial como totalmente probada.

Referencia de Windows: https://learn.microsoft.com/en-us/windows/win32/api/spellcheck/nn-spellcheck-ispellchecker .

## Corrección del portapapeles — versión 0.3.1

El botón Traducir portapapeles captura el texto y comienza la traducción inmediatamente con el idioma y modelo guardados. No es necesario pulsar Traducir después. El gesto Traducir el texto del portapapeles usa esa misma traducción directa. El original aparece en el campo de entrada; Resultado muestra la respuesta de Gemini o el error de la consulta, nunca una copia del original como sustituto de la traducción.

Para pegar sin traducir puedes usar Control+V en el campo de texto. Si hay una consulta en curso, espera a que termine antes de iniciar otra. El portapapeles original se conserva hasta que pulses Copiar resultado.

Se verificaron botón y gesto con Gemini simulado, portapapeles vacío y consulta en curso. Pruebas: 17 aprobadas y una omitida (DPAPI). La prueba con Gemini real y dentro de NVDA sigue pendiente.

## Texto devuelto sin cambios — versión 0.4.0

Idioma de destino significa el idioma al que quieres traducir, no el idioma del texto original. Para traducir de inglés a español, elige español en Opciones y acepta. Las preferencias anteriores se mantienen.

Si Gemini devuelve exactamente el texto original, el complemento hace un solo reintento con una instrucción explícita. Si no cambia, muestra un aviso con el idioma de destino, en lugar de presentar el original como una traducción completada. Esto puede ocurrir cuando el original ya está en el idioma de destino o es un nombre propio. El reintento supone una petición adicional a Gemini y se somete a sus cuotas y costes. Las preguntas a Gemini no usan este reintento.

Se verificaron el reintento y el aviso con respuestas simuladas: 19 pruebas aprobadas y una omitida (DPAPI). No se ha reproducido el caso del usuario con una clave real; la verificación de Gemini y de la interfaz dentro de NVDA sigue pendiente.

## Actualizaciones e historial

Buscar actualizaciones consulta `update.json` del repositorio público y ofrece descargar el instalador, verifica SHA-256 y manifiesto y lo abre con NVDA. Publicar siempre el paquete y `update.json` juntos en la raíz de main. `build.py` genera ambos. No se instala sin intervención del usuario.

Historial conserva consultas correctas y traducciones con texto original, resultado, fecha, idioma y modelo. Opciones permite de 0 a 10000 entradas (100 por defecto); 0 desactiva y vacía el historial. Recuperar no envía otra petición. Se puede copiar, eliminar y vaciar. Los textos se almacenan localmente sin cifrado en `lexico-history.json`, sin claves de API.

## DPD y definición del portapapeles — versión 0.5.0

Escribe una palabra o expresión en «Palabra o expresión» y pulsa «Consultar DPD». El artículo del Diccionario panhispánico de dudas de la RAE y ASALE aparece en Resultado dentro de Léxico, con sus apartados y ejemplos; se puede leer con las flechas, copiar y recuperar desde el historial. Consulta directamente https://www.rae.es/dpd/; no usa Gemini ni abre el navegador. Si el sitio remite a otra entrada, se muestra esa entrada y su dirección oficial. Las referencias del artículo se presentan como texto; para consultar otra entrada, escribe su nombre en el campo de palabra y vuelve a pulsar Consultar DPD. Si no hay entrada o el sitio bloquea el acceso, se muestra un aviso.

Copia una palabra o expresión y pulsa NVDA+Control+Mayús+D para consultar su definición en el DLE. También puedes usar «Definición del portapapeles». Ambos capturan el portapapeles, abren Léxico si hace falta y consultan directamente sin sobrescribir el texto de traducción. Admiten una sola línea de hasta 150 caracteres. El gesto puede modificarse en NVDA → Preferencias → Gestos de entrada → Léxico → Consulta la definición de la palabra del portapapeles en el DLE dentro de Léxico.

Se verificó el acceso real a las entradas haber, porque y solo (remite a tilde), y una consulta sin entrada. Las pruebas automáticas comprueban la extracción exclusiva del artículo, entidades y apartados, portapapeles vacío o excesivo y el gesto con NVDA simulado. Queda pendiente comprobar la interfaz y el atajo en una sesión real de NVDA.

## Lectura por fragmentos — versión 0.5.1

Los resultados y la vista del historial utilizan líneas reales de hasta 90 caracteres (salvo palabras o direcciones más largas) y una línea en blanco como máximo cada tres líneas de un párrafo largo. Se conservan los apartados. En el DPD, los ejemplos citados se separan de la explicación y conservan su referencia. En el DLE, cada definición, ejemplo, lista de sinónimos y antónimos tiene su propio párrafo. El resultado se adapta también al ancho de la ventana. Los resultados antiguos del historial reciben el nuevo formato al recuperarlos, sin modificar el texto almacenado. Usa las flechas para recorrer los fragmentos. Leer todo de NVDA continúa leyendo hasta el final.
