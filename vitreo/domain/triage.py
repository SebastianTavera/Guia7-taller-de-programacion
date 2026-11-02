"""Emergency Severity Index (ESI v4) classification for adult patients.

Simplified decision points of the ESI algorithm (Gilboy et al., 2011):
  A. Needs an immediate life-saving intervention (critical vital signs) -> ESI 1
  B. High-risk situation or severe pain                                  -> ESI 2
  C. Expected resources: 0 -> ESI 5, 1 -> ESI 4, 2 or more -> ESI 3
  D. Danger-zone vital signs with 2+ resources upgrade ESI 3 to ESI 2
"""

from dataclasses import dataclass

# Decision point A: critical vital signs
SPO2_CRITICA = 90  # % (below)
PRESION_SISTOLICA_CRITICA = 80  # mmHg (below)
FC_MIN_CRITICA = 40  # bpm (below)
FC_MAX_CRITICA = 150  # bpm (above)
FR_MIN_CRITICA = 8  # breaths/min (below)
FR_MAX_CRITICA = 35  # breaths/min (above)

# Decision point B
DOLOR_SEVERO = 7  # pain scale 0-10 (at or above)

# Decision point D: danger-zone vital signs
FC_PELIGRO = 100  # bpm (above)
FR_PELIGRO = 20  # breaths/min (above)
SPO2_PELIGRO = 92  # % (below)
TEMPERATURA_PELIGRO = 40.0  # °C (at or above)

NIVEL_CRITICO_MAX = 2  # ESI 1 and 2 raise a real-time alert


@dataclass(frozen=True)
class SignosVitales:
    frecuencia_cardiaca: int
    frecuencia_respiratoria: int
    saturacion_oxigeno: int
    presion_sistolica: int
    temperatura: float
    dolor: int


def requiere_intervencion_inmediata(v: SignosVitales) -> bool:
    return (
        v.saturacion_oxigeno < SPO2_CRITICA
        or v.presion_sistolica < PRESION_SISTOLICA_CRITICA
        or not FC_MIN_CRITICA <= v.frecuencia_cardiaca <= FC_MAX_CRITICA
        or not FR_MIN_CRITICA <= v.frecuencia_respiratoria <= FR_MAX_CRITICA
    )


def en_zona_de_peligro(v: SignosVitales) -> bool:
    return (
        v.frecuencia_cardiaca > FC_PELIGRO
        or v.frecuencia_respiratoria > FR_PELIGRO
        or v.saturacion_oxigeno < SPO2_PELIGRO
        or v.temperatura >= TEMPERATURA_PELIGRO
    )


def clasificar_esi(v: SignosVitales, recursos_estimados: int, alto_riesgo: bool = False) -> int:
    """Return the ESI level (1 = most urgent, 5 = least urgent)."""
    if requiere_intervencion_inmediata(v):
        return 1
    if alto_riesgo or v.dolor >= DOLOR_SEVERO:
        return 2
    if recursos_estimados >= 2:
        return 2 if en_zona_de_peligro(v) else 3
    return 4 if recursos_estimados == 1 else 5


def es_critico(nivel_esi: int) -> bool:
    return nivel_esi <= NIVEL_CRITICO_MAX
