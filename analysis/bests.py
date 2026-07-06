"""Top runs: fastest, longest, most efficient (meters per heartbeat)."""
from .common import fmt_pace, load_runs


def show(title, rows, note=""):
    print(f"=== {title} ==={' ' + note if note else ''}")
    for i, (_, r) in enumerate(rows.iterrows(), 1):
        print(f"  {i}. {r['startTimeLocal']:%Y-%m-%d}  {r['km']:5.1f} km  "
              f"{fmt_pace(r['pace_s']):>8}  {r['averageHR']:.0f} bpm  "
              f"{r['m_per_beat']:.3f} m/beat")
    print()


def main():
    df = load_runs()
    real = df[df["km"] >= 3]  # ponytail: <3 km runs skew pace/efficiency stats

    show("Fastest runs", real.nsmallest(3, "pace_s"), "(min 3 km)")
    show("Longest runs", df.nlargest(3, "km"))
    show("Most efficient runs", real.nlargest(3, "m_per_beat"),
         "(most distance per heartbeat, min 3 km)")

    best = real.nlargest(1, "m_per_beat").iloc[0]
    worst = real.nsmallest(1, "m_per_beat").iloc[0]
    print(f"Spread: best run covered {best['m_per_beat']/worst['m_per_beat']-1:.0%} "
          f"more ground per heartbeat than the least efficient one\n"
          f"  best : {best['startTimeLocal']:%Y-%m-%d} "
          f"({fmt_pace(best['pace_s'])} at {best['averageHR']:.0f} bpm)\n"
          f"  worst: {worst['startTimeLocal']:%Y-%m-%d} "
          f"({fmt_pace(worst['pace_s'])} at {worst['averageHR']:.0f} bpm)")


if __name__ == "__main__":
    main()
