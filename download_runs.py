#!/usr/bin/env python3
"""Download the last 25 runs from Garmin Connect into data/runs.json + data/runs.csv.

First run prompts for Garmin credentials (and MFA code if enabled);
tokens are saved to ~/.garminconnect so later runs need no login.
"""
import csv
import json
import os
from getpass import getpass

from garminconnect import Garmin

TOKENSTORE = os.path.expanduser("~/.garminconnect")
N_RUNS = 25
COLS = ["activityId", "activityName", "startTimeLocal", "distance",
        "duration", "elapsedDuration", "averageSpeed", "maxSpeed",
        "averageHR", "maxHR", "calories", "elevationGain", "elevationLoss",
        "avgGradeAdjustedSpeed", "averageRunningCadenceInStepsPerMinute",
        "aerobicTrainingEffect", "anaerobicTrainingEffect", "vO2MaxValue"]


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
    g = login()
    # ponytail: fetch a batch and filter client-side; 200 is plenty to find 25 runs
    activities = g.get_activities(0, 200)
    runs = [a for a in activities
            if "running" in a.get("activityType", {}).get("typeKey", "")][:N_RUNS]
    print(f"Found {len(runs)} runs")

    os.makedirs("data", exist_ok=True)
    with open("data/runs.json", "w") as f:
        json.dump(runs, f, indent=2)

    with open("data/runs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(runs)
    print("Wrote data/runs.json and data/runs.csv")


if __name__ == "__main__":
    main()
