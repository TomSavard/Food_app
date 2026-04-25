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
