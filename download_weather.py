#!/usr/bin/env python3
"""Download per-activity weather into data/weather.csv.

Skips activity IDs already in the csv (a run with no weather, e.g.
treadmill, is cached as a blank row). Safe to re-run.
"""
import csv
import json
import os

from garminconnect import Garmin

PATH = "data/weather.csv"
FIELDS = ["activityId", "temp_c", "feels_c", "dew_c", "humidity",
          "wind_kmh", "conditions"]


def f2c(f):
    return round((f - 32) / 1.8, 1)


def main():
    g = Garmin()
    g.login(os.path.expanduser("~/.garminconnect"))
    runs = json.load(open("data/runs.json"))

    have = {}
    if os.path.exists(PATH):
        have = {r["activityId"]: r for r in csv.DictReader(open(PATH))}

    for r in runs:
        aid = str(r["activityId"])
        if aid in have:
            continue
        row = {"activityId": aid}
        try:
            w = g.get_activity_weather(aid) or {}
            # Garmin's weather DTO is imperial (°F, mph) regardless of settings
            for col, key in (("temp_c", "temp"), ("feels_c", "apparentTemp"),
                             ("dew_c", "dewPoint")):
                row[col] = f2c(w[key]) if w.get(key) is not None else ""
            row["humidity"] = w.get("relativeHumidity", "")
            row["wind_kmh"] = (round(w["windSpeed"] * 1.609)
                               if w.get("windSpeed") is not None else "")
            row["conditions"] = (w.get("weatherTypeDTO") or {}).get("desc") or ""
        except Exception as e:
            print(f"{r['startTimeLocal'][:10]}  {aid}  no weather ({e})")
        have[aid] = row
        if row.get("temp_c", "") != "":
            print(f"{r['startTimeLocal'][:10]}  {row['temp_c']:>5}°C  "
                  f"dew {row['dew_c']:>5}°C  {row['conditions']}")

    with open(PATH, "w", newline="") as f:
        wtr = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        wtr.writeheader()
        wtr.writerows(have.values())
    print(f"Wrote {PATH} ({len(have)} activities)")


if __name__ == "__main__":
    main()
