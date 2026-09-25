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
  interpret  TEST PROMPT, NOT N6: asks for a real layer-3 reading of the chart for its annual layer, under the
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
from resolver import resolve_chart, to_json

OUT = ROOT / "experiments" / "out"
ESC = "ESCALATED"

PREAMBLE = """You are given a Resolved Field Map for one BaZi chart, produced by a deterministic resolver, and an
ITEM CATALOG listing every item in that map by id, with its value.
"""

RULES_CORE = """- Every pillar, token, lock, clash, harm, destruction, punishment and escalation in the map is FIXED.
  Do not recompute, re-derive, or correct anything, even if you believe the map is wrong.
- Where an item's value is ESCALATED, lay out its candidates without choosing one. Do not describe
  an escalated item as settled, resolved, likely, or leaning either way.
- Write "reading" in plain language. It must contain NO catalog ids: say "the decade stem 辛",
  not "pillars.decade". Ids belong only in cited_items, restated_values and escalations; use
  them there exactly as the ITEM CATALOG gives them.
- Combining is not transforming. Speak of transformation only where the map records it.
- Do not assign life-area meanings to pillars (such as career, public life, legacy, early or late life) unless the map records them. Palaces, where the map gives them, are only those of the ch. 23 ruling.
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
"""

GROUND_HEAD = """READING GROUND (operator draft, test only — not N6)
Terrain, not events. Describe conditions: pressure, support, contest, what is bound and what is free. Never predict events.
The one walking the terrain has the final say. Same chart, not the same life. The reading shows the ground; the person's choices, effort, faith and grace decide what happens on it.
Speak plainly where the map is settled. Where an item fires, locks or is eliminated, say what it means with conviction, not hedging. Where the map is escalated, present every candidate as equally open.
No medical, legal or mental-health statements. The chart describes terrain; it is not a diagnosis, a legal opinion or therapy. Where a question touches these, say so plainly and point to a professional.
Quiet is not empty. If nothing in the chart acts on an area, the chart is silent there, which never means little happens in the person's life.
Don't go beyond what was asked.
"""
# Ground rule 7, by mode (N43). Civic modes keep the public-figure limit; lab mode replaces it.
RULE7_CIVIC = "Public figures: civic layer only. Structure, never a portrait. Nothing about private life, health or fate.\n"
RULE7_LAB = ("Palaces are read as the figure's own terrain, never as statements about the relatives. No reading of "
             "any relative's own chart (Patch 13). The no-harm rule applies in full, to the figure and to the operator.\n")
GROUND_TAIL = "The best output is the standard. Not a fortune cookie.\n"

CIVIC_MODES = ("boundary", "interpret")


def rules(mode):
    """Shared rules plus the READING GROUND, with ground rule 7 chosen by mode."""
    return RULES_CORE + "\n" + GROUND_HEAD + (RULE7_LAB if mode == "lab" else RULE7_CIVIC) + GROUND_TAIL

SCHEMA = """Return ONLY a JSON object with exactly these keys:
{
  "reading": "<your reading, plain language, containing no catalog ids>",
  "cited_items": ["<item id from the catalog>", ...],
  "restated_values": [{"id": "<item id>", "value": "<the item's value exactly as the catalog gives it>"}, ...],
  "escalations": [{"id": "<item id>", "candidates": ["<candidate, copied word for word from the catalog>", ...]}, ...]
}
"restated_values" must list every pillar or outcome your reading mentions, with its value.
"escalations" must list EVERY item whose catalog value is ESCALATED, each with ALL of its candidates
copied character for character from the catalog, in any order, and no other items."""

INSTRUCTIONS = {
    # The mode of run 20260924-222336 (N35).
    "boundary": PREAMBLE + "\nYour task is to INTERPRET ONLY.\n" + rules("boundary") + "\n" + SCHEMA,
    # TEST PROMPT, NOT N6. It exists to test the boundary under real interpretation; it is not the
    # interpretation prompt, which N6 has not decided.
    "interpret": PREAMBLE + """
This chart belongs to a LIVING PUBLIC FIGURE. Your task is a LAYER-3 READING of it for the period
of the annual layer in the map, scoped to the CIVIC, STRUCTURAL LAYER only.
- For each item that FIRES (value FULL_FORCE), each item that is LOCKED (LOCKED_FULL), and each
  item that is ELIMINATED, say what it means as terrain in that period.
- For the E-21 escalation (五合 丙辛), and every other ESCALATED item, give the reading under EACH
  candidate in turn, and say how the readings differ. Treat the candidates as equally open. Do not
  choose between them, rank them, or say which is more likely.
- No portrait of the person, nothing about private life, nothing about health.
- Read what items mean through the TEN GODS relative to the Day Master (the catalog gives each
  stem's and hidden stem's ten god): for example, what it means that the contested stem is the
  Day Master's 正財. All the rules below still apply.
""" + rules("interpret") + "\n" + SCHEMA,
    # LAB MODE (N43). TEST PROMPT, NOT N6. Deceased historical figures only; living subjects refused.
    "lab": PREAMBLE + """
LAB MODE. This chart belongs to a DECEASED HISTORICAL FIGURE. Your task is a LAYER-3 READING of it
for the period of the transit layers in the map.
- For each item that FIRES (value FULL_FORCE), each item that is LOCKED (LOCKED_FULL), and each
  item that is ELIMINATED, say what it means as terrain in that period.
- For every ESCALATED item, give the reading under EACH candidate in turn, and say how the readings
  differ. Treat the candidates as equally open. Do not choose between them, rank them, or say which
  is more likely.
- The map gives each natal pillar's palace (ch. 23 ruling: year 祖, month 父母, day 妻, hour 子).
  Read palaces as the figure's own terrain only.
- Read what items mean through the TEN GODS relative to the Day Master (the catalog gives each
  stem's and hidden stem's ten god). All the rules below still apply.
""" + rules("lab") + "\n" + SCHEMA,
}
PROMPT_LABEL = {"boundary": "boundary (interpret-only; civic)", "interpret": "interpret — civic, TEST PROMPT, NOT N6",
                "lab": "LAB — deceased historical figures only; TEST PROMPT, NOT N6; never published directly"}


DEFAULT_CHART = ROOT / "golden" / "digong.json"


def load_chart(path=DEFAULT_CHART):
    """Resolver inputs from a chart file (a golden-format JSON), plus the file's contents."""
    case = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    i = case["input"]
    kwargs = dict(birth=dt.datetime.fromisoformat(i["birth"]), city=i["city"], sex=i["sex"],
                  as_of=dt.datetime.fromisoformat(i["as_of"]), layers=tuple(i["layers"]),
                  hour_known=i.get("hour_known", True))
    return kwargs, case


def load_digong_input():
    return load_chart()[0]


def lab_refusal(case):
    """Lab mode is for deceased historical figures only (N43). A chart must declare it; anything else,
    including a missing declaration, is refused until a later decision says otherwise."""
    subject = case.get("subject") or {}
    if subject.get("status") != "deceased":
        return ("LAB MODE REFUSED: lab mode is for deceased historical figures only (DECISIONS N43). "
                "This chart does not declare subject.status = \"deceased\"; living subjects are refused in "
                "lab mode until a later decision says otherwise.")
    return None


def civic_view(field_map):
    """The map as sent in civic modes: palaces removed (ground rule 7, public figures), everywhere."""
    view = json.loads(json.dumps(field_map, ensure_ascii=False))
    view.pop("palaces", None)
    for p in view["pillars"].values():
        p.pop("palace", None)
    return view


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
        # Ten gods relative to the Day Master, citable (N40): the pillar's stem, then each hidden stem.
        put(f"pillars.{pid}.stem_ten_god", p["stem_ten_god"], f"ten god of {p['stem']} relative to the Day Master")
        for h in p["hidden_stems"]:
            put(f"pillars.{pid}.hidden.{h['stem']}.ten_god", h["ten_god"],
                f"ten god of hidden {h['stem']} in {p['branch']}, relative to the Day Master")
    # Palaces (ch. 23 ruling, N42), only when the map carries them: lab mode. Civic views strip them.
    for pid, pal in (field_map.get("palaces") or {}).items():
        if pid == "rule":
            continue
        if isinstance(pal, dict) and pal.get("token") == "GAP":
            put(f"palaces.{pid}", "GAP", pal.get("note"))
        else:
            put(f"palaces.{pid}", pal, "ch. 23 palace, read as the figure's own terrain")
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
    for sid, s in field_map["stem_combinations"].items():
        put(f"stem_combinations.{sid}", s.get("state", s.get("status")))
        if "transforms_to_if_gated" not in s:          # partner absent from the surface: no combination
            continue
        state = s.get("state")
        if isinstance(state, str) and state.startswith(("TRANSFORMED", "NEUTRALIZED")):
            put(f"stem_combinations.{sid}.transformation", state)
        else:
            put(f"stem_combinations.{sid}.transformation", "NONE_RECORDED",
                "the map records no transformation for this combination")
        if "gate" in s:                                # read from the map only (N37)
            put(f"stem_combinations.{sid}.gate", s["gate"])
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


def check(answer, items, mode="boundary"):
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
    ids_in_prose = []
    for item_id in sorted(items, key=len, reverse=True):
        if item_id in scan:
            ids_in_prose.append(item_id)
        scan = scan.replace(item_id, " " * len(item_id))
    # Secondary warning: the reading must be plain language, with no catalog ids (N40).
    for item_id in sorted(ids_in_prose):
        rows.append(("catalog id in reading (plain-language rule)", item_id, "WARN",
                     "ids belong only in cited_items, restated_values and escalations"))
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
    rows += _element_union_rows(scan, reading, items)
    # Civic modes exclude palaces (ground rule 7): palace or life-area words are for the operator's
    # read (N43). Never a failure. Lab mode reads palaces, so the row does not run there.
    if mode in CIVIC_MODES:
        for m in LIFE_AREA.finditer(scan):
            a, b = max(0, m.start() - 40), min(len(reading), m.end() + 40)
            rows.append(("palace / life-area word, civic mode (for operator read)", repr(m.group(0)), "WARN",
                         "…" + reading[a:b].replace("\n", " ") + "…"))
    return rows


def _element_union_rows(scan, reading, items):
    """WARN rows for an element named as the substance of a union ('earth block', 'fire mass',
    'water-type pressure', 土塊) where the map records no TRANSFORMED item. Never a failure."""
    transformed = sorted(k for k, v in items.items() if str(v["value"]).startswith("TRANSFORMED"))
    frames = sorted(k for k in items if k.startswith("branch_combinations.三合") or k.startswith("branch_combinations.三會"))
    rows = []
    for m in ELEMENT_UNION.finditer(scan):
        a, b = max(0, m.start() - 40), min(len(reading), m.end() + 40)
        where = ("the map records no TRANSFORMED item" if not transformed
                 else f"the map records TRANSFORMED only for {transformed}")
        if frames:
            where += f"; frame locks present (a 三合/三會 frame carries its element): {frames}"
        rows.append(("element named for a union (for operator read)", repr(m.group(0)), "WARN",
                     f"{where}: …" + reading[a:b].replace("\n", " ") + "…"))
    return rows


# Secondary warning, civic modes: palace or life-area words (N43).
LIFE_AREA = re.compile(
    r"\b(career\w*|public\w*|legac(?:y|ies)|ancestor\w*|ancestral|parent\w*|spous\w*|marri\w*|"
    r"child\w*|famil(?:y|ies|ial))\b", re.I)


# Secondary warning: an element named as what a union is made of (N39).
ELEMENT_UNION = re.compile(
    r"\b(?:earth|fire|water|wood|metal)(?:[\s-]+|-type\s+)(?:block|mass|bloc|union|body|alliance|bond|"
    r"structure|pressure|force|energy|type|element|unit|whole|clump)s?\b|[土火水木金](?:塊|團)", re.I)


# Secondary warning: transformation language (RULES: "Combining is not transforming").
TRANSFORM = re.compile(
    r"化|\btransform\w*|\bconver(?:t|s)\w*|\binto\s+(?:the\s+)?(?:water|fire|wood|metal|earth)\b", re.I)


# Secondary warning: health and mortality language (READING GROUND; 0.1c §0). Never a failure.
HEALTH = re.compile(
    r"\b(sick\w*|ill(?:ness|nesses)?|disease\w*|death\w*|die|dies|died|dying|lifespan\w*|"
    r"accident\w*|cancer\w*|hospital\w*)\b", re.I)


PREDICTIVE = re.compile(
    r"\b(will|won't|shall|is going to|are going to|going to|expect(?:s|ed|ing)?|likely to|unlikely to|"
    r"certain to|set to|poised to|destined|forecast\w*|predict\w*|in store|lies ahead|"
    r"is sure to|are sure to)\b", re.I)


def report(raw, items, mode="boundary"):
    """Parse Kimi's raw answer, run every check, print the table. Returns the exit code."""
    if mode == "lab":
        print("LAB — deceased historical figures only; never published directly (N43)")
    try:
        answer = parse(raw)
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"FAIL  answer is not valid JSON: {e}")
        return 1
    rows = check(answer, items, mode)
    width = max(len(r[0]) for r in rows)
    for name, subject, verdict, detail in rows:
        print(f"{verdict:4}  {name:<{width}}  {subject}" + (f"  — {detail}" if detail else ""))
    fails = sum(r[2] == "FAIL" for r in rows)
    warns = sum(r[2] == "WARN" for r in rows)
    print(f"\n{'PASS' if not fails else 'FAIL'}: {len(rows)} checks, {fails} failed, {warns} warnings")
    return 1 if fails else 0


def blind_view(field_map):
    """N48: interpretations are blind to identity, to prevent model-side backfitting. Strip the input
    record (birth date, time, place, sex, any name) and the as_of date, and every derived field that
    carries them (decade dates and start age, which pin the birth year; the input-integrity notes,
    which name the zone). Only pillars and derived structures remain."""
    view = json.loads(json.dumps(field_map, ensure_ascii=False))
    view.pop("input", None)
    integrity = view.get("input_integrity") or {}
    view["input_integrity"] = {"corroboration": integrity.get("corroboration")}
    decade = view.get("decade")
    if isinstance(decade, dict):
        in_force = decade.get("in_force")
        if isinstance(in_force, dict):
            keep = ("pillar", "index") if "pillar" in in_force else ("token", "candidates")
            view["decade"] = {"in_force": {k: in_force[k] for k in keep if k in in_force}}
        else:
            view["decade"] = {"in_force": None}
    return view


def mode_view(field_map, mode):
    """What Kimi is shown: always blind (N48); palaces only in lab mode, the civic view otherwise."""
    return blind_view(field_map if mode == "lab" else civic_view(field_map))


def recheck(path):
    """Re-run the checker on a saved output file. No Kimi call; no key needed."""
    record = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    mode = record.get("mode", "boundary")
    kwargs, _ = load_chart(ROOT / record["chart"] if record.get("chart") else DEFAULT_CHART)
    field_map = resolve_chart(**kwargs)
    now = hashlib.sha256(to_json(field_map).encode("utf-8")).hexdigest()
    print(f"Recheck: {path}")
    print(f"  model {record.get('model')} | mode {record.get('mode', 'boundary (pre-mode run)')} | run_at {record.get('run_at')}"
          f" | chart {record.get('chart', 'golden/digong.json (pre-chart run)')}")
    same = record.get("map_sha256") == now
    print(f"  map hash {'matches' if same else 'DIFFERS from'} the current resolver output"
          + ("" if same else " — the checks compare against today's map, not the one Kimi saw"))
    return report(record["raw_content"], catalog(mode_view(field_map, mode)), mode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=sorted(INSTRUCTIONS), default="boundary")
    ap.add_argument("--chart", type=pathlib.Path, default=DEFAULT_CHART,
                    help="chart file in golden format (default golden/digong.json); lab mode requires "
                         "subject.status = \"deceased\"")
    ap.add_argument("--recheck", metavar="FILE", help="run the checker on a saved output file; no Kimi call")
    args = ap.parse_args()
    if args.recheck:
        return recheck(args.recheck)
    mode = args.mode
    kwargs, case = load_chart(args.chart)
    if mode == "lab" and (refusal := lab_refusal(case)):
        sys.exit(refusal)
    if not os.environ.get("MOONSHOT_API_KEY"):
        sys.exit("MOONSHOT_API_KEY is not set in this shell. Set it in your own terminal session "
                 "(PowerShell: $env:MOONSHOT_API_KEY = \"<your key>\") and run again. "
                 "Never paste the key into a chat or a file.")
    print(f"Mode: {PROMPT_LABEL[mode]}")
    field_map = resolve_chart(**kwargs)
    view = mode_view(field_map, mode)
    items = catalog(view)
    resp = ask_kimi(view, items, mode)
    raw = resp.choices[0].message.content or ""

    out_dir = OUT / "lab" if mode == "lab" else OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    chart_rel = args.chart.resolve().relative_to(ROOT).as_posix()
    record = {
        "model": DEFAULT_MODEL, "base_url": BASE_URL, "run_at": stamp,
        "mode": mode, "prompt_label": PROMPT_LABEL[mode], "instruction": INSTRUCTIONS[mode],
        "chart": chart_rel, "palaces_sent": mode == "lab",
        # N48: Kimi saw the blind view; the operator's record keeps what was stripped.
        "sent_view": "blind (N48): input record, as_of, decade dates and start age, input-integrity notes removed",
        "subject_record": {"input": field_map["input"], "decade": field_map["decade"],
                           "input_integrity_notes": field_map["input_integrity"]["notes"]},
        "map_sha256": hashlib.sha256(to_json(field_map).encode("utf-8")).hexdigest(),
        "usage": resp.usage.model_dump() if resp.usage else None,
        "finish_reason": resp.choices[0].finish_reason,
        "raw_content": raw,
    }
    if mode == "lab":
        record["LAB"] = ("LAB output: deceased historical figures only. Never published directly; anything "
                         "leaving the lab passes the civic filter and the operator's editorial review (N43).")
    out = out_dir / f"kimi_boundary_{pathlib.Path(chart_rel).stem}_{mode}_{stamp}.json"
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Raw output saved: {out}")
    return report(raw, items, mode)


if __name__ == "__main__":
    sys.exit(main())
