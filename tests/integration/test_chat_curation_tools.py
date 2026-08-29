"""Direct tests for the reference-curation + shopping-write chat tools (PR C)."""
import uuid

import pytest

from backend.api.chat import (
    _build_reference_write_tools,
    _build_shopping_write_tools,
)
from backend.db.models import (
    IngredientAlias,
    IngredientDatabase,
    ShoppingList,
    ShoppingListContribution,
)


@pytest.fixture
def fresh():
    return f"TEST_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def shop_tools(db_session):
    return _build_shopping_write_tools(db_session)


@pytest.fixture
def ref_tools(db_session):
    return _build_reference_write_tools(db_session)


def _by_name(tools, name):
    return next(t for t in tools if t.__name__ == name)


# ---- shopping writes ----

def test_add_shopping_item_creates_and_appends(shop_tools, db_session, fresh):
    add = _by_name(shop_tools, "add_shopping_item")
    res = add(name=f"{fresh}_LAIT", quantity_text="1 L")
    assert "item_id" in res
    assert res["name"] == f"{fresh}_LAIT"
    item = db_session.query(ShoppingList).filter(ShoppingList.item_id == uuid.UUID(res["item_id"])).first()
    assert item is not None
    contribs = (
        db_session.query(ShoppingListContribution)
        .filter(ShoppingListContribution.item_id == item.item_id).all()
    )
    assert any(c.quantity_text == "1 L" for c in contribs)


def test_add_shopping_item_requires_name(shop_tools):
    add = _by_name(shop_tools, "add_shopping_item")
    assert "error" in add(name="")


def test_toggle_shopping_item(shop_tools, db_session, fresh):
    toggle = _by_name(shop_tools, "toggle_shopping_item")
    item = ShoppingList(name=f"{fresh}_X", position=999, is_checked=False)
    db_session.add(item); db_session.flush()
    iid = str(item.item_id)
    assert toggle(item_id=iid, is_checked=True)["is_checked"] is True
    assert toggle(item_id=iid, is_checked=False)["is_checked"] is False
    assert "error" in toggle(item_id=str(uuid.uuid4()), is_checked=True)


def test_remove_shopping_item(shop_tools, db_session, fresh):
    remove = _by_name(shop_tools, "remove_shopping_item")
    item = ShoppingList(name=f"{fresh}_X", position=999)
    db_session.add(item); db_session.flush()
    iid = str(item.item_id)
    assert remove(item_id=iid)["deleted"] is True
    assert remove(item_id=iid)["deleted"] is False


# ---- reference writes ----

def _make_canon(db, fresh, **kwargs):
    row = IngredientDatabase(
        alim_nom_fr=f"{fresh}_CANON",
        nutrition_data=kwargs.pop("nutrition_data", {"a": 1.0, "b": None}),
        **kwargs,
    )
    db.add(row); db.flush()
    return row


def test_set_ingredient_category(ref_tools, db_session, fresh):
    setcat = _by_name(ref_tools, "set_ingredient_category")
    row = _make_canon(db_session, fresh)
    res = setcat(ingredient_db_id=str(row.id), category="Boulangerie")
    assert res["category"] == "Boulangerie"


def test_set_ingredient_category_invalid(ref_tools, db_session, fresh):
    setcat = _by_name(ref_tools, "set_ingredient_category")
    row = _make_canon(db_session, fresh)
    assert "error" in setcat(ingredient_db_id=str(row.id), category="Bogus")


def test_set_ingredient_density(ref_tools, db_session, fresh):
    setden = _by_name(ref_tools, "set_ingredient_density")
    row = _make_canon(db_session, fresh)
    res = setden(ingredient_db_id=str(row.id), value=0.92)
    assert res["density_g_per_ml"] == 0.92
    assert "error" in setden(ingredient_db_id=str(row.id), value=0)


def test_add_ingredient_alias(ref_tools, db_session, fresh):
    add_alias = _by_name(ref_tools, "add_ingredient_alias")
    row = _make_canon(db_session, fresh)
    res = add_alias(ingredient_db_id=str(row.id), alias_text=f"{fresh}_alt")
    assert res["alias_added"] == f"{fresh}_alt"
    aliases = (
        db_session.query(IngredientAlias)
        .filter(IngredientAlias.ingredient_db_id == row.id).all()
    )
    assert any(a.alias_text == f"{fresh}_alt" for a in aliases)
    # duplicate -> skipped
    res2 = add_alias(ingredient_db_id=str(row.id), alias_text=f"{fresh}_alt")
    assert "skipped" in res2


def test_add_alias_equals_canonical(ref_tools, db_session, fresh):
    add_alias = _by_name(ref_tools, "add_ingredient_alias")
    row = _make_canon(db_session, fresh)
    res = add_alias(ingredient_db_id=str(row.id), alias_text=row.alim_nom_fr)
    assert "skipped" in res


def test_fill_nutrition_dry_run_then_apply(ref_tools, db_session, fresh, monkeypatch):
    fill = _by_name(ref_tools, "fill_ingredient_nutrition")
    row = _make_canon(db_session, fresh, nutrition_data={"a": 1.0, "b": None, "c": None})

    # Mock the underlying llm_fill_proposal to return a deterministic proposal.
    from backend.api import ingredients as ing_mod

    class _Resp:
        proposal = {"b": 2.5, "c": 3.7}

    def _fake(ingredient_id, db):  # noqa: ARG001
        return _Resp()

    monkeypatch.setattr(ing_mod, "llm_fill_proposal", _fake)

    dry = fill(ingredient_db_id=str(row.id), dry_run=True)
    assert dry["applied"] is False
    assert dry["proposal"] == {"b": 2.5, "c": 3.7}

    applied = fill(ingredient_db_id=str(row.id), dry_run=False)
    assert applied["applied"] is True
    assert set(applied["filled"]) == {"b", "c"}
    db_session.refresh(row)
    assert row.nutrition_data["b"] == 2.5
    assert row.nutrition_data["c"] == 3.7


def test_fill_nutrition_invalid_id(ref_tools):
    fill = _by_name(ref_tools, "fill_ingredient_nutrition")
    assert "error" in fill(ingredient_db_id="not-a-uuid")
    assert "error" in fill(ingredient_db_id=str(uuid.uuid4()))
