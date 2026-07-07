# running-ops

Personal running analytics for Garmin. Downloads your runs, per-second
power/HR/dynamics streams and daily wellness data (resting HR, HRV, sleep)
from Garmin Connect, then generates 15 analyses — from weekly volume to
Critical Power modeling, W'bal, training load (TRIMP/PMC), effective VO2max
with race predictions, grade-adjusted pace, and recovery tracking.

**Stryd** pods are supported — their power data is read automatically and
used in favor of Garmin's native power. Pass `--ignore-stryd` to any
analysis command to use native power instead.

## Privacy

**Your data doesn't leave your machine — unless you choose to share data.**
The scripts talk directly to Garmin's API with your own account;
everything is written to local files (`data/`, `report/`) that are
gitignored. No third-party services, no telemetry, nothing shared with
anyone.

The only way data leaves is if you decide to: `--zip` builds a share
archive, to send to someone (a coach, this project's maintainers). By
default it contains everything that was downloaded — including GPS
coordinates and activity names. Add `--privacy` to anonymize it: GPS
coordinates, activity/location names and account IDs are then stripped,
leaving only training metrics (power/HR/pace streams, wellness trends)
and the report. Auth tokens are never included either way.

## Quick start (one-liner)

Everything — install, download, analyze, PDF — in one call (needs
[uv](https://docs.astral.sh/uv/) and Chrome or Brave installed; first run
asks for your Garmin login + emailed MFA code):

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python garminconnect pandas matplotlib markdown && .venv/bin/python download_runs.py && .venv/bin/python download_streams.py && .venv/bin/python download_wellness.py && .venv/bin/python -m analysis.report --pdf
```

The finished report lands in `report/report.pdf` (plus `.md` and `.html`).

## Setup

Requires Python 3.10+ (managed here with [uv](https://docs.astral.sh/uv/)):

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python garminconnect pandas matplotlib markdown
```

## Downloading your data

```bash
.venv/bin/python download_runs.py       # last 50 runs -> data/runs.json + runs.csv
.venv/bin/python download_streams.py    # per-second streams -> data/streams/
.venv/bin/python download_wellness.py   # daily RHR/HRV/sleep -> data/wellness.csv
```

`download_runs.py` takes the last 50 runs by default; pick a different
amount or a date range instead:

```bash
.venv/bin/python download_runs.py -n 100                           # last 100 runs
.venv/bin/python download_runs.py --start 2026-06-01               # everything since June 1
.venv/bin/python download_runs.py --start 2026-06-01 --end 2026-06-30   # June only
```

**First run: you'll be asked to log in.** Enter your Garmin email and
password; Garmin will then email you an MFA code — type it at the
`MFA code:` prompt. After that, auth tokens are saved to
`~/.garminconnect` and all further downloads run without any login.

(Two `429 — IP rate limited` lines during login are normal; the library
falls back to a slower login path and continues.)

Downloads are incremental: already-fetched runs, streams and days are
skipped, so re-running is cheap and only picks up what's new.

## Analyzing

```bash
.venv/bin/python -m analysis            # all analyses, text output in the terminal
.venv/bin/python -m analysis.volume     # or any single one (cp, wbal, intervals,
                                        # zones, quadrant, load, vo2max, recovery,
                                        # decoupling, dynamics, elevation, fitness,
                                        # correlate, bests)
```

## Correlations

Any two columns can be paired — raw Garmin datapoints (distance, HR,
cadence, elevation…), wellness data (HRV, resting HR, sleep) and every
calculated metric (TRIMP, CTL/ATL/TSB, decoupling, W' depletion,
effective VO2max…) all live in one per-run frame, so any combination is
one command away. You get the Pearson correlation, a per-run table and a
chart PNG; `--list` shows all available columns.

```bash
# does a well-recovered morning (high HRV) make the run more efficient?
.venv/bin/python -m analysis.correlate hrv m_per_beat

# does short sleep show up as slower pace?
.venv/bin/python -m analysis.correlate sleep_h pace_s

# is the fitness you're building (CTL) actually lifting your VO2max?
.venv/bin/python -m analysis.correlate ctl evo2
```

A pairing worth keeping permanently becomes a chapter in the report's
**Correlations** section: add one entry to `CHAPTERS` in
`analysis/correlate.py` and it shows up in every future report as its
own panel with a proper title and axis labels — no plotting code needed.

```python
CHAPTERS = [
    ...
    # (title, left axis [(column, label)], right axis [(column, label)])
    ("Sleep vs next-day pace",
     [("sleep_h", "sleep (h)")], [("pace_s", "pace (s/km)")]),
]
```

Column names are the same ones `--list` shows; the labels are free text
for the chart axes. Mind the usual caveat: with ~50 runs these are
exploratory correlations, not proof of causation.

## The report

```bash
.venv/bin/python -m analysis.report        # report/report.md + PNG charts
.venv/bin/python -m analysis.report --pdf  # + report.html and report.pdf
```

A **markdown report with charts** is generated in `report/`; `--pdf` also
produces a standalone **HTML page and a PDF** (rendered locally via
headless Chrome or Brave — one of the two must be installed). The report
contains every analysis section with its chart and full text output,
stamped with the generation date.

To share your data (e.g. with a coach or for debugging an analysis),
`--zip` creates `report/share-<date>.zip` with the report plus all
downloaded data; add `--privacy` to strip location and identity first —
see the privacy section above for exactly what that removes.

## Tests

The sports-science math is verified against published reference values
(Daniels VDOT tables), closed-form solutions (W'bal) and hand-computed
constants (TRIMP):

```bash
.venv/bin/python -m unittest
```
