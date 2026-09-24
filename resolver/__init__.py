"""PillarMind Phase 1 resolver: birth datetime + city → Resolved Field Map (JSON).

Deterministic. No network calls, no language-model calls, anywhere in this package.
"""
from __future__ import annotations

import datetime as dt

from .derive import HardStop, derive
from .resolve import resolve, to_json

__all__ = ["resolve_chart", "HardStop", "to_json"]


def resolve_chart(birth: dt.datetime, city: str, sex: str, as_of: dt.datetime | None = None,
                  layers: tuple = ("decade", "annual"), hour_known: bool = True) -> dict:
    """The full pipeline: derive (lunar-python) → resolve. hour_known=False uses the date only."""
    return resolve(derive(birth, city, sex, as_of=as_of, layers=layers if as_of else (),
                          hour_known=hour_known))
