#!/usr/bin/env python3
"""Download runs from Garmin Connect into data/runs.json + data/runs.csv.

Default: the last 50 runs. -n/--count changes how many;
--start/--end (YYYY-MM-DD) downloads all runs in a date range instead.
Afterwards runs download_streams.py and download_weather.py so the
per-run caches always match runs.json.

First run prompts for Garmin credentials (and MFA code if enabled);
tokens are saved to ~/.garminconnect so later runs need no login.
"""
import argparse
import csv
import json
import os
import subprocess
import sys
from getpass import getpass

from garminconnect import Garmin

TOKENSTORE = os.path.expanduser("~/.garminconnect")
N_RUNS = 50
COLS = ["activityId", "activityName", "startTimeLocal", "distance",
        "duration", "elapsedDuration", "averageSpeed", "maxSpeed",
        "averageHR", "maxHR", "calories", "elevationGain", "elevationLoss",
        "avgGradeAdjustedSpeed", "averageRunningCadenceInStepsPerMinute",
        "aerobicTrainingEffect", "anaerobicTrainingEffect", "vO2MaxValue",
        "avgRespirationRate", "minTemperature", "maxTemperature",
        "fastestSplit_1000", "fastestSplit_1609", "fastestSplit_5000",
        "fastestSplit_10000", "fastestSplit_21098"]


def login():
    try:
        g = Garmin()
        g.login(TOKENSTORE)  # reuse saved tokens
        return g
    except Exception:
        pass
    email = input("Garmin email: ")
    password = getpass("Garmin password: ")
    g = Garmin(email=email, password=password,
               prompt_mfa=lambda: input("MFA code: "))
    g.login(TOKENSTORE)  # logs in and saves tokens to TOKENSTORE
    print(f"Tokens saved to {TOKENSTORE}")
    return g


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = p.add_mutually_exclusive_group()
    group.add_argument("-n", "--count", type=int, default=N_RUNS, metavar="N",
                       help=f"download the last N runs (default {N_RUNS})")
    group.add_argument("--start", metavar="YYYY-MM-DD",
                       help="download all runs from this date (use with --end)")
    p.add_argument("--end", metavar="YYYY-MM-DD",
                   help="end of date range (default: today)")
    args = p.parse_args()
    if args.end and not args.start:
        p.error("--end requires --start")

    g = login()
    if args.start:
        activities = g.get_activities_by_date(args.start, args.end,
                                              activitytype="running")
        limit = None
    else:
        # fetch a batch and filter client-side; oversize so -n > runs still fits
        activities = g.get_activities(0, max(200, 2 * args.count))
        limit = args.count
    runs = [a for a in activities
            if "running" in a.get("activityType", {}).get("typeKey", "")][:limit]
    print(f"Found {len(runs)} runs")

    os.makedirs("data", exist_ok=True)
    with open("data/runs.json", "w") as f:
        json.dump(runs, f, indent=2)

    with open("data/runs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(runs)
    print("Wrote data/runs.json and data/runs.csv")

    # streams/weather are per-run caches keyed off runs.json — keep them in
    # sync automatically (incremental, so a no-op when nothing changed).
    # wellness is day-based and can backfill years; run it manually.
    for script in ("download_streams.py", "download_weather.py"):
        print(f"\n--- {script} ---")
        subprocess.run([sys.executable, script], check=True)


if __name__ == "__main__":
    main()
