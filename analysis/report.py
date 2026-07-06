"""Combined markdown report with charts: python -m analysis.report → report/report.md

Pass --html to also write report/report.html (self-styled, images relative).
Pass --pdf for report/report.pdf (rendered via a headless Chromium browser).
"""
import io
import os
import subprocess
import sys
from contextlib import redirect_stdout
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from . import (bests, cp, decoupling, dynamics, fitness, intervals, quadrant,
               recovery, volume, wbal, zones)
from .common import load_runs, load_stream

OUT = "report"


def chart_volume(df):
    km = df.set_index("startTimeLocal").resample("W")["km"].sum()
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = ["#d62728" if prev and k > prev * 1.5 and k > 20 else "#1f77b4"
              for prev, k in zip([None] + list(km[:-1]), km)]
    ax.bar(km.index, km.values, width=5, color=colors)
    ax.set_title("Weekly volume (red = >50% ramp)")
    ax.set_ylabel("km")
    fig.autofmt_xdate()
    return fig


def chart_fitness(df):
    df = df.dropna(subset=["averageHR"])
    fig, ax = plt.subplots(figsize=(8, 4))
    sc = ax.scatter(df["startTimeLocal"], df["m_per_beat"],
                    s=df["km"] * 12, c=df["averageHR"], cmap="coolwarm")
    ax.plot(df["startTimeLocal"],
            df["m_per_beat"].rolling(5, min_periods=1).mean(),
            color="gray", lw=2, label="5-run avg")
    ax.set_title("Efficiency: meters per heartbeat (size = distance, color = HR)")
    ax.set_ylabel("m/beat")
    ax.legend()
    fig.colorbar(sc, label="avg HR")
    fig.autofmt_xdate()
    return fig


def chart_bests(df):
    fig, ax = plt.subplots(figsize=(8, 4))
    sc = ax.scatter(df["km"], df["pace_s"] / 60,
                    c=df["averageHR"], cmap="coolwarm", s=60)
    ax.invert_yaxis()  # faster pace on top
    ax.set_title("Every run: distance vs pace (color = HR)")
    ax.set_xlabel("km")
    ax.set_ylabel("pace (min/km, faster ↑)")
    fig.colorbar(sc, label="avg HR")
    return fig


def chart_cp(df):
    fig, ax = plt.subplots(figsize=(8, 4))
    half = df["startTimeLocal"].iloc[len(df) // 2]
    for label, part, color in [
            ("first half", df[df["startTimeLocal"] < half], "#1f77b4"),
            ("second half", df[df["startTimeLocal"] >= half], "#d62728")]:
        m = cp.mmp_curve(part)
        ax.plot(m.index / 60, m["power"], "o-", color=color, label=label)
        try:
            pcp, _ = cp.fit_cp(m)
            ax.axhline(pcp, color=color, ls="--", lw=1)
            ax.text(60, pcp + 3, f"CP {pcp:.0f}W", color=color, ha="right")
        except Exception:
            pass
    ax.set_xscale("log")
    ax.set_xticks([0.25, 1, 5, 20, 60], ["15s", "1m", "5m", "20m", "60m"])
    ax.set_title("Mean-Maximal Power curve (dashed = fitted CP)")
    ax.set_ylabel("W")
    ax.legend()
    return fig


def chart_wbal(df):
    mmp = cp.mmp_curve(df)
    cpv, w_prime = cp.fit_cp(mmp)
    deepest = None
    for _, r in df.iterrows():
        p = load_stream(r["activityId"])["power"]
        wb = wbal.wbal_series(p, cpv, w_prime)
        if deepest is None or wb.min() < deepest[1].min():
            deepest = (r, wb, p)
    r, wb, p = deepest
    fig, ax = plt.subplots(figsize=(8, 4))
    t = p.index / 60
    ax.plot(t, p.rolling(30, min_periods=1).mean(), color="#cccccc", lw=1,
            label="power (30s avg)")
    ax.axhline(cpv, color="gray", ls="--", lw=1, label=f"CP {cpv:.0f}W")
    ax.set_ylabel("W")
    ax.set_xlabel("min")
    ax2 = ax.twinx()
    ax2.plot(t, wb / 1000, color="#d62728", lw=2, label="W'bal")
    ax2.axhline(0, color="#d62728", ls=":", lw=1)
    ax2.set_ylabel("W'bal (kJ)", color="#d62728")
    ax.set_title(f"Deepest dig: {r['startTimeLocal']:%Y-%m-%d} "
                 f"({r['km']:.1f} km) — anaerobic tank over time")
    fig.legend(loc="lower left", bbox_to_anchor=(0.1, 0.12))
    return fig


def chart_intervals(df):
    iv, cpv = intervals.all_intervals()
    fig, ax = plt.subplots(figsize=(8, 4))
    sc = ax.scatter(iv["date"], iv["power"], s=iv["dur"] / 2,
                    c=iv["pacing"], cmap="RdYlGn", vmin=0.85, vmax=1.15)
    ax.axhline(cpv, color="gray", ls="--", lw=1)
    ax.text(iv["date"].min(), cpv + 2, f"CP {cpv:.0f}W", color="gray")
    ax.set_title("Discovered intervals (size = duration, green = negative split)")
    ax.set_ylabel("avg power (W)")
    fig.colorbar(sc, label="pacing index")
    fig.autofmt_xdate()
    return fig


def chart_zones(df):
    s = zones.all_power(df)
    cpv, _ = cp.fit_cp(cp.mmp_curve(df))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    colors = ["#4daf4a", "#a6d854", "#ffd92f", "#fc8d62", "#e41a1c"]
    for (lo, hi, name), c in zip(zones.ZONES, colors):
        ax1.axvspan(lo * cpv, min(hi * cpv, 500), color=c, alpha=0.25)
    ax1.hist(s["power"], bins=range(100, 500, 10), color="#1f77b4")
    ax1.axvline(cpv, color="black", ls="--", lw=1, label=f"CP {cpv:.0f}W")
    ax1.set_title("Power distribution (zones shaded)")
    ax1.set_xlabel("W")
    ax1.legend()
    ax2.hist(s["hr"], bins=range(100, 200, 2), color="#d62728")
    ax2.set_title("Heart-rate distribution")
    ax2.set_xlabel("bpm")
    return fig


def chart_quadrant(df):
    q = quadrant.force_cadence(df).iloc[::5]  # thin for plotting
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sc = ax.scatter(q["cadence"], q["force"], s=3, alpha=0.3,
                    c=q["speed"] * 3.6, cmap="viridis")
    ax.axvline(q["cadence"].median(), color="gray", ls="--", lw=1)
    ax.axhline(q["force"].median(), color="gray", ls="--", lw=1)
    ax.set_title("Quadrant: step force vs cadence (color = speed km/h)")
    ax.set_xlabel("cadence (spm)")
    ax.set_ylabel("force (N)")
    ax.set_xlim(120, 200)
    ax.set_ylim(50, 200)
    fig.colorbar(sc, label="km/h")
    return fig


def chart_recovery(df):
    w = recovery.load_wellness()
    km = df.set_index("startTimeLocal")["km"].resample("D").sum()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 5), sharex=True,
                                   height_ratios=[2, 1])
    ax1.fill_between(w.index, w["hrv_low"], w["hrv_high"],
                     color="#4daf4a", alpha=0.15, label="HRV baseline")
    ax1.plot(w.index, w["hrv"], "o-", ms=3, color="#4daf4a", label="HRV (ms)")
    ax1.set_ylabel("HRV (ms)", color="#4daf4a")
    ax1b = ax1.twinx()
    ax1b.plot(w.index, w["rhr"], "o-", ms=3, color="#d62728", label="RHR")
    ax1b.set_ylabel("RHR (bpm)", color="#d62728")
    ax1b.invert_yaxis()  # up = better for both lines
    ax1.set_title("Recovery: HRV & resting HR (both lines up = good) vs load")
    ax2.bar(km.index, km.values, color="#1f77b4")
    ax2.set_ylabel("km/day")
    fig.autofmt_xdate()
    return fig


def chart_decoupling(df):
    rows = [(r, decoupling.decoupling(load_stream(r["activityId"])))
            for _, r in df.iterrows()]
    rows = [(r, d) for r, d in rows if d is not None]
    fig, ax = plt.subplots(figsize=(8, 4))
    dates = [r["startTimeLocal"] for r, _ in rows]
    vals = [d * 100 for _, d in rows]
    colors = ["#4daf4a" if d < 5 else "#ff7f0e" if d < 8 else "#d62728"
              for d in vals]
    ax.bar(dates, vals, width=1.2, color=colors)
    for (r, _), v in zip(rows, vals):
        if r["km"] >= 10:
            ax.annotate("★", (r["startTimeLocal"], v), ha="center",
                        va="bottom", fontsize=12)
    ax.axhline(5, color="gray", ls="--", lw=1)
    ax.text(dates[0], 5.2, "5% line", color="gray")
    ax.set_title("Aerobic decoupling per run (★ = long run, lower = better)")
    ax.set_ylabel("Pw:Hr drift (%)")
    fig.autofmt_xdate()
    return fig


def chart_dynamics(df):
    rows = []
    for _, r in df.iterrows():
        s = load_stream(r["activityId"])
        if s["gct"].notna().sum() >= 60:
            rows.append((r["pace_s"] / 60, s["gct"].mean(),
                         r["startTimeLocal"]))
    pace, gct, dates = zip(*rows)
    fig, ax = plt.subplots(figsize=(8, 4))
    order = pd.Series(pd.to_datetime(dates)).rank().values
    sc = ax.scatter(pace, gct, c=order, cmap="viridis", s=60)
    ax.set_xlabel("pace (min/km)")
    ax.set_ylabel("ground contact time (ms)")
    ax.set_title("GCT vs pace (bright = recent runs)")
    fig.colorbar(sc, label="run order (old → new)")
    return fig


def capture(mod):
    buf = io.StringIO()
    with redirect_stdout(buf):
        mod.main()
    return buf.getvalue()


def main():
    os.makedirs(OUT, exist_ok=True)
    df = load_runs()

    sections = [
        ("Weekly volume", "volume.png", chart_volume, volume),
        ("Fitness: pace vs HR", "fitness.png", chart_fitness, fitness),
        ("Critical Power model", "cp.png", chart_cp, cp),
        ("W'bal: anaerobic reserve", "wbal.png", chart_wbal, wbal),
        ("Interval discovery", "intervals.png", chart_intervals, intervals),
        ("Power & HR distribution", "zones.png", chart_zones, zones),
        ("Quadrant: force vs cadence", "quadrant.png", chart_quadrant, quadrant),
        ("Recovery: HRV & resting HR", "recovery.png", chart_recovery, recovery),
        ("Aerobic decoupling", "decoupling.png", chart_decoupling, decoupling),
        ("Running dynamics", "dynamics.png", chart_dynamics, dynamics),
        ("Bests", "bests.png", chart_bests, bests),
    ]
    lines = [f"# Running report — {df['startTimeLocal'].min():%Y-%m-%d} to "
             f"{df['startTimeLocal'].max():%Y-%m-%d}",
             f"\nGenerated {datetime.now():%Y-%m-%d %H:%M}\n",
             f"\n{len(df)} runs · {df['km'].sum():.0f} km · "
             f"{df['duration'].sum() / 3600:.1f} h\n"]
    for title, png, chart_fn, mod in sections:
        fig = chart_fn(df)
        fig.savefig(f"{OUT}/{png}", dpi=120, bbox_inches="tight")
        plt.close(fig)
        lines += [f"## {title}\n", f"![{title}]({png})\n",
                  "```", capture(mod).rstrip(), "```\n"]

    path = f"{OUT}/report.md"
    md = "\n".join(lines)
    with open(path, "w") as f:
        f.write(md)
    print(f"Wrote {path} + {len(sections)} PNGs")

    if "--html" in sys.argv or "--pdf" in sys.argv:
        import markdown
        body = markdown.markdown(md, extensions=["fenced_code"])
        style = ("body{max-width:900px;margin:2em auto;padding:0 1em;"
                 "font-family:system-ui,sans-serif;line-height:1.5}"
                 "img{max-width:100%}"
                 "pre{background:#f6f8fa;padding:1em;overflow-x:auto;"
                 "font-size:13px;border-radius:6px}")
        with open(f"{OUT}/report.html", "w") as f:
            f.write(f"<!doctype html><meta charset='utf-8'>"
                    f"<title>Running report</title>"
                    f"<style>{style}</style>\n{body}")
        print(f"Wrote {OUT}/report.html")

    if "--pdf" in sys.argv:
        browsers = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
        browser = next((b for b in browsers if os.path.exists(b)), None)
        if not browser:
            print("PDF skipped: neither Chrome nor Brave is installed "
                  "(needed to render report.html to PDF)")
            return
        subprocess.run(
            [browser, "--headless", "--disable-gpu",
             f"--print-to-pdf={os.path.abspath(OUT)}/report.pdf",
             "--no-pdf-header-footer",
             f"file://{os.path.abspath(OUT)}/report.html"],
            check=True, capture_output=True)
        print(f"Wrote {OUT}/report.pdf")


if __name__ == "__main__":
    main()
