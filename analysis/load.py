"""Training load: TRIMP + power-based PSS per run, ATL/CTL/TSB
(fitness/fatigue/form), Foster monotony & strain.

Assumptions: HRmax = highest maxHR observed across the runs (~197);
HRrest = mean daily RHR from data/wellness.csv (~43). Both are printed.

--race YYYY-MM-DD adds a race-day TSB projection (rest/maintenance/current).
"""
import sys

import numpy as np
import pandas as pd

from .common import bar, load_runs, load_stream
from .cp import fit_cp, mmp_curve
from .recovery import load_wellness


def trimp(hr, hr_rest, hr_max):
    """Banister TRIMP from a 1 Hz HR series."""
    hrr = ((hr - hr_rest) / (hr_max - hr_rest)).clip(0, 1)
    return float((hrr * 0.64 * np.exp(1.92 * hrr)).sum() / 60)


def np_power(p):
    """Normalized power from 1 Hz watts: 30 s rolling mean → mean of 4th powers → 4th root."""
    return float(((p.rolling(30, min_periods=1).mean() ** 4).mean()) ** 0.25)


def pss(p, cp):
    """Power stress score, rTSS-style: 100 = one hour at CP. NaN without power."""
    p = p.dropna()
    if not len(p):
        return float("nan")
    return 100 * len(p) * (np_power(p) / cp) ** 2 / 3600


def form_verdict(tsb):
    return ("fresh — ready to race" if tsb > 5 else
            "neutral — normal training" if tsb > -10 else
            "productive overload — building fitness, recover soon" if tsb > -30
            else "heavy overload — back off")


def project_tsb(daily, until, factor):
    """TSB on `until` if daily load from tomorrow on = factor × today's CTL."""
    _, ctl, tsb = pmc(daily)
    future = pd.date_range(daily.index[-1] + pd.Timedelta(days=1), until)
    if not len(future):
        return tsb.iloc[-1]
    ext = pd.concat([daily, pd.Series(ctl.iloc[-1] * factor, index=future)])
    return pmc(ext)[2].iloc[-1]


def daily_load():
    """Daily TRIMP series (0 on rest days) + the HR anchors used."""
    runs = load_runs()
    w = load_wellness()
    hr_rest, hr_max = w["rhr"].mean(), runs["maxHR"].max()
    per_day = {}
    for _, r in runs.iterrows():
        hr = load_stream(r["activityId"])["hr"].dropna()
        d = r["startTimeLocal"].normalize()
        per_day[d] = per_day.get(d, 0) + trimp(hr, hr_rest, hr_max)
    idx = pd.date_range(min(per_day), max(max(per_day), w.index.max()), freq="D")
    return pd.Series(per_day).reindex(idx, fill_value=0), hr_rest, hr_max


def pmc(daily):
    """Classic performance-management chart: ATL 7d, CTL 42d, TSB."""
    atl = daily.ewm(alpha=1 / 7, adjust=False).mean()
    ctl = daily.ewm(alpha=1 / 42, adjust=False).mean()
    return atl, ctl, ctl - atl


def main():
    daily, hr_rest, hr_max = daily_load()
    atl, ctl, tsb = pmc(daily)

    runs = load_runs()
    cpv, _ = fit_cp(mmp_curve(runs))
    per_day = {}
    for _, r in runs.iterrows():
        d = r["startTimeLocal"].normalize()
        v = pss(load_stream(r["activityId"])["power"], cpv)
        if pd.notna(v):
            per_day[d] = per_day.get(d, 0) + v
    pss_daily = pd.Series(per_day).reindex(daily.index, fill_value=0)

    print(f"=== Training load (TRIMP; HRrest {hr_rest:.0f}, "
          f"HRmax {hr_max:.0f}; PSS anchored on CP {cpv:.0f} W) ===\n")
    weekly = daily.resample("W")
    rows = [(wk, g) for wk, g in weekly
            if g.sum() > 0 and len(g) >= 4]  # partial weeks: monotony meaningless
    shown = rows[-26:]
    if len(shown) < len(rows):
        print(f"(last {len(shown)} of {len(rows)} training weeks)")
    print(f"{'week ending':>12} {'TRIMP':>6} {'PSS':>6} {'monotony':>9} "
          f"{'strain':>7}  load")
    for wk, g in shown:
        mono = g.mean() / g.std() if g.std() > 0 else float("inf")
        strain = g.sum() * mono
        flag = " ⚠" if mono > 2 else ""
        print(f"{wk:%Y-%m-%d} {g.sum():6.0f} {pss_daily[g.index].sum():6.0f} "
              f"{mono:9.2f} {strain:7.0f}  "
              f"{bar(g.sum(), weekly.sum().max(), 20)}{flag}")
    print("\n(PSS = power-based load, 100 = 1 h at CP — diverges from TRIMP "
          "in heat and hard intervals;\n monotony >2 = too same-y; "
          "strain spikes = overtraining risk)")

    a, c, t = atl.iloc[-1], ctl.iloc[-1], tsb.iloc[-1]
    print(f"\nToday: fitness (CTL) {c:.0f} · fatigue (ATL) {a:.0f} · "
          f"form (TSB) {t:+.0f}")
    print(f"Form verdict: {form_verdict(t)}")
    print(f"Fitness trend: CTL {ctl.iloc[-28]:.0f} → {c:.0f} over last 4 weeks "
          f"({c - ctl.iloc[-28]:+.0f})")

    if "--race" in sys.argv:
        race = pd.Timestamp(sys.argv[sys.argv.index("--race") + 1])
        days = (race - daily.index[-1]).days
        print(f"\nRace {race:%Y-%m-%d} in {days} days — projected race-day TSB "
              "(target +5..+15):")
        for label, f in [("full rest", 0.0), ("maintenance (70% CTL)", 0.7),
                         ("current load (100% CTL)", 1.0)]:
            print(f"  {label:24} TSB {project_tsb(daily, race, f):+.0f}")


if __name__ == "__main__":
    main()
