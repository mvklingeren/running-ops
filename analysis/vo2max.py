"""Effective VO2max (Runalyze-style, from HR-vs-pace) + race prognosis.

Per run: Daniels/Gilbert oxygen cost of the pace, divided by %VO2max
implied by avg HR (Swain). Race times solved from the Daniels model.
Compared against Garmin's own vO2MaxValue.
"""
import math

import pandas as pd

from .common import fmt_pace, load_runs

RACES = [("5k", 5000), ("10k", 10000), ("half", 21097.5), ("marathon", 42195)]


def vo2_cost(v):
    """Oxygen cost (ml/kg/min) of running at v m/min (Daniels/Gilbert)."""
    return -4.6 + 0.182258 * v + 0.000104 * v * v


def pct_at_duration(t_min):
    """Fraction of VO2max sustainable for t minutes (Daniels)."""
    return (0.8 + 0.1894393 * math.exp(-0.012778 * t_min)
            + 0.2989558 * math.exp(-0.1932605 * t_min))


def effective_vo2max(runs, hr_max):
    v = runs["distance"] / (runs["duration"] / 60)  # m/min
    pct = ((runs["averageHR"] / hr_max) - 0.37) / 0.64  # Swain %VO2max
    return vo2_cost(v) / pct


def predict(vdot, meters):
    """Race time (min) for a distance at a given VDOT, by bisection."""
    lo, hi = 5.0, 600.0
    for _ in range(60):
        mid = (lo + hi) / 2
        need = vo2_cost(meters / mid) - vdot * pct_at_duration(mid)
        lo, hi = (lo, mid) if need < 0 else (mid, hi)
    return (lo + hi) / 2


def fmt_time(minutes):
    s = int(round(minutes * 60))
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def main():
    runs = load_runs()
    hr_max = runs["maxHR"].max()
    runs = runs.assign(evo2=effective_vo2max(runs, hr_max))

    print("=== Effective VO2max (ours vs Garmin) ===\n")
    print(f"{'date':>10} {'km':>5} {'pace':>8} {'HR':>4} {'eff':>5} {'garmin':>7}")
    for _, r in runs.iterrows():
        garmin = f"{r['vO2MaxValue']:.0f}" if pd.notna(r["vO2MaxValue"]) else "-"
        print(f"{r['startTimeLocal']:%m-%d} {r['km']:9.1f} "
              f"{fmt_pace(r['pace_s']):>8} {r['averageHR']:4.0f} "
              f"{r['evo2']:5.1f} {garmin:>7}")

    recent = runs.tail(10)
    vdot = recent["evo2"].median()
    garmin_now = runs["vO2MaxValue"].dropna().iloc[-1] \
        if runs["vO2MaxValue"].notna().any() else None
    first = runs.head(10)["evo2"].median()
    print(f"\nEffective VO2max: {vdot:.1f} (median of last 10 runs; "
          f"first 10: {first:.1f}, {vdot - first:+.1f})")
    if garmin_now:
        print(f"Garmin says     : {garmin_now:.0f}")

    print("\nRace prognosis (from effective VO2max):")
    for name, meters in RACES:
        t = predict(vdot, meters)
        print(f"  {name:9} {fmt_time(t):>8}  ({fmt_pace(t * 60 / (meters / 1000))})")
    print("\n(marathon/half assume the endurance is there — with current "
          "long runs treat those as upper bounds)")


if __name__ == "__main__":
    main()
