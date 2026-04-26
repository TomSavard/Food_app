"""Tests for GET /api/meal-plan/nutrition."""
from datetime import date, timedelta

import pytest

from backend.db.models import (
    Ingredient,
    IngredientDatabase,
    MealPlanSlot,
    Recipe,
)
from backend.services.anses import DAILY_MACROS, RDI

CAL_KEY = "Energie, Règlement UE N° 1169 2011 (kcal 100 g)"
PROT_KEY = "Protéines, N x facteur de Jones (g 100 g)"


def _next_monday() -> date:
    today = date.today()
    return today + timedelta(days=(0 - today.weekday()) % 7 or 7)


@pytest.fixture
def make_canonical(db_session):
    def _make(name: str, *, nutrition_data=None, density=None):
        row = IngredientDatabase(
            alim_nom_fr=name,
            nutrition_data=nutrition_data or {},
            density_g_per_ml=density,
        )
        db_session.add(row)
        db_session.flush()
        return row
    return _make


@pytest.fixture
def make_recipe_with_ing(db_session, make_canonical):
    def _make(name="R", servings=2, ings=()):
        r = Recipe(name=name, servings=servings)
        db_session.add(r); db_session.flush()
        for ing_name, qty, unit, fk in ings:
            db_session.add(Ingredient(
                recipe_id=r.recipe_id,
                name=ing_name,
                quantity=qty,
                unit=unit,
                ingredient_db_id=fk,
            ))
        db_session.flush()
        return r
    return _make


def _add_slot(db_session, recipe, d, servings, position=0):
    s = MealPlanSlot(
        slot_date=d, position=position, recipe_id=recipe.recipe_id, servings=servings,
    )
    db_session.add(s); db_session.flush()
    return s


def test_empty_week(client):
    monday = _next_monday().isoformat()
    res = client.get("/api/meal-plan/nutrition", params={"week_start": monday})
    assert res.status_code == 200
    body = res.json()
    assert body["week_start"] == monday
    assert len(body["days"]) == 7
    assert all(all(v == 0.0 for v in d["macros"].values()) for d in body["days"])
    assert body["week"] == {}
    assert body["untracked"] == []
    # ANSES keys round-tripped.
    assert set(body["rdi"].keys()) == set(RDI.keys())


def test_macros_scale_with_servings(client, db_session, make_canonical, make_recipe_with_ing):
    rice = make_canonical(
        "Riz",
        nutrition_data={CAL_KEY: 130, PROT_KEY: 2.5},
    )
    r = make_recipe_with_ing(name="Bowl", servings=2, ings=[
        ("riz", 200, "g", rice.id),
    ])
    monday = _next_monday()
    # Slot with servings=4 → 2x scaling.
    _add_slot(db_session, r, monday, servings=4)

    res = client.get("/api/meal-plan/nutrition", params={"week_start": monday.isoformat()}).json()
    day0 = res["days"][0]
    # 200g of rice × 2x scale = 400g, calories per 100g = 130 → 130 * 4 = 520.
    assert day0["macros"][CAL_KEY] == pytest.approx(520.0, rel=1e-3)
    assert day0["macros"][PROT_KEY] == pytest.approx(10.0, rel=1e-3)
    # Week totals match the only day.
    assert res["week"][CAL_KEY] == pytest.approx(520.0, rel=1e-3)


def test_untracked_missing_fk(client, db_session, make_recipe_with_ing):
    r = make_recipe_with_ing(name="Soup", servings=2, ings=[
        ("mystère", 100, "g", None),
    ])
    monday = _next_monday()
    _add_slot(db_session, r, monday, servings=2)

    res = client.get("/api/meal-plan/nutrition", params={"week_start": monday.isoformat()}).json()
    assert any(
        u["reason"] == "missing_fk" and u["ingredient_name"] == "mystère"
        for u in res["untracked"]
    )


def test_untracked_no_data(client, db_session, make_canonical, make_recipe_with_ing):
    stub = make_canonical("StubIngredient", nutrition_data={})
    r = make_recipe_with_ing(name="X", servings=1, ings=[
        ("stub", 50, "g", stub.id),
    ])
    monday = _next_monday()
    _add_slot(db_session, r, monday, servings=1)

    res = client.get("/api/meal-plan/nutrition", params={"week_start": monday.isoformat()}).json()
    assert any(u["reason"] == "no_data" for u in res["untracked"])


def test_untracked_missing_density(client, db_session, make_canonical, make_recipe_with_ing):
    oil = make_canonical("Huile", nutrition_data={CAL_KEY: 900}, density=None)
    r = make_recipe_with_ing(name="Salad", servings=1, ings=[
        ("huile", 10, "ml", oil.id),
    ])
    monday = _next_monday()
    _add_slot(db_session, r, monday, servings=1)

    res = client.get("/api/meal-plan/nutrition", params={"week_start": monday.isoformat()}).json()
    assert any(
        u["reason"] == "missing_density" and u["ingredient_name"] == "huile"
        for u in res["untracked"]
    )
    # No nutrition contribution because density is missing.
    assert all(d["macros"][CAL_KEY] == 0.0 for d in res["days"])


def test_density_resolves_volume(client, db_session, make_canonical, make_recipe_with_ing):
    oil = make_canonical("Huile olive", nutrition_data={CAL_KEY: 900}, density=0.92)
    r = make_recipe_with_ing(name="Salad", servings=1, ings=[
        ("huile", 100, "ml", oil.id),
    ])
    monday = _next_monday()
    _add_slot(db_session, r, monday, servings=1)

    res = client.get("/api/meal-plan/nutrition", params={"week_start": monday.isoformat()}).json()
    # 100ml × 0.92 = 92g. 900 kcal/100g × 92g/100 = 828 kcal.
    assert res["week"][CAL_KEY] == pytest.approx(828.0, rel=1e-3)


def test_two_slots_two_days_sum_in_week(client, db_session, make_canonical, make_recipe_with_ing):
    rice = make_canonical("Riz2", nutrition_data={CAL_KEY: 100})
    r = make_recipe_with_ing(name="B", servings=1, ings=[("riz", 100, "g", rice.id)])
    monday = _next_monday()
    _add_slot(db_session, r, monday, servings=1)
    _add_slot(db_session, r, monday + timedelta(days=2), servings=1)

    res = client.get("/api/meal-plan/nutrition", params={"week_start": monday.isoformat()}).json()
    assert res["days"][0]["macros"][CAL_KEY] == pytest.approx(100.0)
    assert res["days"][2]["macros"][CAL_KEY] == pytest.approx(100.0)
    assert res["week"][CAL_KEY] == pytest.approx(200.0)


def test_daily_macros_keys_are_eight(client):
    monday = _next_monday().isoformat()
    res = client.get("/api/meal-plan/nutrition", params={"week_start": monday}).json()
    assert len(res["days"][0]["macros"]) == 8
    assert set(res["days"][0]["macros"].keys()) == set(DAILY_MACROS)


def test_rdi_changes_with_sex(client):
    monday = _next_monday().isoformat()
    male = client.get("/api/meal-plan/nutrition", params={"week_start": monday, "sex": "male"}).json()
    female = client.get("/api/meal-plan/nutrition", params={"week_start": monday, "sex": "female"}).json()
    diffs = [k for k in male["rdi"] if male["rdi"][k] != female["rdi"].get(k)]
    assert len(diffs) >= 5
