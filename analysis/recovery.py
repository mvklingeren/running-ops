"""Recovery: nightly HRV and resting HR vs training load.

HRV dropping below its baseline band or RHR creeping up while volume
rises = not absorbing the load.
"""
import pandas as pd

from .common import bar, load_runs


def load_wellness():
    w = pd.read_csv("data/wellness.csv", parse_dates=["date"])
    return w.set_index("date")


def main():
    w = load_wellness()
    runs = load_runs()
    km = runs.set_index("startTimeLocal")["km"].resample("D").sum()

    print("=== Recovery: HRV & resting HR vs load ===\n")
    lo, hi = w["hrv_low"].iloc[-1], w["hrv_high"].iloc[-1]
    hrv7 = w["hrv_weekly"].iloc[-1]
    inband = "inside" if lo <= hrv7 <= hi else "OUTSIDE"
    print(f"HRV baseline (balanced): {lo:.0f}-{hi:.0f} ms; "
          f"current 7-day avg {hrv7:.0f} ms ({inband} the band)\n")

    print("Last 14 days:")
    print(f"{'date':>10} {'km':>5} {'HRV':>4} {'RHR':>4} {'sleep':>6} "
          f"{'score':>5}  status")
    recent = w.tail(14)
    for d, r in recent.iterrows():
        k = km.get(d, 0)
        flag = ""
        if pd.notna(r["hrv"]) and r["hrv"] < lo:
            flag = " ⚠ below baseline"
        if pd.notna(r.get("sleep_h")) and r["sleep_h"] < 6:
            flag += " ⚠ short sleep"
        sleep = f"{r['sleep_h']:5.1f}h" if pd.notna(r.get("sleep_h")) else "     -"
        score = f"{r['sleep_score']:5.0f}" if pd.notna(r.get("sleep_score")) \
            else "    -"
        print(f"{d:%m-%d} {k:9.1f} {r['hrv']:4.0f} {r['rhr']:4.0f} {sleep} "
              f"{score}  {str(r['status']).lower()}{flag}")

    weekly_km = km.resample("W").sum()
    weekly_hrv = w["hrv"].resample("W").mean()
    weekly_rhr = w["rhr"].resample("W").mean()
    weekly_sleep = w["sleep_h"].resample("W").mean()
    print(f"\n{'week ending':>12} {'km':>6} {'HRV':>5} {'RHR':>5} {'sleep':>6}  load")
    for wk in weekly_km.index:
        print(f"{wk:%Y-%m-%d} {weekly_km.get(wk, 0):6.1f} "
              f"{weekly_hrv.get(wk, float('nan')):5.0f} "
              f"{weekly_rhr.get(wk, float('nan')):5.1f} "
              f"{weekly_sleep.get(wk, float('nan')):5.1f}h  "
              f"{bar(weekly_km.get(wk, 0), weekly_km.max(), 20)}")

    # verdict: compare this week's recovery markers to the rest
    base_hrv, base_rhr = w["hrv"].iloc[:-7].mean(), w["rhr"].iloc[:-7].mean()
    cur_hrv, cur_rhr = w["hrv"].tail(7).mean(), w["rhr"].tail(7).mean()
    print(f"\nThis week vs prior avg: HRV {cur_hrv:.0f} vs {base_hrv:.0f} ms "
          f"({cur_hrv - base_hrv:+.0f}), RHR {cur_rhr:.1f} vs {base_rhr:.1f} "
          f"({cur_rhr - base_rhr:+.1f})")
    cur_sleep = w["sleep_h"].tail(7).mean()
    if pd.notna(cur_sleep):
        print(f"Sleep last 7 days: {cur_sleep:.1f} h/night avg")
    if cur_hrv >= base_hrv and cur_rhr <= base_rhr + 1:
        verdict = "absorbing the load — HRV holding, RHR stable"
        if pd.notna(cur_sleep) and cur_sleep < 7:
            verdict += ", but sleep is the weak link"
        print(f"Verdict: {verdict}.")
    else:
        print("Verdict: recovery markers dipping — watch the ramp.")


if __name__ == "__main__":
    main()
