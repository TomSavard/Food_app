"""Direct tests for the recipe-write chat tools (PR B)."""
import uuid

import pytest

from backend.api.chat import _build_recipe_edit_tools
from backend.db.models import Ingredient, IngredientDatabase, Recipe


@pytest.fixture
def fresh():
    return f"TEST_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def edit_tools(db_session):
    return _build_recipe_edit_tools(db_session)


def _by_name(tools, name):
    return next(t for t in tools if t.__name__ == name)


def test_create_recipe_links_known_ingredients(edit_tools, db_session, fresh):
    create_recipe = _by_name(edit_tools, "create_recipe")
    canon = IngredientDatabase(alim_nom_fr=f"{fresh}_TOMATE", nutrition_data={})
    db_session.add(canon); db_session.flush()
    res = create_recipe(
        name=f"{fresh}_SALADE",
        ingredients=[
            {"name": f"{fresh}_TOMATE", "quantity": 200, "unit": "g"},
            {"name": f"{fresh}_UNKNOWN", "quantity": 50, "unit": "g"},
        ],
        instructions=["Mélanger.", "Servir."],
        servings=2,
        cuisine_type="française",
    )
    assert "recipe_id" in res
    assert res["ingredients_added"] == 2
    assert res["ingredients_linked_to_db"] == 1
    assert res["instructions_added"] == 2


def test_create_recipe_requires_name(edit_tools):
    create_recipe = _by_name(edit_tools, "create_recipe")
    assert "error" in create_recipe(name="", ingredients=[], instructions=[])


def test_update_recipe_metadata(edit_tools, db_session, fresh):
    update = _by_name(edit_tools, "update_recipe_metadata")
    r = Recipe(name=f"{fresh}_OLD", servings=1)
    db_session.add(r); db_session.flush()
    res = update(
        recipe_id=str(r.recipe_id),
        name=f"{fresh}_NEW",
        servings=4,
        tags=["dîner"],
    )
    assert res["changed"]["name"] == f"{fresh}_NEW"
    assert res["changed"]["servings"] == 4
    assert res["changed"]["tags"] == ["dîner"]


def test_update_recipe_metadata_unknown(edit_tools):
    update = _by_name(edit_tools, "update_recipe_metadata")
    assert "error" in update(recipe_id=str(uuid.uuid4()), name="X")


def test_add_ingredient_links_to_db(edit_tools, db_session, fresh):
    add_ing = _by_name(edit_tools, "add_ingredient_to_recipe")
    r = Recipe(name=f"{fresh}_R", servings=1)
    db_session.add(r); db_session.flush()
    canon = IngredientDatabase(alim_nom_fr=f"{fresh}_OEUF", nutrition_data={})
    db_session.add(canon); db_session.flush()
    res = add_ing(
        recipe_id=str(r.recipe_id),
        name=f"{fresh}_OEUF",
        quantity=2,
        unit="pcs",
    )
    assert res["linked_to_db"] is True
    assert res["ingredient_db_id"] is not None


def test_add_ingredient_unknown_recipe(edit_tools):
    add_ing = _by_name(edit_tools, "add_ingredient_to_recipe")
    assert "error" in add_ing(recipe_id=str(uuid.uuid4()), name="x")


def test_update_ingredient_relinks_on_name_change(edit_tools, db_session, fresh):
    update_ing = _by_name(edit_tools, "update_ingredient_in_recipe")
    r = Recipe(name=f"{fresh}_R", servings=1)
    db_session.add(r); db_session.flush()
    ing = Ingredient(recipe_id=r.recipe_id, name=f"{fresh}_OLD", quantity=1, unit="g")
    db_session.add(ing); db_session.flush()
    canon = IngredientDatabase(alim_nom_fr=f"{fresh}_NEW_CANON", nutrition_data={})
    db_session.add(canon); db_session.flush()
    res = update_ing(
        ingredient_id=str(ing.ingredient_id),
        name=f"{fresh}_NEW_CANON",
        quantity=2,
    )
    assert res["name"] == f"{fresh}_NEW_CANON"
    assert res["quantity"] == 2
    assert res["relinked_to"] is not None


def test_remove_ingredient(edit_tools, db_session, fresh):
    remove_ing = _by_name(edit_tools, "remove_ingredient_from_recipe")
    r = Recipe(name=f"{fresh}_R", servings=1)
    db_session.add(r); db_session.flush()
    ing = Ingredient(recipe_id=r.recipe_id, name="x", quantity=1, unit="g")
    db_session.add(ing); db_session.flush()
    iid = str(ing.ingredient_id)
    res = remove_ing(ingredient_id=iid)
    assert res["deleted"] is True
    # second call: nothing to delete
    res2 = remove_ing(ingredient_id=iid)
    assert res2["deleted"] is False


def test_delete_recipe_dry_run_then_apply(edit_tools, db_session, fresh):
    delete = _by_name(edit_tools, "delete_recipe")
    r = Recipe(name=f"{fresh}_DOOMED", servings=1)
    db_session.add(r); db_session.flush()
    db_session.add(Ingredient(recipe_id=r.recipe_id, name="x", quantity=1, unit="g"))
    db_session.flush()

    dry = delete(recipe_id=str(r.recipe_id), dry_run=True)
    assert dry["applied"] is False
    assert dry["preview"]["name"] == f"{fresh}_DOOMED"
    assert dry["preview"]["ingredients_count"] == 1

    applied = delete(recipe_id=str(r.recipe_id), dry_run=False)
    assert applied["applied"] is True

    # Recipe is gone
    from backend.db.models import Recipe as R
    assert db_session.query(R).filter(R.recipe_id == r.recipe_id).first() is None


def test_delete_recipe_invalid(edit_tools):
    delete = _by_name(edit_tools, "delete_recipe")
    assert "error" in delete(recipe_id="not-a-uuid")
    assert "error" in delete(recipe_id=str(uuid.uuid4()))
