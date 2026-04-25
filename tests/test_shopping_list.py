"""Tests for /api/shopping-list and meal-plan ↔ shopping sync."""
from datetime import date, timedelta

from backend.db.models import (
    Ingredient,
    MealPlanSlot,
    Recipe,
    ShoppingList,
    ShoppingListContribution,
)


def _next_monday() -> str:
    today = date.today()
    return (today + timedelta(days=(0 - today.weekday()) % 7 or 7)).isoformat()


def _make_recipe(db, name="Pasta", servings=2, **k):
    r = Recipe(name=name, servings=servings, is_favorite=k.get("is_favorite", False))
    db.add(r); db.flush()
    return r


def _add_ingredient(db, recipe, name, qty, unit):
    db.add(Ingredient(recipe_id=recipe.recipe_id, name=name, quantity=qty, unit=unit))
    db.flush()


def test_get_empty(client):
    res = client.get("/api/shopping-list")
    assert res.status_code == 200
    body = res.json()
    assert body == {"items": [], "total": 0}


def test_post_manual_creates_item_with_one_contribution(client):
    res = client.post("/api/shopping-list", json={"name": "Pain", "quantity_text": "1 baguette"})
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Pain"
    assert body["is_checked"] is False
    assert len(body["contributions"]) == 1
    assert body["contributions"][0]["quantity_text"] == "1 baguette"
    assert body["contributions"][0]["source_label"] == "Manuel"


def test_post_manual_merges_by_name_case_insensitive(client):
    client.post("/api/shopping-list", json={"name": "Tomate", "quantity_text": "200g"})
    res = client.post("/api/shopping-list", json={"name": "  TOMATE ", "quantity_text": "100g"})
    assert res.status_code == 201
    items = client.get("/api/shopping-list").json()["items"]
    assert len(items) == 1
    assert len(items[0]["contributions"]) == 2


def test_patch_is_checked(client):
    created = client.post("/api/shopping-list", json={"name": "Pain", "quantity_text": "1"}).json()
    res = client.patch(f"/api/shopping-list/{created['item_id']}", json={"is_checked": True})
    assert res.status_code == 200
    assert res.json()["is_checked"] is True


def test_delete_item_cascades_contributions(client, db_session):
    created = client.post("/api/shopping-list", json={"name": "X", "quantity_text": "1"}).json()
    res = client.delete(f"/api/shopping-list/{created['item_id']}")
    assert res.status_code == 204
    remaining = db_session.query(ShoppingListContribution).filter(
        ShoppingListContribution.item_id == created["item_id"]
    ).count()
    assert remaining == 0


def test_delete_contribution_keeps_item_when_others_remain(client):
    client.post("/api/shopping-list", json={"name": "Tomate", "quantity_text": "200g"})
    client.post("/api/shopping-list", json={"name": "Tomate", "quantity_text": "100g"})
    item = client.get("/api/shopping-list").json()["items"][0]
    cid = item["contributions"][0]["contribution_id"]

    res = client.delete(f"/api/shopping-list/contributions/{cid}")
    assert res.status_code == 204

    items = client.get("/api/shopping-list").json()["items"]
    assert len(items) == 1
    assert len(items[0]["contributions"]) == 1


def test_delete_last_contribution_deletes_item(client):
    item = client.post("/api/shopping-list", json={"name": "X", "quantity_text": "1"}).json()
    cid = item["contributions"][0]["contribution_id"]
    res = client.delete(f"/api/shopping-list/contributions/{cid}")
    assert res.status_code == 204
    assert client.get("/api/shopping-list").json()["items"] == []


def test_reorder(client, db_session):
    a = client.post("/api/shopping-list", json={"name": "A", "quantity_text": "1"}).json()
    b = client.post("/api/shopping-list", json={"name": "B", "quantity_text": "1"}).json()
    c = client.post("/api/shopping-list", json={"name": "C", "quantity_text": "1"}).json()

    res = client.put("/api/shopping-list/reorder", json={
        "items": [
            {"item_id": c["item_id"], "position": 0},
            {"item_id": a["item_id"], "position": 1},
            {"item_id": b["item_id"], "position": 2},
        ]
    })
    assert res.status_code == 200
    names = [it["name"] for it in res.json()["items"]]
    assert names == ["C", "A", "B"]


def test_clear_all(client):
    client.post("/api/shopping-list", json={"name": "A", "quantity_text": "1"})
    client.post("/api/shopping-list", json={"name": "B", "quantity_text": "1"})
    res = client.delete("/api/shopping-list")
    assert res.status_code == 204
    assert client.get("/api/shopping-list").json()["items"] == []


# ---- Meal-plan sync ----

def test_meal_slot_add_creates_contributions(client, db_session):
    r = _make_recipe(db_session, name="Pâtes carbonara", servings=2)
    _add_ingredient(db_session, r, "pâtes", 200, "g")
    _add_ingredient(db_session, r, "lardons", 100, "g")
    monday = _next_monday()

    client.post("/api/meal-plan", json={
        "slot_date": monday, "recipe_id": str(r.recipe_id), "servings": 4,
    })

    items = client.get("/api/shopping-list").json()["items"]
    by_name = {it["name"]: it for it in items}
    assert "pâtes" in by_name and "lardons" in by_name
    # Servings doubled from 2 → 4 means 2x scaling.
    assert by_name["pâtes"]["contributions"][0]["quantity_text"] == "400 g"
    assert by_name["lardons"]["contributions"][0]["source_label"].startswith("Pâtes carbonara · ")


def test_meal_slot_servings_change_refreshes_contributions(client, db_session):
    r = _make_recipe(db_session, name="Soupe", servings=2)
    _add_ingredient(db_session, r, "carotte", 100, "g")
    monday = _next_monday()

    created = client.post("/api/meal-plan", json={
        "slot_date": monday, "recipe_id": str(r.recipe_id), "servings": 2,
    }).json()
    items = client.get("/api/shopping-list").json()["items"]
    assert items[0]["contributions"][0]["quantity_text"] == "100 g"

    # Bump servings 2 → 6 (3x).
    client.patch(f"/api/meal-plan/{created['slot_id']}", json={"servings": 6})
    items = client.get("/api/shopping-list").json()["items"]
    assert items[0]["contributions"][0]["quantity_text"] == "300 g"
    # Still exactly one contribution (the old was replaced, not appended).
    assert len(items[0]["contributions"]) == 1


def test_meal_slot_delete_cascades_contributions(client, db_session):
    r = _make_recipe(db_session, name="Soupe", servings=2)
    _add_ingredient(db_session, r, "carotte", 100, "g")
    monday = _next_monday()

    created = client.post("/api/meal-plan", json={
        "slot_date": monday, "recipe_id": str(r.recipe_id), "servings": 2,
    }).json()
    assert client.get("/api/shopping-list").json()["total"] == 1

    client.delete(f"/api/meal-plan/{created['slot_id']}")

    # Contribution gone; item auto-removed since it was the only contribution.
    assert client.get("/api/shopping-list").json()["items"] == []


def test_meal_slot_delete_keeps_item_with_other_contributions(client, db_session):
    r1 = _make_recipe(db_session, name="A", servings=2)
    r2 = _make_recipe(db_session, name="B", servings=2)
    _add_ingredient(db_session, r1, "tomate", 200, "g")
    _add_ingredient(db_session, r2, "tomate", 100, "g")
    monday = _next_monday()

    s1 = client.post("/api/meal-plan", json={
        "slot_date": monday, "recipe_id": str(r1.recipe_id), "servings": 2,
    }).json()
    client.post("/api/meal-plan", json={
        "slot_date": monday, "recipe_id": str(r2.recipe_id), "servings": 2,
    })

    items = client.get("/api/shopping-list").json()["items"]
    assert len(items) == 1
    assert len(items[0]["contributions"]) == 2

    client.delete(f"/api/meal-plan/{s1['slot_id']}")

    items = client.get("/api/shopping-list").json()["items"]
    assert len(items) == 1
    assert len(items[0]["contributions"]) == 1
    assert items[0]["contributions"][0]["source_label"].startswith("B · ")
