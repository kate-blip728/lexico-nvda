# Traducción de voz de NVDA — prueba 0.5.5

Elegir el idioma de destino en Opciones de Léxico. NVDA+Alt+Mayús+T activa o desactiva la traducción de los textos que NVDA anuncia. También puede reasignarse desde Gestos de entrada, categoría Léxico. El modo comienza desactivado cada vez que se inicia NVDA y se desactiva al descargar el complemento.

Este modo usa Google Translate sin clave, independientemente del proveedor para el cuadro de traducción. El texto anunciado se envía a Google; no se guarda en el historial. Las traducciones repetidas se reutilizan en una memoria limitada de la sesión. Se omiten los campos protegidos identificados por NVDA. No traduce audio grabado ni voces ajenas a NVDA.

La cancelación de voz y la desactivación descartan resultados pendientes. La cola es limitada y conserva los comandos de voz; si se llena, un texto supera 5.000 caracteres o se produce un error, se permite leer el original. Ante un error de red se desactiva la traducción para no dejar NVDA sin voz. El sintetizador sigue siendo el configurado en NVDA; elegir un idioma de traducción no instala voces para ese idioma.

Las pruebas simulan los límites de NVDA y de la red. Cubren activación, caché, conservación de comandos, cancelación, desactivación, campos protegidos, prevención de bucles y fallo con lectura original. Falta validar el modo con NVDA en ejecución y el servicio real; se entrega como versión de prueba y no se publica automáticamente.

La investigación de Gemini sigue pendiente. El botón «Medir tiempos de Gemini» de esta versión permite medirla desde NVDA.
