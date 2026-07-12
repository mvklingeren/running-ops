"""Interval discovery: find sustained efforts above CP, rank and compare them.

An interval = 30s-smoothed power above CP for >=60s (dips <30s merged).
Pacing index = 2nd-half avg power / 1st-half (1.00 even, <1.00 fading).
Effort = work done above CP (how much of W' it cost).
"""
import pandas as pd

from .common import fmt_pace, load_runs, load_stream
from .cp import fit_cp, mmp_curve

MIN_LEN, MERGE_GAP = 60, 30


def find_intervals(power, cp):
    smooth = power.fillna(0).rolling(30, min_periods=1).mean()
    above = smooth > cp
    # merge short dips, then extract contiguous stretches
    blocks, start, gap = [], None, 0
    for t, a in above.items():
        if a:
            start, gap = (t if start is None else start), 0
        elif start is not None:
            gap += 1
            if gap > MERGE_GAP:
                blocks.append((start, t - gap))
                start = None
    if start is not None:
        blocks.append((start, above.index[-1]))
    return [(s, e) for s, e in blocks if e - s >= MIN_LEN]


def interval_metrics(run, stream, s, e):
    seg = stream.loc[s:e]
    dur = len(seg)  # 1 Hz samples, inclusive bounds: e - s + 1 seconds of work
    half = dur // 2
    p1 = seg["power"].iloc[:half].mean()
    p2 = seg["power"].iloc[half:].mean()
    return {
        "date": run["startTimeLocal"], "start_min": s / 60, "dur": dur,
        "power": seg["power"].mean(), "hr": seg["hr"].mean(),
        "pace_s": 1000 / seg["speed"].mean(),
        "pacing": p2 / p1,
    }


def all_intervals():
    runs = load_runs()
    cp, _ = fit_cp(mmp_curve(runs))
    out = []
    for _, r in runs.iterrows():
        stream = load_stream(r["activityId"])
        for s, e in find_intervals(stream["power"], cp):
            m = interval_metrics(r, stream, s, e)
            m["work_kj"] = (m["power"] - cp) * m["dur"] / 1000  # W' spent
            out.append(m)
    return pd.DataFrame(out), cp


def main():
    df, cp = all_intervals()
    if df.empty:
        print(f"No intervals found above CP {cp:.0f} W")
        return
    df = df.sort_values("work_kj", ascending=False).reset_index(drop=True)
    top = df.head(20)
    print(f"=== {len(df)} intervals discovered (efforts above CP {cp:.0f} W), "
          f"ranked by W' spent"
          + (f"; top {len(top)} shown" if len(df) > len(top) else "")
          + " ===\n")
    print(f"{'date':>10} {'at':>6} {'dur':>5} {'power':>6} {'%CP':>5} "
          f"{'HR':>4} {'pace':>8} {'pacing':>7} {'W`kJ':>6}")
    for _, i in top.iterrows():
        style = ("even" if 0.97 <= i['pacing'] <= 1.03
                 else "fade" if i['pacing'] < 0.97 else "neg-split")
        print(f"{i['date']:%Y-%m-%d} {i['start_min']:5.1f}m {i['dur']:4.0f}s "
              f"{i['power']:5.0f}W {i['power'] / cp:5.0%} {i['hr']:4.0f} "
              f"{fmt_pace(i['pace_s']):>8} {i['pacing']:6.2f} {i['work_kj']:6.1f}"
              f"  {style}")

    by_run = df.groupby(df["date"].dt.date)
    multi = {d: g for d, g in by_run if len(g) > 1}
    if multi:
        print("\nFatigue across repeated efforts (same run, last 10 days):")
        for d in sorted(multi)[-10:]:
            g = multi[d].sort_values("start_min")
            drop = g["power"].iloc[-1] / g["power"].iloc[0] - 1
            print(f"  {d}: {len(g)} efforts, last vs first power {drop:+.1%}")
    even = (df["pacing"] >= 0.97).mean()
    print(f"\nPacing: {even:.0%} of intervals held even or negative splits")


if __name__ == "__main__":
    main()
