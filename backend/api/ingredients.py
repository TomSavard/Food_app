"""
/api/ingredients — knowledge-base browse + curation surface.

- GET /search?q=...               : autocomplete (matches name OR alias)
- GET /                           : paginated list with filters
- GET /{id}                       : full row + aliases
- PATCH /{id}                     : edit name/category/density/nutrition_data; sets modified flag
- POST /{id}/llm-fill             : LLM proposes values for empty nutrient cells
- POST /{id}/llm-density          : LLM proposes density_g_per_ml
- DELETE /{id}/aliases/{alias_id} : remove a wrong alias
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from backend.db.models import IngredientAlias, IngredientDatabase
from backend.db.session import get_db
from backend.services.categorize import CATEGORIES

router = APIRouter(prefix="/api/ingredients", tags=["ingredients"])


# ---------- Schemas ----------

class AliasOut(BaseModel):
    alias_id: str
    alias_text: str
    created_by: str

    model_config = ConfigDict(from_attributes=False)


class IngredientSearchResponse(BaseModel):
    id: str
    name: str
    has_nutrition_data: bool

    model_config = ConfigDict(from_attributes=True)


class IngredientRow(BaseModel):
    id: str
    name: str
    category: Optional[str] = None
    source: str
    modified: bool
    modified_by: Optional[str] = None
    modified_at: Optional[datetime] = None
    density_g_per_ml: Optional[float] = None
    aliases: List[AliasOut] = []


class IngredientDetail(IngredientRow):
    nutrition_data: dict[str, Any] = {}


class IngredientListResponse(BaseModel):
    items: List[IngredientRow]
    total: int


class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    density_g_per_ml: Optional[float] = None
    nutrition_data: Optional[dict[str, Any]] = None  # full or partial replacement (merge)
    add_alias: Optional[str] = None  # convenience: add an alias in the same call


class LLMFillResponse(BaseModel):
    proposal: dict[str, Any]


class LLMFillConfirm(BaseModel):
    values: dict[str, Any]


class LLMDensityResponse(BaseModel):
    value: float
    reason: str


# ---------- Helpers ----------

def _to_alias(a: IngredientAlias) -> AliasOut:
    return AliasOut(
        alias_id=str(a.alias_id), alias_text=a.alias_text, created_by=a.created_by
    )


def _to_row(r: IngredientDatabase) -> IngredientRow:
    return IngredientRow(
        id=str(r.id),
        name=r.alim_nom_fr,
        category=r.category,
        source=r.source,
        modified=r.modified,
        modified_by=r.modified_by,
        modified_at=r.modified_at,
        density_g_per_ml=r.density_g_per_ml,
        aliases=[_to_alias(a) for a in (r.aliases or [])],
    )


def _to_detail(r: IngredientDatabase) -> IngredientDetail:
    return IngredientDetail(
        **_to_row(r).model_dump(),
        nutrition_data=r.nutrition_data or {},
    )


def _has_missing_nutrients(nd: Optional[dict]) -> bool:
    if not nd:
        return True
    return any(v is None or v == "" for v in nd.values())


def _mark_modified(row: IngredientDatabase, by: str) -> None:
    row.modified = True
    row.modified_by = by
    row.modified_at = datetime.now(timezone.utc)


def _gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set")
    from google import genai
    return genai.Client(api_key=api_key)


# ---------- Endpoints ----------

@router.get("/search", response_model=List[IngredientSearchResponse])
def search_ingredients(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Autocomplete. Matches canonical name OR any alias."""
    needle = q.strip().lower()
    if not needle:
        return []
    pattern = f"%{needle}%"

    # Direct name matches.
    name_rows = (
        db.query(IngredientDatabase)
        .filter(IngredientDatabase.alim_nom_fr.ilike(pattern))
        .limit(limit * 2)
        .all()
    )
    # Alias matches → resolve to canonical.
    alias_rows = (
        db.query(IngredientAlias)
        .filter(IngredientAlias.alias_text.ilike(pattern))
        .limit(limit * 2)
        .all()
    )
    by_id: dict[str, IngredientDatabase] = {str(r.id): r for r in name_rows}
    for a in alias_rows:
        if str(a.ingredient_db_id) not in by_id:
            ref = db.get(IngredientDatabase, a.ingredient_db_id)
            if ref:
                by_id[str(ref.id)] = ref

    # Score: exact > startswith > contains.
    scored = []
    for r in by_id.values():
        n = r.alim_nom_fr.lower()
        if n == needle:
            score = 1000
        elif n.startswith(needle):
            score = 500 - len(n)
        else:
            score = 100 - n.find(needle) - len(n) / 10
        scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        IngredientSearchResponse(
            id=str(r.id),
            name=r.alim_nom_fr,
            has_nutrition_data=bool(r.nutrition_data),
        )
        for _, r in scored[:limit]
    ]


@router.get("", response_model=IngredientListResponse)
def list_ingredients(
    search: Optional[str] = None,
    category: Optional[str] = None,
    missing: bool = False,
    missing_density: bool = False,
    modified: Optional[bool] = None,
    source: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(IngredientDatabase)
    if search:
        pat = f"%{search.strip().lower()}%"
        # Subquery so the alias match piggybacks on the GIN trigram index instead
        # of round-tripping a (potentially large) id list back to Postgres.
        alias_subq = (
            db.query(IngredientAlias.ingredient_db_id)
            .filter(IngredientAlias.alias_text.ilike(pat))
            .subquery()
        )
        q = q.filter(
            or_(
                IngredientDatabase.alim_nom_fr.ilike(pat),
                IngredientDatabase.id.in_(alias_subq.select()),
            )
        )
    if category:
        q = q.filter(IngredientDatabase.category == category)
    if modified is not None:
        q = q.filter(IngredientDatabase.modified.is_(modified))
    if source:
        q = q.filter(IngredientDatabase.source == source)
    if missing_density:
        q = q.filter(IngredientDatabase.density_g_per_ml.is_(None))

    if missing:
        # JSONB heuristic in SQL: row counts as "missing" when nutrition_data is
        # NULL/empty OR at least one value is JSON null. Pulls all matches once
        # through the index — still bounded by the search/category filters above.
        from sqlalchemy import text as _text
        q = q.filter(
            or_(
                IngredientDatabase.nutrition_data.is_(None),
                _text("nutrition_data = '{}'::jsonb"),
                _text("EXISTS (SELECT 1 FROM jsonb_each(nutrition_data) e WHERE e.value = 'null'::jsonb)"),
            )
        )

    total = q.with_entities(func.count(IngredientDatabase.id)).scalar() or 0
    rows = (
        q.options(selectinload(IngredientDatabase.aliases))
        .order_by(IngredientDatabase.alim_nom_fr)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return IngredientListResponse(items=[_to_row(r) for r in rows], total=total)


@router.get("/{ingredient_id}", response_model=IngredientDetail)
def get_ingredient(ingredient_id: str, db: Session = Depends(get_db)):
    try:
        uid = UUID(ingredient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ingredient ID format")
    row = (
        db.query(IngredientDatabase)
        .options(selectinload(IngredientDatabase.aliases))
        .filter(IngredientDatabase.id == uid)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return _to_detail(row)


@router.patch("/{ingredient_id}", response_model=IngredientDetail)
def update_ingredient(
    ingredient_id: str, payload: IngredientUpdate, db: Session = Depends(get_db)
):
    try:
        uid = UUID(ingredient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ingredient ID format")
    row = (
        db.query(IngredientDatabase)
        .options(selectinload(IngredientDatabase.aliases))
        .filter(IngredientDatabase.id == uid)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    touched = False
    if payload.name is not None:
        row.alim_nom_fr = payload.name.strip()
        touched = True
    if payload.category is not None:
        if payload.category not in CATEGORIES:
            raise HTTPException(status_code=400, detail=f"Unknown category: {payload.category}")
        row.category = payload.category
        touched = True
    if payload.density_g_per_ml is not None:
        row.density_g_per_ml = float(payload.density_g_per_ml)
        touched = True
    if payload.nutrition_data is not None:
        merged = dict(row.nutrition_data or {})
        merged.update(payload.nutrition_data)
        row.nutrition_data = merged
        touched = True
    if payload.add_alias:
        alias_text = payload.add_alias.strip()
        if alias_text and alias_text.lower() != row.alim_nom_fr.lower():
            existing = (
                db.query(IngredientAlias)
                .filter(IngredientAlias.alias_text.ilike(alias_text))
                .first()
            )
            if existing is None:
                db.add(IngredientAlias(
                    ingredient_db_id=row.id,
                    alias_text=alias_text,
                    created_by="user",
                ))
                touched = True

    if touched:
        _mark_modified(row, "user")
        db.commit()
        db.refresh(row)
    return _to_detail(row)


@router.delete("/{ingredient_id}/aliases/{alias_id}", status_code=204)
def delete_alias(ingredient_id: str, alias_id: str, db: Session = Depends(get_db)):
    try:
        aid = UUID(alias_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alias_id")
    deleted = (
        db.query(IngredientAlias).filter(IngredientAlias.alias_id == aid).delete()
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Alias not found")
    db.commit()


@router.post("/{ingredient_id}/llm-fill", response_model=LLMFillResponse)
def llm_fill_proposal(ingredient_id: str, db: Session = Depends(get_db)):
    """Ask Gemini to propose values for empty nutrient cells. Returns a
    proposal — the caller must then PATCH to persist."""
    try:
        uid = UUID(ingredient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ingredient ID format")
    row = db.get(IngredientDatabase, uid)
    if not row:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    nd = dict(row.nutrition_data or {})
    empty_keys = [k for k, v in nd.items() if v is None or v == ""]
    if not empty_keys:
        return LLMFillResponse(proposal={})

    client = _gemini_client()
    from google.genai import types

    prompt = (
        f"Pour l'ingrédient « {row.alim_nom_fr} », propose des valeurs nutritionnelles "
        "réalistes (par 100 g) pour les colonnes manquantes ci-dessous. "
        "Réponds UNIQUEMENT avec un JSON {colonne: valeur_numérique}. "
        "Si tu ne peux pas estimer une colonne, omets-la.\n\n"
        f"Colonnes manquantes: {empty_keys}"
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    try:
        proposal = json.loads(response.text or "{}")
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=502, detail=f"Bad LLM response: {e}")
    # Filter to keys we asked about.
    proposal = {k: v for k, v in proposal.items() if k in empty_keys}
    return LLMFillResponse(proposal=proposal)


@router.post("/{ingredient_id}/llm-fill/confirm", response_model=IngredientDetail)
def llm_fill_confirm(
    ingredient_id: str, payload: LLMFillConfirm, db: Session = Depends(get_db)
):
    """Persist the (possibly user-edited) LLM proposal."""
    try:
        uid = UUID(ingredient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ingredient ID format")
    row = (
        db.query(IngredientDatabase)
        .options(selectinload(IngredientDatabase.aliases))
        .filter(IngredientDatabase.id == uid)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    merged = dict(row.nutrition_data or {})
    merged.update(payload.values)
    row.nutrition_data = merged
    _mark_modified(row, "llm")
    db.commit()
    db.refresh(row)
    return _to_detail(row)


@router.post("/{ingredient_id}/llm-density", response_model=LLMDensityResponse)
def llm_density(ingredient_id: str, db: Session = Depends(get_db)):
    """Estimate density_g_per_ml. The caller PATCHes to persist."""
    try:
        uid = UUID(ingredient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ingredient ID format")
    row = db.get(IngredientDatabase, uid)
    if not row:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    client = _gemini_client()
    from google.genai import types
    prompt = (
        f"Estime la densité en g/ml d'un mililitre de « {row.alim_nom_fr} ». "
        "Réponds UNIQUEMENT en JSON {value: number, reason: string}. "
        "Pour information: eau ≈ 1.0, lait ≈ 1.03, huile végétale ≈ 0.92, miel ≈ 1.42."
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    try:
        parsed = json.loads(response.text or "{}")
        value = float(parsed.get("value"))
        reason = str(parsed.get("reason") or "")
    except (TypeError, ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=502, detail=f"Bad LLM response: {e}")
    return LLMDensityResponse(value=value, reason=reason)
