"""Weekly volume: totals, trend, long-run share, ramp warnings."""
from .common import bar, load_runs


def main():
    df = load_runs()
    weekly = df.set_index("startTimeLocal").resample("W")
    km = weekly["km"].sum()
    n_runs = weekly["km"].count()
    longest = weekly["km"].max().fillna(0)

    print(f"=== Weekly volume ({df['km'].sum():.0f} km total, "
          f"{len(df)} runs) ===\n")
    print(f"{'week ending':>12} {'km':>6} {'runs':>4} {'Δ prev':>8}  chart")
    prev = None
    for week, k in km.items():
        delta = "" if prev in (None, 0) else f"{(k - prev) / prev:+.0%}"
        warn = " ⚠ ramp" if prev and k > prev * 1.5 and k > 20 else ""
        print(f"{week:%Y-%m-%d} {k:6.1f} {n_runs[week]:4d} {delta:>8}  "
              f"{bar(k, km.max())}{warn}")
        prev = k

    print(f"\nAvg week        : {km.mean():.1f} km")
    print(f"Biggest week    : {km.max():.1f} km ({km.idxmax():%Y-%m-%d})")
    share = longest / km.replace(0, float("nan"))
    print(f"Long-run share  : biggest run is {share.mean():.0%} of its week "
          f"on average (guideline: keep under ~50%)")
    lr = df.loc[df.groupby(df["startTimeLocal"].dt.isocalendar().week)["km"]
                .idxmax()]
    prog = lr[lr["km"] >= 8].sort_values("startTimeLocal")
    if len(prog) > 1:
        print("Long-run build  : " +
              " → ".join(f"{k:.1f}" for k in prog["km"]) + " km")


if __name__ == "__main__":
    main()
