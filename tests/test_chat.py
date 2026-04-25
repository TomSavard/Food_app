"""Tests for /api/chat. Gemini is mocked — no real API calls."""
import os
from unittest.mock import patch

import pytest


def test_chat_empty_messages_400(client):
    res = client.post("/api/chat", json={"messages": []})
    assert res.status_code == 400


def test_chat_missing_api_key_500(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    res = client.post("/api/chat", json={"messages": [{"role": "user", "text": "hi"}]})
    assert res.status_code == 500
    assert "GEMINI_API_KEY" in res.json()["detail"]


def test_chat_streams_chunks(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")

    class FakeChunk:
        def __init__(self, text):
            self.text = text

    class FakeModels:
        def generate_content_stream(self, **kwargs):
            for t in ["Hello ", "world", "!"]:
                yield FakeChunk(t)

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    with patch("backend.api.chat.genai.Client", FakeClient):
        res = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "text": "hi"}]},
        )
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        body = res.text
        assert '"Hello "' in body
        assert '"world"' in body
        assert '"!"' in body
        assert "[DONE]" in body


def test_meal_plan_tools(client, db_session):
    """Exercise the 4 meal-plan tools (stack model)."""
    from datetime import date, timedelta
    from backend.api.chat import _build_meal_plan_tools
    from backend.db.models import Recipe

    today = date.today()
    monday = today + timedelta(days=(0 - today.weekday()) % 7 or 7)

    r = Recipe(name="Pasta", servings=2, is_favorite=True)
    db_session.add(r); db_session.flush()

    get_plan, add_meal, remove_meal, generate = _build_meal_plan_tools(db_session)

    assert get_plan(monday.isoformat())["slots"] == []

    out = add_meal(monday.isoformat(), str(r.recipe_id), 4)
    assert out["recipe_name"] == "Pasta"
    assert out["servings"] == 4
    assert out["position"] == 0

    out2 = add_meal(monday.isoformat(), str(r.recipe_id), 2)
    assert out2["position"] == 1

    assert remove_meal(out["slot_id"])["deleted"] is True

    gen = generate(monday.isoformat(), meals_per_day=2)
    # 7 days × 2 meals; one already exists from add_meal #2 so it counts toward Monday's quota.
    assert len(gen["slots"]) >= 7 * 2 - 1


def test_list_recipes_tool_filters(client, db_session):
    """Direct test of the bound tool function, exercising the DB filter logic."""
    from backend.api.chat import _build_list_recipes_tool
    from backend.db.models import Recipe, Ingredient

    r1 = Recipe(name="Pasta", cuisine_type="italian", tags=["quick"], servings=2)
    r2 = Recipe(name="Sushi", cuisine_type="japanese", tags=["fish"], servings=2)
    db_session.add_all([r1, r2])
    db_session.flush()
    db_session.add(Ingredient(recipe_id=r1.recipe_id, name="tomate", quantity=2, unit="pcs"))
    db_session.flush()

    list_recipes = _build_list_recipes_tool(db_session)

    by_cuisine = list_recipes(cuisine="japan")
    assert any(r["name"] == "Sushi" for r in by_cuisine)
    assert not any(r["name"] == "Pasta" for r in by_cuisine)

    by_ing = list_recipes(ingredient="tomate")
    assert any(r["name"] == "Pasta" for r in by_ing)
    assert not any(r["name"] == "Sushi" for r in by_ing)
