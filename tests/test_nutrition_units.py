"""Unit tests for backend.utils.nutrition.convert_to_grams.

Covers the spoon table, density-based ml→g, and edge cases.
"""
import pytest

from backend.utils.nutrition import convert_to_grams


def test_grams_pass_through():
    assert convert_to_grams(150, "g") == 150.0


def test_kg_to_g():
    assert convert_to_grams(1.5, "kg") == 1500.0


def test_mg_to_g():
    assert convert_to_grams(500, "mg") == 0.5


@pytest.mark.parametrize("unit", ["ml", "cl", "l"])
def test_volume_without_density_returns_none(unit):
    assert convert_to_grams(100, unit) is None


def test_ml_with_density():
    # Oil density ~0.92 g/ml
    assert convert_to_grams(100, "ml", density_g_per_ml=0.92) == pytest.approx(92.0)


def test_cl_with_density():
    assert convert_to_grams(10, "cl", density_g_per_ml=1.03) == pytest.approx(103.0)


def test_l_with_density():
    assert convert_to_grams(1, "l", density_g_per_ml=1.0) == pytest.approx(1000.0)


@pytest.mark.parametrize(
    "unit",
    [
        "cuillère à soupe", "cuillere a soupe", "cas", "C.A.S", "c.s",
        "Cuillères à soupe",
    ],
)
def test_tablespoon_recognized(unit):
    # 1 cas = 15 ml. With density 1.0 → 15 g.
    assert convert_to_grams(1, unit, density_g_per_ml=1.0) == pytest.approx(15.0)


@pytest.mark.parametrize("unit", ["cuillère à café", "cac", "c.a.c"])
def test_teaspoon_recognized(unit):
    assert convert_to_grams(1, unit, density_g_per_ml=1.0) == pytest.approx(5.0)


def test_pincee_is_direct_mass_no_density_needed():
    # Pincée bypasses density (it's a direct mass approximation).
    assert convert_to_grams(2, "pincée") == pytest.approx(1.0)


def test_verre():
    assert convert_to_grams(1, "verre", density_g_per_ml=1.03) == pytest.approx(206.0)


def test_unknown_unit_returns_none():
    assert convert_to_grams(1, "barrel", density_g_per_ml=1.0) is None
