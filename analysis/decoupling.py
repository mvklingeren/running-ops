"""Aerobic decoupling (Pw:Hr): does power-per-heartbeat fade within a run?

EF = power / HR. Decoupling = (EF first half - EF second half) / EF first.
Under 5% on a 40min+ steady run = solid aerobic base.
First 5 min excluded (HR lag), runs under 20 min skipped.
"""
import pandas as pd

from .common import fmt, fmt_pace, load_runs, load_stream

WARMUP, MIN_DUR = 300, 1200
HOT_DEW = 16  # °C dew point above which drift is partly heat, not fitness
MAX_ZERO_POWER = 0.15  # skip runs where the pod sat idle much of a half


def decoupling(stream):
    s = stream.iloc[WARMUP:].dropna(subset=["power", "hr"])
    if len(s) < MIN_DUR - WARMUP:
        return None
    half = len(s) // 2
    p1, p2 = s["power"].iloc[:half], s["power"].iloc[half:]
    if max((p1 == 0).mean(), (p2 == 0).mean()) > MAX_ZERO_POWER:
        return None  # zero-heavy half drags EF toward 0, drift blows up
    ef1 = p1.mean() / s["hr"].iloc[:half].mean()
    ef2 = p2.mean() / s["hr"].iloc[half:].mean()
    return (ef1 - ef2) / ef1


def main():
    runs = load_runs()
    print("=== Aerobic decoupling (Pw:Hr), runs over 20 min ===\n")
    vals = []
    for _, r in runs.iterrows():
        d = decoupling(load_stream(r["activityId"]))
        if d is not None:
            vals.append((r, d))
    if len(vals) > 20:
        print(f"(last 20 of {len(vals)} eligible runs; stats below use all)")
    print(f"{'date':>10} {'km':>5} {'pace':>8} {'drift':>7} {'temp':>5} {'dew':>5}  verdict")
    for r, d in vals[-20:]:
        verdict = ("excellent" if d < 0.02 else "good" if d < 0.05
                   else "moderate" if d < 0.08 else "high")
        mark = " ★" if r["km"] >= 10 else ""
        dew = r.get("dew_c")
        wx = f"{fmt(r.get('temp_c'), '4.0f', '°')} {fmt(dew, '4.0f', '°')}"
        if pd.notna(dew) and dew >= HOT_DEW and d >= 0.05:
            mark += " (hot)"
        print(f"{r['startTimeLocal']:%Y-%m-%d} {r['km']:5.1f} "
              f"{fmt_pace(r['pace_s']):>8} {d:6.1%} {wx}  {verdict}{mark}")

    print("\n★ = long run, the ones that matter most; "
          f"(hot) = dew point ≥ {HOT_DEW}°C, drift is partly heat")
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
