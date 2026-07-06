"""Aerobic decoupling (Pw:Hr): does power-per-heartbeat fade within a run?

EF = power / HR. Decoupling = (EF first half - EF second half) / EF first.
Under 5% on a 40min+ steady run = solid aerobic base.
First 5 min excluded (HR lag), runs under 20 min skipped.
"""
from .common import fmt_pace, load_runs, load_stream

WARMUP, MIN_DUR = 300, 1200


def decoupling(stream):
    s = stream.iloc[WARMUP:].dropna(subset=["power", "hr"])
    if len(s) < MIN_DUR - WARMUP:
        return None
    half = len(s) // 2
    ef1 = s["power"].iloc[:half].mean() / s["hr"].iloc[:half].mean()
    ef2 = s["power"].iloc[half:].mean() / s["hr"].iloc[half:].mean()
    return (ef1 - ef2) / ef1


def main():
    runs = load_runs()
    print("=== Aerobic decoupling (Pw:Hr), runs over 20 min ===\n")
    print(f"{'date':>10} {'km':>5} {'pace':>8} {'drift':>7}  verdict")
    vals = []
    for _, r in runs.iterrows():
        d = decoupling(load_stream(r["activityId"]))
        if d is None:
            continue
        vals.append((r, d))
        verdict = ("excellent" if d < 0.02 else "good" if d < 0.05
                   else "moderate" if d < 0.08 else "high")
        mark = " ★" if r["km"] >= 10 else ""
        print(f"{r['startTimeLocal']:%m-%d} {r['km']:9.1f} "
              f"{fmt_pace(r['pace_s']):>8} {d:6.1%}  {verdict}{mark}")

    print("\n★ = long run, the ones that matter most")
    longs = [(r, d) for r, d in vals if r["km"] >= 10]
    if longs:
        avg = sum(d for _, d in longs) / len(longs)
        print(f"Long-run average drift: {avg:.1%} "
              f"({'aerobic base is solid' if avg < 0.05 else 'base still building'})")
    n = len(vals)
    good = sum(1 for _, d in vals if d < 0.05)
    print(f"Overall: {good}/{n} runs under the 5% line")


if __name__ == "__main__":
    main()
