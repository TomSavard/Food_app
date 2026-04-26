"""
/api/reference — read-only endpoints exposing ANSES + Interfel data.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from backend.services import reference

router = APIRouter(prefix="/api/reference", tags=["reference"])


@router.get("/rdi")
def get_rdi():
    """Full ANSES daily intake reference table (sources + both sexes)."""
    return reference.rdi_payload()


@router.get("/seasonality")
def get_seasonality():
    """Full Interfel calendar (every fruit + légume × 12 months)."""
    return reference.seasonality_payload()


@router.get("/seasonality/in-season")
def get_in_season(month: Optional[int] = Query(None, ge=1, le=12)):
    """Items in season for the given month (defaults to the current month)."""
    m = month if month is not None else date.today().month
    return {"month": m, "items": reference.seasonality_for(m)}
