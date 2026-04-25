"""Tests for /api/meal-plan endpoints."""
from datetime import date, timedelta

from backend.db.models import MealPlanSlot, Recipe


def _next_monday() -> str:
    today = date.today()
    return (today + timedelta(days=(0 - today.weekday()) % 7 or 7)).isoformat()


def _make_recipe(db, **k):
    r = Recipe(name=k.get("name", "R"), servings=k.get("servings", 2),
               is_favorite=k.get("is_favorite", False))
    db.add(r); db.flush()
    return r


def test_get_meal_plan_empty(client):
    monday = _next_monday()
    res = client.get(f"/api/meal-plan?week_start={monday}")
    assert res.status_code == 200
    body = res.json()
    assert body["week_start"] == monday
    assert body["slots"] == []


def test_get_meal_plan_requires_monday(client):
    today = date.today()
    not_monday = today + timedelta(days=(2 - today.weekday()) % 7)  # next Wednesday
    res = client.get(f"/api/meal-plan?week_start={not_monday.isoformat()}")
    assert res.status_code == 400


def test_upsert_and_clear_slot(client, db_session):
    r = _make_recipe(db_session, name="Pasta", servings=4)
    monday = _next_monday()

    res = client.put("/api/meal-plan/slot", json={
        "slot_date": monday,
        "slot": "lunch",
        "recipe_id": str(r.recipe_id),
        "servings": 3,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["slot"] == "lunch"
    assert body["recipe_name"] == "Pasta"
    assert body["servings"] == 3

    # Update same slot — should overwrite, not create a second row
    r2 = _make_recipe(db_session, name="Soup")
    res2 = client.put("/api/meal-plan/slot", json={
        "slot_date": monday,
        "slot": "lunch",
        "recipe_id": str(r2.recipe_id),
        "servings": 1,
    })
    assert res2.status_code == 200
    assert res2.json()["recipe_name"] == "Soup"

    # GET should return exactly one slot
    week = client.get(f"/api/meal-plan?week_start={monday}").json()
    assert len(week["slots"]) == 1

    # Clear it
    res3 = client.delete(f"/api/meal-plan/slot?slot_date={monday}&slot=lunch")
    assert res3.status_code == 204
    week = client.get(f"/api/meal-plan?week_start={monday}").json()
    assert week["slots"] == []


def test_upsert_invalid_slot_400(client, db_session):
    r = _make_recipe(db_session)
    res = client.put("/api/meal-plan/slot", json={
        "slot_date": _next_monday(),
        "slot": "brunch",  # invalid
        "recipe_id": str(r.recipe_id),
        "servings": 1,
    })
    assert res.status_code == 400


def test_upsert_unknown_recipe_404(client):
    res = client.put("/api/meal-plan/slot", json={
        "slot_date": _next_monday(),
        "slot": "lunch",
        "recipe_id": "00000000-0000-0000-0000-000000000000",
        "servings": 1,
    })
    assert res.status_code == 404


def test_clear_unknown_slot_404(client):
    res = client.delete(f"/api/meal-plan/slot?slot_date={_next_monday()}&slot=dinner")
    assert res.status_code == 404


def test_generate_fills_empty_week(client, db_session):
    _make_recipe(db_session, name="A", is_favorite=True)
    _make_recipe(db_session, name="B", is_favorite=True)
    monday = _next_monday()

    res = client.post(f"/api/meal-plan/generate?week_start={monday}")
    assert res.status_code == 200
    body = res.json()
    # 7 days × 4 slots = 28
    assert len(body["slots"]) == 28


def test_generate_skips_existing_unless_overwrite(client, db_session):
    r = _make_recipe(db_session, name="Existing", is_favorite=True)
    monday_date = date.fromisoformat(_next_monday())
    db_session.add(MealPlanSlot(
        slot_date=monday_date, slot="lunch", recipe_id=r.recipe_id, servings=2
    ))
    db_session.flush()

    res = client.post(f"/api/meal-plan/generate?week_start={monday_date.isoformat()}")
    assert res.status_code == 200
    body = res.json()
    assert len(body["slots"]) == 28
    # The pre-existing lunch is preserved
    pre = [s for s in body["slots"] if s["slot_date"] == monday_date.isoformat() and s["slot"] == "lunch"]
    assert len(pre) == 1
    assert pre[0]["servings"] == 2
