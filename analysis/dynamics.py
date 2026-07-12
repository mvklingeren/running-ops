"""Running dynamics: ground contact time, vertical oscillation, vertical ratio.

Form check: elite GCT <240ms, recreational ~250-300ms. Vertical ratio
(bounce per meter travelled) under ~7% is efficient. Also checks whether
form falls apart late in long runs.
"""
import pandas as pd

from .common import fmt_pace, load_runs, load_stream


def main():
    runs = load_runs()
    rows = []
    for _, r in runs.iterrows():
        s = load_stream(r["activityId"])
        if s["gct"].notna().sum() < 60:
            continue
        rows.append({
            "date": r["startTimeLocal"], "km": r["km"], "pace_s": r["pace_s"],
            "gct": s["gct"].mean(), "vo": s["vo"].mean(),
            "vratio": s["vratio"].mean(), "stride": s["stride"].mean(),
            "stream": s,
        })
    df = pd.DataFrame(rows)

    print("=== Running dynamics ===\n")
    if len(df) > 20:
        print(f"(last 20 of {len(df)} runs; averages below use all)")
    print(f"{'date':>10} {'km':>5} {'pace':>8} {'GCT':>6} {'VO':>6} "
          f"{'vRatio':>7} {'stride':>7}")
    for _, r in df.tail(20).iterrows():
        print(f"{r['date']:%m-%d} {r['km']:9.1f} {fmt_pace(r['pace_s']):>8} "
              f"{r['gct']:5.0f}ms {r['vo']:5.1f}cm {r['vratio']:6.2f}% "
              f"{r['stride']:5.0f}cm")

    print(f"\nAverages: GCT {df['gct'].mean():.0f} ms, "
          f"VO {df['vo'].mean():.1f} cm, vertical ratio "
          f"{df['vratio'].mean():.2f}%, stride {df['stride'].mean():.0f} cm")
    fast = df.nsmallest(5, "pace_s")
    slow = df.nlargest(5, "pace_s")
    print(f"Fast runs : GCT {fast['gct'].mean():.0f} ms, stride "
          f"{fast['stride'].mean():.0f} cm at {fmt_pace(fast['pace_s'].mean())}")
    print(f"Slow runs : GCT {slow['gct'].mean():.0f} ms, stride "
          f"{slow['stride'].mean():.0f} cm at {fmt_pace(slow['pace_s'].mean())}")

    print("\nForm under fatigue (first vs last quarter, last 10 runs >= 10 km):")
    for _, r in df[df["km"] >= 10].tail(10).iterrows():
        s = r["stream"].dropna(subset=["gct"])
        q = len(s) // 4
        g1, g4 = s["gct"].iloc[:q].mean(), s["gct"].iloc[-q:].mean()
        v1, v4 = s["vratio"].iloc[:q].mean(), s["vratio"].iloc[-q:].mean()
        print(f"  {r['date']:%m-%d} ({r['km']:.1f} km): GCT {g1:.0f}->{g4:.0f} ms "
              f"({(g4 - g1) / g1:+.1%}), vRatio {v1:.2f}->{v4:.2f}%")


if __name__ == "__main__":
    main()
