"""ESI classification: every threshold is tested on both sides of its boundary."""

from dataclasses import replace

import pytest

from vitreo.domain.triage import SignosVitales, clasificar_esi, en_zona_de_peligro, es_critico

NORMALES = SignosVitales(
    frecuencia_cardiaca=80,
    frecuencia_respiratoria=16,
    saturacion_oxigeno=98,
    presion_sistolica=120,
    temperatura=36.8,
    dolor=2,
)


def con(**cambios: float) -> SignosVitales:
    return replace(NORMALES, **cambios)


@pytest.mark.parametrize(
    ("cambios", "esperado"),
    [
        ({"saturacion_oxigeno": 89}, 1),
        ({"saturacion_oxigeno": 90}, 5),
        ({"presion_sistolica": 79}, 1),
        ({"presion_sistolica": 80}, 5),
        ({"frecuencia_cardiaca": 39}, 1),
        ({"frecuencia_cardiaca": 40}, 5),
        ({"frecuencia_cardiaca": 150}, 5),
        ({"frecuencia_cardiaca": 151}, 1),
        ({"frecuencia_respiratoria": 7}, 1),
        ({"frecuencia_respiratoria": 8}, 5),
        ({"frecuencia_respiratoria": 35}, 5),
        ({"frecuencia_respiratoria": 36}, 1),
    ],
)
def test_critical_vital_signs_need_immediate_intervention(cambios: dict, esperado: int) -> None:
    assert clasificar_esi(con(**cambios), recursos_estimados=0) == esperado


def test_critical_vitals_win_over_every_other_criterion() -> None:
    assert clasificar_esi(con(saturacion_oxigeno=80, dolor=10), recursos_estimados=3, alto_riesgo=True) == 1


@pytest.mark.parametrize(("dolor", "esperado"), [(6, 5), (7, 2), (10, 2)])
def test_severe_pain_is_esi_2(dolor: int, esperado: int) -> None:
    assert clasificar_esi(con(dolor=dolor), recursos_estimados=0) == esperado


def test_high_risk_situation_is_esi_2() -> None:
    assert clasificar_esi(NORMALES, recursos_estimados=0, alto_riesgo=True) == 2


@pytest.mark.parametrize(("recursos", "esperado"), [(0, 5), (1, 4), (2, 3), (5, 3)])
def test_expected_resources_define_levels_3_to_5(recursos: int, esperado: int) -> None:
    assert clasificar_esi(NORMALES, recursos_estimados=recursos) == esperado


@pytest.mark.parametrize(
    ("cambios", "en_peligro"),
    [
        ({"frecuencia_cardiaca": 100}, False),
        ({"frecuencia_cardiaca": 101}, True),
        ({"frecuencia_respiratoria": 20}, False),
        ({"frecuencia_respiratoria": 21}, True),
        ({"saturacion_oxigeno": 92}, False),
        ({"saturacion_oxigeno": 91}, True),
        ({"temperatura": 39.9}, False),
        ({"temperatura": 40.0}, True),
        ({}, False),
    ],
)
def test_danger_zone_vitals(cambios: dict, en_peligro: bool) -> None:
    vitales = con(**cambios)

    assert en_zona_de_peligro(vitales) is en_peligro
    assert clasificar_esi(vitales, recursos_estimados=2) == (2 if en_peligro else 3)


def test_danger_zone_only_upgrades_patients_needing_two_resources() -> None:
    assert clasificar_esi(con(frecuencia_cardiaca=120), recursos_estimados=1) == 4


@pytest.mark.parametrize(("nivel", "critico"), [(1, True), (2, True), (3, False), (5, False)])
def test_es_critico(nivel: int, critico: bool) -> None:
    assert es_critico(nivel) is critico
