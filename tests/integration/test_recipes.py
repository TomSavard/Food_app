"""Endpoint tests for /api/recipes."""
from backend.db.models import Recipe, Ingredient


def _make_recipe(db, **overrides):
    defaults = {
        "name": "Test Recipe",
        "description": "desc",
        "cuisine_type": "italian",
        "tags": ["quick", "vegetarian"],
        "servings": 2,
    }
    defaults.update(overrides)
    recipe = Recipe(**defaults)
    db.add(recipe)
    db.flush()
    return recipe


def test_list_recipes_empty_filters(client, db_session):
    _make_recipe(db_session, name="Alpha")
    _make_recipe(db_session, name="Beta")
    db_session.flush()

    res = client.get("/api/recipes")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 2
    names = [r["name"] for r in body["recipes"]]
    assert "Alpha" in names and "Beta" in names


def test_list_recipes_search_filter(client, db_session):
    _make_recipe(db_session, name="Tarte aux pommes")
    _make_recipe(db_session, name="Soupe de courge")
    db_session.flush()

    res = client.get("/api/recipes", params={"search": "pomme"})
    assert res.status_code == 200
    names = [r["name"] for r in res.json()["recipes"]]
    assert "Tarte aux pommes" in names
    assert "Soupe de courge" not in names


def test_list_recipes_cuisine_filter(client, db_session):
    _make_recipe(db_session, name="Pizza", cuisine_type="italian")
    _make_recipe(db_session, name="Sushi", cuisine_type="japanese")
    db_session.flush()

    res = client.get("/api/recipes", params={"cuisine": "japan"})
    assert res.status_code == 200
    names = [r["name"] for r in res.json()["recipes"]]
    assert "Sushi" in names
    assert "Pizza" not in names


def test_list_recipes_ingredient_filter(client, db_session):
    r1 = _make_recipe(db_session, name="Poulet rôti")
    r2 = _make_recipe(db_session, name="Salade verte")
    db_session.add(Ingredient(recipe_id=r1.recipe_id, name="poulet cru", quantity=1, unit="kg"))
    db_session.add(Ingredient(recipe_id=r2.recipe_id, name="salade", quantity=1, unit="pcs"))
    db_session.flush()

    res = client.get("/api/recipes", params={"ingredient": "poulet"})
    assert res.status_code == 200
    names = [r["name"] for r in res.json()["recipes"]]
    assert "Poulet rôti" in names
    assert "Salade verte" not in names


def test_get_recipe_404(client):
    res = client.get("/api/recipes/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


def test_get_recipe_ok(client, db_session):
    r = _make_recipe(db_session, name="Specific")
    db_session.flush()

    res = client.get(f"/api/recipes/{r.recipe_id}")
    assert res.status_code == 200
    assert res.json()["name"] == "Specific"


def test_create_recipe(client):
    payload = {
        "name": "Created in test",
        "description": "via API",
        "servings": 3,
        "ingredients": [{"name": "tomate", "quantity": 2, "unit": "pcs"}],
        "instructions": [{"instruction_text": "Mix everything."}],
    }
    res = client.post("/api/recipes", json=payload)
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Created in test"
    assert len(body["ingredients"]) == 1
    assert body["ingredients"][0]["name"] == "tomate"
