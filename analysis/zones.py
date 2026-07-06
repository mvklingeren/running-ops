"""Power & HR distribution: time-in-zone and histograms across all runs.

Zones are %CP (Stryd-style): Z1 easy <80, Z2 80-90, Z3 90-100,
Z4 100-115, Z5 >115.
"""
import pandas as pd

from .common import bar, load_runs, load_stream
from .cp import fit_cp, mmp_curve

ZONES = [(0, 0.80, "Z1 easy"), (0.80, 0.90, "Z2 moderate"),
         (0.90, 1.00, "Z3 threshold"), (1.00, 1.15, "Z4 interval"),
         (1.15, 99, "Z5 max")]


def all_power(runs):
    return pd.concat([load_stream(r["activityId"])[["power", "hr"]]
                      for _, r in runs.iterrows()], ignore_index=True).dropna()


def main():
    runs = load_runs()
    cp, _ = fit_cp(mmp_curve(runs))
    s = all_power(runs)
    total = len(s)

    print(f"=== Time in power zones, {len(runs)} runs "
          f"({total / 3600:.1f} h recorded, CP {cp:.0f} W) ===\n")
    for lo, hi, name in ZONES:
        t = ((s["power"] >= lo * cp) & (s["power"] < hi * cp)).sum()
        rng = f"{lo * cp:.0f}-{hi * cp:.0f}W" if hi < 99 else f">{lo * cp:.0f}W"
        print(f"{name:13} {rng:>10} {t / 3600:5.1f}h {t / total:5.0%}  "
              f"{bar(t, total)}")

    half = runs["startTimeLocal"].iloc[len(runs) // 2]
    print("\nHard time (>=Z3) by period:")
    for label, part in [("first half ", runs[runs["startTimeLocal"] < half]),
                        ("second half", runs[runs["startTimeLocal"] >= half])]:
        sp = all_power(part)
        hard = (sp["power"] >= 0.9 * cp).mean()
        print(f"  {label}: {hard:.1%} of running time")

    print(f"\nMedian power : {s['power'].median():.0f} W "
          f"({s['power'].median() / cp:.0%} of CP)")
    print(f"Median HR    : {s['hr'].median():.0f} bpm")


if __name__ == "__main__":
    main()
