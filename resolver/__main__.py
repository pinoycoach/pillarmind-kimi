"""CLI. Output is written to a UTF-8 file (the Windows console mangles Chinese text).

    python -m resolver --birth "1990-05-17 14:30" --city Manila --sex female \
        --as-of "2026-08-15 12:00" --layers decade annual monthly --out map.json
"""
import argparse
import datetime as dt
import pathlib
import sys

from . import HardStop, resolve_chart, to_json


def _dt(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s)


if __name__ == "__main__":
    p = argparse.ArgumentParser(prog="resolver")
    p.add_argument("--birth", required=True, type=_dt,
                   help="local clock time, 'YYYY-MM-DD HH:MM' (or 'YYYY-MM-DD' with --hour-unknown)")
    p.add_argument("--hour-unknown", action="store_true",
                   help="derive year/month/day only; omit the hour pillar; decade boundary as a range")
    p.add_argument("--city", required=True)
    p.add_argument("--sex", required=True, choices=["male", "female"])
    p.add_argument("--as-of", type=_dt, default=None)
    p.add_argument("--layers", nargs="*", default=["decade", "annual"],
                   choices=["decade", "annual", "monthly", "daily"])
    p.add_argument("--out", type=pathlib.Path, default=pathlib.Path("resolved_field_map.json"))
    a = p.parse_args()
    try:
        result = resolve_chart(a.birth, a.city, a.sex, as_of=a.as_of, layers=tuple(a.layers),
                               hour_known=not a.hour_unknown)
    except HardStop as stop:
        sys.exit(f"HARD STOP: {stop}")
    a.out.write_text(to_json(result), encoding="utf-8")
    print(f"Written to {a.out}")
