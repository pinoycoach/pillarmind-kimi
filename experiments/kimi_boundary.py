"""Kimi boundary experiment (DECISIONS N34). Not part of the resolver; the resolver never imports it.

Runs the resolver on golden/digong.json's input, sends the full Resolved Field Map to Kimi, and
checks the answer against the map:
  1. every cited item id exists in the map;
  2. every restated value equals the map's value;
  3. the `escalations` array lists every ESCALATED item, each with its candidates quoted word for
     word, and nothing else;
  4. no ESCALATED item is described as settled (structurally via restated values; in prose only as
     a secondary warning).
Kimi's raw output is saved under experiments/out/ (git-ignored). N5 and N6 stay open; this decides
neither.

Modes (--mode):
  boundary   (default) interpret-only instruction; the mode of run 20260924-222336 (N35), which
             produced a restatement of the map rather than an interpretation.
  interpret  TEST PROMPT, NOT N6: asks for a real layer-3 reading of the chart for 2026, under the
             same prohibitions (no recomputing or correcting the map, no choosing between candidates).

Usage (Windows PowerShell, in your own terminal; never paste the key into a chat or a file):
    $env:MOONSHOT_API_KEY = "<your key>"
    .\\.venv\\Scripts\\python.exe -X utf8 experiments\\kimi_boundary.py --mode interpret
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kimi_audit import BASE_URL, DEFAULT_MODEL      # same endpoint and model as the audit script
from resolver import resolve_chart, to_json

OUT = ROOT / "experiments" / "out"
ESC = "ESCALATED"

PREAMBLE = """You are given a Resolved Field Map for one BaZi chart, produced by a deterministic resolver, and an
ITEM CATALOG listing every item in that map by id, with its value.
"""

RULES = """- Every pillar, token, lock, clash, harm, destruction, punishment and escalation in the map is FIXED.
  Do not recompute, re-derive, or correct anything, even if you believe the map is wrong.
- Where an item's value is ESCALATED, lay out its candidates without choosing one. Do not describe
  an escalated item as settled, resolved, likely, or leaning either way.
- Refer to items only by the ids in the ITEM CATALOG.
"""

SCHEMA = """Return ONLY a JSON object with exactly these keys:
{
  "reading": "<your reading, plain prose>",
  "cited_items": ["<item id from the catalog>", ...],
  "restated_values": [{"id": "<item id>", "value": "<the item's value exactly as the catalog gives it>"}, ...],
  "escalations": [{"id": "<item id>", "candidates": ["<candidate, copied word for word from the catalog>", ...]}, ...]
}
"restated_values" must list every pillar or outcome your reading mentions, with its value.
"escalations" must list EVERY item whose catalog value is ESCALATED, each with ALL of its candidates
copied character for character from the catalog, in any order, and no other items."""

INSTRUCTIONS = {
    # The mode of run 20260924-222336 (N35).
    "boundary": PREAMBLE + "\nYour task is to INTERPRET ONLY.\n" + RULES + "\n" + SCHEMA,
    # TEST PROMPT, NOT N6. It exists to test the boundary under real interpretation; it is not the
    # interpretation prompt, which N6 has not decided.
    "interpret": PREAMBLE + """
Your task is a LAYER-3 READING of this chart for the year 2026 (the annual layer in the map).
- For each item that FIRES (value FULL_FORCE), each item that is LOCKED (LOCKED_FULL), and each
  item that is ELIMINATED, say what it means for this chart in 2026.
- For each ESCALATED item, give the reading under EACH candidate in turn, and say how the readings
  differ. Treat the candidates as equally open. Do not choose between them, rank them, or say
  which is more likely.
""" + RULES + "\n" + SCHEMA,
}
PROMPT_LABEL = {"boundary": "boundary (interpret-only)", "interpret": "interpret — TEST PROMPT, NOT N6"}


def load_digong_input():
    case = json.loads((ROOT / "golden" / "digong.json").read_text(encoding="utf-8"))
    i = case["input"]
    return dict(birth=dt.datetime.fromisoformat(i["birth"]), city=i["city"], sex=i["sex"],
                as_of=dt.datetime.fromisoformat(i["as_of"]), layers=tuple(i["layers"]))


def _value(v):
    """The single value an item carries: a token string, or ESCALATED for an escalation object."""
    if isinstance(v, dict) and v.get("token") == ESC:
        return ESC, list(v.get("candidates", []))
    return v, None


def catalog(field_map):
    """Every item in the map as id -> {value, candidates}. The ids are what Kimi must cite."""
    items = {}

    def put(item_id, raw):
        value, cands = _value(raw)
        items[item_id] = {"value": value, "candidates": cands}

    for pid, p in field_map["pillars"].items():
        put(f"pillars.{pid}", p["stem"] + p["branch"])
    put("void.pair", "".join(field_map["void"]["pair"]))
    if field_map.get("decade") and isinstance(field_map["decade"].get("in_force"), dict) \
            and "pillar" in field_map["decade"]["in_force"]:
        put("decade.in_force", field_map["decade"]["in_force"]["pillar"])
    for cid, c in field_map["branch_combinations"].items():
        put(f"branch_combinations.{cid}.lock", c.get("lock", c.get("status")))
        if "transformation" in c:
            put(f"branch_combinations.{cid}.transformation", c["transformation"])
    for pool in ("clashes", "harms", "destructions", "punishments"):
        for rid, rec in field_map[pool].items():
            put(f"{pool}.{rid}", rec["outcome"])
    for sid, s in field_map["stem_combinations"].items():
        put(f"stem_combinations.{sid}", s.get("state", s.get("status")))
    for pool in ("branch_tokens", "stem_tokens"):
        for pid, tok in field_map[pool].items():
            put(f"{pool}.{pid}", tok)
    for var, e in field_map["escalations"].items():
        put(f"escalations.{var}", e)
    return items


def ask_kimi(field_map, items, mode):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["MOONSHOT_API_KEY"], base_url=BASE_URL)
    user = ("RESOLVED FIELD MAP:\n" + to_json(field_map)
            + "\n\nITEM CATALOG (id -> value, and candidates where ESCALATED):\n"
            + json.dumps(items, ensure_ascii=False, indent=1))
    resp = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "system", "content": INSTRUCTIONS[mode]}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        # no temperature: Kimi models enforce their own fixed value (kimi_audit.py)
    )
    return resp


def parse(text):
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)                # tolerate stray fences or preamble
    return json.loads(m.group(0) if m else text)


def _named(candidate, reading):
    """True if the reading names a candidate by its label (any CJK term in it, e.g. 先合 / 爭合 / 情不專)
    or by its description (most of the English words after the colon, in any wording)."""
    if any(term in reading for term in re.findall(r"[一-鿿]{2,}", candidate)):
        return True
    desc = candidate.split(":", 1)[1] if ":" in candidate else candidate
    words = {w for w in re.findall(r"[a-z]{3,}", desc.lower())}
    if not words:
        return False
    text = set(re.findall(r"[a-z]{3,}", reading.lower()))
    return len(words & text) / len(words) >= 0.6


def check(answer, items):
    rows = []                                          # (check, subject, PASS/FAIL/WARN, detail)
    for key in ("reading", "cited_items", "restated_values", "escalations"):
        rows.append(("schema", key, "PASS" if key in answer else "FAIL", "" if key in answer else "missing key"))
    for cid in answer.get("cited_items", []):
        ok = cid in items
        rows.append(("cited id exists", cid, "PASS" if ok else "FAIL", "" if ok else "not in the map"))
    escalated = {k for k, v in items.items() if v["value"] == ESC}
    for rv in answer.get("restated_values", []):
        rid, val = rv.get("id"), str(rv.get("value", "")).strip()
        if rid not in items:
            rows.append(("restated value", str(rid), "FAIL", "id not in the map"))
            continue
        want = str(items[rid]["value"])
        rows.append(("restated value", rid, "PASS" if val == want else "FAIL",
                     "" if val == want else f"said {val!r}, map has {want!r}"))
        if rid in escalated and val != ESC:
            rows.append(("escalation not settled", rid, "FAIL", f"restated as {val!r}"))
    # The escalations array, checked exactly: every ESCALATED item, no others, candidates verbatim.
    listed = {}
    for entry in answer.get("escalations", []) or []:
        eid = entry.get("id") if isinstance(entry, dict) else None
        if eid in listed:
            rows.append(("escalations array", str(eid), "FAIL", "listed twice"))
        listed[eid] = entry.get("candidates", []) if isinstance(entry, dict) else None
    for rid in sorted(escalated):
        if rid not in listed:
            rows.append(("escalations array", rid, "FAIL", "ESCALATED item missing"))
            continue
        want, got = items[rid]["candidates"], listed[rid]
        ok = isinstance(got, list) and sorted(map(str, got)) == sorted(want)
        rows.append(("escalations array", rid, "PASS" if ok else "FAIL",
                     "" if ok else f"candidates not word for word: got {got!r}, map has {want!r}"))
    for eid in listed:
        if eid not in escalated:
            rows.append(("escalations array", str(eid), "FAIL",
                         "not an ESCALATED item" if eid in items else "id not in the map"))
    # Secondary warning on the prose: an escalated item whose candidates are named, but not all.
    reading = answer.get("reading", "")
    for rid in sorted(escalated):
        cands = items[rid]["candidates"] or []
        named = [c for c in cands if _named(c, reading)]
        if len(cands) >= 2 and 1 <= len(named) < len(cands):
            rows.append(("escalation not settled (prose heuristic)", rid, "WARN",
                         f"reading names {len(named)} of {len(cands)} candidates: {named!r}"))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=sorted(INSTRUCTIONS), default="boundary")
    mode = ap.parse_args().mode
    if not os.environ.get("MOONSHOT_API_KEY"):
        sys.exit("MOONSHOT_API_KEY is not set in this shell. Set it in your own terminal session "
                 "(PowerShell: $env:MOONSHOT_API_KEY = \"<your key>\") and run again. "
                 "Never paste the key into a chat or a file.")
    print(f"Mode: {PROMPT_LABEL[mode]}")
    field_map = resolve_chart(**load_digong_input())
    items = catalog(field_map)
    resp = ask_kimi(field_map, items, mode)
    raw = resp.choices[0].message.content or ""

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    record = {
        "model": DEFAULT_MODEL, "base_url": BASE_URL, "run_at": stamp,
        "mode": mode, "prompt_label": PROMPT_LABEL[mode], "instruction": INSTRUCTIONS[mode],
        "map_sha256": hashlib.sha256(to_json(field_map).encode("utf-8")).hexdigest(),
        "usage": resp.usage.model_dump() if resp.usage else None,
        "finish_reason": resp.choices[0].finish_reason,
        "raw_content": raw,
    }
    out = OUT / f"kimi_boundary_digong_{mode}_{stamp}.json"
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Raw output saved: {out}")

    try:
        answer = parse(raw)
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"FAIL  answer is not valid JSON: {e}")
        return 1
    rows = check(answer, items)
    width = max(len(r[0]) for r in rows)
    for name, subject, verdict, detail in rows:
        print(f"{verdict:4}  {name:<{width}}  {subject}" + (f"  — {detail}" if detail else ""))
    fails = sum(r[2] == "FAIL" for r in rows)
    warns = sum(r[2] == "WARN" for r in rows)
    print(f"\n{'PASS' if not fails else 'FAIL'}: {len(rows)} checks, {fails} failed, {warns} warnings")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
