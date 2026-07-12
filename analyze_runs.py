#!/usr/bin/env python3
"""Analyze downloaded runs (data/runs.csv): totals, pace/HR trends, weekly volume, bests."""
import math

import pandas as pd

pd.options.display.float_format = "{:.2f}".format


def fmt_pace(sec_per_km):
    if not math.isfinite(sec_per_km):  # NaN or inf (zero-distance run)
        return "-"
    m, s = divmod(int(round(sec_per_km)), 60)
    return f"{m}:{s:02d}/km"


def main():
    df = pd.read_csv("data/runs.csv", parse_dates=["startTimeLocal"])
    df = df.sort_values("startTimeLocal").reset_index(drop=True)
    df["km"] = df["distance"] / 1000
    df["pace_s_per_km"] = df["duration"] / df["km"]
    df["pace"] = df["pace_s_per_km"].apply(fmt_pace)

    print(f"=== {len(df)} runs, {df['startTimeLocal'].min():%Y-%m-%d} to "
          f"{df['startTimeLocal'].max():%Y-%m-%d} ===\n")
    print(f"Total distance : {df['km'].sum():.1f} km")
    print(f"Total time     : {df['duration'].sum() / 3600:.1f} h")
    print(f"Avg distance   : {df['km'].mean():.1f} km")
    print(f"Avg pace       : {fmt_pace(df['duration'].sum() / df['km'].sum())}")
    print(f"Avg HR         : {df['averageHR'].mean():.0f} bpm")

    print("\n=== Weekly volume ===")
    weekly = df.set_index("startTimeLocal").resample("W")["km"].sum()
    print(weekly.to_string())

    print("\n=== Trend (first half vs second half) ===")
    half = len(df) // 2
    for label, part in [("first", df.iloc[:half]), ("second", df.iloc[half:])]:
        pace = fmt_pace(part["duration"].sum() / part["km"].sum())
        print(f"{label:6s}: pace {pace}, avg HR {part['averageHR'].mean():.0f}")

    print("\n=== Bests ===")
    fastest = df.loc[df["pace_s_per_km"].idxmin()]
    longest = df.loc[df["km"].idxmax()]
    print(f"Fastest: {fastest['pace']} ({fastest['km']:.1f} km on "
          f"{fastest['startTimeLocal']:%Y-%m-%d})")
    print(f"Longest: {longest['km']:.1f} km ({longest['pace']} on "
          f"{longest['startTimeLocal']:%Y-%m-%d})")

    print("\n=== All runs ===")
    print(df[["startTimeLocal", "km", "pace", "averageHR", "elevationGain"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
