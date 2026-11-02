# Registro de sugerencias del asistente de IA

La guía pide documentar qué generó la IA, cómo se evaluó y qué se corrigió. Completen esta tabla
con las sugerencias que **ustedes** revisaron. Sirve para la pregunta orientadora 4 y para el video.

| # | Archivo / tarea | Sugerencia de la IA | ¿Correcta? | Cómo se detectó el problema | Corrección aplicada |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

Casos de esta práctica donde la primera versión no era correcta y las pruebas o el análisis lo detectaron:

- **Limitador de login**: el código liberaba la memoria de las cuentas con fallos expirados, pero
  ninguna prueba lo verificaba. Un mutante que eliminaba esa limpieza sobrevivió; se añadió
  `__len__` al limitador y una prueba que lo mata.
- **Filtro de citas por fecha**: la primera versión usaba `datetime.combine(fecha, time.max)` como
  límite superior. Se cambió por `inicio_dia + timedelta(days=1)` con `<`, que no depende de la
  precisión de microsegundos.
- **mutmut en Windows**: mutmut 3 no corre en Windows nativo (`fork`). Se movió la ejecución
  oficial a GitHub Actions (Linux).
- **`starlette.testclient`**: aparecía un aviso de deprecación con `httpx`; se cambió a `httpx2`.
