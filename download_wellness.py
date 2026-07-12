#!/usr/bin/env python3
"""Download daily resting HR, nightly HRV and sleep into data/wellness.csv.

Covers from 7 days before the first run through today, or from
--start (YYYY-MM-DD). Skips dates already in the csv. Safe to re-run.
"""
import argparse
import csv
import json
import os
from datetime import date, timedelta

from garminconnect import Garmin

PATH = "data/wellness.csv"
FIELDS = ["date", "rhr", "hrv", "hrv_weekly", "hrv_low", "hrv_high", "status",
          "sleep_h", "sleep_score"]


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--start", metavar="YYYY-MM-DD",
                   help="first date to fetch (default: 7 days before first run)")
    args = p.parse_args()

    g = Garmin()
    g.login(os.path.expanduser("~/.garminconnect"))

    if args.start:
        start = date.fromisoformat(args.start)
    else:
        runs = json.load(open("data/runs.json"))
        start = date.fromisoformat(min(r["startTimeLocal"][:10] for r in runs)) \
            - timedelta(days=7)

    have = {}
    if os.path.exists(PATH):
        have = {r["date"]: r for r in csv.DictReader(open(PATH))}

    d = start
    while d <= date.today():
        ds = d.isoformat()
        if ds not in have:
            row = {"date": ds}
            try:
                rhr = g.get_rhr_day(ds)
                m = rhr["allMetrics"]["metricsMap"]["WELLNESS_RESTING_HEART_RATE"]
                row["rhr"] = m[0]["value"] if m else ""
            except Exception:
                row["rhr"] = ""
            try:
                s = (g.get_hrv_data(ds) or {}).get("hrvSummary", {})
                row.update(hrv=s.get("lastNightAvg", ""),
                           hrv_weekly=s.get("weeklyAvg", ""),
                           hrv_low=s.get("baseline", {}).get("balancedLow", ""),
                           hrv_high=s.get("baseline", {}).get("balancedUpper", ""),
                           status=s.get("status", ""))
            except Exception:
                pass
            try:
                sd = (g.get_sleep_data(ds) or {}).get("dailySleepDTO") or {}
                secs = sd.get("sleepTimeSeconds")
                row["sleep_h"] = round(secs / 3600, 2) if secs else ""
                row["sleep_score"] = ((sd.get("sleepScores") or {})
                                      .get("overall", {}).get("value", ""))
            except Exception:
                pass
            have[ds] = row
            print(f"{ds}  rhr={row.get('rhr', '')} hrv={row.get('hrv', '')}")
        d += timedelta(days=1)

    with open(PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(have.values(), key=lambda r: r["date"]))
    print(f"Wrote {PATH} ({len(have)} days)")


if __name__ == "__main__":
    main()
