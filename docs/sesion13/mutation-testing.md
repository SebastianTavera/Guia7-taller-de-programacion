# Mutation Testing con mutmut

## Qué se mide

mutmut 3.8 introduce cambios pequeños (mutantes) en el código y ejecuta la suite de pruebas contra
cada uno. Si alguna prueba falla, el mutante muere; si todas pasan, sobrevive, lo que significa que
hay un comportamiento que ninguna prueba verifica.

**Mutation score** = (muertos + timeout) / (total − omitidos). Es la misma fórmula de `mutmut badge`
y de [scripts/check_mutation_score.py](../../scripts/check_mutation_score.py).

**Alcance** (`[tool.mutmut]` en [pyproject.toml](../../pyproject.toml)): el código donde un error
pasa desapercibido con más facilidad y tiene más impacto.

| Módulo | Contenido |
|---|---|
| `vitreo/domain/triage.py` | Clasificación ESI (umbrales de signos vitales) |
| `vitreo/domain/citas.py` | Transiciones de estado y ventana de conflicto de agenda |
| `vitreo/security/passwords.py` | Hash scrypt y verificación en tiempo constante |
| `vitreo/security/tokens.py` | Emisión y validación de JWT |
| `vitreo/security/rate_limit.py` | Bloqueo por intentos fallidos de login |

Los routers, modelos y schemas quedan fuera del alcance: los cubren las pruebas de integración y
mutarlos solo mide a FastAPI y SQLAlchemy.

## Resultados

mutmut no funciona en Windows nativo (necesita `fork`). La medición local se hizo con el mismo
generador de mutantes de mutmut (`create_mutations`), ejecutando pytest contra cada mutante. La
cifra oficial es la del job `Mutation testing` de GitHub Actions.

| Ejecución | Mutantes | Muertos | Sobrevivientes | Score |
|---|---|---|---|---|
| 1. Suite inicial (152 pruebas) | 177 | 173 | 4 | 97,7 % |
| 2. Con las pruebas añadidas (154 pruebas) | 177 | 176 | 1 (equivalente) | **99,4 %** |
| CI (`mutmut run`, Linux) | | | | _completar con la captura_ |

Mutantes por módulo (ejecución 2):

| Módulo | Muertos | Sobrevivientes |
|---|---|---|
| domain/triage.py | 38 | 0 |
| domain/citas.py | 22 | 0 |
| security/passwords.py | 40 | 0 |
| security/rate_limit.py | 42 | 0 |
| security/tokens.py | 34 | 1 |

## Mutantes sobrevivientes analizados

| # | Ubicación | Mutación | Por qué sobrevivió | Acción |
|---|---|---|---|---|
| 1 | `domain/citas.py` `EstadoCita.NO_ASISTIO` | `"NO_ASISTIO"` → `"XXNO_ASISTIOXX"` | Ninguna prueba fijaba el texto de ese estado, que es parte del contrato público de la API. | Prueba añadida: `test_status_values_are_the_public_api_contract` |
| 2 | `domain/citas.py` `EstadoCita.NO_ASISTIO` | `"NO_ASISTIO"` → `"no_asistio"` | Mismo motivo. | La misma prueba lo mata. |
| 3 | `security/rate_limit.py` `_recent_failures` | `self._failures.pop(key, None)` → `pop(None, None)` | El limitador seguía funcionando, pero ya no olvidaba las cuentas con fallos expirados: la memoria crecía sin límite (OWASP API4). Ninguna prueba lo observaba. | Se añadió `__len__` al limitador y la prueba `test_expired_accounts_are_forgotten_to_bound_memory` |
| 4 | `security/tokens.py` `create_access_token` | se elimina `algorithm=ALGORITHM` en `jwt.encode` | **Mutante equivalente**: PyJWT firma con HS256 por defecto, así que el token es idéntico. | Ninguna. El riesgo real (aceptar otro algoritmo) está en `decode`, que fija `algorithms=["HS256"]` y está cubierto por `test_unsigned_alg_none_token_is_rejected`. |

## Ejemplos de mutantes que las pruebas de frontera matan

| Mutación | Prueba que la mata |
|---|---|
| `v.saturacion_oxigeno < SPO2_CRITICA` → `<=` | SpO2 = 90 % debe dar ESI 5, no ESI 1 |
| `recursos_estimados >= 2` → `> 2` | 2 recursos debe dar ESI 3 |
| `failures[0] <= cutoff` → `<` | un fallo de exactamente 60 s ya no cuenta |
| `max(1, math.ceil(...))` → `max(2, ...)` | `Retry-After` debe ser 1 a 0,5 s de expirar |
| `algorithm != ALGORITHM` → `==` | un hash scrypt válido debe verificarse |

## Integración en CI

Job `mutation` de [ci.yml](../../.github/workflows/ci.yml):

1. `mutmut run`
2. `mutmut export-cicd-stats` + `python scripts/check_mutation_score.py --min 50`: **el build falla si el score es menor al 50 %**. El resultado se publica en el resumen del job.
3. En `main`, `mutmut badge` genera el JSON del badge y se publica en la rama `badges`, que lee shields.io desde el README.

## Capturas para el informe (`docs/evidencias/sesion13/`)

- `mutation-ci-summary.png`: resumen del job con la tabla de score.
- `mutation-badge.png`: README con el badge.
- `mutmut-results.png`: salida de `mutmut results` en el log del job.
