"""Tests for backend.services.ingredient_match + /api/match endpoints.

LLM calls are skipped via the no-key fallback path or by inserting an exact
alias before the call so `lookup_exact` short-circuits.
"""
from uuid import UUID

import pytest

from backend.db.models import IngredientAlias, IngredientDatabase
from backend.services import ingredient_match as im


@pytest.fixture
def make_ingredient(db_session):
    """Factory that inserts an IngredientDatabase row and returns it."""
    def _make(name: str, **kw):
        row = IngredientDatabase(alim_nom_fr=name, nutrition_data={}, **kw)
        db_session.add(row)
        db_session.flush()
        return row
    return _make


def test_lookup_exact_canonical(db_session, make_ingredient):
    r = make_ingredient("Tomate, crue")
    assert im.lookup_exact(db_session, "tomate, crue").id == r.id
    assert im.lookup_exact(db_session, "TOMATE, CRUE").id == r.id


def test_lookup_exact_via_alias(db_session, make_ingredient):
    r = make_ingredient("Tomate, crue")
    db_session.add(IngredientAlias(
        ingredient_db_id=r.id, alias_text="tomates", created_by="user"
    ))
    db_session.flush()
    assert im.lookup_exact(db_session, "TOMATES").id == r.id


def test_lookup_exact_miss(db_session):
    assert im.lookup_exact(db_session, "kombuchasaurus") is None


def test_confirm_match_writes_alias(db_session, make_ingredient):
    r = make_ingredient("Tomate, crue")
    canonical = im.confirm_match(db_session, "tomates cerises", r.id)
    assert canonical.id == r.id
    assert (
        db_session.query(IngredientAlias)
        .filter(IngredientAlias.alias_text == "tomates cerises")
        .count() == 1
    )


def test_confirm_match_idempotent(db_session, make_ingredient):
    r = make_ingredient("Tomate, crue")
    im.confirm_match(db_session, "tomates", r.id)
    im.confirm_match(db_session, "tomates", r.id)
    count = (
        db_session.query(IngredientAlias)
        .filter(IngredientAlias.ingredient_db_id == r.id)
        .count()
    )
    assert count == 1


def test_confirm_match_skips_alias_when_equal_to_canonical(db_session, make_ingredient):
    r = make_ingredient("Tomate, crue")
    im.confirm_match(db_session, "Tomate, crue", r.id)
    assert (
        db_session.query(IngredientAlias)
        .filter(IngredientAlias.ingredient_db_id == r.id).count() == 0
    )


def test_create_new_marks_modified_and_inserts_alias(db_session):
    row = im.create_new(db_session, "Schnitzel maison", category="Viandes & Poissons")
    assert row.modified is True
    assert row.modified_by == "user"
    assert row.source == "user"
    assert row.category == "Viandes & Poissons"
    assert (
        db_session.query(IngredientAlias)
        .filter(IngredientAlias.ingredient_db_id == row.id).count() == 1
    )


def test_create_new_returns_existing_when_name_taken(db_session, make_ingredient):
    existing = make_ingredient("Tomate, crue")
    row = im.create_new(db_session, "TOMATE, CRUE")
    assert row.id == existing.id


# ---- Endpoints ----

def test_candidates_endpoint_returns_exact(client, db_session, make_ingredient):
    make_ingredient("Tomate, crue")
    res = client.get("/api/match/candidates", params={"name": "tomate, crue"})
    assert res.status_code == 200
    body = res.json()
    assert body["exact"] is not None
    assert body["exact"]["name"] == "Tomate, crue"
    assert body["llm_candidates"] == []


def test_confirm_endpoint_writes_alias(client, db_session, make_ingredient):
    r = make_ingredient("Tomate, crue")
    res = client.post(
        "/api/match/confirm",
        json={"name": "tomates cerises", "ingredient_db_id": str(r.id)},
    )
    assert res.status_code == 200
    assert res.json()["id"] == str(r.id)


def test_create_endpoint(client):
    res = client.post(
        "/api/match/create",
        json={"name": "Algue kombu", "category": "Épicerie"},
    )
    assert res.status_code == 201
    body = res.json()
    UUID(body["id"])  # parses
    assert body["source"] == "user"
    assert body["category"] == "Épicerie"
