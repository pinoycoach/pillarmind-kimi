"""Field → Resolved Field Map (V10 0.1c §2). Deterministic; no I/O of any kind.

Resolution order is 0.1c §2.2's: locks → stem commitments → combinations (branches before stems)
→ clashes → harms and destructions → punishments → void note.

Escalations that change downstream resolution fork the run into worlds, one per candidate. The
worlds are then merged: a field identical in every world is settled; a field that differs is
reported ESCALATED with the pending ruling(s) and each world's value.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from . import rulings
from .derive import Field, ten_god
from .rulings import CAPTURE_BLOCKED, Escalation
from .tables import (CLASH, COMBINATION_RANK, DESTRUCTION, DIRECTIONAL, DIRECTIONAL_CARDINAL, HARM,
                     PUNISHMENT_PAIRS, PUNISHMENT_SETS, SELF_PUNISHMENT, SIX_HARMONY, STEM_COMBINATION,
                     STEM_ELEMENT, STEM_GATE_KNOWN, STEMS, THREE_HARMONY, controls)

RESOLVER_VERSION = "phase1-0.1"
MAX_WORLDS = 512
ABSENT = "ABSENT"


# ---- worlds -----------------------------------------------------------------------------------

class World:
    def __init__(self, assumptions: dict):
        self.assumptions = assumptions
        self.discovered = []            # (var, Escalation) not yet assumed in this world
        self.seen = {}                  # var -> Escalation, every escalation met in this world

    def pick(self, var: str, result):
        """Settled value, or this world's assumed candidate for an Escalation."""
        if not isinstance(result, Escalation):
            return result
        self.seen[var] = result
        if not result.forks:
            return result.to_json()
        if var in self.assumptions:
            return self.assumptions[var]
        self.discovered.append((var, result))
        return result.candidates[0]


@dataclass
class Inst:
    id: str
    layer: str
    char: str
    index: int            # position in the pool's listing / consumption order


# ---- branch pass ------------------------------------------------------------------------------

def _pool_patterns():
    for pattern, element in DIRECTIONAL.items():
        yield "三會", pattern, element
    for pattern, element in THREE_HARMONY.items():
        yield "三合", pattern, element
    for pattern, element in SIX_HARMONY.items():
        yield "六合", pattern, element


def _all_natal(insts) -> bool:
    return all(b.layer == "natal" for b in insts)


def _standing_clashes(branches):
    """Clash partners per instance, before any lock. E-23 (ch. 7 / ch. 25, adopted, DECISIONS N22): two
    natal branches of one kind do not clash a single natal opposite. A two-against-one shape involving
    a transit is not settled by the text, so it counts as a potential standing clash here."""
    partners = {b.id: [] for b in branches}
    for pair in CLASH:
        xs = [b for b in branches if b.char == pair[0]]
        ys = [b for b in branches if b.char == pair[1]]
        if not xs or not ys:
            continue
        if sorted((len(xs), len(ys))) == [1, 2] and _all_natal(xs + ys):
            continue
        for x in xs:
            for y in ys:
                partners[x.id].append((y, pair))
                partners[y.id].append((x, pair))
    return partners


def _layers(insts):
    seen = []
    for i in insts:
        if i.layer not in seen:
            seen.append(i.layer)
    return tuple(seen)


def _combo_gate(world, cid, pair, element, field_months):
    """U5 against the natal month, and against the monthly layer if present (E-5)."""
    natal_m, monthly_m = field_months
    g_natal = world.pick(f"U5@{cid}@natal", rulings.six_harmony_gate(pair, element, natal_m))
    if monthly_m is None:
        return g_natal
    g_month = world.pick(f"U5@{cid}@monthly", rulings.six_harmony_gate(pair, element, monthly_m))
    if g_natal == g_month:
        return g_natal
    return world.pick(f"E-5@{cid}", rulings.gate_divergence(
        f"六合 {pair} gate", g_natal, g_month, natal_m, monthly_m, forks=True))


def _branch_pass(world, branches, months, notes):
    partners = _standing_clashes(branches)
    claimed = {}                      # inst id -> combination id
    combos = {}
    failed = {}
    tokens = {b.id: "FREE" for b in branches}

    for ctype, pattern, element in sorted(_pool_patterns(), key=lambda p: COMBINATION_RANK[p[0]]):
        attempt = 0
        while True:
            attempt += 1
            legs, alternatives, lost_to = [], {}, None
            for ch in pattern:
                present = [b for b in branches if b.char == ch]
                free = [b for b in present if b.id not in claimed]
                if not free:
                    if present:
                        lost_to = claimed[present[0].id]
                    legs = None
                    break
                legs.append(free[0])
                if len(free) > 1:
                    alternatives[ch] = [b.id for b in free[1:]]
            if legs is None:
                if lost_to and attempt == 1 and all(any(b.char == c for b in branches) for c in pattern):
                    fid = f"{ctype} {pattern}"
                    failed[fid] = {
                        "status": "FAILED_PRE_COMPLETION", "leg_taken_by": lost_to,
                        "rule": ("R19 (會 > 合 on a contested branch: located by example, ch. 7; "
                                 "方局 > 三合: declared engine decision)"),
                        "losing_resolution": f"{ctype} {pattern} would have completed and locked its legs"}
                break
            cid = f"{ctype} {pattern} [{'+'.join(b.id for b in legs)}]"
            record = {"type": ctype, "pattern": pattern, "element": element,
                      "legs": [b.id for b in legs], "layers": list(_layers(legs))}
            if alternatives:
                record["consumption"] = {
                    "rule": ("a combination forms with one of the identical candidates (ch. 7 戌與卯合 with "
                             "二卯; N28); seat by U10a consumption order (E-3, declared engine decision)"),
                    "unconsumed_alternatives": alternatives}

            # U8: a branch standing in a clash cannot be captured.
            blocked_by = []
            for leg in legs:
                for partner, cpair in partners[leg.id]:
                    if partner.id in {b.id for b in legs}:
                        continue
                    clash_layers = _layers([leg, partner])
                    combo_layers = _layers(legs)
                    clash_desc = f"{cpair} {leg.id}×{partner.id}"
                    var = f"U8@{cid}:{leg.id}×{partner.id}"
                    if len(clash_layers) == 1 and clash_layers == combo_layers:
                        result = rulings.check_same_layer_u8(leg.char, leg.id, clash_desc,
                                                             clash_layers[0], f"{ctype} {pattern}")
                    else:
                        result = rulings.check_layer_seniority(leg.char, leg.id, clash_desc, clash_layers,
                                                               f"{ctype} {pattern}", combo_layers)
                    if world.pick(var, result) == CAPTURE_BLOCKED:
                        blocked_by.append(clash_desc)
            if blocked_by:
                record["status"] = "NOT_FORMED"
                record["blocked_by_U8"] = blocked_by
                combos[cid] = record
                break

            if ctype == "六合":
                gate = _combo_gate(world, cid, pattern, element, months)
                record["gate"] = gate
                if gate == "MET":
                    record["lock"], record["transformation"] = "LOCKED_FULL", "TRANSFORMED"
                else:
                    record["lock"] = world.pick(f"R-DEF-1@{cid}",
                                                rulings.resolve_six_harmony_lock(pattern, "+".join(b.id for b in legs)))
                    record["transformation"] = "NEUTRALIZED"
            else:
                record["lock"] = "LOCKED_FULL"
                record["transformation"] = "none (三合/三會 lock is LOCKED_FULL, not TRANSFORMED; 0.1c U6)"
            record["status"] = "FORMED"
            for b in legs:
                claimed[b.id] = cid
                tokens[b.id] = record["lock"]
            combos[cid] = record

    half = {}
    for pattern, element in THREE_HARMONY.items():
        present = [c for c in pattern if any(b.char == c for b in branches)]
        if len(present) == 2:
            half[f"三合 {pattern}"] = {"present": "".join(present),
                                     "note": "half-frame: tendency only, no token (0.1c §2.4; P-14 open)"}
    for pattern, element in DIRECTIONAL.items():
        present = [c for c in pattern if any(b.char == c for b in branches)]
        if len(present) == 2 and DIRECTIONAL_CARDINAL[pattern] in present:
            half[f"三會 {pattern}"] = {"present": "".join(present), "note": "半會: directional tendency, no token"}
    return tokens, claimed, combos, failed, half


# ---- clash / harm / destruction / punishment --------------------------------------------------

LOCK_OUTCOME = {
    "沖": {"LOCKED_FULL": "ELIMINATED", "LOCKED_PARTIAL": "UNRESOLVED"},     # U3
    "害": {"LOCKED_FULL": "ELIMINATED", "LOCKED_PARTIAL": "ATTENUATED"},     # U4
    "破": {"LOCKED_FULL": "ELIMINATED", "LOCKED_PARTIAL": "ATTENUATED"},     # U4
    "刑": {"LOCKED_FULL": "ELIMINATED", "LOCKED_PARTIAL": "UNRESOLVED"},     # A2
}
RULE = {"沖": "U3", "害": "U4", "破": "U4", "刑": "A2"}


def _against_locks(kind, insts, tokens, claimed):
    states = [tokens[i.id] for i in insts]
    combos = {claimed.get(i.id) for i in insts}
    if len(insts) >= 2 and None not in combos and len(combos) == 1:
        return Escalation(
            pending="E-38", candidates=["ELIMINATED", "FULL_FORCE"], forks=False,
            rule="E-38 pool collision (§2.2's order concerns third branches, not the pair itself; N28)",
            subject=f"{kind} between legs of the same combination {combos.pop()}",
            note="寅亥 and 巳申 sit in both 六合 and 破; no rule says which governs").to_json()
    if "LOCKED_FULL" in states:
        return "ELIMINATED"
    if "LOCKED_PARTIAL" in states:
        return LOCK_OUTCOME[kind]["LOCKED_PARTIAL"]
    return "FULL_FORCE"


def _scope_escalation(kind, pair, xs, ys):
    return Escalation(
        pending="E-23-scope", candidates=["as counted", "NOT_FIRING"], forks=False,
        rule="E-23 (two-do-not-clash-one; located for 沖 and 子卯刑 only)",
        subject=f"{kind} {pair} with {len(xs)}×{len(ys)} instances",
        note="multi-instance configuration outside the located 2-against-1 / 2-against-2 cases").to_json()


def _pair_pool(kind, pool, branches, tokens, claimed, e23_located):
    out = {}
    for pair in pool:
        xs = [b for b in branches if b.char == pair[0]]
        ys = [b for b in branches if b.char == pair[1]]
        if not xs or not ys:
            continue
        rid = f"{kind} {pair}"
        rec = {"instances": [b.id for b in xs + ys], "rule": RULE[kind]}
        counts = sorted((len(xs), len(ys)))
        all_free = all(tokens[b.id] == "FREE" for b in xs + ys)
        if counts == [1, 1]:
            rec["outcome"] = _against_locks(kind, xs + ys, tokens, claimed)
        elif e23_located and counts == [1, 2] and all_free:
            single, dups = (xs, ys) if len(xs) == 1 else (ys, xs)
            if _all_natal(single + dups):
                # N22 transit scope (1): 並 = present together in the natal field, not adjacent.
                rec["outcome"] = "NOT_FIRING"
                rec["rule"] = ("E-23 兩不沖一, natal (ch. 7 二卯不刑一子, ch. 25 兩申並而不沖一寅; "
                               "located 原文, N22)")
            else:
                # N22 transit scope (3), and (a) every other shape with a transit in it: not shown.
                case3 = _all_natal(single) and sum(b.layer != "natal" for b in dups) == 1
                shape = ("a transit supplies one of the outnumbering pair" if case3
                         else "a transit is on the single side, or supplies both duplicates")
                rec["outcome"] = Escalation(
                    pending="E-23-scope", candidates=["NOT_FIRING", "FULL_FORCE"], forks=False,
                    rule="E-23 transit scope (N22 case 3)" if case3 else "E-23 transit scope (N22 (a))",
                    subject=f"{kind} {pair}: {', '.join(b.id for b in dups)} against {single[0].id}",
                    note=(f"two-against-one where {shape}; ch. 7 and ch. 25 show only natal duplicates "
                          f"against a natal single")).to_json()
        elif e23_located and counts == [2, 2] and all_free:
            single_natal = [s for s in (xs, ys) if _all_natal(s)]
            mixed = [s for s in (xs, ys) if sum(b.layer != "natal" for b in s) == 1]
            if len(single_natal) == 1 and len(mixed) == 1:
                # N22 transit scope (2): 運與本命合成二寅，以沖二申.
                rec["outcome"] = "FULL_FORCE"
                rec["rule"] = "E-23 一沖而得兩沖 (ch. 25 運與本命合成二寅; located 原文, N22)"
            elif _all_natal(xs + ys):
                # N22 (b): E-23 carves out the outnumbered shape only; equal numbers fall under U3.
                rec["outcome"] = "FULL_FORCE"
                rec["rule"] = "U3: equal numbers, all natal, both pairs fire (E-23 carve-out not engaged; N22)"
            else:
                rec["outcome"] = _scope_escalation(kind, pair, xs, ys)
        elif e23_located and counts == [1, 2]:
            # ch. 7 因解而反得刑沖: a combination that takes one of the two duplicates leaves the
            # other free, and the free one acts (戌與卯合…則一合而一刑). Count FREE instances only.
            single, dups = (xs, ys) if len(xs) == 1 else (ys, xs)
            free = [b for b in dups if tokens[b.id] == "FREE"]
            if tokens[single[0].id] != "FREE":
                rec["outcome"] = _against_locks(kind, single, tokens, claimed)
                rec["rule"] = f"{RULE[kind]} (the single side is locked)"
            elif len(free) == 1:
                rec["outcome"] = "FULL_FORCE"
                rec["acting"] = [single[0].id, free[0].id]
                rec["rule"] = ("E-23 + 因解而反得刑沖 (ch. 7 戌與卯合…則一合而一刑; located 原文, N22): "
                               "one duplicate is locked, the free one acts")
            else:                                   # both duplicates locked
                rec["outcome"] = _against_locks(kind, dups, tokens, claimed)
                rec["rule"] = f"{RULE[kind]} (every duplicate is locked)"
        else:
            rec["outcome"] = _scope_escalation(kind, pair, xs, ys)
        out[rid] = rec
    return out


def _punishments(branches, tokens, claimed, omissions):
    out = _pair_pool("刑", PUNISHMENT_PAIRS, branches, tokens, claimed, e23_located=True)
    for s in PUNISHMENT_SETS:
        groups = [[b for b in branches if b.char == c] for c in s]
        present = [g for g in groups if g]
        if len(present) == 3:
            insts = [b for g in groups for b in g]
            rid = f"刑 {s}"
            rec = {"instances": [b.id for b in insts], "rule": "A2"}
            if all(len(g) == 1 for g in groups):
                rec["outcome"] = _against_locks("刑", insts, tokens, claimed)
            else:
                rec["outcome"] = Escalation(
                    pending="E-23-scope", candidates=["as counted", "NOT_FIRING"], forks=False,
                    rule="E-23 (scope open for 三刑 sets)", subject=f"刑 {s} with duplicate legs").to_json()
            out[rid] = rec
        elif len(present) == 2:
            chars = "".join(g[0].char for g in present)
            omissions[f"刑 {s} partial ({chars})"] = (
                f"§2.4 lists {s} only as a three-branch set; {chars} alone is not in the pool. "
                f"Reported under U1, not supplied")
    for ch in SELF_PUNISHMENT:
        insts = [b for b in branches if b.char == ch]
        if len(insts) < 2:
            continue
        free = [b for b in insts if tokens[b.id] == "FREE"]
        rec = {"instances": [b.id for b in insts], "rule": "A2"}
        if len(free) >= 2:
            rec["outcome"] = "FULL_FORCE"
            if len(free) < len(insts):
                rec["rule"] = "A2 + U10a surplus-FREE (located for 沖/刑, ch. 7)"
        else:
            rec["outcome"] = _against_locks("刑", insts, tokens, claimed)
        out[f"自刑 {ch}{ch}"] = rec
    return out


def _eliminations(pools, claimed, combos, by_id):
    """0.1c §2.3 mandatory elimination statements, for every ELIMINATED interaction."""
    out = {}
    for rid, rec in pools.items():
        if rec.get("outcome") != "ELIMINATED":
            continue
        locked = [i for i in rec["instances"] if i in claimed]
        others = [i for i in rec["instances"] if i not in claimed]
        parts = []
        for i in locked:
            c = combos[claimed[i]]
            mates = [m for m in c["legs"] if m != i]
            parts.append(f"{by_id[i].char} ({i}) is locked in {c['type']} {c['pattern']} with "
                         f"{', '.join(f'{by_id[m].char} ({m})' for m in mates)}")
        target = ", ".join(f"{by_id[o].char} ({o})" for o in others) or "its partner"
        out[rid] = f"{'; '.join(parts)}, therefore its {rid.split()[0]} with {target} is ELIMINATED."
    return out


# ---- stem pass --------------------------------------------------------------------------------

NATAL_ORDER = {"natal.year": 0, "natal.month": 1, "natal.day": 2, "natal.hour": 3}


def _natal_standing(a, b, stems):
    """子平真詮 ch. 5 (full chapter, 0.1e Addendum A): adjacent → combines; a controlling
    intervener → 有若無; Year–Hour distance → 半合 (十之二三). A one-column gap with no
    controlling intervener is not described by the text."""
    i, j = sorted((NATAL_ORDER[a.id], NATAL_ORDER[b.id]))
    if j - i == 1:
        return "ADJACENT", []
    between = [s for s in stems if s.layer == "natal" and i < NATAL_ORDER[s.id] < j]
    ctrl = [s.id for s in between if controls(s.char, a.char) or controls(s.char, b.char)]
    if ctrl:
        return "BLOCKED", ctrl
    return ("HALF", []) if j - i == 3 else ("GAP1", [])


def _transformed_ten_god(dm, stem, element):
    yang = STEMS.index(stem) % 2 == 0
    target = next(s for s in STEMS if STEM_ELEMENT[s] == element and (STEMS.index(s) % 2 == 0) == yang)
    return ten_god(dm, target)


def _stem_gate_state(world, pair, months, stems, hidden_all, cid, combined=()):
    natal_m, monthly_m = months
    g_n = rulings.stem_gate(pair, natal_m)
    g = g_n
    if monthly_m is not None:
        g_m = rulings.stem_gate(pair, monthly_m)
        if isinstance(g_n, Escalation) or isinstance(g_m, Escalation):
            g = g_n if isinstance(g_n, Escalation) else g_m
        elif g_n != g_m:
            g = rulings.gate_divergence(f"五合 {pair} gate", g_n, g_m, natal_m, monthly_m, forks=False)
    g = world.pick(f"gate@{cid}", g)
    if g != "MET":
        return g
    return _stem_blocker(world, pair, stems, hidden_all, combined, cid)


def _stem_blocker(world, pair, stems, hidden_all, combined, cid):
    """F1's blocking clauses (N28). 柱有X字: X on any surface stem blocks; X only as a hidden stem is
    open (E-18, raised on 丙辛's 丁; the same clause shape for 丁壬 and 戊癸). 有X字間之: X standing on
    a natal stem between the two combining natal stems blocks (妒合 in 三命通會's sense; E-16)."""
    blocker = STEM_GATE_KNOWN[pair]["blocker"]
    x = blocker["stem"]
    if blocker["kind"] == "pillar":
        if any(s.char == x for s in stems):
            return f"NOT_MET (柱有{x}字不化: {x} on a surface stem, F1)"
        if x in hidden_all:
            return world.pick(f"E-18@{cid}", Escalation(
                pending="E-18" if pair == "丙辛" else "E-18-scope", candidates=["MET", "NOT_MET"],
                rule=f"F1 柱有{x}字不化 / E-18", forks=False, subject=f"五合 {pair}",
                note=f"{x} present only as a hidden stem; whether it blocks is open"))
        return "MET"
    positions = sorted(NATAL_ORDER[s.id] for s in combined if s.id in NATAL_ORDER)
    if len(combined) != 2 or len(positions) != 2:
        # No single natal pair (a contest, or a transit partner): "between" is undefined.
        # UNDETERMINED, not "MET (...)": only an exact "MET" may ever produce TRANSFORMED (N38).
        return f"UNDETERMINED (有{x}字間之 not evaluable: no single natal combining pair)"
    between = [s for s in stems if s.id in NATAL_ORDER and positions[0] < NATAL_ORDER[s.id] < positions[1]]
    if any(s.char == x for s in between):
        return f"NOT_MET (有{x}字間之則不化: {x} stands between the two, F1 妒合; E-16 sense)"
    return "MET"


def _stem_pass(world, stems, dm, months, hidden_all):
    records, tokens = {}, {s.id: "FREE" for s in stems}
    for pair, element in STEM_COMBINATION.items():
        xs = [s for s in stems if s.char == pair[0]]
        ys = [s for s in stems if s.char == pair[1]]
        cid = f"五合 {pair}"
        if not xs and not ys:
            continue
        if not xs or not ys:
            have, missing = (xs, pair[1]) if xs else (ys, pair[0])
            if missing in hidden_all:
                records[cid] = {"status": "NOT_FIRING", "instances": [s.id for s in have],
                                "note": f"partner {missing} exists only as a hidden stem and does not reach surface"}
            continue
        insts = xs + ys
        rec = {"transforms_to_if_gated": element, "instances": [s.id for s in insts]}
        transit = any(s.layer != "natal" for s in insts)
        combined = []
        if len(xs) == 1 and len(ys) == 1:
            a, b = xs[0], ys[0]
            if transit:
                rec["status"] = world.pick(f"E-21@{cid}", Escalation(
                    pending="E-21", candidates=["COMBINED", "HALF_COMBINED"], forks=False,
                    rule="子平真詮 ch. 5 / E-21", subject=f"{cid} {a.id}+{b.id}",
                    note="ch. 5's proximity mechanisms concern natal columns only; transit 隔位 is unlocated"))
            else:
                standing, ctrl = _natal_standing(a, b, stems)
                if standing == "ADJACENT":
                    rec["status"], combined = "COMBINED", [a, b]
                elif standing == "BLOCKED":
                    rec["status"] = "BLOCKED_BY_INTERVENER"
                    rec["note"] = f"controlling intervener {', '.join(ctrl)}: 有若無 (ch. 5)"
                elif standing == "HALF":
                    rec["status"] = "HALF_COMBINED"
                    rec["note"] = "隔位太遠 (Year–Hour): 半合, 十之二三 (ch. 5); no transformation"
                    for s in (a, b):
                        tokens[s.id] = "HALF_COMBINED"
                else:
                    rec["status"] = world.pick(f"E-2@{cid}", Escalation(
                        pending="E-2-scope", candidates=["COMBINED", "HALF_COMBINED"], forks=False,
                        rule="子平真詮 ch. 5", subject=f"{cid} {a.id}+{b.id}",
                        note="one-column separation with no controlling intervener: the text gives "
                             "adjacent and Year–Hour cases only"))
        elif transit:
            rec["status"] = world.pick(f"E-21@{cid}", Escalation(
                pending="E-21", forks=False,
                candidates=["A 先合: nearer claimant combines first; the other stands unimpaired",
                            "B 爭合: mutual impairment, 情不專, no clean capture"],
                rule="子平真詮 ch. 5 (本身之合 + 高太尉 vs 兩辛合丙) / 0.1e Addendum B §C2",
                subject=f"{cid} claimants {', '.join(s.id for s in insts)}",
                note="whether natal-vs-transit claimants instantiate 隔位 (the selector) is unlocated"))
        elif len(xs) > 1 and len(ys) > 1:
            rec["status"] = world.pick(f"E-1@{cid}", Escalation(
                pending="E-1-scope", candidates=["pairwise", "CONTESTED"], forks=False,
                rule="子平真詮 ch. 5", subject=cid, note="several claimants on both sides"))
        else:
            claimants, partner = (xs, ys[0]) if len(xs) > 1 else (ys, xs[0])
            standing = {c.id: _natal_standing(c, partner, stems)[0] for c in claimants}
            adjacent = [c for c in claimants if standing[c.id] == "ADJACENT"]
            rec["standing"] = standing
            if len(adjacent) >= 2:
                rec["status"] = "CONTESTED"
                rec["note"] = "爭合 between equal-standing claimants (ch. 5 兩辛合丙; E-1; U13): no transformation"
                for s in adjacent + [partner]:
                    tokens[s.id] = "CONTESTED"
            elif len(adjacent) == 1:
                rec["status"], combined = "COMBINED", [adjacent[0], partner]
                rec["note"] = "兩合一而隔位，全無爭妒 (ch. 5, 高太尉): the separated claimant stands unimpaired"
            else:
                rec["status"] = world.pick(f"E-1@{cid}", Escalation(
                    pending="E-1-scope", candidates=["CONTESTED", "no contest"], forks=False,
                    rule="子平真詮 ch. 5", subject=cid, note="no claimant adjacent to the partner"))
        if isinstance(rec.get("status"), dict):
            for s in insts:
                tokens[s.id] = rec["status"]
        if not combined:
            # The gate is recorded for every stem combination, settled or not (N37), with blockers
            # evaluated, so the map itself carries it. It decides nothing here: no state is set.
            rec["gate"] = _stem_gate_state(world, pair, months, stems, hidden_all, cid, insts)
        if combined:
            gate = _stem_gate_state(world, pair, months, stems, hidden_all, cid, combined)
            rec["gate"] = gate
            dm_bound = any(s.id == "natal.day" for s in combined)
            if gate == "MET" and dm_bound:
                # N28 (6): the Day Master's own combining never transforms it unless the formation is
                # 化格 (ch. 5 本身十干合之，不爲合去; CORE-U7). The resolver has no formation field yet (N27).
                rec["state"] = "NEUTRALIZED"
                rec["grade"] = "被合"
                rec["note_dm"] = ("gate met, but a Day Master combination is TRANSFORMED only in a 化格 "
                                  "formation; formation not derived (N27), so NEUTRALIZED / 被合")
            elif gate == "MET":
                rec["state"] = "TRANSFORMED"
                rec["annihilation"] = {s.id: {"original": ten_god(dm, s.char),
                                              "reassigned": _transformed_ten_god(dm, s.char, element)}
                                       for s in combined}
            elif isinstance(gate, dict):
                rec["state"] = gate
            else:
                rec["state"] = "NEUTRALIZED"
                rec["grade"] = "被合" if dm_bound else "羈絆"
            if STEM_GATE_KNOWN[pair].get("emendation") and gate == "MET":
                rec["gate_emendation"] = STEM_GATE_KNOWN[pair]["emendation"]
            for s in combined:
                tokens[s.id] = "COMMITTED"
        if any(s.id == "natal.day" for s in insts):
            rec["day_master"] = "本身之合: the Day Master's own combining never removes it (ch. 5; P-10 pending)"
        records[cid] = rec
    return records, tokens


# ---- one world --------------------------------------------------------------------------------

def _resolve_once(field: Field, world: World) -> dict:
    ps = field.pillars
    dm = field.day_master
    branches = [Inst(p.id, p.layer, p.branch, n) for n, p in enumerate(ps)]
    stems = [Inst(p.id, p.layer, p.stem, n) for n, p in enumerate(ps)]
    by_id = {b.id: b for b in branches}
    natal_month = next(p.branch for p in ps if p.id == "natal.month")
    monthly = next((p.branch for p in ps if p.id == "monthly"), None)
    months = (natal_month, monthly)
    hidden_all = [h for p in ps for h in p.hidden]
    omissions = {}

    tokens, claimed, combos, failed, half = _branch_pass(world, branches, months, omissions)
    stem_records, stem_tokens = _stem_pass(world, stems, dm, months, hidden_all)

    clashes = _pair_pool("沖", CLASH, branches, tokens, claimed, e23_located=True)
    harms = _pair_pool("害", HARM, branches, tokens, claimed, e23_located=False)
    destructions = _pair_pool("破", DESTRUCTION, branches, tokens, claimed, e23_located=False)
    punishments = _punishments(branches, tokens, claimed, omissions)
    all_pools = {**clashes, **harms, **destructions, **punishments}

    void_pair = field.void["pair"]
    return {
        "branch_combinations": combos,
        "branch_combination_failures": failed,
        "half_frames": half,
        "branch_tokens": tokens,
        "stem_combinations": stem_records,
        "stem_tokens": stem_tokens,
        "clashes": clashes,
        "harms": harms,
        "destructions": destructions,
        "punishments": punishments,
        "eliminations": _eliminations(all_pools, claimed, combos, by_id),
        "omissions": omissions,
        "void_instances": [b.id for b in branches if b.char in void_pair],
    }


# ---- merge ------------------------------------------------------------------------------------

def _neighbors_on(var, a, b):
    if a.get(var, ABSENT) == b.get(var, ABSENT):
        return False
    common = (set(a) & set(b)) - {var}
    return all(a[k] == b[k] for k in common)


def _merge(values, worlds, var_pending):
    first = values[0]
    if all(v == first for v in values):
        return first
    if all(isinstance(v, dict) and v.get("token") != "ESCALATED" for v in values):
        keys = []
        for v in values:
            keys += [k for k in v if k not in keys]
        return {k: _merge([v.get(k, ABSENT) for v in values], worlds, var_pending) for k in keys}
    affecting = []
    for var in var_pending:
        if any(_neighbors_on(var, worlds[i], worlds[j]) and values[i] != values[j]
               for i in range(len(worlds)) for j in range(i + 1, len(worlds))):
            affecting.append(var)
    pending = []
    for var in affecting:
        if var_pending[var] not in pending:
            pending.append(var_pending[var])
    candidates = []
    for v in values:
        if v not in candidates:
            candidates.append(v)
    return {
        "token": "ESCALATED",
        "pending": pending[0] if len(pending) == 1 else pending,
        "candidates": candidates,
        "by_world": [{"assume": {k: w[k] for k in affecting if k in w}, "value": v}
                     for w, v in zip(worlds, values)],
    }


def _dedupe_by_world(obj):
    """Collapse identical by_world rows (worlds that differ only in unrelated variables)."""
    if isinstance(obj, dict):
        out = {k: _dedupe_by_world(v) for k, v in obj.items()}
        if out.get("token") == "ESCALATED" and "by_world" in out:
            rows = []
            for r in out["by_world"]:
                if r not in rows:
                    rows.append(r)
            out["by_world"] = rows
        return out
    if isinstance(obj, list):
        return [_dedupe_by_world(v) for v in obj]
    return obj


# ---- public -----------------------------------------------------------------------------------

def _pillar_json(p, dm, void_pair):
    return {
        "layer": p.layer, "stem": p.stem, "branch": p.branch,
        "stem_ten_god": "日主" if p.id == "natal.day" else ten_god(dm, p.stem),
        "hidden_stems": [{"stem": h, "ten_god": ten_god(dm, h)} for h in p.hidden],
        "void": p.branch in void_pair,
    }


def resolve(field: Field) -> dict:
    """The Resolved Field Map for a derived Field."""
    queue, done = [{}], []
    while queue:
        assumptions = queue.pop(0)
        world = World(assumptions)
        out = _resolve_once(field, world)
        new = [(v, e) for v, e in world.discovered if v not in assumptions]
        if not new:
            done.append((assumptions, out, world.seen))
            continue
        var, esc = new[0]
        for c in esc.candidates:
            queue.append({**assumptions, var: c})
        if len(queue) + len(done) > MAX_WORLDS:
            raise RuntimeError(f"More than {MAX_WORLDS} worlds; field too entangled to report")

    worlds = [a for a, _, _ in done]
    seen = {}
    for _, _, s in done:
        for var, esc in s.items():
            seen.setdefault(var, esc)
    var_pending = {var: esc.pending for var, esc in seen.items() if esc.forks}
    merged = _merge([o for _, o, _ in done], worlds, var_pending)
    merged = _dedupe_by_world(merged)

    dm = field.day_master
    return {
        "resolver": RESOLVER_VERSION,
        "input": field.input_record,
        "input_integrity": {"corroboration": field.corroboration, "notes": field.notes},
        "pillars": {p.id: _pillar_json(p, dm, field.void["pair"]) for p in field.pillars},
        "decade": field.decade_record,
        "day_master": dm,
        "void": {**field.void, "rule": "A1 / U11: note only; void branches participate at full weight",
                 "instances": merged.pop("void_instances")},
        **merged,
        "escalations": {var: esc.to_json() for var, esc in seen.items()},
        "worlds": {"count": len(worlds), "assumptions": worlds},
    }


def to_json(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)
