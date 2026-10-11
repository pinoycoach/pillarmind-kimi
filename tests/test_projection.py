"""P-1: the pillarmind.resolver/v1 projection, on the real pipeline (derive → resolve → project).

Expected values are hand-derived from the 藏干 table, never read off the code. The fixture chart
己酉 庚午 辛巳 癸巳 runs on a placeholder birth, 2029-06-20 10:00 Manila, chosen because it
reproduces those four pillars; it is not anyone's birth record.
"""
import datetime as dt
import hashlib
import json
import pathlib
import re

import pytest

from resolver import resolve_chart
from resolver.projection import project_v1

GOLDEN = pathlib.Path(__file__).resolve().parent.parent / "golden"
ALL_LAYERS = ("decade", "annual", "monthly", "daily")

# 本氣 (main qi) of each branch, hand-written from the 藏干 table.
MAIN_QI = {"子": "癸", "丑": "己", "寅": "甲", "卯": "乙", "辰": "戊", "巳": "丙",
           "午": "丁", "未": "己", "申": "庚", "酉": "辛", "戌": "戊", "亥": "壬"}
STEMS_AND_BRANCHES = set("甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥")


def _fixture():
    return resolve_chart(dt.datetime(2029, 6, 20, 10, 0), "Manila", "male",
                         as_of=dt.datetime(2059, 3, 1, 12, 0), layers=ALL_LAYERS)


def _golden(name):
    inp = json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))["input"]
    return resolve_chart(dt.datetime.fromisoformat(inp["birth"]), inp["city"], inp["sex"],
                         as_of=dt.datetime.fromisoformat(inp["as_of"]), layers=ALL_LAYERS,
                         hour_known=inp.get("hour_known", True))


CHARTS = {"fixture": _fixture, "digong": lambda: _golden("digong"),
          "sara": lambda: _golden("sara_2026_08")}


def test_fixture_chart_projects_to_exactly_the_hand_derived_map():
    pillars = {"year": "己酉", "month": "庚午", "day": "辛巳", "hour": "癸巳"}
    canonical = '{"day":"辛巳","hour":"癸巳","month":"庚午","year":"己酉"}'
    expected = {
        "schema": "pillarmind.resolver/v1",
        "chart_id": "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "pillars": pillars,
        "hidden_stems": {"酉": ["辛"], "午": ["丁", "己"], "巳": ["丙", "庚", "戊"]},
    }
    out = project_v1(_fixture())
    assert out == expected
    assert json.dumps(out, ensure_ascii=False) == json.dumps(expected, ensure_ascii=False)  # key order too


@pytest.mark.parametrize("chart", CHARTS)
def test_hidden_stems_cover_exactly_the_pillar_branches_main_qi_first(chart):
    out = project_v1(CHARTS[chart]())
    branches = {p[1] for p in out["pillars"].values()}
    assert set(out["hidden_stems"]) == branches
    for branch, stems in out["hidden_stems"].items():
        assert stems and stems[0] == MAIN_QI[branch], f"{branch}: {stems}"
    if chart == "sara":
        assert "hour" not in out["pillars"]      # hour unknown: absent, not guessed


def _walk_keys(node, path="$"):
    if isinstance(node, dict):
        for k, v in node.items():
            yield path, k
            yield from _walk_keys(v, f"{path}.{k}")
    elif isinstance(node, list):
        for v in node:
            yield from _walk_keys(v, path)


@pytest.mark.parametrize("chart", CHARTS)
def test_projection_leaks_no_personal_field(chart):
    field_map = CHARTS[chart]()
    out = project_v1(field_map)
    allowed = {"$": {"schema", "chart_id", "pillars", "hidden_stems"},
               "$.pillars": {"year", "month", "day", "hour"},
               "$.hidden_stems": STEMS_AND_BRANCHES}
    for path, key in _walk_keys(out):
        assert key in allowed.get(path, ()), f"unexpected key {key!r} at {path}"

    assert re.fullmatch(r"sha256:[0-9a-f]{64}", out["chart_id"])
    text = json.dumps(out, ensure_ascii=False).replace(out["chart_id"], "")  # format checked above
    assert not re.search(r"\d{2,}", text), "digit run that could be a year or date"
    assert not re.search(r"[A-Z]", text), "capital letter: timezone name, abbreviation or place"
    assert set(c for c in text if ord(c) > 127) <= STEMS_AND_BRANCHES
    inp = field_map["input"]
    personal = [inp["birth"], inp["birth"][:10], inp["birth"][:4], inp["city"], inp["zone"],
                inp["sex"], inp["as_of"], inp["as_of"][:10], inp["as_of_zone"]]
    leaked = [v for v in personal if v.lower() in text.lower()]
    assert not leaked, f"personal field in projection: {leaked}"
