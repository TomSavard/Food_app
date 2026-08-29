"""Unit tests for /api/shopping-list — runs against SQLite."""
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


def test_delete_last_contribution_deletes_item(client):
    client.post("/api/shopping-list", json={"name": "Solo", "quantity_text": "1"})
    items = client.get("/api/shopping-list").json()["items"]
    assert len(items) == 1
    cid = items[0]["contributions"][0]["contribution_id"]

    res = client.delete(f"/api/shopping-list/contributions/{cid}")
    assert res.status_code == 204
    remaining = client.get("/api/shopping-list").json()["items"]
    assert len(remaining) == 0


def test_reorder(client):
    created = client.post("/api/shopping-list", json={"name": "B", "quantity_text": "1"}).json()
    client.post("/api/shopping-list", json={"name": "A", "quantity_text": "1"})
    res = client.patch(f"/api/shopping-list/{created['item_id']}", json={"position": 0})
    assert res.status_code == 200
    items = client.get("/api/shopping-list").json()["items"]
    assert items[0]["name"] == "B"
    assert items[1]["name"] == "A"


def test_clear_all(client):
    client.post("/api/shopping-list", json={"name": "X", "quantity_text": "1"})
    client.post("/api/shopping-list", json={"name": "Y", "quantity_text": "1"})
    res = client.delete("/api/shopping-list")
    assert res.status_code == 204
    assert client.get("/api/shopping-list").json()["items"] == []


def test_heuristic_categorizes_on_creation(client):
    res = client.post("/api/shopping-list", json={"name": "Pain", "quantity_text": "1 baguette"})
    assert res.status_code == 201
    assert res.json()["category"] is not None  # should be auto-categorized


def test_patch_category_learns_into_knowledge_base(client):
    created = client.post("/api/shopping-list", json={"name": "Fromage", "quantity_text": "1"}).json()
    res = client.patch(f"/api/shopping-list/{created['item_id']}", json={"category": "fromages"})
    assert res.status_code == 200
    assert res.json()["category"] == "fromages"
