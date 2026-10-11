"""P-1: the N48-clean projection of a Resolved Field Map, schema pillarmind.resolver/v1.

Built by allow-list, never by stripping: the output is assembled from the natal pillars' stem and
branch characters and their hidden stems, each checked against the closed stem and branch sets,
so no input, date, place, zone, sex, decade or note field can reach it, at any depth. Transit
layers are left out because they are dated by as_of (N48). Hidden stems keep the resolver's order
(lunar-python, U14: main qi first); this module holds no hidden-stem table of its own.

chart_id hashes the pillars alone, so it names the chart, not the person: two births with the same
four pillars share it. A hash of the birth record would be a brute-forceable stand-in for the date.
"""
from __future__ import annotations

import hashlib
import json

from .tables import BRANCHES, NATAL_POSITIONS, STEMS

SCHEMA = "pillarmind.resolver/v1"


def _one_of(chars: str, value, what: str) -> str:
    if not (isinstance(value, str) and len(value) == 1 and value in chars):
        raise ValueError(f"not a {what}: {value!r}")
    return value


def project_v1(field_map: dict) -> dict:
    """The resolver's output → {schema, chart_id, pillars, hidden_stems} and nothing else.
    Hour unknown: the hour pillar is absent, never guessed."""
    pillars, hidden = {}, {}
    for position in NATAL_POSITIONS:
        p = field_map["pillars"].get(f"natal.{position}")
        if p is None:
            if position != "hour":
                raise ValueError(f"natal {position} pillar missing")
            continue
        stem = _one_of(STEMS, p["stem"], "heavenly stem")
        branch = _one_of(BRANCHES, p["branch"], "earthly branch")
        stems = [_one_of(STEMS, h["stem"], "heavenly stem") for h in p["hidden_stems"]]
        if not stems or hidden.get(branch, stems) != stems:
            raise ValueError(f"hidden stems of {branch} empty or inconsistent: {stems}")
        pillars[position] = stem + branch
        hidden[branch] = stems
    canonical = json.dumps(pillars, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "schema": SCHEMA,
        "chart_id": "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "pillars": pillars,
        "hidden_stems": hidden,
    }
