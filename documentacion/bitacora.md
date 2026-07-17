# Notas de Desarrollo — API Cruz Morada

Hola profe. En este espacio dejamos anotados los puntos clave de cómo fuimos armando el código de la API, las decisiones técnicas que tomamos y los resultados de las pruebas de rendimiento que corrimos con los 3.2 millones de filas del CSV.

---

## 1. Carga paralela y rendimiento
Para procesar el archivo CSV gigante de Cruz Morada sin saturar la memoria y cargar los datos rápido al iniciar el servidor, hicimos lo siguiente:
* Implementamos lectura por bloques (chunks) de 50,000 filas en `carga.py`.
* Usamos `ProcessPoolExecutor` para procesar los bloques en paralelo usando los núcleos de la CPU de forma dinámica. En nuestras pruebas en local con 6 procesos, **el dataset completo de 3,242,878 filas válidas se cargó y limpió en memoria en 27.22 segundos**.
* Para optimizar la memoria RAM, pusimos un liberador manual de memoria (`del chunks_procesados`) inmediatamente después de concatenar el DataFrame final.
* Si el CSV viene comprimido (`ventas_completas.csv.gz`), el código lo detecta solo y lo procesa directo usando `gzip` para ahorrar espacio en disco.

---

## 2. Filtros y Zonas Horarias
El motor de filtrado en `filtros.py` opera con máscaras booleanas directas sobre el DataFrame en memoria, lo que nos da respuestas en pocos milisegundos.
* **Fix de medianoche:** Si el cliente consulta una fecha límite superior sin hora (ej: `2024-12-31`), Pandas asume por defecto la medianoche del inicio de ese día. Para no perder transacciones, le sumamos automáticamente un delta de `23:59:59.999999` para desplazar el filtro hasta el último instante del día.
* **Soporte de Zonas Horarias:** Si el cliente manda fechas con formato de zona horaria internacional (como la `Z` de UTC o el offset `-04:00`), Pandas arrojaba un error de tipo al compararlo con las fechas naivas de la base de datos. Lo arreglamos convirtiendo la fecha con zona horaria al huso horario fijo UTC-4 exigido por el enunciado (usando `timezone(timedelta(hours=-4))` en Python) y luego quitándole la zona horaria con `.tz_localize(None)`. Esto evita el crash de tipos en Pandas y además previene descalces horarios (como las 4 horas de desfase entre UTC y UTC-4) en los filtros de fecha, manteniéndose completamente consistente con la especificación del CSV.
* **Validación e Insensibilidad a Mayúsculas:** Inicialmente, FastAPI ignoraba silenciosamente parámetros de consulta no reconocidos en la URL del GET (como typos, ej: `?CANALL=POS`), y además forzaba a que las llaves fueran estrictamente en mayúsculas exactas para el binding (ej: `?genero=Femenino` en minúsculas pasaba la validación pero no filtraba la consulta, ignorándose en silencio). Para solucionar esto, implementamos una extracción dinámica en `get_estadisticas` que lee directamente de `request.query_params.items()`, normaliza las llaves en mayúsculas, rechaza cualquier campo no permitido con HTTP 400 (VF) y procesa los filtros de forma 100% case-insensitive para las llaves, garantizando una validación simétrica y robusta con el POST.

---

## 3. Lógica Estadística
Calculamos las 7 estadísticas descriptivas exigidas en `estadisticas.py` de la siguiente forma:
* **Mediana Manual:** El algoritmo ordena los montos con `np.sort()` y calcula manualmente el valor central dependiendo de si el conteo de registros es par o impar, sin usar funciones automáticas de librerías.
* **Desviación Estándar Poblacional:** Usamos `np.std(valores, ddof=0)` (grados de libertad en cero). Elegimos la poblacional en vez de la muestral porque estamos trabajando con el universo completo de las transacciones reales del periodo, no con una aproximación sobre una muestra aleatoria.
* **Datos vacíos:** Si el motor de filtrado reduce los datos a 0 registros (porque los filtros no cruzaron nada), el código intercepta la lista vacía al inicio y devuelve de inmediato todas las estadísticas en `0.0` o `0` con código HTTP 200, evitando errores de división por cero.

---

## 4. Control de Errores (Formato Pauta)
Configuramos interceptores globales en `main.py` para asegurar que ante cualquier falla, el servidor siempre devuelva exactamente el JSON con los **9 campos unificados** exigidos por la rúbrica:
`detail`, `instance`, `status`, `title`, `type`, `timestamp`, `errorCode`, `errorLabel` y `method`.
* Ocultamos el detalle técnico de la excepción en los errores 500 para evitar fugas de información interna al cliente, dejando el error detallado solo en los logs internos del servidor.

---

## 5. Validación de la Suite de Pruebas
Para garantizar que todo funcione impecable, armamos dos suites de pruebas:
1. **Pruebas Unitarias Automatizadas (con Pytest):** Son **22 pruebas** en `tests/test_api.py` que se ejecutan en segundos inyectando un dataset mock controlado de 4 filas.
2. **Pruebas Funcionales en Vivo (PowerShell):** Creamos el script `test_manual_completo.ps1` que ejecuta **38 consultas reales en vivo** contra el servidor de Uvicorn (filtros válidos, límites de edad, local en 0, floats inválidos, campos erróneos en GET, filtros en minúsculas, etc.) y todas pasan en verde exitosamente (`38/38 pruebas pasaron`).
