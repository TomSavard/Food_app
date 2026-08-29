"""Unit tests for chat read tools — runs against SQLite."""
from datetime import date, timedelta

from backend.db.models import Recipe, Ingredient, MealPlanSlot


def _make_recipe(db, name="Pasta", **k):
    r = Recipe(name=name, **k)
    db.add(r); db.flush()
    return r


def _next_monday() -> str:
    today = date.today()
    return (today + timedelta(days=(0 - today.weekday()) % 7 or 7)).isoformat()


def test_get_recipe_returns_detail(client, db_session):
    r = _make_recipe(db_session, name="Risotto")
    db_session.flush()
    
    res = client.get(f"/api/recipes/{r.recipe_id}")
    assert res.status_code == 200
    assert res.json()["name"] == "Risotto"


def test_get_recipe_invalid_id(client):
    res = client.get("/api/recipes/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


def test_get_shopping_list_returns_items(client):
    client.post("/api/shopping-list", json={"name": "Milk", "quantity_text": "1L"})
    res = client.get("/api/shopping-list")
    assert res.status_code == 200
    assert len(res.json()["items"]) == 1


def test_get_weekly_nutrition_empty_week(client):
    monday = _next_monday()
    res = client.get("/api/meal-plan/nutrition", params={"monday": monday})
    assert res.status_code == 200


def test_get_weekly_nutrition_invalid_date(client):
    res = client.get("/api/meal-plan/nutrition", params={"monday": "bad-date"})
    assert res.status_code == 422


def test_get_in_season_default(client):
    res = client.get("/api/reference/seasonality")
    assert res.status_code == 200


def test_get_in_season_april(client):
    res = client.get("/api/reference/seasonality", params={"month": "4"})
    assert res.status_code == 200


def test_find_ingredient_in_db(client, db_session):
    db = IngredientDatabase(alim_nom_fr="tomate")
    db_session.add(db)
    db_session.flush()
    
    res = client.get("/api/match/lookup", params={"name": "tomate"})
    assert res.status_code == 200
