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
Re-check a saved run without calling Kimi (no key needed):
    .\\.venv\\Scripts\\python.exe -X utf8 experiments\\kimi_boundary.py --recheck experiments\\out\\<file>.json
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
from resolver import resolve_chart, rulings, to_json

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
- Combining is not transforming. Speak of transformation only where the map records it.
- Prose discipline, in the specification's own words (V10 0.1d Patch 7; 0.1c §0):
  "Conditions, not outcomes. State the condition. Do not predict what will happen. The biological
  case in §0 is the strictest instance of this rule, not its whole extent."
  "No biological outcome predictions. Organ systems and structural loads may be named. Disease
  outcomes may not."
  "No behavioural prescriptions. Banned: "You must…", "Avoid…", "You should…", "Make sure you…",
  "Don't let…", "Take action…", "Capitalize on…", "Deploy…", "Protect your…", "Ruthlessly…". The
  permitted substitution is the Mechanical Necessity formula: "For [condition] to hold, [element]
  must [function].""
  "Vocabulary is structural. No luck, fate, destiny, fortune, auspicious, inauspicious."
  "Commercial reframing is blocked. A broken formation is broken. Do not soften a 破格 verdict, and
  do not present a structural constraint as an opportunity."

READING GROUND (operator draft, test only — not N6)
Terrain, not events. Describe conditions: pressure, support, contest, what is bound and what is free. Never predict events.
The one walking the terrain has the final say. Same chart, not the same life. The reading shows the ground; the person's choices, effort, faith and grace decide what happens on it.
Speak plainly where the map is settled. Where an item fires, locks or is eliminated, say what it means with conviction, not hedging. Where the map is escalated, present every candidate as equally open.
No medical, legal or mental-health statements. The chart describes terrain; it is not a diagnosis, a legal opinion or therapy. Where a question touches these, say so plainly and point to a professional.
Quiet is not empty. If nothing in the chart acts on an area, the chart is silent there, which never means little happens in the person's life.
Don't go beyond what was asked.
Public figures: civic layer only. Structure, never a portrait. Nothing about private life, health or fate.
The best output is the standard. Not a fortune cookie.
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
This chart belongs to a LIVING PUBLIC FIGURE. Your task is a LAYER-3 READING of it for the year
2026 (the annual layer in the map), scoped to the CIVIC, STRUCTURAL LAYER only.
- For each item that FIRES (value FULL_FORCE), each item that is LOCKED (LOCKED_FULL), and each
  item that is ELIMINATED, say what it means as terrain in 2026.
- For the E-21 escalation (五合 丙辛), and every other ESCALATED item, give the reading under EACH
  candidate in turn, and say how the readings differ. Treat the candidates as equally open. Do not
  choose between them, rank them, or say which is more likely.
- No portrait of the person, nothing about private life, nothing about health.
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

    def put(item_id, raw, note=None):
        value, cands = _value(raw)
        items[item_id] = {"value": value, "candidates": cands}
        if note:
            items[item_id]["note"] = note

    put("day_master", f"{field_map['day_master']} (natal.day)",
        "the Day Master; its own combining never removes it (本身之合, ch. 5)")
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
        if "gate" in c:
            put(f"branch_combinations.{cid}.gate", c["gate"])
    for pool in ("clashes", "harms", "destructions", "punishments"):
        for rid, rec in field_map[pool].items():
            put(f"{pool}.{rid}", rec["outcome"])
    natal_month = field_map["pillars"]["natal.month"]["branch"]
    for sid, s in field_map["stem_combinations"].items():
        put(f"stem_combinations.{sid}", s.get("state", s.get("status")))
        if "element" not in s:                         # partner absent from the surface: no combination
            continue
        state = s.get("state")
        if isinstance(state, str) and state.startswith(("TRANSFORMED", "NEUTRALIZED")):
            put(f"stem_combinations.{sid}.transformation", state)
        else:
            put(f"stem_combinations.{sid}.transformation", "NONE_RECORDED",
                "the map records no transformation for this combination")
        if "gate" in s:
            put(f"stem_combinations.{sid}.gate", s["gate"])
        else:
            computed = rulings.stem_gate(sid.split()[-1], natal_month)
            put(f"stem_combinations.{sid}.gate", computed if isinstance(computed, str) else computed.to_json(),
                f"computed by the resolver's gate function for the natal month {natal_month}; the map itself "
                f"records no gate for a combination that is not settled"
                + ("; blockers (柱有X字 / 有X字間之) not evaluated" if computed == "MET" else ""))
        if s.get("day_master"):
            put(f"stem_combinations.{sid}.day_master", "natal.day", s["day_master"])
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
    # Secondary warning: predictive language in the reading (0.1d Patch 7 item 2). For the operator's
    # read; never counted as a failure.
    # The language scans skip catalog item ids (e.g. "...transformation" in an id is a field name,
    # not a claim); ids are blanked out, keeping positions so the context snippets stay accurate.
    scan = reading
    for item_id in sorted(items, key=len, reverse=True):
        scan = scan.replace(item_id, " " * len(item_id))
    for pattern, label in ((PREDICTIVE, "predictive language (for operator read)"),
                           (HEALTH, "health / mortality language (for operator read)")):
        for m in pattern.finditer(scan):
            a, b = max(0, m.start() - 40), min(len(reading), m.end() + 40)
            rows.append((label, repr(m.group(0)), "WARN", "…" + reading[a:b].replace("\n", " ") + "…"))
    # Secondary warning: transformation language where the map records no transformation. Never a
    # failure. If the map does record one, the row names it so the operator can judge the sentence.
    transformed = sorted(k for k, v in items.items() if str(v["value"]).startswith("TRANSFORMED"))
    open_tf = sorted(k for k, v in items.items() if k.endswith(".transformation") and v["value"] == ESC)
    for m in TRANSFORM.finditer(scan):
        a, b = max(0, m.start() - 40), min(len(reading), m.end() + 40)
        where = ("the map records no transformation" if not transformed
                 else f"the map records TRANSFORMED only for {transformed}")
        if open_tf:
            where += f"; transformation is ESCALATED for {open_tf}"
        rows.append(("transformation language (for operator read)", repr(m.group(0)), "WARN",
                     f"{where}: …" + reading[a:b].replace("\n", " ") + "…"))
    return rows


# Secondary warning: transformation language (RULES: "Combining is not transforming").
TRANSFORM = re.compile(
    r"化|\btransform\w*|\bconver(?:t|s)\w*|\binto\s+(?:the\s+)?(?:water|fire|wood|metal|earth)\b", re.I)


# Secondary warning: health and mortality language (READING GROUND; 0.1c §0). Never a failure.
HEALTH = re.compile(
    r"\b(sick\w*|ill(?:ness|nesses)?|disease\w*|death\w*|die|dies|died|dying|lifespan\w*|"
    r"accident\w*|cancer\w*|hospital\w*)\b", re.I)


PREDICTIVE = re.compile(
    r"\b(will|won't|shall|is going to|are going to|going to|expect(?:s|ed|ing)?|likely to|unlikely to|"
    r"bound to|certain to|set to|poised to|destined|forecast\w*|predict\w*|in store|lies ahead|"
    r"is sure to|are sure to)\b", re.I)


def report(raw, items):
    """Parse Kimi's raw answer, run every check, print the table. Returns the exit code."""
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


def recheck(path):
    """Re-run the checker on a saved output file. No Kimi call; no key needed."""
    record = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    field_map = resolve_chart(**load_digong_input())
    now = hashlib.sha256(to_json(field_map).encode("utf-8")).hexdigest()
    print(f"Recheck: {path}")
    print(f"  model {record.get('model')} | mode {record.get('mode', 'boundary (pre-mode run)')} | run_at {record.get('run_at')}")
    same = record.get("map_sha256") == now
    print(f"  map hash {'matches' if same else 'DIFFERS from'} the current resolver output"
          + ("" if same else " — the checks compare against today's map, not the one Kimi saw"))
    return report(record["raw_content"], catalog(field_map))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=sorted(INSTRUCTIONS), default="boundary")
    ap.add_argument("--recheck", metavar="FILE", help="run the checker on a saved output file; no Kimi call")
    args = ap.parse_args()
    if args.recheck:
        return recheck(args.recheck)
    mode = args.mode
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
    return report(raw, items)


if __name__ == "__main__":
    sys.exit(main())
