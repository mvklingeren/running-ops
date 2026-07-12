"""Power & HR distribution: time-in-zone and histograms across all runs.

Zones are %CP (Stryd-style): Z1 easy <80, Z2 80-90, Z3 90-100,
Z4 100-115, Z5 >115.
"""
import pandas as pd

from .common import bar, load_runs, load_stream, recent_prior
from .cp import fit_cp, mmp_curve

ZONES = [(0, 0.80, "Z1 easy"), (0.80, 0.90, "Z2 moderate"),
         (0.90, 1.00, "Z3 threshold"), (1.00, 1.15, "Z4 interval"),
         (1.15, 99, "Z5 max")]


def all_power(runs):
    return pd.concat([load_stream(r["activityId"])[["power", "hr"]]
                      for _, r in runs.iterrows()], ignore_index=True).dropna()


def time_in_zones(power, cp):
    """Seconds in each ZONES bucket (1 sample = 1 s, lower bound inclusive)."""
    return [((power >= lo * cp) & (power < hi * cp)).sum()
            for lo, hi, _ in ZONES]


def weekly_zones(runs, cp):
    """Seconds per zone per week -> DataFrame (rows = week end, cols = zones)."""
    rows = {}
    for _, r in runs.iterrows():
        p = load_stream(r["activityId"])["power"].dropna()
        wk = r["startTimeLocal"].to_period("W").end_time.normalize()
        t = time_in_zones(p, cp)
        rows[wk] = [a + b for a, b in zip(rows.get(wk, [0] * len(ZONES)), t)]
    return pd.DataFrame(rows, index=[n for *_, n in ZONES]).T.sort_index()


def main():
    runs = load_runs()
    cp, _ = fit_cp(mmp_curve(runs))
    s = all_power(runs)
    total = len(s)

    print(f"=== Time in power zones, {len(runs)} runs "
          f"({total / 3600:.1f} h recorded, CP {cp:.0f} W) ===\n")
    for (lo, hi, name), t in zip(ZONES, time_in_zones(s["power"], cp)):
        rng = f"{lo * cp:.0f}-{hi * cp:.0f}W" if hi < 99 else f">{lo * cp:.0f}W"
        print(f"{name:13} {rng:>10} {t / 3600:5.1f}h {t / total:5.0%}  "
              f"{bar(t, total)}")

    prior, recent = recent_prior(runs)
    print("\nHard time (>=Z3) by period:")
    for label, part in [("prior 90 d", prior), ("last 90 d ", recent)]:
        if not len(part):
            print(f"  {label}: no runs")
            continue
        sp = all_power(part)
        hard = (sp["power"] >= 0.9 * cp).mean()
        print(f"  {label}: {hard:.1%} of running time")

    wz = weekly_zones(runs, cp).tail(12)
    print(f"\nWeekly intensity split, last {len(wz)} weeks "
          "(easy = Z1+Z2, hard = >=Z3):")
    print(f"{'week ending':>12} {'hours':>6} {'easy':>5} {'hard':>5}")
    for wk, row in wz.iterrows():
        tot = row.sum()
        if not tot:
            continue
        easy = (row.iloc[0] + row.iloc[1]) / tot
        print(f"{wk:%Y-%m-%d} {tot / 3600:6.1f} {easy:5.0%} {1 - easy:5.0%}")
    tz = time_in_zones(s["power"], cp)
    easy_all = (tz[0] + tz[1]) / total
    print(f"All-time: {easy_all:.0%} easy / {1 - easy_all:.0%} hard "
          "(polarized-training guideline ~80/20)")

    print(f"\nMedian power : {s['power'].median():.0f} W "
          f"({s['power'].median() / cp:.0%} of CP)")
    print(f"Median HR    : {s['hr'].median():.0f} bpm")


if __name__ == "__main__":
    main()
