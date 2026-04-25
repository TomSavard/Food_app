"""
/api/match endpoints — fuzzy ingredient matching.

The frontend calls /candidates when a free-text ingredient is entered;
the user picks one (or 'create') and the match is persisted as an alias.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.db.models import IngredientDatabase
from backend.db.session import get_db
from backend.services import ingredient_match

router = APIRouter(prefix="/api/match", tags=["match"])


class CanonicalRow(BaseModel):
    id: str
    name: str
    category: Optional[str] = None
    source: str

    model_config = ConfigDict(from_attributes=False)


class CandidateOut(BaseModel):
    ingredient_db_id: str
    name: str
    reason: str
    confidence: float


class CandidatesResponse(BaseModel):
    exact: Optional[CanonicalRow] = None
    llm_candidates: list[CandidateOut]


def _to_row(r: IngredientDatabase) -> CanonicalRow:
    return CanonicalRow(
        id=str(r.id), name=r.alim_nom_fr, category=r.category, source=r.source
    )


@router.get("/candidates", response_model=CandidatesResponse)
def candidates(
    name: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    exact = ingredient_match.lookup_exact(db, name)
    if exact:
        return CandidatesResponse(exact=_to_row(exact), llm_candidates=[])
    cands = ingredient_match.llm_candidates(db, name)
    return CandidatesResponse(
        exact=None, llm_candidates=[CandidateOut(**c) for c in cands]
    )


class ConfirmRequest(BaseModel):
    name: str
    ingredient_db_id: str


@router.post("/confirm", response_model=CanonicalRow)
def confirm(req: ConfirmRequest, db: Session = Depends(get_db)):
    row = ingredient_match.confirm_match(
        db, req.name, UUID(req.ingredient_db_id), created_by="user"
    )
    db.commit()
    return _to_row(row)


class CreateRequest(BaseModel):
    name: str
    category: Optional[str] = None


@router.post("/create", response_model=CanonicalRow, status_code=201)
def create(req: CreateRequest, db: Session = Depends(get_db)):
    row = ingredient_match.create_new(
        db, req.name, category=req.category, created_by="user"
    )
    db.commit()
    return _to_row(row)
