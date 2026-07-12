"""Durability: does efficiency fade as work accumulates within a run?

EF = power/HR per second. Each run is bucketed by cumulative kJ of work
done so far and normalized to its own first bucket, so all runs pool
into one dose-response curve: relative EF vs kJ. The fitted slope is
fatigue resistance — what separates two runners with the same fresh
CP/VO2max. First 5 min of EF excluded (HR lag), but its work still
counts toward the dose. Hot runs fade extra from thermoregulation, so
the slope is also given for cool days only (needs data/weather.csv).
"""
import numpy as np
import pandas as pd

from .common import load_runs, load_stream
from .decoupling import HOT_DEW, WARMUP

BIN_KJ = 100


def ef_by_kj(stream, bin_kj=BIN_KJ):
    """Rel-EF Series indexed by kJ bin, normalized to the run's first bin."""
    s = stream.dropna(subset=["power", "hr"])
    if not len(s):
        return None
    kj_bin = (s["power"].cumsum() / 1000 // bin_kj).astype(int)
    keep = s.index >= WARMUP
    if not keep.any():
        return None
    m = (s["power"] / s["hr"])[keep].groupby(kj_bin[keep]).mean()
    return m / m.iloc[0]


def collect(runs):
    """[(run row, rel-EF curve)] for every run with a usable power+HR stream."""
    out = []
    for _, r in runs.iterrows():
        c = ef_by_kj(load_stream(r["activityId"]))
        if c is not None and len(c) >= 2:
            out.append((r, c))
    return out


def fade(curves):
    """(slope, intercept) of rel EF vs kJ, fitted over every run's bins."""
    # ponytail: pools all bins equally, so long runs weigh more; per-run
    # slopes averaged would fix that if composition bias starts to matter
    x = [(i + 0.5) * BIN_KJ for _, c in curves for i in c.index]
    y = [v for _, c in curves for v in c.values]
    return tuple(np.polyfit(x, y, 1))


def main():
    runs = load_runs()
    curves = collect(runs)
    print("=== Durability: efficiency fade as work accumulates ===\n")
    print(f"EF = power/HR, each run vs its own first {BIN_KJ} kJ, "
          "pooled across runs.\n")
    pooled = pd.concat([c.rename(i) for i, (_, c) in enumerate(curves)], axis=1)
    med, n = pooled.median(axis=1), pooled.count(axis=1)
    print(f"{'kJ done':>11} {'rel EF':>7} {'runs':>5}")
    for i in med.index.sort_values():
        print(f"{i * BIN_KJ:5d}-{(i + 1) * BIN_KJ:<5d} {med[i]:6.1%} {n[i]:5d}")

    slope, _ = fade(curves)
    print(f"\nFade: {slope * 1000:+.1%} power-at-same-HR per 1000 kJ of work")
    if "dew_c" in runs.columns:
        cool = [(r, c) for r, c in curves
                if pd.notna(r["dew_c"]) and r["dew_c"] < HOT_DEW]
        if len(cool) >= 5:
            cs, _ = fade(cool)
            print(f"Cool days only (dew point < {HOT_DEW}°C): {cs * 1000:+.1%} "
                  f"per 1000 kJ ({len(cool)} runs)")
    top = max(c.index.max() for _, c in curves) * BIN_KJ
    print(f"Longest dose on record: ~{top} kJ; bins past "
          f"~{int(n[n >= 3].index.max() + 1) * BIN_KJ} kJ rest on <3 runs "
          "(the longest, easiest runs — composition, not recovery)")


if __name__ == "__main__":
    main()
