"""Direct tests for the replace_ingredient_in_recipes chat tool.

Uses uniquely-prefixed ingredient names to avoid colliding with rows that
exist in the shared test Neon branch.
"""
import uuid

import pytest

from backend.api.chat import _build_recipe_edit_tools
from backend.db.models import Ingredient, IngredientDatabase, Recipe


@pytest.fixture
def tool(db_session):
    [t] = _build_recipe_edit_tools(db_session)
    return t


@pytest.fixture
def fresh():
    return f"TEST_{uuid.uuid4().hex[:8]}"


def _make_recipe(db, name, ing_name):
    r = Recipe(name=name, servings=1)
    db.add(r); db.flush()
    db.add(Ingredient(recipe_id=r.recipe_id, name=ing_name, quantity=1, unit="g"))
    db.flush()
    return r


def test_dry_run_does_not_write(tool, db_session, fresh):
    old = f"{fresh}_OLD"
    _make_recipe(db_session, "R1", old)
    res = tool(old_name=old, new_name=f"{fresh}_NEW", dry_run=True)
    assert res["matched"] == 1
    assert res["applied"] is False
    untouched = (
        db_session.query(Ingredient).filter(Ingredient.name == old).count()
    )
    assert untouched == 1


def test_apply_renames(tool, db_session, fresh):
    old, new = f"{fresh}_OLD", f"{fresh}_NEW"
    _make_recipe(db_session, "R1", old)
    _make_recipe(db_session, "R2", old)
    res = tool(old_name=old, new_name=new, dry_run=False)
    assert res["matched"] == 2
    assert res["applied"] is True
    assert db_session.query(Ingredient).filter(Ingredient.name == old).count() == 0
    assert db_session.query(Ingredient).filter(Ingredient.name == new).count() == 2


def test_match_is_case_insensitive(tool, db_session, fresh):
    old = f"{fresh}_OLD"
    _make_recipe(db_session, "R", old.upper())
    res = tool(old_name=old.lower(), new_name=f"{fresh}_NEW", dry_run=False)
    assert res["matched"] == 1


def test_relink_sets_fk(tool, db_session, fresh):
    canonical_name = f"{fresh}_CANON"
    canonical = IngredientDatabase(alim_nom_fr=canonical_name, nutrition_data={})
    db_session.add(canonical); db_session.flush()
    old = f"{fresh}_OLD"
    _make_recipe(db_session, "R", old)
    res = tool(
        old_name=old,
        new_name=canonical_name,
        relink_to_db_name=canonical_name,
        dry_run=False,
    )
    assert res["applied"] is True
    assert res["relinked_to_id"] == str(canonical.id)
    ing = (
        db_session.query(Ingredient).filter(Ingredient.name == canonical_name).first()
    )
    assert str(ing.ingredient_db_id) == str(canonical.id)


def test_relink_target_not_found_returns_error(tool, db_session, fresh):
    old = f"{fresh}_OLD"
    _make_recipe(db_session, "R", old)
    res = tool(
        old_name=old,
        new_name="X",
        relink_to_db_name=f"NONEXISTENT_{fresh}",
        dry_run=True,
    )
    assert "error" in res
