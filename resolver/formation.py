"""Formation (格局) derivation, settled core only (DECISIONS N27, N50). Natal pillars only.

Rules applied, and nothing else:
  P-12 (N25): the month command's 本氣 governs if it is on a heavenly stem; otherwise a single visible
      中氣/餘氣 governs; 子午卯酉 do not vary (子平真詮 ch. 10).
  E-41 (N26): for taking the formation, 午 is single-stemmed (丁).
  N50 (1): 透出 is judged on the three natal stems other than the Day Master's own; transit stems
      never count.
  N50 (2): hour unknown: every hour stem the day stem allows (五鼠遁) is tested; if any changes the
      result, the formation is UNDETERMINED with its candidates listed.
Every case outside that core escalates by name. The output is a PROPOSAL: the resolver never
certifies a formation; `certified_by_operator` stays null until the operator sets it.
"""
from __future__ import annotations

from .derive import ten_god
from .tables import BRANCHES, DIRECTIONAL, STEMS, THREE_HARMONY

FIXED = {"子": "癸", "午": "丁", "卯": "乙", "酉": "辛"}      # 子午卯酉 do not vary; 午 = 丁 (E-41)
ZAQI = "辰戌丑未"                                              # 雜氣 months: ch. 16 (unread) decides

ESC_ZAQI = "ESCALATED: 雜氣 month; ch. 16 would decide (unread)"
ESC_HUI = "ESCALATED: a combination (會) with the month branch may change the formation (ch. 10; N25 open case)"
ESC_TWO = "ESCALATED: two secondary stems visible (N25 open case)"
ESC_NONE = "ESCALATED: nothing visible (N25 open case)"
ESC_LU = "ESCALATED: 建祿/月劫 (the governing stem is the Day Master's 比肩 or 劫財; ch. 45–46 unread)"

SPECIAL_GATE = {
    "token": "ESCALATED",
    "pending": "Patch 3 special-formation criteria (not ruled)",
    "note": ("0.1d Patch 3 requires 化格/從格/專旺格 to be checked first, with confirmed absence as an output. "
             "No criteria are ruled (從格 and 專旺 also need the E-19 strength procedure, N8), so the resolver "
             "cannot show absence on any chart; the standard formation is proposed beside this escalation."),
}


def _combination_with_month(branches: dict) -> list:
    """Completed natal 三合/三會 with the month branch as a leg."""
    present = set(branches.values())
    month = branches["month"]
    return [f"{kind} {p}" for kind, pool in (("三合", THREE_HARMONY), ("三會", DIRECTIONAL))
            for p in pool if month in p and set(p) <= present]


def _one(stems: dict, branches: dict, hidden_month: list, dm: str) -> dict:
    """The formation for one complete set of natal stems (year, month, day, hour)."""
    month = branches["month"]
    visible = {pos: s for pos, s in stems.items() if pos != "day"}           # N50 (1)
    out = {"month_command": month, "visible_stems": visible}
    if month in ZAQI:
        return {**out, "proposed": ESC_ZAQI}
    hui = _combination_with_month(branches)
    if hui:
        return {**out, "proposed": ESC_HUI, "combinations": hui}
    if month in FIXED:
        governing, source = FIXED[month], "fixed: 子午卯酉 do not vary" + (" (午 = 丁, E-41)" if month == "午" else "")
    elif hidden_month[0] in visible.values():
        governing, source = hidden_month[0], "本氣 visible"
    else:
        seen = [h for h in hidden_month[1:] if h in visible.values()]
        if len(seen) >= 2:
            return {**out, "proposed": ESC_TWO, "secondary_visible": seen}
        if not seen:
            return {**out, "proposed": ESC_NONE}
        governing, source = seen[0], "one secondary stem visible (本氣 not)"
    god = ten_god(dm, governing)
    out.update(governing_stem=governing, source=source, ten_god=god)
    if god in ("比肩", "劫財"):
        return {**out, "proposed": ESC_LU}
    return {**out, "proposed": f"{god}格"}


def _as_proposal(value):
    """A settled name stays a string; an escalation label becomes an ESCALATED object."""
    return {"token": "ESCALATED", "pending": value} if value.startswith("ESCALATED") else value


def derive_formation(pillars) -> dict:
    natal = {p.position: p for p in pillars if p.layer == "natal"}
    dm = natal["day"].stem
    stems = {pos: p.stem for pos, p in natal.items()}
    branches = {pos: p.branch for pos, p in natal.items()}
    hidden_month = list(natal["month"].hidden)
    base = {
        "rule": ("P-12 (N25), E-41 (N26), 透出 on the three natal stems other than the Day Master's "
                 "(N50); transit stems never count"),
        "special_formation_gate": SPECIAL_GATE,
        "certified_by_operator": None,
        "certification_note": "The resolver never certifies; only the operator sets certified_by_operator.",
    }
    if "hour" in natal:
        one = _one(stems, branches, hidden_month, dm)
        one["proposed"] = _as_proposal(one["proposed"])
        return {**base, "status": "PROPOSED" if isinstance(one["proposed"], str) else "ESCALATED", **one}
    # N50 (2): hour unknown. Every hour pillar the day stem allows (五鼠遁), all twelve.
    ds = STEMS.index(dm)
    by_hour = []
    for b, br in enumerate(BRANCHES):
        stem = STEMS[((ds % 5) * 2 + b) % 10]
        r = _one({**stems, "hour": stem}, {**branches, "hour": br}, hidden_month, dm)
        by_hour.append({"hour_pillar": stem + br, "formation": r["proposed"]})
    candidates = []
    for h in by_hour:
        if h["formation"] not in candidates:
            candidates.append(h["formation"])
    if len(candidates) == 1:
        return {**base, "status": "PROPOSED" if not candidates[0].startswith("ESCALATED") else "ESCALATED",
                "proposed": _as_proposal(candidates[0]), "hour_unknown": "all twelve hour pillars give the same result",
                "by_hour": by_hour}
    return {**base, "status": "UNDETERMINED",
            "proposed": {"token": "UNDETERMINED", "candidates": candidates,
                         "note": "hour unknown: the hour stem decides (N50)"},
            "by_hour": by_hour}
