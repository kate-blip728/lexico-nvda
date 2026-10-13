# Corrección Gemini en Léxico 0.5.2

La versión publicada al iniciar la revisión era 0.5.1, commit 31f93d8b07119d612e84988872f84e65475a9d60.

Se comprobó con la clave guardada por NVDA, sin imprimirla: DNS y TLS correctos, acceso al modelo gemini-3.5-flash-lite confirmado por la API, y generateContent entre sus operaciones disponibles. Las llamadas de generación con y sin temperature agotaron 30 segundos. Por tanto, no se ha encontrado una ausencia general de Internet ni un modelo inexistente.

Cambios: espera de generación ampliada a 90 segundos; eliminación de temperature, parámetro obsoleto en modelos recientes; mensajes distintos para DNS, TLS y tiempo de espera; clasificación de errores HTTP y motivos de clave/restricciones sin mostrar el mensaje original del servidor; limpieza de espacios exteriores y rechazo de caracteres inválidos en la clave.

Validación final: la traducción real de «Hola» al inglés se completó correctamente en 44,4 segundos con el código corregido. Las 40 pruebas automatizadas pasaron. Esta observación confirma que la espera anterior de 30 segundos era insuficiente en el caso probado. No garantiza que toda futura petición se complete dentro de 90 segundos.

No se cambian claves, certificados, proxy ni la instalación de NVDA. Instalar el paquete requiere abrirlo y reiniciar NVDA.

Referencia: https://ai.google.dev/gemini-api/docs/generate-content/whats-new-gemini-3.6
