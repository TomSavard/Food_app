"""Tests for the reference data loaders + endpoints."""
from backend.services import reference


def test_rdi_payload_loads():
    p = reference.rdi_payload()
    assert "sources" in p and "nutrients" in p
    assert len(p["nutrients"]) >= 25


def test_rdi_energy_matches_anses_2016():
    male = reference.rdi_for("male")
    female = reference.rdi_for("female")
    cal = "Energie, Règlement UE N° 1169 2011 (kcal 100 g)"
    # ANSES 2016 macros report, p.23: 2600 kcal H, 2100 kcal F.
    assert male[cal] == 2600
    assert female[cal] == 2100


def test_rdi_pages_set_for_documented_nutrients():
    p = reference.rdi_payload()
    pages = [n["source_page"] for n in p["nutrients"]
             if n["source_id"] == "vitamins_minerals"]
    # All vitamins/minerals rows should have a page from the ANSES 2021 PDF.
    assert all(isinstance(pg, int) for pg in pages), pages


def test_rdi_for_male_vs_female_differ():
    male = reference.rdi_for("male")
    female = reference.rdi_for("female")
    diffs = [k for k in male if male[k] != female[k]]
    # Calcium, Fer, Magnésium, Zinc, kcal, AG sat, glucides, lipides, B1, B3, vit A — at least these.
    assert len(diffs) >= 8, f"only {diffs} differ"


def test_seasonality_for_april_includes_known_items():
    items = reference.seasonality_for(4)
    names = {it["name"] for it in items}
    assert "Asperge" in names
    assert "Radis" in names


def test_seasonality_sort_coeur_before_saison():
    items = reference.seasonality_for(7)
    levels = [it["level"] for it in items]
    # All 'coeur' items come before any 'saison' item.
    last_coeur = max((i for i, lv in enumerate(levels) if lv == "coeur"), default=-1)
    first_saison = next((i for i, lv in enumerate(levels) if lv == "saison"), len(levels))
    assert last_coeur < first_saison


def test_endpoint_rdi(client):
    res = client.get("/api/reference/rdi")
    assert res.status_code == 200
    body = res.json()
    assert "nutrients" in body
    assert any(n["category"] == "macros" for n in body["nutrients"])


def test_endpoint_seasonality_in_season_default(client):
    res = client.get("/api/reference/seasonality/in-season")
    assert res.status_code == 200
    body = res.json()
    assert 1 <= body["month"] <= 12
    assert isinstance(body["items"], list)


def test_endpoint_seasonality_in_season_with_month(client):
    res = client.get("/api/reference/seasonality/in-season", params={"month": 4})
    body = res.json()
    assert body["month"] == 4
    names = {it["name"] for it in body["items"]}
    assert "Asperge" in names
