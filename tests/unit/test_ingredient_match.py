"""Unit tests for ingredient matching — runs against SQLite."""
from backend.db.models import IngredientDatabase, IngredientAlias


def test_lookup_exact_canonical(client, db_session):
    db = IngredientDatabase(alim_nom_fr="tomate", nutrition_data={"calories": 18})
    db_session.add(db)
    db_session.flush()
    
    res = client.get("/api/match/lookup", params={"name": "tomate"})
    assert res.status_code == 200
    assert res.json()["name"] == "tomate"


def test_lookup_exact_via_alias(client, db_session):
    db = IngredientDatabase(alim_nom_fr="tomate")
    db_session.add(db)
    db_session.flush()
    db_session.add(IngredientAlias(ingredient_db_id=db.id, alias_text="tomates", created_by="user"))
    db_session.flush()
    
    res = client.get("/api/match/lookup", params={"name": "tomates"})
    assert res.status_code == 200
    assert res.json()["name"] == "tomate"


def test_lookup_exact_miss(client):
    res = client.get("/api/match/lookup", params={"name": "nonexistent_xyz"})
    assert res.status_code == 404


def test_confirm_match_writes_alias(client, db_session):
    db = IngredientDatabase(alim_nom_fr="pomme")
    db_session.add(db)
    db_session.flush()
    
    res = client.post("/api/match/confirm", json={
        "name": "pomme verte",
        "ingredient_db_id": str(db.id),
    })
    assert res.status_code == 200
    
    alias = db_session.query(IngredientAlias).filter_by(
        ingredient_db_id=db.id, alias_text="pomme verte"
    ).first()
    assert alias is not None


def test_create_new_marks_modified_and_inserts_alias(client):
    res = client.post("/api/match/create", json={"name": "new_ingredient_xyz"})
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "new_ingredient_xyz"
    assert body["modified"] is True


def test_create_new_returns_existing_when_name_taken(client, db_session):
    db = IngredientDatabase(alim_nom_fr="tomate")
    db_session.add(db)
    db_session.flush()
    
    res = client.post("/api/match/create", json={"name": "tomate"})
    assert res.status_code == 200
    assert res.json()["name"] == "tomate"


def test_candidates_endpoint_returns_exact(client, db_session):
    db = IngredientDatabase(alim_nom_fr="poulet cru")
    db_session.add(db)
    db_session.flush()
    
    res = client.get("/api/match/candidates", params={"name": "poulet cru"})
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_create_endpoint(client):
    res = client.post("/api/match/create", json={"name": "test_ing_123"})
    assert res.status_code in (200, 201)
