# Léxico 0.5.4 — versión de prueba

Opciones permite elegir Google Translate o Gemini. Google Translate usa el mismo endpoint sin clave que la rama stable de Instant Translate: translate.googleapis.com/translate_a/single, client=gtx, dj=1. El código se ha implementado para Léxico; conserva la validación de certificados TLS. El acceso no es la API oficial de Google Cloud y puede cambiar o bloquearse. No hay claves incrustadas ni cambio automático de proveedor.

Las configuraciones existentes conservan Gemini. Para usar Google Translate, seleccionarlo en Opciones. Las instalaciones nuevas empiezan con Google Translate. Las preguntas siempre usan Gemini.

Gemini recibe los resultados por fragmentos. El botón «Medir tiempos de Gemini» compara el modelo configurado con dos Flash-Lite usando únicamente «Hola». Muestra tiempo hasta el primer texto y hasta terminar, o un error seguro. Puede tardar varios minutos si los modelos agotan sus esperas; no cambia el modelo ni la clave guardados. Los modelos disponibles y cuotas dependen del proyecto.

No se ha confirmado la causa de la lentitud de Gemini. Su comparación real y la validación de Google Translate están pendientes por la restricción de red del entorno de ejecución. Para medir en el entorno donde se observa el problema, instalar esta prueba y pulsar «Medir tiempos de Gemini»; el resultado no incluye la clave. La respuesta de Google Translate también debe comprobarse antes de publicar.

Referencia: https://github.com/nvdaaddons/instantTranslate/blob/stable/addon/globalPlugins/instantTranslate/translator.py
