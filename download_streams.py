#!/usr/bin/env python3
"""Download per-second streams (power/speed/HR) for runs in data/runs.json.

Skips runs already in data/streams/. Safe to re-run.
"""
import json
import os

from garminconnect import Garmin

KEYS = ["directTimestamp", "directPower", "directSpeed", "directHeartRate",
        "directDoubleCadence", "directStrideLength",
        "directGroundContactTime", "directVerticalOscillation",
        "directVerticalRatio"]


def main():
    g = Garmin()
    g.login(os.path.expanduser("~/.garminconnect"))
    runs = json.load(open("data/runs.json"))
    os.makedirs("data/streams", exist_ok=True)

    for r in runs:
        aid = r["activityId"]
        path = f"data/streams/{aid}.json"
        if os.path.exists(path):
            continue
        d = g.get_activity_details(aid, maxchart=100000)
        idx = {m["key"]: m["metricsIndex"] for m in d["metricDescriptors"]}
        cols = {k: [] for k in KEYS}
        for p in d["activityDetailMetrics"]:
            for k in KEYS:
                v = p["metrics"][idx[k]] if k in idx else None
                cols[k].append(v)
        with open(path, "w") as f:
            json.dump(cols, f)
        print(f"{r['startTimeLocal'][:10]}  {r['distance']/1000:5.1f} km  "
              f"{len(d['activityDetailMetrics'])} points -> {path}")


if __name__ == "__main__":
    main()
