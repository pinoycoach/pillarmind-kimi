"""Unruled decisions. Every function here returns either a settled token or an Escalation.

The resolver never picks a candidate itself. When a function returns an Escalation whose outcome
changes downstream resolution, the engine (resolve.py) runs one world per candidate and reports
every field that differs between worlds as ESCALATED (0.1c §2.5: "give both maps").

THE SEAM FOR N1 / N2 (DECISIONS.md). `resolve_six_harmony_lock` and `check_layer_seniority` each
open with a single `if ... is None:` branch returning the escalation. When the operator rules, set
R_DEF_1_RULING / R_DEF_2_RULING below (or delete that branch and return the ruled value). Nothing
downstream changes: the engine already handles both a plain token and an Escalation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .tables import SANHE_WANG, SEASONAL_WANG, STEM_GATE_KNOWN

CAPTURE_ALLOWED = "capture_allowed"
CAPTURE_BLOCKED = "capture_blocked"

# N1 / R-DEF-1. "LOCKED_FULL" or "LOCKED_PARTIAL"; None = unruled.
# RULED 23 Sep 2026 (operator): LOCKED_FULL. Basis, located: 子平真詮 ch. 7 論刑沖會合解法 原文
# 「有戌，則卯與戌合而不沖」, with no 化 condition anywhere in the chapter (東里書齋 3720).
R_DEF_1_RULING: str | None = "LOCKED_FULL"


def _r_def_2_capture_allowed(clash_layers: tuple, combination_layers: tuple) -> str:
    return CAPTURE_ALLOWED


# N2 / R-DEF-2. A function (clash_layers, combination_layers) -> CAPTURE_ALLOWED | CAPTURE_BLOCKED;
# None = unruled.
# RULED 23 Sep 2026 (operator): capture allowed across layers. Declared engine decision: ch. 25
# 「逢沖而不沖」 (東里書齋 3738) is 原文 for an arriving branch whose own 會 beats its own clash,
# applied here by analogy to a standing clash and a later capture (inference tier; 0.1f
# Addendum A §A5). Same-layer cases still escalate on E-8b (check_same_layer_u8).
R_DEF_2_RULING = _r_def_2_capture_allowed


@dataclass
class Escalation:
    pending: str                       # register / ruling ID the resolution waits on
    candidates: list                   # every candidate value, in a fixed order
    rule: str                          # the rule that flagged it
    subject: str                       # what in this field is unsettled
    note: str | None = None
    forks: bool = True                 # False: a leaf finding, nothing downstream depends on it
    detail: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        out = {"token": "ESCALATED", "pending": self.pending}
        if self.note:
            out["note"] = self.note
        out["candidates"] = list(self.candidates)
        out["rule"] = self.rule
        out["subject"] = self.subject
        if self.detail:
            out["detail"] = self.detail
        return out


# ---- N1 ---------------------------------------------------------------------------------------

def resolve_six_harmony_lock(pair: str, legs: str) -> str | Escalation:
    """Lock token for a completed branch 六合 whose transformation gate (U5/U6) is NOT met.

    DAILY-CORE 0.3.2 says LOCKED_PARTIAL; the forensic stack's ratified practice (digong 午未,
    0.1e Part One items 3-4) says LOCKED_FULL. The two may not disagree and neither is ruled.
    """
    if R_DEF_1_RULING is None:
        return Escalation(
            pending="R-DEF-1", candidates=["LOCKED_FULL", "LOCKED_PARTIAL"],
            rule="U3/U4/A2 via N1 (LOCKED_PARTIAL undefined in the forensic stack)",
            subject=f"ungated 六合 {pair} ({legs})")
    return R_DEF_1_RULING


# ---- N2 ---------------------------------------------------------------------------------------

def check_layer_seniority(branch: str, leg: str, clash_desc: str, clash_layers: tuple,
                          combo_desc: str, combo_layers: tuple) -> str | Escalation:
    """U8 where the captured branch stands in a clash from a different time layer.

    Whether that clash is "standing" when the combination arrives depends on a layer order
    (natal > decade > annual > monthly > daily?) the stack never defines.
    """
    if R_DEF_2_RULING is None:
        return Escalation(
            pending="R-DEF-2", candidates=[CAPTURE_BLOCKED, CAPTURE_ALLOWED],
            rule="U8 (layer seniority undefined)",
            subject=f"{combo_desc} capturing {branch} ({leg})",
            note=(f"{branch} stands in a {'×'.join(clash_layers)} clash ({clash_desc}); capture by "
                  f"{'×'.join(combo_layers)} combination unresolved"))
    return R_DEF_2_RULING(clash_layers, combo_layers)


# ---- Other unruled selectors the stack already escalates on -----------------------------------

def check_same_layer_u8(branch: str, leg: str, clash_desc: str, layer: str,
                        combo_desc: str) -> Escalation:
    """E-8b, same-layer case. 0.1c U8: apply the priority reading and declare it; where the choice
    changes whether a lock completes, escalate. In the same layer it always does."""
    return Escalation(
        pending="E-8b", candidates=[CAPTURE_ALLOWED, CAPTURE_BLOCKED],
        rule="U8 / E-8b (priority reading vs pre-emption reading)",
        subject=f"{combo_desc} capturing {branch} ({leg})",
        note=(f"{branch} stands in a same-layer ({layer}) clash ({clash_desc}). Priority reading: "
              f"capture allowed. Pre-emption reading: capture blocked. The choice decides whether "
              f"the lock completes"))


def six_harmony_gate(pair: str, element: str, month_branch: str) -> str | Escalation:
    """U5 for a branch 六合 against one month branch. "MET" / "NOT_MET" or an Escalation."""
    if pair == "午未" and month_branch in pair:
        return Escalation(
            pending="E-14", candidates=["MET", "NOT_MET"], rule="U5 / E-14",
            subject=f"六合 {pair} gate in a {month_branch} month",
            note="午未 gate self-reference: the month branch is itself a leg of the combination")
    if element == "Earth":
        return "MET" if month_branch in SEASONAL_WANG["Earth"] else "NOT_MET"
    seasonal = month_branch in SEASONAL_WANG[element]
    sanhe = month_branch in SANHE_WANG[element]
    if seasonal == sanhe:
        return "MET" if seasonal else "NOT_MET"
    return Escalation(
        pending="U5-旺月", candidates=["MET", "NOT_MET"] if sanhe else ["NOT_MET", "MET"],
        rule="U5 (旺月 never tabulated; September audit L-3)",
        subject=f"六合 {pair} → {element} gate in a {month_branch} month",
        note=(f"seasonal 旺月 reading ({SEASONAL_WANG[element]}) says {'MET' if seasonal else 'NOT_MET'}; "
              f"三合-month reading ({SANHE_WANG[element]}, as 0.1e item 6 uses for Water) says "
              f"{'MET' if sanhe else 'NOT_MET'}"))


def stem_gate(pair: str, month_branch: str) -> str | Escalation:
    """U5 for a stem 五合, using only the F1 clauses the stack carries."""
    known = STEM_GATE_KNOWN[pair]
    months = (known["primary"] or "") + (known["secondary"] or "")
    if month_branch in months:
        return "MET"
    if known["complete"]:
        return "NOT_MET"
    return Escalation(
        pending="L-3", candidates=["MET", "NOT_MET"], rule="U5 / F1 (gate table not in the stack)",
        subject=f"五合 {pair} gate in a {month_branch} month", forks=False,
        note=(f"known gate months for {pair}: {months or 'none'}; the rest of 三命通會 論十干化氣 "
              f"(F1) is not in the stack, and 丁壬/戊癸 secondary months are open conjecture"))


def gate_divergence(subject: str, natal_value, monthly_value, natal_month: str,
                    monthly_month: str, forks: bool) -> Escalation:
    """E-5: which month branch gates the combination, natal or the monthly layer."""
    return Escalation(
        pending="E-5", candidates=[natal_value, monthly_value], rule="U5 / E-5", subject=subject,
        forks=forks,
        note=(f"natal month {natal_month} gives {natal_value}; monthly layer {monthly_month} "
              f"gives {monthly_value}"))
