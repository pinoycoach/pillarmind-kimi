"""Pipeline tests: the real derive → resolve path, from a birth datetime."""
import ast
import datetime as dt
import pathlib
import socket

import pytest

from resolver import HardStop, resolve_chart

PKG = pathlib.Path(__file__).resolve().parent.parent / "resolver"
FORBIDDEN = {"socket", "urllib", "http", "requests", "httpx", "aiohttp", "openai", "anthropic"}


def test_no_network_or_llm_imports_in_the_resolver():
    for path in PKG.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for n in names:
                assert n.split(".")[0] not in FORBIDDEN, f"{path.name} imports {n}"


def test_full_run_opens_no_socket(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    r = resolve_chart(dt.datetime(1990, 5, 17, 14, 30), "Manila", "female",
                      as_of=dt.datetime(2026, 8, 15, 12, 0), layers=("decade", "annual", "monthly"))
    assert r["pillars"]["natal.day"]["stem"] + r["pillars"]["natal.day"]["branch"] == "壬午"


def test_deterministic():
    args = (dt.datetime(1990, 5, 17, 14, 30), "Manila", "female")
    kw = dict(as_of=dt.datetime(2026, 8, 15, 12, 0), layers=("decade", "annual", "monthly"))
    assert resolve_chart(*args, **kw) == resolve_chart(*args, **kw)


def test_void_is_enumerated_from_the_xun():
    r = resolve_chart(dt.datetime(1990, 5, 17, 14, 30), "Manila", "female")
    assert r["void"]["xun"] == "甲戌旬"
    assert r["void"]["stream"][0] == "甲戌" and r["void"]["stream"][-1] == "癸未"
    assert r["void"]["pair"] == ["申", "酉"]


def test_zi_hour_boundary_is_a_hard_stop():
    with pytest.raises(HardStop, match="子時"):
        resolve_chart(dt.datetime(1990, 5, 17, 23, 30), "Manila", "male")


def test_dst_that_changes_a_pillar_is_a_hard_stop():
    # tzdata: Manila observed DST in mid-1990. 13:30 clock = 12:30 standard: 未 hour vs 午 hour.
    with pytest.raises(HardStop, match="daylight saving"):
        resolve_chart(dt.datetime(1990, 6, 1, 13, 30), "Manila", "male")


@pytest.mark.parametrize("date,offset_hours", [
    (dt.datetime(1977, 5, 1, 12), 9),     # DST: Proclamations 1629 / 1641, 28 Mar–21 Sep 1977
    (dt.datetime(1978, 5, 31, 12), 8),    # no DST in 1978 (no proclamation; DECISIONS N19)
    (dt.datetime(1990, 6, 15, 12), 9),    # DST per IANA; primary source not located
])
def test_manila_offsets_in_installed_tzdata(date, offset_hours):
    """Regression guard for the DST hard stop, which is only as good as the installed tzdata
    (requirements.txt pins tzdata>=2026.4)."""
    from zoneinfo import ZoneInfo
    assert date.replace(tzinfo=ZoneInfo("Asia/Manila")).utcoffset() == dt.timedelta(hours=offset_hours)


def test_unknown_city_is_refused():
    with pytest.raises(ValueError, match="Unknown city"):
        resolve_chart(dt.datetime(1990, 5, 17, 14, 30), "Atlantis", "male")


TEST_DATE = dt.datetime(1990, 5, 17)       # not a real person's birth; decade boundary 6 Jan–27 Apr 2024


def test_hour_unknown_omits_the_hour_and_assumes_no_time():
    r = resolve_chart(TEST_DATE, "Manila", "female", as_of=dt.datetime(2026, 8, 15, 12),
                      layers=("decade", "annual", "monthly"), hour_known=False)
    assert "natal.hour" not in r["pillars"]
    assert r["input"]["birth"] == "1990-05-17" and r["input"]["hour_known"] is False
    assert r["input_integrity"]["corroboration"]["five_rat"]["pass"] is None
    assert any("子時" in n for n in r["input_integrity"]["notes"])        # 23:00–24:00 caveat


def test_hour_unknown_reports_the_decade_boundary_as_a_range():
    r = resolve_chart(TEST_DATE, "Manila", "female", as_of=dt.datetime(2026, 8, 15, 12),
                      layers=("decade",), hour_known=False)
    first = r["decade"]["first_decade_starts"]
    assert set(first) == {"earliest", "latest"} and first["earliest"] < first["latest"]
    assert r["decade"]["in_force"]["pillar"] == "丁丑"                    # well after the range
    assert set(r["decade"]["in_force"]["ends"]) == {"earliest", "latest"}


def test_hour_unknown_inside_the_boundary_range_leaves_the_decade_undetermined():
    r = resolve_chart(TEST_DATE, "Manila", "female", as_of=dt.datetime(2024, 3, 1, 12),
                      layers=("decade",), hour_known=False)
    assert r["decade"]["in_force"]["token"] == "UNDETERMINED"
    assert set(r["decade"]["in_force"]["candidates"]) == {"戊寅", "丁丑"}
    assert "decade" not in r["pillars"]


def test_hour_unknown_on_a_jie_date_is_a_hard_stop():
    # 立春 2026 falls during 4 Feb: year and month pillars depend on the hour.
    with pytest.raises(HardStop, match="hour"):
        resolve_chart(dt.datetime(2026, 2, 4), "Manila", "male", hour_known=False)


def test_transit_layers_need_a_date():
    r = resolve_chart(dt.datetime(1990, 5, 17, 14, 30), "Manila", "male")
    assert set(r["pillars"]) == {"natal.year", "natal.month", "natal.day", "natal.hour"}
