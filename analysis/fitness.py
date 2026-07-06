"""Pace vs heart rate over time — is the same speed getting cheaper?

Metric: meters per heartbeat (speed normalized by effort).
Rising m/beat at flat pace = aerobic fitness improving.
"""
from .common import bar, fmt_pace, load_runs


def main():
    df = load_runs().dropna(subset=["averageHR"])
    df["eff_smooth"] = df["m_per_beat"].rolling(5, min_periods=1).mean()

    print("=== Pace vs HR: efficiency per run (meters per heartbeat) ===\n")
    print(f"{'date':>10} {'km':>5} {'pace':>8} {'HR':>4} {'m/beat':>7}  "
          f"trend (5-run avg)")
    lo, hi = df["eff_smooth"].min(), df["eff_smooth"].max()
    for _, r in df.iterrows():
        rel = r["eff_smooth"] - lo
        print(f"{r['startTimeLocal']:%m-%d} {r['km']:9.1f} "
              f"{fmt_pace(r['pace_s']):>8} {r['averageHR']:4.0f} "
              f"{r['m_per_beat']:7.3f}  {bar(rel, hi - lo, 25, '▒')}")

    half = len(df) // 2
    first, second = df.iloc[:half], df.iloc[half:]
    e1, e2 = first["m_per_beat"].mean(), second["m_per_beat"].mean()
    print(f"\nFirst half  : {fmt_pace(first['pace_s'].mean())} at "
          f"{first['averageHR'].mean():.0f} bpm → {e1:.3f} m/beat")
    print(f"Second half : {fmt_pace(second['pace_s'].mean())} at "
          f"{second['averageHR'].mean():.0f} bpm → {e2:.3f} m/beat")
    gain = (e2 - e1) / e1
    print(f"Efficiency  : {gain:+.1%}", end="")
    if gain > 0:
        beats = first["averageHR"].mean() * (1 - e1 / e2)
        print(f" — each km now costs ~{abs(beats):.0f} fewer beats/min "
              f"at the same pace. Fitness is improving.")
    else:
        print(" — flat/declining; could be heat, fatigue, or harder terrain.")


if __name__ == "__main__":
    main()
