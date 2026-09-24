"""Closed taxonomies (V10 0.1c §2.4, U1) and the small fixed tables the resolver reads.

Nothing here is derived at runtime. Pillars, hidden stems and void come from lunar-python
(derive.py); this file holds only the interaction pools and element relations the stack states.
"""

STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"

STEM_ELEMENT = {
    "甲": "Wood", "乙": "Wood", "丙": "Fire", "丁": "Fire", "戊": "Earth",
    "己": "Earth", "庚": "Metal", "辛": "Metal", "壬": "Water", "癸": "Water",
}

# 克 relation: key controls value.
CONTROLS = {"Wood": "Earth", "Earth": "Water", "Water": "Fire", "Fire": "Metal", "Metal": "Wood"}

# Layers, in the order instances are listed and consumed (U10a: natal Year → Month → Day → Hour
# first; transit instances only where no natal instance is available). The order *among* transit
# layers is not stated anywhere in the stack; it is used here for listing only and every use of it
# as a tie-break is reported as E-3.
NATAL_POSITIONS = ("year", "month", "day", "hour")
TRANSIT_LAYERS = ("decade", "annual", "monthly", "daily")

# §2.4 pools, verbatim.
CLASH = ("子午", "丑未", "寅申", "卯酉", "辰戌", "巳亥")
SIX_HARMONY = {"子丑": "Earth", "寅亥": "Wood", "卯戌": "Fire", "辰酉": "Metal", "巳申": "Water", "午未": "Earth"}
THREE_HARMONY = {"申子辰": "Water", "亥卯未": "Wood", "寅午戌": "Fire", "巳酉丑": "Metal"}
DIRECTIONAL = {"寅卯辰": "Wood", "巳午未": "Fire", "申酉戌": "Metal", "亥子丑": "Water"}
DIRECTIONAL_CARDINAL = {"寅卯辰": "卯", "巳午未": "午", "申酉戌": "酉", "亥子丑": "子"}
SELF_PUNISHMENT = ("午", "酉", "亥", "辰")
PUNISHMENT_SETS = ("寅巳申", "丑戌未")
PUNISHMENT_PAIRS = ("子卯",)
HARM = ("子未", "丑午", "寅巳", "卯辰", "申亥", "酉戌")
DESTRUCTION = ("子酉", "午卯", "寅亥", "申巳", "辰丑", "戌未")
STEM_COMBINATION = {"甲己": "Earth", "乙庚": "Metal", "丙辛": "Water", "丁壬": "Wood", "戊癸": "Fire"}

# R19 (0.1c, provisional): 三會 > 三合 > 六合. Lower number wins a contested branch.
COMBINATION_RANK = {"三會": 0, "三合": 1, "六合": 2}

# ---- Transformation gates (U5) --------------------------------------------------------------
#
# U5's text says "the transformed element's 旺月". The stack never tabulates it, and it is used two
# ways: 0.1e Part One item 6 treats Water's primary gate as 申子辰 (the 三合 months), while the plain
# seasonal reading gives 亥子. Both readings are carried; where they disagree the gate escalates.
SEASONAL_WANG = {"Wood": "寅卯", "Fire": "巳午", "Earth": "辰戌丑未", "Metal": "申酉", "Water": "亥子"}
SANHE_WANG = {"Wood": "亥卯未", "Fire": "寅午戌", "Metal": "巳酉丑", "Water": "申子辰"}

# Stem gates per 三命通會 論十干化氣 (F1), all five rows ruled by the operator 24 Sep 2026 (DECISIONS
# N28). Page text (識典古籍 SK1610): 甲己 「非辰戌丑未月不化，其次午月亦化，有戊字間之則不化」 ·
# 乙庚 「非巳酉丑月不化，其次七月亦化，有甲字間之則不化」 · 丙辛 「非申子辰月不化，其次十月亦化，
# 柱有丁字不化」 · 丁壬 「非亥卯未月不化，其次正月亦化，柱有丙字不化」 · 戊癸 「非丙午戍月不化，
# 其次四月亦化，柱有己字不化」 (Wikisource 卷二; the 識典古籍 chapter page shows 巳, a known 己/已/巳 glyph
# confusion). 戊癸's primary 寅午戌 is a labelled emendation: the text reads 丙午戌 in three editions.
# Blocker kinds: "pillar" = the stem anywhere on a surface stem (柱有X字); "intervener" = the stem
# standing between the two combining stems (有X字間之).
STEM_GATE_KNOWN = {
    "甲己": {"primary": "辰戌丑未", "secondary": "午", "complete": True,
             "blocker": {"kind": "intervener", "stem": "戊"}},
    "乙庚": {"primary": "巳酉丑", "secondary": "申", "complete": True,
             "blocker": {"kind": "intervener", "stem": "甲"}},
    "丙辛": {"primary": "申子辰", "secondary": "亥", "complete": True,
             "blocker": {"kind": "pillar", "stem": "丁"}},
    "丁壬": {"primary": "亥卯未", "secondary": "寅", "complete": True,
             "blocker": {"kind": "pillar", "stem": "丙"}},
    "戊癸": {"primary": "寅午戌", "secondary": "巳", "complete": True,
             "blocker": {"kind": "pillar", "stem": "己"},
             "emendation": "primary 寅午戌 for the text's 丙午戌 (N28)"},
}


def stem_element(stem: str) -> str:
    return STEM_ELEMENT[stem]


def controls(a: str, b: str) -> bool:
    """True if stem a 克s stem b."""
    return CONTROLS[STEM_ELEMENT[a]] == STEM_ELEMENT[b]


def pair_key(pool, a: str, b: str):
    """Return the pool entry naming the unordered pair (a, b), or None."""
    for key in pool:
        if len(key) == 2 and {key[0], key[1]} == {a, b} and (a != b):
            return key
    return None
