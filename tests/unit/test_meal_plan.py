"""Unit tests for /api/meal-plan — runs against SQLite."""
from datetime import date, timedelta

from backend.db.models import MealPlanSlot, Recipe


def _make_recipe(db, name="Pasta", **k):
    r = Recipe(name=name, **k)
    db.add(r); db.flush()
    return r


def _next_monday() -> str:
    today = date.today()
    return (today + timedelta(days=(0 - today.weekday()) % 7 or 7)).isoformat()


def test_get_meal_plan_empty(client):
    res = client.get("/api/meal-plan")
    assert res.status_code == 200
    body = res.json()
    assert body == {"plan": {}}


def test_get_meal_plan_requires_monday(client):
    res = client.get("/api/meal-plan", params={"monday": "not-a-date"})
    assert res.status_code == 422


def test_add_meal_appends_to_day(client):
    r = _make_recipe(db_session, name="Pizza")
    monday = _next_monday()
    res = client.post(f"/api/meal-plan/{monday}/slots", json={"recipe_id": str(r.recipe_id), "servings": 2})
    assert res.status_code == 201
    plan = client.get("/api/meal-plan", params={"monday": monday}).json()
    assert len(plan["plan"][monday]) == 1


def test_add_meal_unknown_recipe_404(client):
    monday = _next_monday()
    res = client.post(f"/api/meal-plan/{monday}/slots", json={"recipe_id": "00000000-0000-0000-0000-000000000000"})
    assert res.status_code == 404


def test_delete_meal(client, db_session):
    monday = _next_monday()
    r = _make_recipe(db_session, name="Soup")
    client.post(f"/api/meal-plan/{monday}/slots", json={"recipe_id": str(r.recipe_id)})
    slot = client.get("/api/meal-plan", params={"monday": monday}).json()["plan"][monday][0]
    res = client.delete(f"/api/meal-plan/{monday}/slots/{slot['slot_id']}")
    assert res.status_code == 204


def test_reorder_within_day(client, db_session):
    monday = _next_monday()
    r1 = _make_recipe(db_session, name="A")
    r2 = _make_recipe(db_session, name="B")
    client.post(f"/api/meal-plan/{monday}/slots", json={"recipe_id": str(r1.recipe_id)})
    client.post(f"/api/meal-plan/{monday}/slots", json={"recipe_id": str(r2.recipe_id)})
    plan = client.get("/api/meal-plan", params={"monday": monday}).json()
    slot_b = [s for s in plan["plan"][monday] if s["recipe"]["name"] == "B"][0]
    res = client.patch(f"/api/meal-plan/{monday}/slots/{slot_b['slot_id']}", json={"position": 0})
    assert res.status_code == 200
