# Léxico 0.5.3 — prueba local pendiente de validación en vivo

La traducción utiliza streamGenerateContent para mostrar los fragmentos de texto conforme los entrega Gemini. Solo se anuncia una vez que ha empezado a llegar texto. Se conserva la selección del lector al añadir fragmentos y se guarda en el historial únicamente el resultado completo. Los pensamientos internos y las respuestas interrumpidas no se consideran traducciones terminadas.

La selección del modelo no se ha cambiado. Gemini 3.5 Flash-Lite ya tiene por defecto el nivel de pensamiento minimal según la documentación oficial. No hay evidencia para atribuir la demora al uso de un nivel alto de pensamiento ni para afirmar que cambiar de modelo la resuelva.

Las pruebas automatizadas comprueban fragmentos incrementales, finalización, errores, exclusión de pensamientos y los comportamientos existentes. La comparación real de modelos y la validación del streaming contra Google están pendientes: la política de ejecución de este turno rechazó las peticiones de red fuera del entorno restringido. Esta versión no se ha publicado en GitHub.

Referencia: https://ai.google.dev/gemini-api/docs/generate-content/thinking
