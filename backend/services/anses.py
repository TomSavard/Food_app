"""
Backwards-compat shim. The reference data has moved to
`backend/services/reference.py` (sex-aware, source-cited, JSON-backed).

This module keeps the old import surface alive so existing callers don't
break. New code should import from `reference` directly.
"""
from __future__ import annotations

from backend.services.reference import (
    DAILY_MACROS,
    lower_is_better_set,
    rdi_for,
)

# Default RDI = adult male.
RDI: dict[str, float] = rdi_for("male")

LOWER_IS_BETTER: set[str] = lower_is_better_set()

__all__ = ["RDI", "LOWER_IS_BETTER", "DAILY_MACROS"]
