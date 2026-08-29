"""Tests for /api/meal-plan endpoints (stack-of-meals model)."""
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
    not_monday = today + timedelta(days=(2 - today.weekday()) % 7)
    res = client.get(f"/api/meal-plan?week_start={not_monday.isoformat()}")
    assert res.status_code == 400


def test_add_meal_appends_to_day(client, db_session):
    r1 = _make_recipe(db_session, name="A")
    r2 = _make_recipe(db_session, name="B")
    monday = _next_monday()

    res1 = client.post("/api/meal-plan", json={
        "slot_date": monday, "recipe_id": str(r1.recipe_id), "servings": 2,
    })
    assert res1.status_code == 201
    assert res1.json()["position"] == 0

    res2 = client.post("/api/meal-plan", json={
        "slot_date": monday, "recipe_id": str(r2.recipe_id), "servings": 1,
    })
    assert res2.status_code == 201
    assert res2.json()["position"] == 1

    week = client.get(f"/api/meal-plan?week_start={monday}").json()
    names = [s["recipe_name"] for s in week["slots"]]
    assert names == ["A", "B"]


def test_add_meal_unknown_recipe_404(client):
    res = client.post("/api/meal-plan", json={
        "slot_date": _next_monday(),
        "recipe_id": "00000000-0000-0000-0000-000000000000",
        "servings": 1,
    })
    assert res.status_code == 404


def test_update_servings(client, db_session):
    r = _make_recipe(db_session)
    monday = _next_monday()
    created = client.post("/api/meal-plan", json={
        "slot_date": monday, "recipe_id": str(r.recipe_id), "servings": 1,
    }).json()
    res = client.patch(f"/api/meal-plan/{created['slot_id']}", json={"servings": 5})
    assert res.status_code == 200
    assert res.json()["servings"] == 5


def test_delete_meal(client, db_session):
    r = _make_recipe(db_session)
    monday = _next_monday()
    created = client.post("/api/meal-plan", json={
        "slot_date": monday, "recipe_id": str(r.recipe_id), "servings": 1,
    }).json()
    res = client.delete(f"/api/meal-plan/{created['slot_id']}")
    assert res.status_code == 204
    assert client.delete(f"/api/meal-plan/{created['slot_id']}").status_code == 404


def test_reorder_within_day(client, db_session):
    r1 = _make_recipe(db_session, name="A")
    r2 = _make_recipe(db_session, name="B")
    r3 = _make_recipe(db_session, name="C")
    monday_date = date.fromisoformat(_next_monday())
    s1 = MealPlanSlot(slot_date=monday_date, position=0, recipe_id=r1.recipe_id, servings=1)
    s2 = MealPlanSlot(slot_date=monday_date, position=1, recipe_id=r2.recipe_id, servings=1)
    s3 = MealPlanSlot(slot_date=monday_date, position=2, recipe_id=r3.recipe_id, servings=1)
    db_session.add_all([s1, s2, s3]); db_session.flush()

    res = client.put("/api/meal-plan/reorder", json={
        "items": [
            {"slot_id": str(s2.slot_id), "slot_date": monday_date.isoformat(), "position": 0},
            {"slot_id": str(s3.slot_id), "slot_date": monday_date.isoformat(), "position": 1},
            {"slot_id": str(s1.slot_id), "slot_date": monday_date.isoformat(), "position": 2},
        ]
    })
    assert res.status_code == 200
    week = client.get(f"/api/meal-plan?week_start={monday_date.isoformat()}").json()
    names = [s["recipe_name"] for s in week["slots"]]
    assert names == ["B", "C", "A"]


def test_reorder_across_days(client, db_session):
    r1 = _make_recipe(db_session, name="A")
    r2 = _make_recipe(db_session, name="B")
    monday = date.fromisoformat(_next_monday())
    tuesday = monday + timedelta(days=1)
    s1 = MealPlanSlot(slot_date=monday, position=0, recipe_id=r1.recipe_id, servings=1)
    s2 = MealPlanSlot(slot_date=tuesday, position=0, recipe_id=r2.recipe_id, servings=1)
    db_session.add_all([s1, s2]); db_session.flush()

    # Move s1 from Monday to Tuesday position 1.
    res = client.put("/api/meal-plan/reorder", json={
        "items": [
            {"slot_id": str(s1.slot_id), "slot_date": tuesday.isoformat(), "position": 1},
        ]
    })
    assert res.status_code == 200

    week = client.get(f"/api/meal-plan?week_start={monday.isoformat()}").json()
    by_day = {}
    for s in week["slots"]:
        by_day.setdefault(s["slot_date"], []).append(s["recipe_name"])
    assert by_day.get(monday.isoformat(), []) == []
    assert by_day[tuesday.isoformat()] == ["B", "A"]


def test_generate_appends_meals_per_day(client, db_session):
    _make_recipe(db_session, name="X", is_favorite=True)
    _make_recipe(db_session, name="Y", is_favorite=True)
    monday = _next_monday()

    res = client.post(f"/api/meal-plan/generate?week_start={monday}&meals_per_day=2")
    assert res.status_code == 200
    body = res.json()
    # 7 days × 2 meals = 14
    assert len(body["slots"]) == 14


def test_generate_overwrite_replaces_existing(client, db_session):
    r = _make_recipe(db_session, name="Existing", is_favorite=True)
    monday_date = date.fromisoformat(_next_monday())
    db_session.add(MealPlanSlot(
        slot_date=monday_date, position=0, recipe_id=r.recipe_id, servings=2,
    )); db_session.flush()

    res = client.post(
        f"/api/meal-plan/generate?week_start={monday_date.isoformat()}&meals_per_day=1&overwrite=true"
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["slots"]) == 7  # 7 days × 1 meal
