"""Shared loading + helpers for run analysis modules."""
import json

import pandas as pd


def load_runs(path="data/runs.csv"):
    df = pd.read_csv(path, parse_dates=["startTimeLocal"])
    df = df.sort_values("startTimeLocal").reset_index(drop=True)
    df["km"] = df["distance"] / 1000
    df["pace_s"] = df["duration"] / df["km"]  # seconds per km
    # meters covered per heartbeat — higher = same speed at less effort
    df["m_per_beat"] = df["distance"] / (df["averageHR"] * df["duration"] / 60)
    return df


def load_stream(activity_id):
    """Per-second stream for one run: DataFrame(power, speed, hr), index = elapsed s."""
    with open(f"data/streams/{activity_id}.json") as f:
        d = json.load(f)
    ts = pd.to_datetime(d["directTimestamp"], unit="ms")
    cols = {"power": "directPower", "speed": "directSpeed",
            "hr": "directHeartRate", "cadence": "directDoubleCadence",
            "stride": "directStrideLength", "gct": "directGroundContactTime",
            "vo": "directVerticalOscillation",
            "vratio": "directVerticalRatio"}
    if all(v is None for v in d.get("directPower", [])):
        ciq = [k for k in sorted(d) if k.startswith("connectIQDeveloperField")
               and any(v is not None for v in d[k])]
        if ciq:
            #  Stryd writes power via a Connect IQ dev field, not
            # directPower; multiple CIQ fields would need metricDescriptors
            # units to disambiguate
            cols["power"] = ciq[0]
    df = pd.DataFrame({n: d[k] for n, k in cols.items() if k in d},
                      index=ts, dtype=float)
    df = df[~df.index.duplicated()].resample("1s").mean().interpolate(limit=15)
    df.index = (df.index - df.index[0]).total_seconds().astype(int)
    return df


def fmt_pace(sec_per_km):
    m, s = divmod(int(round(sec_per_km)), 60)
    return f"{m}:{s:02d}/km"


def fmt_hms(seconds):
    h, rem = divmod(int(round(seconds)), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def bar(value, vmax, width=30, char="█"):
    n = int(round(width * value / vmax)) if vmax else 0
    return char * max(n, 1 if value > 0 else 0)
