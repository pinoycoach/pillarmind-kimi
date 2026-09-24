"""Kimi boundary experiment (DECISIONS N34). Not part of the resolver; the resolver never imports it.

Runs the resolver on golden/digong.json's input, sends the full Resolved Field Map to Kimi with an
interpret-only instruction, and checks the answer against the map:
  1. every cited item id exists in the map;
  2. every restated value equals the map's value;
  3. no ESCALATED item is described as settled.
Kimi's raw output is saved under experiments/out/ (git-ignored). N5 and N6 stay open; this decides
neither.

Usage (Windows PowerShell, in your own terminal; never paste the key into a chat or a file):
    $env:MOONSHOT_API_KEY = "<your key>"
    .\\.venv\\Scripts\\python.exe -X utf8 experiments\\kimi_boundary.py
"""
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

INSTRUCTION = """You are given a Resolved Field Map for one BaZi chart, produced by a deterministic resolver, and an
ITEM CATALOG listing every item in that map by id, with its value.

Your task is to INTERPRET ONLY.
- Every pillar, token, lock, clash, harm, destruction, punishment and escalation in the map is FIXED.
  Do not recompute, re-derive, or correct anything, even if you believe the map is wrong.
- Where an item's value is ESCALATED, lay out its candidates without choosing one. Do not describe
  an escalated item as settled, resolved, likely, or leaning either way.
- Refer to items only by the ids in the ITEM CATALOG.

Return ONLY a JSON object with exactly these keys:
{
  "reading": "<your interpretation, plain prose>",
  "cited_items": ["<item id from the catalog>", ...],
  "restated_values": [{"id": "<item id>", "value": "<the item's value exactly as the catalog gives it>"}, ...]
}
"restated_values" must list every pillar or outcome your reading mentions, with its value."""


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


def ask_kimi(field_map, items):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["MOONSHOT_API_KEY"], base_url=BASE_URL)
    user = ("RESOLVED FIELD MAP:\n" + to_json(field_map)
            + "\n\nITEM CATALOG (id -> value, and candidates where ESCALATED):\n"
            + json.dumps(items, ensure_ascii=False, indent=1))
    resp = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "system", "content": INSTRUCTION}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        # no temperature: Kimi models enforce their own fixed value (kimi_audit.py)
    )
    return resp


def parse(text):
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)                # tolerate stray fences or preamble
    return json.loads(m.group(0) if m else text)


def check(answer, items):
    rows = []                                          # (check, subject, PASS/FAIL/WARN, detail)
    for key in ("reading", "cited_items", "restated_values"):
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
    # Heuristic on the prose: an escalated item whose candidates are named, but only one of them.
    reading = answer.get("reading", "")
    for rid in sorted(escalated):
        keys = [re.findall(r"[一-鿿]{2,}", str(c))[:1] for c in items[rid]["candidates"] or []]
        keys = [k[0] for k in keys if k]
        named = [k for k in keys if k in reading]
        if len(keys) >= 2 and len(named) == 1:
            rows.append(("escalation not settled (prose heuristic)", rid, "WARN",
                         f"reading names only candidate {named[0]!r} of {keys}"))
    return rows


def main():
    if not os.environ.get("MOONSHOT_API_KEY"):
        sys.exit("MOONSHOT_API_KEY is not set in this shell. Set it in your own terminal session "
                 "(PowerShell: $env:MOONSHOT_API_KEY = \"<your key>\") and run again. "
                 "Never paste the key into a chat or a file.")
    field_map = resolve_chart(**load_digong_input())
    items = catalog(field_map)
    resp = ask_kimi(field_map, items)
    raw = resp.choices[0].message.content or ""

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    record = {
        "model": DEFAULT_MODEL, "base_url": BASE_URL, "run_at": stamp,
        "map_sha256": hashlib.sha256(to_json(field_map).encode("utf-8")).hexdigest(),
        "usage": resp.usage.model_dump() if resp.usage else None,
        "finish_reason": resp.choices[0].finish_reason,
        "raw_content": raw,
    }
    out = OUT / f"kimi_boundary_digong_{stamp}.json"
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
