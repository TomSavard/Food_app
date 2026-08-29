"""Direct tests for the read-side chat tools (PR A)."""
import uuid
from datetime import date, timedelta

import pytest

from backend.api.chat import (
    _build_nutrition_tools,
    _build_recipe_read_tools,
    _build_reference_read_tools,
    _build_seasonality_tools,
    _build_shopping_read_tools,
)
from backend.db.models import (
    Ingredient,
    IngredientDatabase,
    MealPlanSlot,
    Recipe,
    ShoppingList,
    ShoppingListContribution,
)


@pytest.fixture
def fresh():
    return f"TEST_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def recipe_tools(db_session):
    return _build_recipe_read_tools(db_session)


@pytest.fixture
def shopping_tools(db_session):
    return _build_shopping_read_tools(db_session)


@pytest.fixture
def nutrition_tools(db_session):
    return _build_nutrition_tools(db_session)


@pytest.fixture
def seasonality_tools(db_session):
    return _build_seasonality_tools(db_session)


@pytest.fixture
def reference_tools(db_session):
    return _build_reference_read_tools(db_session)


def _make_recipe(db, name, *, servings=2, cuisine=None, tags=None):
    r = Recipe(name=name, servings=servings, cuisine_type=cuisine, tags=tags or [])
    db.add(r); db.flush()
    return r


# ---- get_recipe / recipe_overview / get_recipe_nutrition ----

def test_get_recipe_returns_detail(recipe_tools, db_session, fresh):
    [get_recipe, _overview, _nutri] = recipe_tools
    r = _make_recipe(db_session, f"{fresh}_PASTA", servings=2, cuisine="italienne")
    db_session.add(Ingredient(recipe_id=r.recipe_id, name="pâtes", quantity=200, unit="g"))
    db_session.flush()
    res = get_recipe(str(r.recipe_id))
    assert res["name"] == f"{fresh}_PASTA"
    assert res["servings"] == 2
    assert res["cuisine_type"] == "italienne"
    assert any(i["name"] == "pâtes" for i in res["ingredients"])


def test_get_recipe_invalid_id(recipe_tools):
    [get_recipe, *_] = recipe_tools
    assert "error" in get_recipe("not-a-uuid")
    assert "error" in get_recipe(str(uuid.uuid4()))


def test_recipe_overview_runs(recipe_tools, db_session, fresh):
    [_g, overview, _n] = recipe_tools
    _make_recipe(db_session, f"{fresh}_A", cuisine="française", tags=["rapide"])
    res = overview()
    assert "total_recipes" in res
    assert res["total_recipes"] >= 1
    assert "top_cuisines" in res
    assert "linked_to_db" in res


def test_get_recipe_nutrition_zero_when_unlinked(recipe_tools, db_session, fresh):
    [_g, _o, get_nutri] = recipe_tools
    r = _make_recipe(db_session, f"{fresh}_R", servings=1)
    db_session.add(Ingredient(recipe_id=r.recipe_id, name="x", quantity=100, unit="g"))
    db_session.flush()
    res = get_nutri(str(r.recipe_id))
    assert res["recipe_name"] == f"{fresh}_R"
    assert res["calories"] == 0  # nothing linked


# ---- shopping ----

def test_get_shopping_list_returns_items(shopping_tools, db_session, fresh):
    [get_shopping] = shopping_tools
    item = ShoppingList(name=f"{fresh}_LAIT", position=999, is_checked=False)
    db_session.add(item); db_session.flush()
    db_session.add(ShoppingListContribution(
        item_id=item.item_id, quantity_text="1 L", source_label="Manuel"
    ))
    db_session.flush()
    res = get_shopping()
    assert res["total"] >= 1
    names = [it["name"] for it in res["items"]]
    assert f"{fresh}_LAIT" in names


# ---- nutrition ----

def test_get_weekly_nutrition_empty_week(nutrition_tools):
    [get_weekly] = nutrition_tools
    today = date.today()
    monday = today + timedelta(days=(0 - today.weekday()) % 7 or 7)
    res = get_weekly(week_start=monday.isoformat(), sex="male")
    assert "days" in res and len(res["days"]) == 7
    assert "rdi" in res
    assert "untracked" in res


def test_get_weekly_nutrition_invalid_date(nutrition_tools):
    [get_weekly] = nutrition_tools
    res = get_weekly(week_start="garbage", sex="male")
    assert "error" in res


# ---- seasonality ----

def test_get_in_season_default(seasonality_tools):
    [get_in_season, _suggest] = seasonality_tools
    res = get_in_season()
    assert 1 <= res["month"] <= 12
    assert isinstance(res["items"], list)


def test_get_in_season_april(seasonality_tools):
    [get_in_season, _suggest] = seasonality_tools
    res = get_in_season(month=4)
    names = {it["name"] for it in res["items"]}
    assert "Asperge" in names


def test_suggest_seasonal_recipes_april(seasonality_tools, db_session, fresh):
    [_g, suggest] = seasonality_tools
    # Build a recipe whose ingredients clearly hit April: asperge + radis.
    r = _make_recipe(db_session, f"{fresh}_PRINTEMPS", servings=2)
    db_session.add(Ingredient(recipe_id=r.recipe_id, name="asperge", quantity=300, unit="g"))
    db_session.add(Ingredient(recipe_id=r.recipe_id, name="radis", quantity=10, unit="pcs"))
    db_session.flush()
    res = suggest(month=4, k=3)
    assert res["month"] == 4
    matched_names = [r["recipe_name"] for r in res["recipes"]]
    assert f"{fresh}_PRINTEMPS" in matched_names


# ---- reference lookup ----

def test_find_ingredient_in_db(reference_tools, db_session, fresh):
    [find] = reference_tools
    canon = IngredientDatabase(
        alim_nom_fr=f"{fresh}_FOO_CANON",
        nutrition_data={"a": 1.0, "b": None},
    )
    db_session.add(canon); db_session.flush()
    res = find(name=f"{fresh}_FOO")
    names = [c["name"] for c in res["candidates"]]
    assert any(f"{fresh}_FOO" in n for n in names)
    # missing_nutrients_count > 0 because "b" is None
    foo = next(c for c in res["candidates"] if c["name"] == f"{fresh}_FOO_CANON")
    assert foo["missing_nutrients_count"] >= 1
