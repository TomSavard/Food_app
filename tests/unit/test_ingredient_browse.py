"""Unit tests for ingredient browsing — runs against SQLite."""
from backend.db.models import IngredientDatabase, IngredientAlias


def test_search_matches_alias(client, db_session):
    db = IngredientDatabase(alim_nom_fr="tomate")
    db_session.add(db)
    db_session.flush()
    db_session.add(IngredientAlias(
        ingredient_db_id=db.id, alias_text="tomates cerises", created_by="user"
    ))
    db_session.flush()
    
    res = client.get("/api/ingredients", params={"q": "cerises"})
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_list_filters_modified(client, db_session):
    db = IngredientDatabase(alim_nom_fr="basic", modified=False)
    db_session.add(db)
    db_session.flush()
    
    db2 = IngredientDatabase(alim_nom_fr="custom", modified=True, modified_by="user")
    db_session.add(db2)
    db_session.flush()
    
    res = client.get("/api/ingredients", params={"modified": "true"})
    assert res.status_code == 200
    names = [i["name"] for i in res.json()]
    assert "custom" in names


def test_get_detail_404(client):
    res = client.get("/api/ingredients/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


def test_patch_updates_and_marks_modified(client, db_session):
    db = IngredientDatabase(alim_nom_fr="tomate", category=None)
    db_session.add(db)
    db_session.flush()
    
    res = client.patch(f"/api/ingredients/{db.id}", json={"category": "fruits"})
    assert res.status_code == 200
    assert res.json()["category"] == "fruits"
    assert res.json()["modified"] is True


def test_patch_adds_alias(client, db_session):
    db = IngredientDatabase(alim_nom_fr="tomate")
    db_session.add(db)
    db_session.flush()
    
    res = client.patch(f"/api/ingredients/{db.id}", json={
        "new_alias": "tomates fraîches"
    })
    assert res.status_code == 200


def test_delete_alias(client, db_session):
    db = IngredientDatabase(alim_nom_fr="tomate")
    db_session.add(db)
    db_session.flush()
    alias = IngredientAlias(ingredient_db_id=db.id, alias_text="old_alias", created_by="user")
    db_session.add(alias)
    db_session.flush()
    
    res = client.delete(f"/api/ingredients/{db.id}/aliases/{alias.alias_id}")
    assert res.status_code == 204
