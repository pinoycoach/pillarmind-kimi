"""Daily structural check against an operator-certified formation (private use).

Runs the resolver for a chart on a given date, then looks the five certified roles up in the
result: 用神, 相神, 忌神, 仇神, 救應. For each role it reports whether the role appears among the
stems or branches (natal or transit), whether that instance is FREE or LOCKED, and which clashes,
harms, destructions, punishments, combinations or stem combinations it stands in, with their
outcomes. A separate line says whether the 用神 has any support today that it lacks natally.

Pure resolver output plus a lookup. No network call, no language-model call. It reads the chart's
birth data and the certified roles from a private fixture at run time (default
golden_local/nap.json, git-ignored); nothing about any chart is written into this file, and
nothing is written to disk by it.

The fixture needs: input {birth, city, sex} and operator_certification.certified_roles, each role
{stem | stems, element, label}. The resolver never certifies; the roles are the operator's.

Usage (Windows PowerShell, from the repository root):
    .\\.venv\\Scripts\\python.exe -X utf8 experiments\\daily\\daily_check.py
    .\\.venv\\Scripts\\python.exe -X utf8 experiments\\daily\\daily_check.py --date 2026-09-27
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from resolver import resolve_chart  # noqa: E402
from resolver.tables import STEM_ELEMENT  # noqa: E402

LAYERS = ("decade", "annual", "monthly", "daily")
TRANSIT = set(LAYERS)
DAY_SPECIFIC = {"annual", "monthly", "daily"}
QI = ("本氣", "中氣", "餘氣")
ROLE_ORDER = ("用神", "相神", "忌神", "仇神", "救應")
ACTIVE = {"FULL_FORCE", "ATTENUATED"}


def outcome_str(o) -> str:
    if isinstance(o, dict):
        return f"ESCALATED({o.get('pending')})"
    return str(o)


def tag(pid: str) -> str:
    return pid.replace("natal.", "natal ")


def token_of(m: dict, pid: str, kind: str) -> str:
    tok = m["stem_tokens" if kind == "stem" else "branch_tokens"][pid]
    if isinstance(tok, dict):
        return outcome_str(tok)
    return f"LOCKED ({tok})" if tok.startswith("LOCKED") else tok


def interactions(m: dict, pid: str, kind: str) -> list[str]:
    """Every recorded interaction the pillar's stem (kind 'stem') or branch (kind 'branch') stands in."""
    rows = []
    if kind == "branch":
        for section in ("clashes", "harms", "destructions", "punishments"):
            for name, rec in m[section].items():
                if pid not in rec["instances"]:
                    continue
                out = outcome_str(rec["outcome"])
                note = ""
                if isinstance(rec["outcome"], dict):
                    out += " = unsettled"
                elif rec["outcome"] in ACTIVE:
                    acting = rec.get("acting")
                    note = " (acts)" if acting is None or pid in acting else " (not the acting pair)"
                    out += " = ACTIVE" + note
                else:
                    out += " = not active"
                rows.append(f"{name} {out}")
        for cid, rec in m["branch_combinations"].items():
            if pid in rec["legs"]:
                lock = outcome_str(rec.get("lock")) if rec.get("lock") is not None else "-"
                rows.append(f"{cid.split(' [')[0]} {outcome_str(rec['status'])}, {lock}")
    else:
        for name, rec in m["stem_combinations"].items():
            if pid in rec.get("instances", []):
                gate = rec.get("gate")
                g = f", gate {outcome_str(gate)}" if gate is not None else ""
                rows.append(f"{name} {outcome_str(rec['status'])}{g}")
    return rows


def matches(role: dict, stem: str) -> bool:
    if "stems" in role:
        return stem in role["stems"]
    if "stem" in role:
        return stem == role["stem"]
    return STEM_ELEMENT[stem] == role["element"]


def instances(m: dict, role: dict, only=None) -> list[dict]:
    """Every place the role's stem(s) or element appears: a surface stem, or a stem hidden in a branch."""
    found = []
    for pid, p in m["pillars"].items():
        if only is not None and not only(pid):
            continue
        if matches(role, p["stem"]):
            found.append({"pid": pid, "where": f"stem {p['stem']}", "kind": "stem", "stem": p["stem"], "qi": None})
        for i, h in enumerate(p["hidden_stems"]):
            if matches(role, h["stem"]):
                found.append({"pid": pid, "where": f"hidden {h['stem']} ({QI[min(i, 2)]}) in {p['branch']}",
                              "kind": "branch", "stem": h["stem"], "qi": i})
    return found


def describe(m: dict, inst: dict) -> str:
    pid, kind = inst["pid"], inst["kind"]
    ints = interactions(m, pid, kind)
    line = f"  [{tag(pid)} {m['pillars'][pid]['stem']}{m['pillars'][pid]['branch']}] {inst['where']}: {token_of(m, pid, kind)}"
    if ints:
        line += "\n" + "\n".join(f"        - {r}" for r in ints)
    return line


def support_line(m: dict, role: dict) -> list[str]:
    """Does the 用神 have any support today that it lacks natally? Exact-stem hidden roots are kept apart
    from same-element qi, and decade-layer support (not day-specific) apart from annual/monthly/daily."""
    stem, el = role["stem"], role["element"]
    natal = [i for i in instances(m, {"element": el}, only=lambda p: p.startswith("natal."))]
    natal_roots = [i for i in natal if i["kind"] == "branch" and i["stem"] == stem]
    natal_other = [i for i in natal if not (i["kind"] == "branch" and i["stem"] == stem)
                   and not (i["kind"] == "stem" and i["stem"] == stem)]
    trans = [i for i in instances(m, {"element": el}, only=lambda p: p in TRANSIT)]

    def st(i):
        return token_of(m, i["pid"], i["kind"])

    def fmt(i):
        return f"{tag(i['pid'])} {m['pillars'][i['pid']]['stem']}{m['pillars'][i['pid']]['branch']}: {i['where']}, {st(i)}"

    roots = [i for i in trans if i["kind"] == "branch" and i["stem"] == stem]
    day_roots = [i for i in roots if i["pid"] in DAY_SPECIFIC]
    dec_roots = [i for i in roots if i["pid"] == "decade"]
    day_other = [i for i in trans if i["pid"] in DAY_SPECIFIC and i not in roots]
    dec_other = [i for i in trans if i["pid"] == "decade" and i not in roots]
    lines = []
    free_day = [i for i in day_roots if st(i) == "FREE"]
    if free_day:
        head = "YES, an unlocked root from today's layers: " + "; ".join(fmt(i) for i in free_day)
    elif day_roots:
        head = "SEALED ONLY from today's layers (E-4 open): " + "; ".join(fmt(i) for i in day_roots)
    else:
        head = "NO exact-" + stem + " root from annual, monthly or daily"
    lines.append(f">>> 用神 {stem} SUPPORT TODAY beyond natal: {head}")
    lines.append("    natal baseline: " + (
        "rootless, no branch holds " + stem + " (matches the certification)" if not natal_roots
        else "NOT rootless, the resolver finds " + "; ".join(fmt(i) for i in natal_roots)))
    if natal_other:
        lines.append("    natal same-element qi (not the stem itself): " + "; ".join(fmt(i) for i in natal_other))
    if day_other:
        lines.append("    also today, same-element but not a root: " + "; ".join(fmt(i) for i in day_other))
    if dec_roots or dec_other:
        lines.append("    decade layer (in force since the decade began, not day-specific): " +
                     "; ".join(fmt(i) for i in dec_roots + dec_other))
    ints = {i["pid"] for i in day_roots + dec_roots}
    for pid in sorted(ints):
        for r in interactions(m, pid, "branch"):
            lines.append(f"    {tag(pid)} branch interactions: {r}")
    return lines


def load(path: pathlib.Path):
    c = json.loads(path.read_text(encoding="utf-8"))
    roles = c.get("operator_certification", {}).get("certified_roles")
    if not roles:
        sys.exit(f"{path}: no operator_certification.certified_roles; nothing to look up.")
    inp = c["input"]
    return inp, roles


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--chart", default=str(ROOT / "golden_local" / "nap.json"))
    ap.add_argument("--date", help="YYYY-MM-DD (default: today at the birthplace)")
    ap.add_argument("--time", default=None, help="HH:MM (default: now if --date is absent, else 12:00)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    inp, roles = load(pathlib.Path(args.chart))
    birth = dt.datetime.fromisoformat(inp["birth"])
    if args.date:
        as_of = dt.datetime.fromisoformat(f"{args.date} {args.time or '12:00'}")
    else:
        # A resolver call reads as_of as a local time at the birthplace; take "now" from Manila's clock
        # for a Manila chart, from the fixture's own zone otherwise.
        zone = ZoneInfo("Asia/Manila") if inp["city"].lower() == "manila" else None
        now = dt.datetime.now(zone) if zone else dt.datetime.now()
        as_of = now.replace(tzinfo=None, microsecond=0, second=0)
    m = resolve_chart(birth, inp["city"], inp["sex"], as_of=as_of, layers=LAYERS,
                      hour_known=inp.get("hour_known", True))

    p = m["pillars"]
    print(f"as_of {as_of:%Y-%m-%d %H:%M} ({m['input']['as_of_zone']}); resolver {m['resolver']}; "
          f"{len(m['worlds']['assumptions'])} world(s)")
    print("pillars: " + "  ".join(f"{tag(k)} {v['stem']}{v['branch']}" for k, v in p.items()))
    d = m["decade"]["in_force"]
    print(f"decade in force: {d['pillar']}, {d['starts'][:10]} to {d['ends'][:10]}; day master {m['day_master']}")

    print("\n== THE FIVE ROLES ==")
    for name in ROLE_ORDER:
        role = roles[name]
        print(f"\n{role['label']}")
        found = instances(m, role)
        if not found:
            print("  absent: no matching stem or hidden stem anywhere in the field today")
        for inst in found:
            print(describe(m, inst))
        if name == "用神":
            print()
            for line in support_line(m, role):
                print(line)

    print("\n== STRUCTURE TODAY (as the resolver states it) ==")
    locked = [k for k, v in m["branch_tokens"].items() if isinstance(v, str) and v.startswith("LOCKED")]
    free = [k for k, v in m["branch_tokens"].items() if v == "FREE"]
    other = {k: outcome_str(v) for k, v in m["branch_tokens"].items() if isinstance(v, dict)}
    print("branches LOCKED: " + (", ".join(f"{tag(k)} {p[k]['branch']}" for k in locked) or "none"))
    print("branches FREE:   " + (", ".join(f"{tag(k)} {p[k]['branch']}" for k in free) or "none"))
    if other:
        print("branches unsettled: " + ", ".join(f"{tag(k)} {v}" for k, v in other.items()))
    for cid, rec in m["branch_combinations"].items():
        print(f"combination {cid}: {outcome_str(rec['status'])}, {outcome_str(rec.get('lock'))}")
    for cid, rec in m["branch_combination_failures"].items():
        print(f"combination {cid}: {rec['status']}, leg taken by {rec['leg_taken_by']}")
    for k, v in m["half_frames"].items():
        print(f"half frame {k}: {v['present']}")
    for section in ("clashes", "harms", "destructions", "punishments"):
        for name, rec in m[section].items():
            acting = f", acting {[tag(a) for a in rec['acting']]}" if rec.get("acting") else ""
            print(f"{name} [{', '.join(tag(i) for i in rec['instances'])}]: {outcome_str(rec['outcome'])}{acting}")
    for name, rec in m["stem_combinations"].items():
        print(f"{name} [{', '.join(tag(i) for i in rec.get('instances', []))}]: {outcome_str(rec['status'])}")
    for k, v in m["eliminations"].items():
        print(f"elimination {k}: {v}")
    if m["escalations"]:
        print("escalations: " + "; ".join(f"{k} ({v.get('pending')})" for k, v in m["escalations"].items()))
    print("\nFormation (resolver's proposal, never certified): " +
          f"{m['formation']['status']} {m['formation'].get('proposed')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
