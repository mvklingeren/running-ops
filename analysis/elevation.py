"""Elevation: how much do hills cost, via grade-adjusted pace (GAP).

Garmin's avgGradeAdjustedSpeed estimates the flat-ground-equivalent
speed of a run; actual pace minus GAP pace = seconds per km lost to
gradient. Gain per km says how hilly the route was. Runs recorded
without GAP (2 early ones) are skipped.
"""
from .common import fmt_pace, load_runs


def hill_cost(df):
    """Seconds per km lost to gradient: actual pace minus GAP pace."""
    return df["pace_s"] - 1000 / df["avgGradeAdjustedSpeed"]


def main():
    df = load_runs().dropna(subset=["avgGradeAdjustedSpeed"]).copy()
    df["gain_km"] = df["elevationGain"] / df["km"]
    df["cost"] = hill_cost(df)

    print(f"=== Elevation: hill cost via grade-adjusted pace, "
          f"{len(df)} runs ===\n")
    if len(df) > 20:
        print(f"(last 20 of {len(df)} runs; averages below use all)")
    print(f"{'date':>10} {'km':>5} {'gain':>5} {'gain/km':>8} {'pace':>8} "
          f"{'GAP':>8} {'hill cost':>10}")
    for _, r in df.tail(20).iterrows():
        print(f"{r['startTimeLocal']:%m-%d} {r['km']:9.1f} "
              f"{r['elevationGain']:4.0f}m {r['gain_km']:6.1f}m/km "
              f"{fmt_pace(r['pace_s']):>8} "
              f"{fmt_pace(r['pace_s'] - r['cost']):>8} {r['cost']:+7.1f} s/km")

    print(f"\nAverage: {df['gain_km'].mean():.1f} m gain/km, hill cost "
          f"{df['cost'].mean():+.1f} s/km")
    h = df.loc[df["gain_km"].idxmax()]
    print(f"Hilliest run: {h['startTimeLocal']:%m-%d} "
          f"({h['gain_km']:.1f} m/km, {h['elevationGain']:.0f} m total) "
          f"cost {h['cost']:+.1f} s/km")
    r = df["gain_km"].corr(df["cost"])
    print(f"Gain/km vs hill cost: r = {r:+.2f}", end="")
    if r > 0.5:
        print(" — slow days on hilly routes are the hills, not lost fitness.")
    else:
        print(" — these routes are flat enough that hills barely move pace.")


if __name__ == "__main__":
    main()
