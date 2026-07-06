"""Critical Power model + Mean-Maximal Power curve from running power streams.

MMP: best average power for each duration across all runs.
CP fit: linear work-time model P(t) = CP + W'/t over 2-20 min efforts.
Compares first-half vs second-half date ranges to show improvement.
"""
import numpy as np
import pandas as pd

from .common import load_runs, load_stream

DURATIONS = [5, 15, 30, 60, 120, 180, 300, 480, 600, 900, 1200, 1800, 2700, 3600]
FIT_RANGE = (120, 1200)  # ponytail: 2-20 min is the validated CP window


def mmp_curve(runs):
    """Best mean power per duration across runs -> DataFrame(power, date)."""
    best = {}
    for _, r in runs.iterrows():
        p = load_stream(r["activityId"])["power"].dropna()
        for d in DURATIONS:
            if len(p) < d:
                continue
            v = p.rolling(d).mean().max()
            if pd.notna(v) and v > best.get(d, (0,))[0]:
                best[d] = (v, r["startTimeLocal"])
    return pd.DataFrame(
        {"power": {d: v for d, (v, _) in best.items()},
         "date": {d: t for d, (_, t) in best.items()}}).sort_index()


def fit_cp(mmp):
    """P = CP + W'/t on efforts within FIT_RANGE. Returns (cp_watts, w_prime_joules)."""
    m = mmp[(mmp.index >= FIT_RANGE[0]) & (mmp.index <= FIT_RANGE[1])]
    w_prime, cp = np.polyfit(1 / m.index.values, m["power"].values, 1)
    return cp, w_prime


def main():
    runs = load_runs()
    mmp = mmp_curve(runs)
    cp, w = fit_cp(mmp)

    print("=== Mean-Maximal Power curve (all 25 runs) ===\n")
    print(f"{'duration':>9} {'power':>7}  set on")
    for d, row in mmp.iterrows():
        label = f"{d}s" if d < 60 else f"{d // 60}min"
        print(f"{label:>9} {row['power']:6.0f}W  {row['date']:%Y-%m-%d}")

    print(f"\nCritical Power : {cp:.0f} W  (sustainable ~30-60 min)")
    print(f"W' (anaerobic) : {w / 1000:.1f} kJ "
          f"(~{w / (mmp.loc[300, 'power'] - cp):.0f} s at 5-min power)")

    half = runs["startTimeLocal"].iloc[len(runs) // 2]
    parts = {}
    for label, part in [("first half ", runs[runs["startTimeLocal"] < half]),
                        ("second half", runs[runs["startTimeLocal"] >= half])]:
        m = mmp_curve(part)
        try:
            pcp, pw = fit_cp(m)
            parts[label] = (m, pcp, pw)
            print(f"\n{label} ({part['startTimeLocal'].min():%m-%d} to "
                  f"{part['startTimeLocal'].max():%m-%d}): "
                  f"CP {pcp:.0f} W, W' {pw / 1000:.1f} kJ")
        except Exception:
            print(f"\n{label}: not enough long efforts to fit")

    if len(parts) == 2:
        (_, cp1, _), (_, cp2, _) = parts.values()
        print(f"\nCP change      : {cp2 - cp1:+.0f} W ({(cp2 - cp1) / cp1:+.1%})")
    return mmp, cp, w, parts


if __name__ == "__main__":
    main()
