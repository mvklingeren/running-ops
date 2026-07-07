"""Correlations: pair any raw datapoint with any calculated metric.

build() joins every run with that morning's wellness (HRV/RHR/sleep),
the daily PMC state (ATL/CTL/TSB) and per-run derived metrics (TRIMP,
decoupling, W' depletion, effective VO2max) into one tidy frame.
Each CHAPTERS entry pairs columns of that frame into a chart + Pearson r —
a new chapter is one tuple, no new plotting code.

CLI: python -m analysis.correlate <colA> <colB> explores any pair ad-hoc
(text + report/adhoc-*.png); --list shows the available columns.
"""
import os
import sys

import pandas as pd

from .common import load_runs, load_stream
from .cp import fit_cp, mmp_curve
from .decoupling import decoupling
from .load import pmc, trimp
from .recovery import load_wellness
from .vo2max import effective_vo2max
from .wbal import wbal_series

# (title, left axis [(column, label)], right axis [(column, label)] or None)
CHAPTERS = [
    ("Morning HRV vs efficiency",
     [("hrv", "HRV (ms)")], [("m_per_beat", "m/beat")]),
    ("Form (TSB) vs aerobic decoupling",
     [("tsb", "form (TSB)")], [("decoupling", "Pw:Hr drift")]),
    ("Sleep vs W' depletion",
     [("sleep_h", "sleep (h)")], [("wbal_depl", "W' used")]),
    ("Garmin aerobic training effect vs TRIMP",
     [("aerobicTrainingEffect", "aerobic TE")], [("trimp", "TRIMP")]),
    ("Heat vs efficiency",
     [("maxTemperature", "max temp (°C)")], [("m_per_beat", "m/beat")]),
]

LEFT_C, RIGHT_C = "#1f77b4", "#d62728"


def assemble(runs, wellness, atl, ctl, tsb):
    """Pure join: run rows + that date's wellness + that date's PMC values."""
    df = runs.copy()
    df["date"] = df["startTimeLocal"].dt.normalize()
    df = df.join(wellness, on="date")  # left join: never drops runs
    for name, s in (("atl", atl), ("ctl", ctl), ("tsb", tsb)):
        df[name] = s.reindex(df["date"]).values
    return df


def build():
    """One per-run frame: all runs.csv columns + wellness + derived metrics."""
    runs = load_runs()
    w = load_wellness()
    hr_rest, hr_max = w["rhr"].mean(), runs["maxHR"].max()
    try:
        cpv, w_prime = fit_cp(mmp_curve(runs))
    except Exception:
        cpv = w_prime = None  # not enough efforts to fit — wbal_depl stays NaN

    tr, dec, depl = [], [], []
    for _, r in runs.iterrows():
        s = load_stream(r["activityId"])
        hr = s["hr"].dropna()
        tr.append(trimp(hr, hr_rest, hr_max) if len(hr) else float("nan"))
        d = decoupling(s)
        dec.append(float("nan") if d is None else d)
        p = s["power"]
        #  <60 s of power = no meaningful W'bal, not 0% depletion
        if cpv is not None and p.notna().sum() > 60:
            depl.append(1 - wbal_series(p, cpv, w_prime).min() / w_prime)
        else:
            depl.append(float("nan"))
    runs = runs.assign(trimp=tr, decoupling=dec, wbal_depl=depl,
                       evo2=effective_vo2max(runs, hr_max))

    dates = runs["startTimeLocal"].dt.normalize()
    daily = runs.groupby(dates)["trimp"].sum().reindex(
        pd.date_range(dates.min(), dates.max(), freq="D"), fill_value=0)
    df = assemble(runs, w, *pmc(daily))
    # a runs.csv predating a CHAPTERS column is all-NaN there, not a crash
    for col in {c for _, left, right in CHAPTERS
                for c, _ in left + (right or [])}:
        if col not in df.columns:
            df[col] = float("nan")
    return df


def plot_chapter(ax, df, spec):
    """One CHAPTERS entry on one axis: left cols solid blue, right dashed red."""
    #  all cols on a side share one color; a chapter that needs more
    # graduates to its own hand-written chart like the other modules
    title, left, right = spec
    for col, _ in left:
        ax.plot(df["date"], df[col], "o-", ms=4, color=LEFT_C)
    ax.set_ylabel(" / ".join(l for _, l in left), color=LEFT_C, fontsize=9)
    if right:
        ax2 = ax.twinx()
        for col, _ in right:
            ax2.plot(df["date"], df[col], "o--", ms=4, color=RIGHT_C)
        ax2.set_ylabel(" / ".join(l for _, l in right), color=RIGHT_C,
                       fontsize=9)
    ax.set_title(title, fontsize=10)


def print_chapter(df, title, left, right):
    cols = left + (right or [])
    line = f"\n{title}"
    if right:
        a, b = left[0][0], right[0][0]
        sub = df[[a, b]].dropna()
        if len(sub) > 2:
            line += f" — r = {sub[a].corr(sub[b]):+.2f} (n={len(sub)})"
        else:
            line += " — not enough overlapping data"
    print(line)
    print(f"{'date':>5} " + "".join(f"{lbl:>14}" for _, lbl in cols))
    for _, r in df.iterrows():
        cells = "".join(
            f"{r[c]:>14.3g}" if pd.notna(r[c]) else f"{'-':>14}"
            for c, _ in cols)
        print(f"{r['date']:%m-%d} {cells}")


def main():
    df = build()
    print("=== Correlations: any datapoint vs any calculated metric ===")
    for title, left, right in CHAPTERS:
        print_chapter(df, title, left, right)


def list_columns(df):
    print("Columns you can correlate (non-null / runs):")
    for c in df.select_dtypes("number").columns:
        print(f"  {c:24} {df[c].notna().sum()}/{len(df)}")


def explore(a, b):
    """Ad-hoc chapter for any column pair: text + PNG, no code edit."""
    df = build()
    for c in (a, b):
        if c not in df.columns:
            print(f"unknown column: {c}\n")
            list_columns(df)
            sys.exit(1)
    spec = (f"{a} vs {b}", [(a, a)], [(b, b)])
    print_chapter(df, *spec)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 3))
    plot_chapter(ax, df, spec)
    fig.autofmt_xdate()
    os.makedirs("report", exist_ok=True)
    path = f"report/adhoc-{a}-vs-{b}.png"
    fig.savefig(path, dpi=120, bbox_inches="tight")
    print(f"\nChart: {path}")


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if x != "--list"]
    if "--list" in sys.argv:
        list_columns(build())
    elif len(args) == 2:
        explore(*args)
    else:
        main()
