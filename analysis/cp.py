"""Critical Power model + Mean-Maximal Power curve from running power streams.

MMP: best average power for each duration across all runs.
CP fit: linear work-time model P(t) = CP + W'/t over 2-20 min efforts.
Compares first-half vs second-half date ranges to show improvement.
"""
import numpy as np
import pandas as pd

from .common import load_runs, load_stream, recent_prior

DURATIONS = [5, 15, 30, 60, 120, 180, 300, 480, 600, 900, 1200, 1800, 2700, 3600]
FIT_RANGE = (120, 1200)  #  2-20 min is the validated CP window
TEST_STALE_DAYS = 42  # CP anchored on efforts older than this = test due


def mmp_curve(runs):
    """Best mean power per duration across runs -> DataFrame(power, date)."""
    best = {}
    for _, r in runs.iterrows():
        p = load_stream(r["activityId"])["power"].dropna()
        for d in DURATIONS:
            if len(p) < d:
                continue
            v = p.rolling(d).mean().max()
            if pd.notna(v) and v > best.get(d, (0,))[0]:
                best[d] = (v, r["startTimeLocal"])
    return pd.DataFrame(
        {"power": {d: v for d, (v, _) in best.items()},
         "date": {d: t for d, (_, t) in best.items()}}).sort_index()


def fit_cp(mmp):
    """P = CP + W'/t on efforts within FIT_RANGE. Returns (cp_watts, w_prime_joules)."""
    m = mmp[(mmp.index >= FIT_RANGE[0]) & (mmp.index <= FIT_RANGE[1])]
    w_prime, cp = np.polyfit(1 / m.index.values, m["power"].values, 1)
    return cp, w_prime


def fit_r2(mmp):
    """R² of the CP fit over its FIT_RANGE points — how hyperbolic the data is."""
    m = mmp[(mmp.index >= FIT_RANGE[0]) & (mmp.index <= FIT_RANGE[1])]
    cp, w = fit_cp(mmp)
    resid = m["power"] - (cp + w / m.index.values)
    return 1 - (resid ** 2).sum() / ((m["power"] - m["power"].mean()) ** 2).sum()


def rolling_cp(runs, window=28, step=7):
    """[(window_end, cp, w_prime, n_runs)] — the CP fit over a sliding window."""
    t = runs["startTimeLocal"]
    ends = pd.date_range(t.max().normalize() + pd.Timedelta(days=1),
                         t.min().normalize() + pd.Timedelta(days=window),
                         freq=f"-{step}D")[::-1]
    out = []
    for end in ends:
        part = runs[(t >= end - pd.Timedelta(days=window)) & (t < end)]
        m = mmp_curve(part) if len(part) >= 3 else pd.DataFrame()
        if len(m) and len(m[(m.index >= FIT_RANGE[0])
                            & (m.index <= FIT_RANGE[1])]) >= 3:
            out.append((end, *fit_cp(m), len(part)))
    return out


def main():
    runs = load_runs()
    mmp = mmp_curve(runs)
    cp, w = fit_cp(mmp)

    print(f"=== Mean-Maximal Power curve (all {len(runs)} runs) ===\n")
    print(f"{'duration':>9} {'power':>7}  set on")
    for d, row in mmp.iterrows():
        label = f"{d}s" if d < 60 else f"{d // 60}min"
        print(f"{label:>9} {row['power']:6.0f}W  {row['date']:%Y-%m-%d}")

    print(f"\nCritical Power : {cp:.0f} W  (sustainable ~30-60 min)")
    print(f"W' (anaerobic) : {w / 1000:.1f} kJ "
          f"(~{w / (mmp.loc[300, 'power'] - cp):.0f} s at 5-min power)")

    m = mmp[(mmp.index >= FIT_RANGE[0]) & (mmp.index <= FIT_RANGE[1])]
    age = (runs["startTimeLocal"].max() - m["date"].max()).days
    print(f"Fit quality    : R² {fit_r2(mmp):.3f} on {len(m)} points; "
          f"newest 2-20 min max effort {age} d ago")
    if age > TEST_STALE_DAYS:
        print(f"⚠ CP rests on efforts older than {TEST_STALE_DAYS} d — "
              "schedule an all-out 10-20 min test to re-anchor it")

    prior, recent = recent_prior(runs)
    parts = {}
    for label, part in [("prior 90 d ", prior), ("last 90 d  ", recent)]:
        m = mmp_curve(part) if len(part) else pd.DataFrame()
        try:
            pcp, pw = fit_cp(m)
            parts[label] = (m, pcp, pw)
            print(f"\n{label} ({part['startTimeLocal'].min():%m-%d} to "
                  f"{part['startTimeLocal'].max():%m-%d}): "
                  f"CP {pcp:.0f} W, W' {pw / 1000:.1f} kJ")
        except Exception:
            print(f"\n{label}: not enough long efforts to fit")

    if len(parts) == 2:
        (_, cp1, _), (_, cp2, _) = parts.values()
        print(f"\nCP change      : {cp2 - cp1:+.0f} W ({(cp2 - cp1) / cp1:+.1%}) "
              "prior → last 90 d")

    trend = rolling_cp(runs)
    if trend:
        show = trend[-26:]
        extra = (f" (last {len(show)} of {len(trend)} windows)"
                 if len(trend) > len(show) else "")
        print(f"\n28-day rolling CP, stepped weekly{extra}:")
        print(f"{'window end':>10} {'runs':>5} {'CP':>6} {'W′':>9}")
        for end, c, wp, n in show:
            print(f"{end:%m-%d} {n:9d} {c:5.0f}W {wp / 1000:6.1f} kJ")
        print("a jump means a long hard effort entered/left the window — "
              "the fit is only as good as its best 2-20 min efforts")
    return mmp, cp, w, parts


if __name__ == "__main__":
    main()
