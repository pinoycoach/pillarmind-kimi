"""Golden cases: the bench's hand-derived findings, checked against the real pipeline.

Each golden/<chart>.json holds an "input" (birth datetime, city, sex, as_of, layers) and an
"expected" object. The expected values are written from the bench's documented findings, never
captured from the resolver's own output. Matching is by subset: only the paths the bench
documented are checked. For an ESCALATED field, token and pending must match exactly and every
expected candidate must be present.

A golden file whose input birth datetime is still null (DECISIONS N15) is skipped, loudly.
"""
import datetime as dt
import json
import pathlib

import pytest

from resolver import resolve_chart

GOLDEN = pathlib.Path(__file__).resolve().parent.parent / "golden"
# golden_local/ holds golden cases with real birth data. It is git-ignored and exists only on the
# operator's machine; when present, its files run too.
GOLDEN_LOCAL = GOLDEN.parent / "golden_local"
FILES = sorted(GOLDEN.glob("*.json")) + sorted(GOLDEN_LOCAL.glob("*.json"))


def _match(expected, actual, path="$"):
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path}: expected an object, got {actual!r}"
        if expected.get("token") == "ESCALATED":
            assert actual.get("token") == "ESCALATED", f"{path}: expected ESCALATED, got {actual!r}"
            if "pending" in expected:
                assert actual.get("pending") == expected["pending"], \
                    f"{path}: pending {actual.get('pending')!r} != {expected['pending']!r}"
            got = actual.get("pending")
            got = [got] if isinstance(got, str) else (got or [])
            lacking = [p for p in expected.get("pending_includes", []) if p not in got]
            assert not lacking, f"{path}: pending {got!r} lacks {lacking}"
            missing = [c for c in expected.get("candidates", []) if c not in actual.get("candidates", [])]
            assert not missing, f"{path}: candidates missing {missing}"
            rest = {k: v for k, v in expected.items()
                    if k not in ("token", "pending", "pending_includes", "candidates")}
            _match(rest, actual, path)
            return
        for k, v in expected.items():
            if k.startswith("_"):
                continue
            assert k in actual, f"{path}.{k}: missing"
            _match(v, actual[k], f"{path}.{k}")
    else:
        assert expected == actual, f"{path}: expected {expected!r}, got {actual!r}"


def _pillars(result):
    return {pid: p["stem"] + p["branch"] for pid, p in result["pillars"].items()}


@pytest.mark.parametrize("path", FILES, ids=[f"{f.parent.name}/{f.stem}" for f in FILES])
def test_golden(path):
    case = json.loads(path.read_text(encoding="utf-8"))
    inp = case["input"]
    if not inp.get("birth"):
        pytest.skip(f"{path.name}: birth datetime not supplied yet (DECISIONS N15)")
    result = resolve_chart(
        dt.datetime.fromisoformat(inp["birth"]), inp["city"], inp["sex"],
        as_of=dt.datetime.fromisoformat(inp["as_of"]) if inp.get("as_of") else None,
        layers=tuple(inp.get("layers", ())), hour_known=inp.get("hour_known", True))
    expected = dict(case["expected"])
    pillars = expected.pop("pillars", None)
    if pillars:
        _match(pillars, _pillars(result), "$.pillars")
    for pid in expected.pop("absent_pillars", []):
        assert pid not in result["pillars"], f"$.pillars.{pid}: expected absent"
    hidden = expected.pop("hidden_stems", None)
    if hidden:
        actual = {pid: [h["stem"] for h in p["hidden_stems"]] for pid, p in result["pillars"].items()}
        _match(hidden, actual, "$.hidden_stems")
    _match(expected, result)


def test_golden_files_exist():
    assert {f.stem for f in GOLDEN.glob("*.json")} >= {"digong", "aa_natal", "aa_gengyin_decade", "sara_2026_08"}
