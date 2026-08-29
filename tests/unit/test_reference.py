"""Unit tests for reference endpoints — runs against SQLite."""

def test_endpoint_rdi(client):
    res = client.get("/api/reference/rdi")
    assert res.status_code == 200


def test_endpoint_seasonality_in_season_default(client):
    res = client.get("/api/reference/seasonality")
    assert res.status_code == 200


def test_endpoint_seasonality_in_season_with_month(client):
    res = client.get("/api/reference/seasonality", params={"month": "6"})
    assert res.status_code == 200
