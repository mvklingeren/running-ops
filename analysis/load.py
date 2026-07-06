"""Training load: TRIMP per run, ATL/CTL/TSB (fitness/fatigue/form),
Foster monotony & strain.

Assumptions: HRmax = highest maxHR observed across the runs (~197);
HRrest = mean daily RHR from data/wellness.csv (~43). Both are printed.
"""
import numpy as np
import pandas as pd

from .common import bar, load_runs, load_stream
from .recovery import load_wellness


def trimp(hr, hr_rest, hr_max):
    """Banister TRIMP from a 1 Hz HR series."""
    hrr = ((hr - hr_rest) / (hr_max - hr_rest)).clip(0, 1)
    return float((hrr * 0.64 * np.exp(1.92 * hrr)).sum() / 60)


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

    print(f"=== Training load (TRIMP; HRrest {hr_rest:.0f}, "
          f"HRmax {hr_max:.0f}) ===\n")
    print(f"{'week ending':>12} {'TRIMP':>6} {'monotony':>9} {'strain':>7}  load")
    weekly = daily.resample("W")
    for wk, g in weekly:
        if g.sum() == 0 or len(g) < 4:  # partial weeks: monotony meaningless
            continue
        mono = g.mean() / g.std() if g.std() > 0 else float("inf")
        strain = g.sum() * mono
        flag = " ⚠" if mono > 2 else ""
        print(f"{wk:%Y-%m-%d} {g.sum():6.0f} {mono:9.2f} {strain:7.0f}  "
              f"{bar(g.sum(), weekly.sum().max(), 20)}{flag}")
    print("\n(monotony >2 = too same-y; strain spikes = overtraining risk)")

    a, c, t = atl.iloc[-1], ctl.iloc[-1], tsb.iloc[-1]
    print(f"\nToday: fitness (CTL) {c:.0f} · fatigue (ATL) {a:.0f} · "
          f"form (TSB) {t:+.0f}")
    verdict = ("fresh — ready to race" if t > 5 else
               "neutral — normal training" if t > -10 else
               "productive overload — building fitness, recover soon" if t > -30
               else "heavy overload — back off")
    print(f"Form verdict: {verdict}")
    print(f"Fitness trend: CTL {ctl.iloc[-28]:.0f} → {c:.0f} over last 4 weeks "
          f"({c - ctl.iloc[-28]:+.0f})")


if __name__ == "__main__":
    main()
