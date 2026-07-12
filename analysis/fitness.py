"""Pace vs heart rate over time — is the same speed getting cheaper?

Metric: meters per heartbeat (speed normalized by effort).
Rising m/beat at flat pace = aerobic fitness improving.
"""
from .common import bar, fmt_pace, load_runs, recent_prior


def beats_saved(hr, e1, e2):
    """bpm cheaper the same pace has become as efficiency rose e1 -> e2."""
    return hr * (1 - e1 / e2)


def main():
    df = load_runs().dropna(subset=["averageHR"])
    df["eff_smooth"] = df["m_per_beat"].rolling(5, min_periods=1).mean()

    print("=== Pace vs HR: efficiency per run (meters per heartbeat) ===\n")
    shown = df.tail(20)
    if len(shown) < len(df):
        print(f"(last {len(shown)} of {len(df)} runs; comparison below uses "
              "90-day windows)")
    print(f"{'date':>10} {'km':>5} {'pace':>8} {'HR':>4} {'m/beat':>7}  "
          f"trend (5-run avg)")
    lo, hi = df["eff_smooth"].min(), df["eff_smooth"].max()
    for _, r in shown.iterrows():
        rel = r["eff_smooth"] - lo
        print(f"{r['startTimeLocal']:%m-%d} {r['km']:9.1f} "
              f"{fmt_pace(r['pace_s']):>8} {r['averageHR']:4.0f} "
              f"{r['m_per_beat']:7.3f}  {bar(rel, hi - lo, 25, '▒')}")

    prior, recent = recent_prior(df)
    if not len(prior) or not len(recent):
        print("\nNot enough history for a 90-day comparison.")
        return
    e1, e2 = prior["m_per_beat"].mean(), recent["m_per_beat"].mean()
    print(f"\nPrior 90 d  : {fmt_pace(prior['pace_s'].mean())} at "
          f"{prior['averageHR'].mean():.0f} bpm → {e1:.3f} m/beat")
    print(f"Last 90 d   : {fmt_pace(recent['pace_s'].mean())} at "
          f"{recent['averageHR'].mean():.0f} bpm → {e2:.3f} m/beat")
    gain = (e2 - e1) / e1
    print(f"Efficiency  : {gain:+.1%}", end="")
    if gain > 0:
        beats = beats_saved(prior["averageHR"].mean(), e1, e2)
        print(f" — running at the same pace now costs ~{abs(beats):.0f} "
              f"fewer bpm. Fitness is improving.")
    else:
        print(" — flat/declining; could be heat, fatigue, or harder terrain.")


if __name__ == "__main__":
    main()
