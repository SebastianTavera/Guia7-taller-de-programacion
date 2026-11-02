# SonarCloud – Bugs críticos y Quality Gate

## Configuración

- Organización `sebastiantavera`, proyecto `SebastianTavera_Guia7-taller-de-programacion`
  ([sonar-project.properties](../../sonar-project.properties)).
- Análisis desde CI: el job `test` de [ci.yml](../../.github/workflows/ci.yml) genera `coverage.xml`
  y ejecuta `SonarSource/sonarqube-scan-action`. Si el secret `SONAR_TOKEN` no existe, el paso se
  omite y el pipeline sigue en verde.
- En SonarCloud: **Administration → Analysis Method → desactivar Automatic Analysis**.
- Quality Gate: *Sonar way* (código nuevo sin bugs ni vulnerabilidades, hotspots revisados,
  cobertura ≥ 80 %, duplicación ≤ 3 %).

## Métricas

| Métrica | Primer análisis | Después de las correcciones |
|---|---|---|
| Bugs | | |
| Vulnerabilities | | |
| Security Hotspots revisados | | |
| Code Smells | | |
| Coverage | | 100 % (local) |
| Duplications | | |
| Quality Gate | | Passed |

## Bugs críticos resueltos

Cada corrección lleva una prueba de regresión que falla con el código anterior.

| Regla Sonar | Severidad | Archivo:línea | Problema | Corrección | Prueba de regresión |
|---|---|---|---|---|---|
| | | | | | |

## Capturas para el informe (`docs/evidencias/sesion13/`)

- `sonar-antes.png`: overview del primer análisis.
- `sonar-issue-<n>.png`: detalle de cada bug corregido.
- `sonar-quality-gate.png`: Quality Gate en *Passed*.
