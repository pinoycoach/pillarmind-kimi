"""Rule-level tests on hand-built fields.

These are NOT the golden cases: they feed pillars straight to the resolver to check resolution
logic, which is exactly what CLAUDE.md says the golden test must never do. The golden cases, which
run derive → resolve from a birth datetime, are in test_golden.py.
"""
import pytest

from resolver import rulings
from resolver.derive import Field, Pillar, _hidden
from resolver.resolve import resolve


def _field(natal, transit=()):
    ps = [Pillar("natal", pos, gz[0], gz[1], _hidden(gz[1]))
          for pos, gz in zip(("year", "month", "day", "hour"), natal)]
    ps += [Pillar(layer, layer, gz[0], gz[1], _hidden(gz[1])) for layer, gz in transit]
    return Field(pillars=ps, day_master=natal[2][0], void={"xun": "", "stream": [], "pair": []},
                 corroboration={}, input_record={}, notes=[])


DIGONG = (("乙酉", "己卯", "丙申", "己丑"), (("decade", "辛未"), ("annual", "丙午")))
LOCK = "六合 午未 [annual+decade]"


def _worlds(esc):
    return {row["value"] for row in esc["by_world"]}


@pytest.fixture
def unruled(monkeypatch):
    """The seam with N1 and N2 unruled: proves the escalation path still works if a ruling is
    ever withdrawn."""
    monkeypatch.setattr(rulings, "R_DEF_1_RULING", None)
    monkeypatch.setattr(rulings, "R_DEF_2_RULING", None)


def test_rulings_in_force():
    assert rulings.R_DEF_1_RULING == "LOCKED_FULL"
    assert rulings.R_DEF_2_RULING(("natal", "decade"), ("annual", "decade")) == rulings.CAPTURE_ALLOWED


def test_digong_under_the_rulings_is_the_ratified_map():
    """N1 = LOCKED_FULL, N2 = capture allowed: 0.1e Part One items 3-5, exactly."""
    r = resolve(_field(*DIGONG))
    assert r["branch_combinations"][LOCK]["lock"] == "LOCKED_FULL"
    assert r["branch_combinations"][LOCK]["transformation"] == "NEUTRALIZED"
    for pool, key in (("clashes", "沖 丑未"), ("harms", "害 丑午"), ("destructions", "破 午卯")):
        assert r[pool][key]["outcome"] == "ELIMINATED"
    assert r["clashes"]["沖 卯酉"]["outcome"] == "FULL_FORCE"
    assert not any(e["pending"] in ("R-DEF-1", "R-DEF-2") for e in r["escalations"].values())
    assert r["stem_combinations"]["五合 丙辛"]["status"]["pending"] == "E-21"     # still open
    assert r["worlds"]["count"] == 1


def test_digong_reproduces_the_three_maps_of_the_september_audit(unruled):
    """exhibits/v10_stack_audit_2026-09.md §2, 'Joint consequence' table."""
    r = resolve(_field(*DIGONG))
    lock = r["branch_combinations"][LOCK]["lock"]
    assert lock["token"] == "ESCALATED" and lock["pending"] == ["R-DEF-2", "R-DEF-1"]
    assert lock["candidates"] == ["ABSENT", "LOCKED_FULL", "LOCKED_PARTIAL"]
    by = {tuple(sorted(row["assume"].values())): row["value"]
          for row in r["clashes"]["沖 丑未"]["outcome"]["by_world"]}
    assert by[("capture_blocked",)] == "FULL_FORCE"                        # U8 applied
    assert by[("LOCKED_FULL", "capture_allowed")] == "ELIMINATED"          # as ratified
    assert by[("LOCKED_PARTIAL", "capture_allowed")] == "UNRESOLVED"       # DAILY-CORE
    assert _worlds(r["harms"]["害 丑午"]["outcome"]) == {"FULL_FORCE", "ELIMINATED", "ATTENUATED"}
    assert _worlds(r["destructions"]["破 午卯"]["outcome"]) == {"FULL_FORCE", "ELIMINATED", "ATTENUATED"}
    assert r["clashes"]["沖 卯酉"]["outcome"] == "FULL_FORCE"
    assert r["branch_tokens"]["natal.day"] == "FREE"                        # 申 inert
    assert r["stem_combinations"]["五合 丙辛"]["status"]["pending"] == "E-21"


def test_escalation_objects_have_the_claude_md_shapes(unruled):
    esc = resolve(_field(*DIGONG))["escalations"]
    n1 = esc[f"R-DEF-1@{LOCK}"]
    assert {k: n1[k] for k in ("token", "pending", "candidates")} == \
        {"token": "ESCALATED", "pending": "R-DEF-1", "candidates": ["LOCKED_FULL", "LOCKED_PARTIAL"]}
    n2 = esc[f"U8@{LOCK}:decade×natal.hour"]
    assert n2["token"] == "ESCALATED" and n2["pending"] == "R-DEF-2"
    assert n2["note"].startswith("未 stands in a decade×natal clash")
    assert n2["note"].endswith("capture by annual×decade combination unresolved")


def test_the_seam_is_the_only_thing_the_rulings_changed(unruled, monkeypatch):
    """Ruled, the map is the unruled run's LOCKED_FULL / capture_allowed world, field for field."""
    r_unruled = resolve(_field(*DIGONG))
    monkeypatch.setattr(rulings, "R_DEF_1_RULING", "LOCKED_FULL")
    monkeypatch.setattr(rulings, "R_DEF_2_RULING", lambda clash, combo: rulings.CAPTURE_ALLOWED)
    r = resolve(_field(*DIGONG))
    for pool, key in (("clashes", "沖 丑未"), ("harms", "害 丑午"), ("destructions", "破 午卯")):
        world = next(row["value"] for row in r_unruled[pool][key]["outcome"]["by_world"]
                     if set(row["assume"].values()) == {"capture_allowed", "LOCKED_FULL"})
        assert r[pool][key]["outcome"] == world == "ELIMINATED"
    assert set(r["eliminations"]) == {"沖 丑未", "害 丑午", "破 午卯"}


def test_n1_alone_escalates_an_ungated_six_harmony_with_no_clash(unruled):
    # natal 午未 in a 卯 month, nothing clashing either leg: only R-DEF-1 is in play.
    r = resolve(_field(("甲午", "丁卯", "丙寅", "乙未")))
    lock = r["branch_combinations"]["六合 午未 [natal.year+natal.hour]"]["lock"]
    assert lock["pending"] == "R-DEF-1"
    assert lock["candidates"] == ["LOCKED_FULL", "LOCKED_PARTIAL"]


def test_gated_six_harmony_is_locked_full_without_escalation():
    # 午未 in a 辰 month (Earth): U5 gate met, and nothing clashes either leg.
    r = resolve(_field(("甲午", "戊辰", "丙寅", "乙未")))
    rec = r["branch_combinations"]["六合 午未 [natal.year+natal.hour]"]
    assert rec["lock"] == "LOCKED_FULL" and rec["transformation"] == "TRANSFORMED"


def test_n1_ruled_ungated_six_harmony_is_locked_full():
    r = resolve(_field(("甲午", "丁卯", "丙寅", "乙未")))
    rec = r["branch_combinations"]["六合 午未 [natal.year+natal.hour]"]
    assert rec["lock"] == "LOCKED_FULL" and rec["transformation"] == "NEUTRALIZED"


def test_same_layer_u8_escalates_on_e8b_not_r_def_2():
    """The N2 ruling covers cross-layer cases only; same-layer U8 remains E-8b and still escalates."""
    # natal 子 clashes natal 午, natal 午未 would capture 午.
    r = resolve(_field(("甲子", "丁卯", "丙午", "乙未")))
    pendings = {e["pending"] for e in r["escalations"].values()}
    assert "E-8b" in pendings and "R-DEF-2" not in pendings


AA = ("庚戌", "甲申", "甲申", "丙寅")


def test_e23_case1_natal_duplicates_against_a_natal_single_do_not_fire():
    """N22 transit scope (1). AA: Month and Day 申 against Hour 寅, all natal. Adjacency is not
    required (並 = present together): Year 申 and Day 申 against Hour 寅 is the same."""
    assert resolve(_field(AA))["clashes"]["沖 寅申"]["outcome"] == "NOT_FIRING"
    r = resolve(_field(("甲申", "丁卯", "壬申", "丙寅")))
    assert r["clashes"]["沖 寅申"]["outcome"] == "NOT_FIRING"


def test_e23_case2_transit_supplies_the_second_of_the_single_side():
    """N22 transit scope (2). AA in the 庚寅 decade: 運與本命合成二寅，以沖二申 → both pairs fire."""
    rec = resolve(_field(AA, (("decade", "庚寅"),)))["clashes"]["沖 寅申"]
    assert rec["outcome"] == "FULL_FORCE"
    assert "運與本命" in rec["rule"]


def test_e23_case3_transit_supplies_one_of_the_outnumbering_pair_escalates():
    """N22 transit scope (3). Natal 申 against natal 寅 (one against one), then an annual 申 makes
    it two against one. Not shown in the text."""
    r = resolve(_field(("庚戌", "甲申", "丙子", "丙寅"), (("annual", "甲申"),)))
    out = r["clashes"]["沖 寅申"]["outcome"]
    assert out["token"] == "ESCALATED" and out["pending"] == "E-23-scope"
    assert out["candidates"] == ["NOT_FIRING", "FULL_FORCE"]
    assert "outnumbering pair" in out["note"]


@pytest.mark.parametrize("natal,transit", [
    (("庚戌", "甲申", "甲申", "丁卯"), (("annual", "丙寅"),)),                     # transit on the single side
    (("庚戌", "丁卯", "丙子", "丙寅"), (("decade", "甲申"), ("annual", "甲申"))),  # both duplicates transit
])
def test_e23_unnamed_transit_shapes_escalate_like_case3(natal, transit):
    """N22 (a): not shown in the text, so E-23-scope with NOT_FIRING / FULL_FORCE."""
    out = resolve(_field(natal, transit))["clashes"]["沖 寅申"]["outcome"]
    assert out["token"] == "ESCALATED" and out["pending"] == "E-23-scope"
    assert out["candidates"] == ["NOT_FIRING", "FULL_FORCE"]
    assert out["rule"] == "E-23 transit scope (N22 (a))"


def test_all_natal_two_against_two_fires_under_u3():
    """N22 (b): E-23 carves out the outnumbered shape only; equal numbers fall under U3."""
    rec = resolve(_field(("甲申", "丙寅", "壬申", "戊寅")))["clashes"]["沖 寅申"]
    assert rec["outcome"] == "FULL_FORCE"
    assert rec["rule"].startswith("U3") and "not shown" not in rec["rule"]


def test_shen_ch7_two_mao_do_not_punish_one_zi():
    """ch. 7: 假如甲生子月，支逢二卯相並，二卯不刑一子."""
    r = resolve(_field(("乙卯", "丙子", "甲申", "丁卯")))
    assert r["punishments"]["刑 子卯"]["outcome"] == "NOT_FIRING"


def test_shen_ch7_xu_combining_one_mao_releases_the_other_to_punish():
    """ch. 7 因解而反得刑沖: 而支又逢戌，戌與卯合，本爲解刑，而合去其一，則一合而一刑.
    甲 born in a 子 month, two 卯, one 戌."""
    r = resolve(_field(("乙卯", "丙子", "甲戌", "丁卯")))
    lock = r["branch_combinations"]["六合 卯戌 [natal.year+natal.day]"]
    assert lock["lock"] == "LOCKED_FULL"                       # year 卯 consumed first (U10a)
    rec = r["punishments"]["刑 子卯"]
    assert rec["outcome"] == "FULL_FORCE"
    assert rec["acting"] == ["natal.month", "natal.hour"]      # 子 and the free 卯


def test_lock_on_the_single_side_still_eliminates():
    # two 卯, one 子 locked in 子丑: U3/A2 on the locked single branch.
    r = resolve(_field(("乙卯", "丙子", "乙卯", "丁丑")))
    assert r["branch_combinations"]["六合 子丑 [natal.month+natal.hour]"]["lock"] == "LOCKED_FULL"
    assert r["punishments"]["刑 子卯"]["outcome"] == "ELIMINATED"
    assert "刑 子卯" in r["eliminations"]


def test_both_duplicates_locked_eliminates():
    """ch. 7 因解而反得刑沖, the case with no free duplicate left: two 卯, each locked in its own
    卯戌 六合 (Year+Month, Day+Hour), against one FREE 子 on the annual layer. Counting FREE
    instances only (N22), the 子 faces no free 卯, so the 子卯 刑 is ELIMINATED."""
    r = resolve(_field(("乙卯", "丙戌", "丁卯", "戊戌"), (("annual", "丙子"),)))
    assert r["branch_combinations"]["六合 卯戌 [natal.year+natal.month]"]["lock"] == "LOCKED_FULL"
    assert r["branch_combinations"]["六合 卯戌 [natal.day+natal.hour]"]["lock"] == "LOCKED_FULL"
    assert r["branch_tokens"]["annual"] == "FREE"
    rec = r["punishments"]["刑 子卯"]
    assert rec["outcome"] == "ELIMINATED"
    assert rec["rule"].endswith("(every duplicate is locked)")


def test_harm_with_a_locked_duplicate_stays_escalated():
    # 子未 harm: two 未 (one locked in 午未), one 子. Outside E-23's located scope.
    r = resolve(_field(("乙未", "丙子", "甲午", "丁未")))
    out = r["harms"]["害 子未"]["outcome"]
    assert out["token"] == "ESCALATED" and out["pending"] == "E-23-scope"


def test_contested_natal_stems_and_gao_taiwei():
    # 高太尉 庚午·乙酉·甲子·乙亥: two 乙 reach for one 庚, Day 甲 between → no contest.
    r = resolve(_field(("庚午", "乙酉", "甲子", "乙亥")))
    rec = r["stem_combinations"]["五合 乙庚"]
    assert rec["status"] == "COMBINED"
    assert r["stem_tokens"]["natal.hour"] == "FREE"
    # Two equal-standing claimants: 辛 (Year) and 辛 (Day) both adjacent to Month 丙.
    r = resolve(_field(("辛丑", "丙申", "辛卯", "戊子")))
    assert r["stem_combinations"]["五合 丙辛"]["status"] == "CONTESTED"


@pytest.mark.parametrize("pair,month,expected", [
    ("甲己", "未", "MET"), ("甲己", "午", "MET"), ("甲己", "申", "NOT_MET"),
    ("乙庚", "丑", "MET"), ("乙庚", "申", "MET"), ("乙庚", "亥", "NOT_MET"),
    ("丙辛", "辰", "MET"), ("丙辛", "亥", "MET"), ("丙辛", "卯", "NOT_MET"),
    ("丁壬", "未", "MET"), ("丁壬", "寅", "MET"), ("丁壬", "巳", "NOT_MET"),
    ("戊癸", "戌", "MET"), ("戊癸", "巳", "MET"), ("戊癸", "子", "NOT_MET"),
])
def test_stem_gate_all_five_f1_rows(pair, month, expected):
    """N28: all five 三命通會 論十干化氣 rows, primary and secondary months; nothing escalates on L-3."""
    assert rulings.stem_gate(pair, month) == expected


def test_day_master_combination_is_never_transformed_without_a_formation():
    """N28 (6): 丁 Month + 壬 Day (the DM) in a 卯 month meets 丁壬's gate (亥卯未), but a DM combination
    transforms only in a 化格 formation, which the resolver does not derive yet (N27)."""
    rec = resolve(_field(("甲子", "丁卯", "壬辰", "乙未")))["stem_combinations"]["五合 丁壬"]
    assert rec["gate"] == "MET"
    assert rec["state"] == "NEUTRALIZED" and rec["grade"] == "被合"
    assert "annihilation" not in rec


def test_non_dm_combination_in_its_gate_month_transforms():
    # 丁 Year + 壬 Month in a 卯 month (亥卯未), DM 甲 elsewhere, no 丙 anywhere, surface or hidden.
    rec = resolve(_field(("丁丑", "壬卯", "甲午", "乙酉")))["stem_combinations"]["五合 丁壬"]
    assert rec["state"] == "TRANSFORMED" and set(rec["annihilation"]) == {"natal.year", "natal.month"}


def test_hidden_pillar_blocker_escalates():
    # 丁壬 in a 寅 month (secondary): 寅 hides 丙, so 柱有丙字 is open (E-18's clause shape).
    rec = resolve(_field(("丁卯", "壬寅", "甲午", "乙亥")))["stem_combinations"]["五合 丁壬"]
    assert rec["state"]["token"] == "ESCALATED" and rec["state"]["pending"] == "E-18-scope"


def test_non_dm_combination_outside_its_gate_is_neutralized_jiban():
    rec = resolve(_field(("丁卯", "壬子", "甲午", "乙亥")))["stem_combinations"]["五合 丁壬"]
    assert rec["state"] == "NEUTRALIZED" and rec["grade"] == "羈絆"


def test_pillar_blocker_bing_blocks_ding_ren():
    # 丁壬 in its gate month, with 丙 on the Hour stem: 柱有丙字不化.
    rec = resolve(_field(("丁丑", "壬卯", "甲午", "丙子")))["stem_combinations"]["五合 丁壬"]
    assert rec["gate"].startswith("NOT_MET (柱有丙字不化") and rec["state"] == "NEUTRALIZED"


def test_wu_gui_primary_is_the_labelled_emendation():
    # 戊 Year + 癸 Month in a 戌 month: met only through the emended primary 寅午戌. No 己 anywhere.
    rec = resolve(_field(("戊子", "癸戌", "甲申", "乙亥")))["stem_combinations"]["五合 戊癸"]
    assert rec["state"] == "TRANSFORMED"
    assert "寅午戌" in rec["gate_emendation"]


def test_intervener_blocker_between_the_two_stems():
    """N28: 甲己 「有戊字間之則不化」. No natal configuration currently reaches the gate with an
    intervener (only adjacent natal stems resolve COMBINED), so the helper is tested directly."""
    from resolver.resolve import Inst, World, _stem_blocker
    stems = [Inst("natal.year", "natal", "甲", 0), Inst("natal.month", "natal", "戊", 1),
             Inst("natal.day", "natal", "己", 2), Inst("natal.hour", "natal", "乙", 3)]
    out = _stem_blocker(World({}), "甲己", stems, [], [stems[0], stems[2]], "t")
    assert out.startswith("NOT_MET (有戊字間之則不化")
    assert _stem_blocker(World({}), "甲己", stems, [], [stems[2], stems[3]], "t") == "MET"


def test_same_pair_destruction_inside_a_six_harmony_escalates_as_e38():
    # 巳 Year + 申 Month lock in 巳申 六合; 申巳 is also a 破 pair.
    out = resolve(_field(("乙巳", "戊申", "甲午", "丙戌")))["destructions"]["破 申巳"]["outcome"]
    assert out["token"] == "ESCALATED" and out["pending"] == "E-38"


@pytest.mark.parametrize("pair,element,month,expected", [
    ("巳申", "Water", "子", "MET"),        # seasonal and 三合 readings agree
    ("巳申", "Water", "卯", "NOT_MET"),
    ("子丑", "Earth", "未", "MET"),
])
def test_six_harmony_gate(pair, element, month, expected):
    assert rulings.six_harmony_gate(pair, element, month) == expected


def test_six_harmony_gate_escalates_where_the_two_wang_readings_split():
    esc = rulings.six_harmony_gate("巳申", "Water", "申")    # seasonal: Metal month; 三合: Water
    assert isinstance(esc, rulings.Escalation) and esc.pending == "U5-旺月"
