"""Tests for /api/ingredients browse + curation endpoints."""
from datetime import datetime, timezone

import pytest

from backend.db.models import IngredientAlias, IngredientDatabase


@pytest.fixture
def make_ingredient(db_session):
    def _make(name: str, **kw):
        row = IngredientDatabase(
            alim_nom_fr=name, nutrition_data=kw.pop("nutrition_data", {}), **kw
        )
        db_session.add(row)
        db_session.flush()
        return row
    return _make


def test_search_matches_alias(client, db_session, make_ingredient):
    r = make_ingredient("Tomate, crue")
    db_session.add(IngredientAlias(
        ingredient_db_id=r.id, alias_text="tomates cerises", created_by="user"
    ))
    db_session.flush()
    res = client.get("/api/ingredients/search", params={"q": "cerises"})
    assert res.status_code == 200
    names = [it["name"] for it in res.json()]
    assert "Tomate, crue" in names


def test_list_filters_modified(client, db_session, make_ingredient):
    make_ingredient("Touched", modified=True, modified_by="user", modified_at=datetime.now(timezone.utc))
    make_ingredient("Pristine")
    res = client.get("/api/ingredients", params={"modified": True}).json()
    names = [it["name"] for it in res["items"]]
    assert "Touched" in names and "Pristine" not in names


def test_list_filters_missing(client, db_session, make_ingredient):
    make_ingredient("Sparse", nutrition_data={"a": None, "b": 1.0})
    make_ingredient("Full", nutrition_data={"a": 2.0, "b": 1.0})
    res = client.get("/api/ingredients", params={"missing": True}).json()
    names = [it["name"] for it in res["items"]]
    assert "Sparse" in names
    assert "Full" not in names


def test_patch_updates_and_marks_modified(client, db_session, make_ingredient):
    r = make_ingredient("Foo")
    res = client.patch(
        f"/api/ingredients/{r.id}",
        json={"category": "Fruits & Légumes", "density_g_per_ml": 1.03},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["category"] == "Fruits & Légumes"
    assert body["density_g_per_ml"] == 1.03
    assert body["modified"] is True
    assert body["modified_by"] == "user"


def test_patch_rejects_unknown_category(client, db_session, make_ingredient):
    r = make_ingredient("Foo")
    res = client.patch(f"/api/ingredients/{r.id}", json={"category": "Bogus"})
    assert res.status_code == 400


def test_patch_adds_alias(client, db_session, make_ingredient):
    r = make_ingredient("Tomate, crue")
    res = client.patch(
        f"/api/ingredients/{r.id}",
        json={"add_alias": "tomates cerises"},
    )
    assert res.status_code == 200
    aliases = [a["alias_text"] for a in res.json()["aliases"]]
    assert "tomates cerises" in aliases


def test_delete_alias(client, db_session, make_ingredient):
    r = make_ingredient("X")
    db_session.add(IngredientAlias(
        ingredient_db_id=r.id, alias_text="bad", created_by="llm"
    ))
    db_session.flush()
    alias = (
        db_session.query(IngredientAlias)
        .filter(IngredientAlias.ingredient_db_id == r.id).one()
    )
    res = client.delete(f"/api/ingredients/{r.id}/aliases/{alias.alias_id}")
    assert res.status_code == 204
    assert (
        db_session.query(IngredientAlias)
        .filter(IngredientAlias.alias_id == alias.alias_id).count() == 0
    )


def test_llm_fill_confirm_persists(client, db_session, make_ingredient):
    r = make_ingredient("X", nutrition_data={"k1": None, "k2": 1.0})
    res = client.post(
        f"/api/ingredients/{r.id}/llm-fill/confirm",
        json={"values": {"k1": 5.5}},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["nutrition_data"]["k1"] == 5.5
    assert body["modified_by"] == "llm"


def test_get_detail_404(client):
    import uuid
    res = client.get(f"/api/ingredients/{uuid.uuid4()}")
    assert res.status_code == 404
