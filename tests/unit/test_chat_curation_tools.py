"""Unit tests for chat curation tools — runs against SQLite."""
from backend.db.models import IngredientDatabase


def test_fill_nutrition_invalid_id(client):
    res = client.post("/api/ingredients/00000000-0000-0000-0000-000000000000/fill-nutrition")
    assert res.status_code == 404


def test_patch_updates_and_marks_modified(client, db_session):
    db = IngredientDatabase(alim_nom_fr="test_ing", category=None)
    db_session.add(db)
    db_session.flush()
    
    res = client.patch(f"/api/ingredients/{str(db.id)}", json={"category": "legumes"})
    assert res.status_code == 200
    assert res.json()["category"] == "legumes"
    assert res.json()["modified"] is True
