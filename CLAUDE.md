# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Personal Garmin running analytics: three downloader scripts pull data from Garmin Connect into `data/`, and the `analysis/` package turns it into terminal output and a markdown report with charts.

## Environment

Use `.venv/bin/python` for everything — it's Python 3.12 (managed by `uv`). The system Python is 3.9 and the pinned old `garminconnect`/`garth` versions it forces are rejected by Garmin's SSO with 401s. Add dependencies with `uv pip install --python .venv/bin/python <pkg>`.

## Commands

```bash
# Refresh data (in this order — streams and wellness read data/runs.json)
.venv/bin/python download_runs.py       # last 25 runs -> data/runs.json + runs.csv
.venv/bin/python download_streams.py    # 1s power/HR/dynamics per run -> data/streams/<id>.json
.venv/bin/python download_wellness.py   # daily RHR + HRV -> data/wellness.csv

# Analyze
.venv/bin/python -m analysis            # all modules, text to terminal
.venv/bin/python -m analysis.volume     # any single module the same way
.venv/bin/python -m analysis.report     # report/report.md + PNGs (--html and/or --pdf for those formats;
                                        # pdf renders report.html via headless Chrome/Brave/Edge)
```

There are no tests or linters. Sanity check = run the module and read the numbers.

## Garmin auth

`Garmin().login("~/.garminconnect")` reuses saved tokens; no credentials needed once tokens exist. If tokens expire, the user must run `download_runs.py` interactively (password + emailed MFA code) — never ask for or handle their password yourself. Garmin rate-limits logins (429 on the fast paths is normal noise; the library falls back).

## Architecture

- **Downloaders are incremental caches.** `download_streams.py` skips activity IDs already in `data/streams/`; `download_wellness.py` skips dates already in the csv. To force a re-fetch with new stream metrics: add the key to `KEYS` in `download_streams.py`, map it to a column in `common.load_stream`, `rm -rf data/streams`, re-run.
- **Every analysis module follows one pattern:** a `main()` that prints a text report, runnable via `python -m analysis.<name>`. `analysis/__main__.py` runs them all; `analysis/report.py` builds the markdown report by calling each module's chart function and capturing its `main()` stdout via `redirect_stdout` — so terminal output and report text can never diverge. To add a module: write `main()`, add it to the tuple in `__main__.py`, add a `(title, png, chart_fn, module)` entry to `sections` in `report.py`.
- **`analysis/common.py` is the only data access layer:** `load_runs()` (summary DataFrame with derived km/pace/m_per_beat) and `load_stream(activity_id)` (per-second DataFrame resampled to a 1 s index: power, speed, hr, cadence, stride, gct, vo, vratio).
- **Cross-module dependency:** `cp.fit_cp(cp.mmp_curve(runs))` provides the Critical Power estimate that `wbal`, `intervals`, and `zones` all consume. It's recomputed per module (cheap, seconds).

## Domain gotchas

- CP (currently ~388 W) is overestimated because the data has no all-out 20+ min effort; W'bal going below zero ("&gt;100% depleted") is that model error surfacing, not a bug.
- Two early runs (May 22/23) were recorded in smart-recording mode — sparse streams with big gaps; stream-based metrics for them are unreliable. `load_stream` interpolates only gaps ≤15 s by design.
- Pw:Hr decoupling is only meaningful on steady runs; interval days legitimately show 10%+ drift.
- No SmO2/tHb (NIRS) fields exist in this user's streams — needs a muscle-oxygen sensor; don't build analysis for it.
- `load` (TRIMP) and `vo2max` anchor on HRmax = observed max across runs and HRrest = mean wellness RHR — estimates, not lab values; both modules print the values they used.
