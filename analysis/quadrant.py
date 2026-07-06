"""Quadrant analysis, running edition: step force vs cadence.

Cycling plots pedal force vs pedal velocity; the running equivalent is
force per step (power/speed, N) vs cadence (steps/min):
  high force + low cadence  = bounding/overstriding (grinding)
  high force + high cadence = powerful fast running
  low force + high cadence  = quick light turnover (spinning)
  low force + low cadence   = easy shuffling
Split lines = your median force and median cadence.
"""
import pandas as pd

from .common import load_runs, load_stream


def force_cadence(runs):
    frames = []
    for _, r in runs.iterrows():
        s = load_stream(r["activityId"])[["power", "speed", "cadence", "hr"]]
        s = s[(s["speed"] > 1) & (s["cadence"] > 100)].dropna()
        s["force"] = s["power"] / s["speed"]  # N, average per-step force proxy
        frames.append(s)
    return pd.concat(frames, ignore_index=True)


def main():
    df = force_cadence(load_runs())
    f_med, c_med = df["force"].median(), df["cadence"].median()

    print("=== Quadrant analysis: step force vs cadence ===\n")
    print(f"Median force   : {f_med:.0f} N   Median cadence: {c_med:.0f} spm\n")
    quads = [
        ("Q1 grind (hi force, lo cadence)",
         (df["force"] >= f_med) & (df["cadence"] < c_med)),
        ("Q2 power (hi force, hi cadence)",
         (df["force"] >= f_med) & (df["cadence"] >= c_med)),
        ("Q3 spin  (lo force, hi cadence)",
         (df["force"] < f_med) & (df["cadence"] >= c_med)),
        ("Q4 easy  (lo force, lo cadence)",
         (df["force"] < f_med) & (df["cadence"] < c_med)),
    ]
    for name, mask in quads:
        sub = df[mask]
        print(f"{name}: {mask.mean():5.1%} of time, "
              f"avg {sub['power'].mean():.0f} W at {sub['hr'].mean():.0f} bpm")

    fast = df[df["speed"] > df["speed"].quantile(0.9)]
    how = "cadence" if (fast["cadence"].mean() - c_med) / c_med > \
        (fast["force"].mean() - f_med) / f_med else "force"
    print(f"\nAt your fastest 10% of running you add {how} first "
          f"({fast['cadence'].mean():.0f} spm, {fast['force'].mean():.0f} N "
          f"vs medians {c_med:.0f}/{f_med:.0f})")


if __name__ == "__main__":
    main()
