"""W'bal: real-time anaerobic reserve depletion per run (Skiba differential model).

Above CP the W' tank drains at (P - CP); below CP it refills
proportionally to how empty it is. Min W'bal = how deep you dug.
"""
import pandas as pd

from .common import fmt_pace, load_runs, load_stream
from .cp import fit_cp, mmp_curve


def wbal_series(power, cp, w_prime):
    """W'bal per second for one run's power series."""
    out, w = [], w_prime
    for p in power.fillna(0):
        if p > cp:
            w -= (p - cp)
        else:
            w += (cp - p) * (w_prime - w) / w_prime
        w = min(w, w_prime)
        out.append(w)
    return pd.Series(out, index=power.index)


def main():
    runs = load_runs()
    mmp = mmp_curve(runs)
    cp, w_prime = fit_cp(mmp)
    print(f"=== W'bal per run (CP {cp:.0f} W, W' {w_prime / 1000:.1f} kJ) ===\n")
    if len(runs) > 20:
        print(f"(last 20 of {len(runs)} runs; stats below use all)")
    print(f"{'date':>10} {'km':>5} {'pace':>8} {'min W`bal':>10} {'depleted':>9}  "
          f"deepest at")
    rows = []
    for i, (_, r) in enumerate(runs.iterrows()):
        p = load_stream(r["activityId"])["power"]
        wb = wbal_series(p, cp, w_prime)
        depleted = 1 - wb.min() / w_prime
        rows.append((r, wb, depleted))
        if i < len(runs) - 20:
            continue
        t = wb.idxmin()
        print(f"{r['startTimeLocal']:%m-%d} {r['km']:9.1f} "
              f"{fmt_pace(r['pace_s']):>8} {wb.min() / 1000:8.1f}kJ "
              f"{depleted:8.0%}  {t // 60}:{t % 60:02d}")

    r, wb, depleted = max(rows, key=lambda x: x[2])
    t = wb.idxmin()
    print(f"\nDeepest dig: {r['startTimeLocal']:%Y-%m-%d} — burned {depleted:.0%} "
          f"of W' by {t // 60}:{t % 60:02d} "
          f"({r['km']:.1f} km at {fmt_pace(r['pace_s'])})")
    easy = sum(1 for *_, d in rows if d < 0.3)
    print(f"{easy}/{len(rows)} runs never used more than 30% of the tank "
          f"(true easy runs)")
    if any(d > 1 for *_, d in rows):
        print("Note: >100% depletion means the effort beat the model — "
              "CP is likely overestimated (no all-out 20min+ test in the data).")
    return rows, cp, w_prime


if __name__ == "__main__":
    main()
