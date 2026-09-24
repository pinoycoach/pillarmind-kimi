"""Derivation: birth datetime + city → the field. lunar-python is the only engine (V10 §2.1, U14).

No network access. City → timezone uses a fixed table plus the bundled IANA database (tzdata),
and only to detect clock offsets the stack has no intake rule for; the clock time itself is fed to
lunar-python unchanged.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from lunar_python import Solar
from lunar_python.util import LunarUtil

from .tables import BRANCHES, STEMS, TEN_GOD_TRADITIONAL, TRANSIT_LAYERS

LUNAR_SECT_DAY = 2   # lunar-python default: 23:00–24:00 keeps the current day pillar
LUNAR_SECT_YUN = 1   # lunar-python default 起運 method; declared, not a stack ruling

CITIES = {
    "manila": "Asia/Manila", "quezon city": "Asia/Manila", "makati": "Asia/Manila",
    "cebu": "Asia/Manila", "cebu city": "Asia/Manila", "davao": "Asia/Manila",
    "davao city": "Asia/Manila", "baguio": "Asia/Manila", "iloilo": "Asia/Manila",
    "maasin": "Asia/Manila", "maasin city": "Asia/Manila",
    "singapore": "Asia/Singapore", "hong kong": "Asia/Hong_Kong", "taipei": "Asia/Taipei",
    "beijing": "Asia/Shanghai", "shanghai": "Asia/Shanghai", "kuala lumpur": "Asia/Kuala_Lumpur",
    "jakarta": "Asia/Jakarta", "bangkok": "Asia/Bangkok", "tokyo": "Asia/Tokyo",
    "seoul": "Asia/Seoul", "sydney": "Australia/Sydney", "london": "Europe/London",
    "new york": "America/New_York", "los angeles": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles", "toronto": "America/Toronto", "dubai": "Asia/Dubai",
}


class HardStop(Exception):
    """0.1d Patch 6: a pillar discrepancy halts the run. Not an escalation."""


@dataclass
class Pillar:
    layer: str            # natal | decade | annual | monthly | daily
    position: str         # year/month/day/hour for natal; the layer name otherwise
    stem: str
    branch: str
    hidden: list = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"natal.{self.position}" if self.layer == "natal" else self.layer


@dataclass
class Field:
    pillars: list                     # natal Year, Month, Day, Hour, then transit layers present
    day_master: str
    void: dict
    corroboration: dict
    input_record: dict
    decade_record: dict | None = None
    notes: list = field(default_factory=list)


def resolve_zone(city: str) -> str:
    key = city.strip().lower()
    if key in CITIES:
        return CITIES[key]
    try:                                   # an IANA name such as "Asia/Manila" is accepted as-is
        ZoneInfo(city.strip())
        return city.strip()
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(f"Unknown city {city!r}. Pass an IANA zone name (e.g. 'Asia/Manila') "
                         f"or one of: {', '.join(sorted(CITIES))}") from None


def _eight_char(t: dt.datetime):
    ec = Solar.fromYmdHms(t.year, t.month, t.day, t.hour, t.minute, t.second).getLunar().getEightChar()
    ec.setSect(LUNAR_SECT_DAY)
    return ec


# lunar-python computes its 節 in Beijing time (UTC+8).
BEIJING = dt.timezone(dt.timedelta(hours=8))


def _beijing(t_local: dt.datetime, zone: str) -> dt.datetime:
    """The same absolute moment as a local clock time at the birthplace, written as Beijing time."""
    return t_local.replace(tzinfo=ZoneInfo(zone)).astimezone(BEIJING).replace(tzinfo=None)


def _local_from_beijing(t_bj: dt.datetime, zone: str) -> dt.datetime:
    return t_bj.replace(tzinfo=BEIJING).astimezone(ZoneInfo(zone)).replace(tzinfo=None)


def _pillars_at(t: dt.datetime, zone: str, day_hour_time: dt.datetime | None = None) -> tuple:
    """N45 (operator ruling, extending N19): month and year pillars are decided by comparing the
    birth moment with the 節 moment in absolute time, whatever the birthplace's zone; day and hour
    pillars come from local time at the birthplace (day_hour_time, if given, else t)."""
    ym = _eight_char(_beijing(t, zone))
    dh = _eight_char(day_hour_time or t)
    return ym.getYear(), ym.getMonth(), dh.getDay(), dh.getTime()


def _hidden(branch: str) -> list:
    return list(LunarUtil.ZHI_HIDE_GAN[branch])


def ten_god(day_master: str, stem: str) -> str:
    """Ten god of a stem relative to the Day Master, in traditional characters (N40)."""
    label = LunarUtil.SHI_SHEN[day_master + stem]
    if label not in TEN_GOD_TRADITIONAL:
        raise ValueError(f"lunar-python ten-god label {label!r} has no traditional mapping")
    return TEN_GOD_TRADITIONAL[label]


def _check_input_integrity(birth: dt.datetime, zone: str) -> list:
    """Stops for the two clock conventions the stack has no ruling on."""
    notes = []
    # 子時 day boundary. lunar-python sect 1 rolls the day at 23:00; sect 2 at 24:00.
    ec1 = Solar.fromYmdHms(birth.year, birth.month, birth.day, birth.hour, birth.minute, birth.second).getLunar().getEightChar()
    ec1.setSect(1)
    ec2 = _eight_char(birth)
    if ec1.getDay() != ec2.getDay():
        raise HardStop(
            f"Pillar discrepancy detected that cannot be resolved by data entry review. Birth time "
            f"{birth:%H:%M} falls in 23:00–24:00; the day pillar is {ec2.getDay()} or {ec1.getDay()} "
            f"depending on the 子時 convention, and the stack rules neither. Human verification "
            f"required before this reading can proceed.")
    # Daylight saving. The clock time is fed as given; if removing the DST offset changes any
    # pillar, the reading cannot proceed (September audit §3: no birth-time offset intake rule).
    local = birth.replace(tzinfo=ZoneInfo(zone))
    dst = local.dst()
    if dst:
        # The absolute moment is fixed by tzdata's offset; DST can only move the local day/hour.
        clock = _pillars_at(birth, zone)
        standard = _pillars_at(birth, zone, day_hour_time=birth - dst)
        if standard != clock:
            raise HardStop(
                f"Pillar discrepancy detected that cannot be resolved by data entry review. "
                f"{zone} observed daylight saving on {birth:%Y-%m-%d}; clock time gives "
                f"{'·'.join(clock)}, standard time gives {'·'.join(standard)}. "
                f"The stack has no birth-time offset intake rule. Human verification required.")
        notes.append(f"DST in force at birth ({zone}); pillars identical with and without it. BOUNDED.")
    notes.append(TIME_NOTE)
    return notes


TIME_NOTE = ("Year and month pillars: the birth moment compared with the 節 in absolute time (N45). Day and "
             "hour pillars: local clock time at the birthplace, with no longitude / true-solar-time "
             "correction (no intake rule in the stack).")


def _void(day_pillar: str, ec) -> dict:
    """0.1d Patch 6: list the ten pillars of the Day Pillar's 旬 by name before declaring void."""
    jia_zi = list(LunarUtil.JIA_ZI)
    i = jia_zi.index(day_pillar)
    start = i - i % 10
    stream = jia_zi[start:start + 10]
    covered = {p[1] for p in stream}
    pair = [b for b in BRANCHES if b not in covered]
    engine_pair = list(ec.getDayXunKong())
    if pair != engine_pair:
        raise HardStop(f"Void enumeration {pair} disagrees with lunar-python {engine_pair}. "
                       f"Human verification required.")
    return {"xun": stream[0] + "旬", "stream": stream, "pair": pair}


def _corroborate(y: str, m: str, d: str, h: str | None) -> dict:
    """五虎遁 and 五鼠遁 internal consistency (0.1e P-7). Not calendrical verification."""
    ys, ds = STEMS.index(y[0]), STEMS.index(d[0])
    mb = BRANCHES.index(m[1])
    month_stem = STEMS[((ys % 5) * 2 + 2 + (mb - 2) % 12) % 10]
    out = {"five_tiger": {"expected_month_stem": month_stem, "actual": m[0], "pass": month_stem == m[0]}}
    if h is None:
        out["five_rat"] = {"pass": None, "note": "not run: hour unknown"}
    else:
        hour_stem = STEMS[((ds % 5) * 2 + BRANCHES.index(h[1])) % 10]
        out["five_rat"] = {"expected_hour_stem": hour_stem, "actual": h[0], "pass": hour_stem == h[0]}
    if out["five_tiger"]["pass"] is False or out["five_rat"]["pass"] is False:
        raise HardStop(f"Five-Tiger / Five-Rat check failed on engine output: {out}")
    return out


def _add_years(t: dt.datetime, n: int) -> dt.datetime:
    try:
        return t.replace(year=t.year + n)
    except ValueError:                      # 29 Feb
        return t.replace(year=t.year + n, day=28)


def _first_start(ec, sex: str, zone: str):
    """ec is built on the Beijing-time moment (N45), so the 起運 distance to the 節 is absolute;
    the start it returns is Beijing time and is converted back to the birthplace's local time."""
    yun = ec.getYun({"male": 1, "female": 0}[sex], LUNAR_SECT_YUN)
    s = yun.getStartSolar()
    start_bj = dt.datetime(s.getYear(), s.getMonth(), s.getDay(), s.getHour(), s.getMinute(), s.getSecond())
    return _local_from_beijing(start_bj, zone), yun


def _decade_index(first_start: dt.datetime, as_of: dt.datetime) -> int:
    """1-based index of the 大運 in force at as_of; 0 before the first one starts."""
    if as_of < first_start:
        return 0
    index = 1 + (as_of.year - first_start.year) // 10
    while index > 1 and as_of < _add_years(first_start, 10 * (index - 1)):
        index -= 1
    while as_of >= _add_years(first_start, 10 * index):
        index += 1
    return index


def _span(values: list):
    """One value, or an earliest/latest range when the unknown hour moves it."""
    iso = [v.isoformat(sep=" ") if isinstance(v, dt.datetime) else v for v in values]
    return iso[0] if len(set(iso)) == 1 else {"earliest": min(iso), "latest": max(iso)}


def _decade_at(ecs: list, sex: str, as_of: dt.datetime, zone: str):
    """ecs holds one EightChar, or two (earliest and latest possible birth moment) when the hour
    is unknown; the 起運 start then moves with the hour and is reported as a range."""
    starts, yuns = zip(*(_first_start(ec, sex, zone) for ec in ecs))
    yun = yuns[0]
    record = {
        "direction": "forward" if yun.isForward() else "backward",
        "first_decade_starts": _span(list(starts)),
        "lunar_python_yun_sect": LUNAR_SECT_YUN,
    }
    indices = [_decade_index(s, as_of) for s in starts]
    pillars = [yun.getDaYun(i + 1)[i].getGanZhi() if i else None for i in indices]
    if len(set(indices)) > 1:
        record["in_force"] = {
            "token": "UNDETERMINED", "candidates": pillars,
            "note": "as_of falls inside the decade-boundary range; only the birth hour decides"}
        record["note"] = "decade layer omitted: the pillar in force depends on the unknown birth hour"
        return None, record
    index = indices[0]
    if index == 0:
        record["in_force"] = None
        record["note"] = "as_of precedes the first 大運; no decade layer"
        return None, record
    begin = [_add_years(s, 10 * (index - 1)) for s in starts]
    record["in_force"] = {"pillar": pillars[0], "index": index,
                          "starts": _span(begin),
                          "ends": _span([_add_years(b, 10) for b in begin]),
                          "start_age": _span([y.getDaYun(index + 1)[index].getStartAge() for y in yuns])}
    return pillars[0], record


def _hour_unknown_bounds(date: dt.date, zone: str):
    """Hour-unknown mode: the earliest and latest possible birth moments on the date. Year, month
    and day must be the same at both, or the unknown hour decides a pillar and the run stops."""
    lo = dt.datetime(date.year, date.month, date.day, 0, 0, 0)
    hi = dt.datetime(date.year, date.month, date.day, 23, 59, 59)
    p_lo, p_hi = _pillars_at(lo, zone)[:3], _pillars_at(hi, zone)[:3]
    if p_lo != p_hi:
        raise HardStop(
            f"Pillar discrepancy detected that cannot be resolved by data entry review. With the hour "
            f"unknown, {date} gives {'·'.join(p_lo)} at 00:00 and {'·'.join(p_hi)} at 23:59 (a 節 or "
            f"立春 falls on this date). Human verification required.")
    notes = ["Hour unknown: the hour pillar is omitted and every hour-dependent quantity is reported "
             "as a range. No birth time is assumed."]
    ec1 = Solar.fromYmdHms(date.year, date.month, date.day, 23, 30, 0).getLunar().getEightChar()
    ec1.setSect(1)
    if ec1.getDay() != p_lo[2]:
        notes.append(f"Day pillar {p_lo[2]} holds for a birth before 23:00. A 23:00–24:00 birth gives "
                     f"{ec1.getDay()} under the other 子時 convention (lunar-python sect 1); the stack "
                     f"rules neither. Not excluded, because the hour is unknown.")
    for t in (lo, hi):
        dst = t.replace(tzinfo=ZoneInfo(zone)).dst()
        if dst and _pillars_at(t, zone, day_hour_time=t - dst)[:3] != p_lo:
            notes.append(f"{zone} clock offset of {dst} (tzdata) at {t:%H:%M}: at standard time a birth "
                         f"near midnight falls on a different day "
                         f"({_pillars_at(t, zone, day_hour_time=t - dst)[2]}). "
                         f"Not excluded, because the hour is unknown.")
            break
    notes.append(TIME_NOTE)
    return lo, hi, notes


def derive(birth: dt.datetime, city: str, sex: str, as_of: dt.datetime | None = None,
           layers: tuple = ("decade", "annual"), hour_known: bool = True) -> Field:
    """Birth datetime (local clock time) + city → Field. Transit layers need as_of.

    hour_known=False: only the birth date is used. Year, month and day pillars are derived, the
    hour pillar is omitted, and the decade boundary is reported as a range."""
    if sex not in ("male", "female"):
        raise ValueError("sex must be 'male' or 'female' (required for 大運 direction)")
    unknown = set(layers) - set(TRANSIT_LAYERS)
    if unknown:
        raise ValueError(f"Unknown layers: {sorted(unknown)}")
    if layers and as_of is None:
        raise ValueError("Transit layers require as_of")
    zone = resolve_zone(city)

    if hour_known:
        notes = _check_input_integrity(birth, zone)
        ec = _eight_char(birth)                                   # local: day pillar and void
        yun_ecs = [_eight_char(_beijing(birth, zone))]            # absolute: 起運 distance to the 節
        y, m, d, h = _pillars_at(birth, zone)
    else:
        lo, hi, notes = _hour_unknown_bounds(birth.date(), zone)
        ec = _eight_char(lo)
        yun_ecs = [_eight_char(_beijing(lo, zone)), _eight_char(_beijing(hi, zone))]
        y, m, d, _ = _pillars_at(lo, zone)
        h = None
    positions = [("year", y), ("month", m), ("day", d)] + ([("hour", h)] if h else [])
    pillars = [Pillar("natal", pos, p[0], p[1], _hidden(p[1])) for pos, p in positions]

    decade_record = None
    if as_of is not None and layers:
        # as_of is read as a local time at the birthplace; annual and monthly by the same N45 rule.
        a_year, a_month, a_day, _ = _pillars_at(as_of, zone)
        transit = {"annual": a_year, "monthly": a_month, "daily": a_day}
        for layer in TRANSIT_LAYERS:
            if layer not in layers:
                continue
            if layer == "decade":
                gz, decade_record = _decade_at(yun_ecs, sex, as_of, zone)
                if gz is None:
                    notes.append(decade_record["note"])
                    continue
            else:
                gz = transit[layer]
            pillars.append(Pillar(layer, layer, gz[0], gz[1], _hidden(gz[1])))

    return Field(
        pillars=pillars,
        day_master=d[0],
        void=_void(d, ec),
        corroboration=_corroborate(y, m, d, h),
        input_record={"birth": birth.isoformat(sep=" ") if hour_known else birth.date().isoformat(),
                      "hour_known": hour_known, "city": city, "zone": zone, "sex": sex,
                      "as_of": as_of.isoformat(sep=" ") if as_of else None, "layers": list(layers),
                      "lunar_python_day_sect": LUNAR_SECT_DAY},
        decade_record=decade_record,
        notes=notes,
    )
