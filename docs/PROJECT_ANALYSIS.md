# running-ops — project analysis & roadmap

*Assessment date: 2026-07-07. Scope: full codebase review (all 16 analysis
modules, 3 downloaders, report pipeline, 55-test suite — all passing).*

## TL;DR

| Question | Verdict |
|---|---|
| Is it complete? | **~80% of a personal tool, ~50% of a distributable one.** The analytics core is done and tested; identity (athlete name), packaging, config, non-power fallbacks and cross-platform PDF are missing. |
| Professional-grade calculations? | **Exceptional density for 2,400 lines** — it already computes things Strava doesn't (CP/W', W'bal, monotony/strain). To beat Strava/Runalyze/GoldenCheetah *in numbers* it needs ~12 more metrics (listed below), led by model-confidence reporting (CP fit quality, endurance-corrected predictions). |

> **Scope decision (2026-07-08):** the tool targets runners on current
> performance watches (Forerunner 255+/Fenix 7+/Epix/Enduro, ~2022 onward, or
> Stryd), which all record running power. Watches without power — including
> current lifestyle models (Venu, vívoactive, FR55/165) and 5-year-old
> devices — are out of scope. The HR+pace fallback lane is therefore
> deprioritized from "top item" to nice-to-have; what remains in scope is
> failing soft on the odd power-less stream and never mixing Stryd and
> Garmin-native watts in one CP fit (§4).
| Biggest structural risk | Every module re-reads every stream and refits CP on every invocation; per-run tables grow linearly with run count. Fine at 50 runs, painful at 500. |
| Report bloat at 50+ runs | Solvable with one shared compact-table helper (head/tail + "… n more"), weekly aggregation, and `<details>` sections in HTML. Design sketch below. |

---

## 1. Current state

**Architecture is genuinely good.** The three-layer split (incremental
downloaders → `common.py` as the single data-access layer → one-pattern
analysis modules) is clean, and the `redirect_stdout` trick in `report.py`
guarantees the terminal and the report can never diverge. Adding a module is
a 3-line registration. The test suite verifies real sports-science math
against published references (Daniels VDOT, closed-form W'bal, hand-computed
TRIMP) and runs in 0.13 s with no data or network — that is better test
hygiene than most open-source sports tools.

**What exists today (15 report sections):** weekly volume + ramp warnings,
m/beat efficiency trend, CP/W' model + MMP curve, W'bal per run, interval
discovery + pacing index, power/HR time-in-zone, force-vs-cadence quadrant,
TRIMP + PMC (CTL/ATL/TSB) + Foster monotony/strain, effective VO2max + race
prognosis, HRV/RHR/sleep recovery, aerobic decoupling, running dynamics
(GCT/VO/vRatio + form-under-fatigue), grade-adjusted-pace hill cost, a
generic correlation engine, and bests/PRs from Garmin fastest-splits.

## 2. Completeness audit — what's missing

### 2.1 Athlete identity (the report is anonymous)

The report header is `# Running report — <date> to <date>`. No athlete name,
age, weight, HRmax/HRrest used, or gear. For a tool meant to be shared with a
coach (the stated purpose of `--zip`), the PDF must say whose data it is.

Fix: an **athlete profile** with two sources, merged:

1. `download_runs.py` saves `data/profile.json` from the Garmin API
   (`get_full_name()`, and `get_user_summary`/body-composition for weight —
   weight also unlocks W/kg, see §4).
2. A user-editable `athlete.toml` (name, weight, HRmax/HRrest/LTHR overrides,
   units) that wins over the Garmin values. This doubles as the config file
   the project currently lacks.

The report header becomes
`# Running report — <name> · <date range> · <n> runs / <km> km`, and each
model prints which anchors it used (load/vo2max already do — extend this).
The `--privacy` zip must strip `profile.json` and the name from the report,
same as it strips `runs.json` today.

### 2.2 Other completeness gaps

| Gap | Where | Impact |
|---|---|---|
| **PDF export is macOS-only** | `report.py` hardcodes `/Applications/...` browser paths | Linux/Windows users silently get no PDF; README promises "Chrome or Brave" without the caveat |
| **No packaging** | no `pyproject.toml`, no pinned versions, install is a README one-liner | can't `pip install`, no `running-ops` CLI entry point, dependency drift |
| **No config layer** | thresholds live as constants (zone %CP bounds, ramp >50%/20 km, long run ≥10 km, 5% decoupling line, histogram bins 100–500 W / 100–200 bpm, quadrant axes 120–200 spm) | wrong defaults for slower/faster athletes; forks required to tune |
| **Power is a hard requirement** | `cp`, `wbal`, `zones`, `intervals`, `quadrant`, `decoupling`, and half of `correlate` assume a power stream | a runner without Stryd/native power gets crashes or empty sections — the majority of potential users |
| **Personal data baked into code** | `cp.py` prints "all 25 runs" (stale, hardcoded); `load.py` docstring says "~197/~43"; CLAUDE.md gotchas ("CP ~388 W", "two May runs") are one athlete's facts | confusing for any other user of an open-source release |
| **Legacy duplicate** | `analyze_runs.py` is a pre-package version of volume/bests | dead code, drifts from the real modules — delete |
| **Download model** | `runs.json` is overwritten each run, default only last 50 runs; no full-history sync | long-term athletes lose history unless they know `--start` |
| **No CI** | tests exist but nothing runs them on push | regressions land silently in an open-source setting |
| **No sample data** | everything needs a Garmin account + tokens | nobody can try the tool (or develop on it) in 30 seconds |

## 3. Calculation coverage vs Strava / Runalyze / GoldenCheetah

Legend: ✅ has it · 🟡 partial · ❌ missing

| Metric | running-ops | Strava | Runalyze | GoldenCheetah |
|---|---|---|---|---|
| Critical Power + W' (2-param) | ✅ | ❌ | ❌ | ✅ (+3-param, exp) |
| W'bal within-run (Skiba differential) | ✅ | ❌ | ❌ | ✅ |
| Mean-maximal power curve | ✅ | 🟡 (best efforts) | ❌ | ✅ |
| PMC: CTL/ATL/TSB | ✅ (TRIMP-based) | ✅ (fitness/freshness) | ✅ | ✅ |
| Banister TRIMP | ✅ | 🟡 (relative effort) | ✅ | ✅ |
| Foster monotony & strain | ✅ | ❌ | ✅ | ❌ |
| Effective VO2max from HR:pace | ✅ | ❌ | ✅ (its signature) | ❌ |
| Race predictions (Daniels) | ✅ | ❌ | ✅ (+shape corr.) | ✅ |
| Aerobic decoupling Pw:Hr | ✅ | ❌ | ❌ | ✅ |
| Time in zones | ✅ (power, %CP) | ✅ (HR/pace too) | ✅ | ✅ |
| Quadrant analysis | ✅ (running adaptation) | ❌ | ❌ | ✅ (cycling) |
| Running dynamics (GCT/VO/vRatio) | ✅ + fatigue drift | ❌ | 🟡 | 🟡 |
| Grade-adjusted pace | 🟡 (Garmin's value) | ✅ (own model) | ✅ | ✅ |
| HRV/RHR/sleep recovery | ✅ | ❌ | 🟡 | ❌ |
| Free-form metric correlations | ✅ (unique!) | ❌ | ❌ | 🟡 (R charts) |
| Interval auto-discovery | ✅ | 🟡 (laps) | ✅ | ✅ |
| **Works without a power meter** | ❌ | ✅ | ✅ | ✅ |
| **Critical Speed (pace-based CP)** | ❌ | ❌ | 🟡 | ✅ |
| **ACWR (acute:chronic 7:28)** | 🟡 (weekly ramp flag) | ❌ | ✅ | 🟡 |
| **Training intensity distribution / polarization (80/20)** | 🟡 (zone table) | ❌ | ✅ | ✅ |
| **PR/best-effort progression over time** | 🟡 (current PRs only) | ✅ | ✅ | ✅ |
| **3-param CP + fit quality (R², CI)** | ❌ | ❌ | ❌ | ✅ |
| **Riegel/endurance-corrected predictions** | ❌ (assumes endurance) | ❌ | ✅ (marathon shape) | 🟡 |
| **Weather/heat-adjusted metrics** | 🟡 (temp correlation) | ❌ | ✅ | ❌ |
| **W/kg, Running Effectiveness, LSS** | ❌ (no weight) | ❌ | ❌ | 🟡 |
| **Gear/shoe mileage** | ❌ | ✅ | ✅ | ❌ |
| **Maps/segments** | ❌ (by design — privacy) | ✅ | 🟡 | ❌ |

**Honest verdict:** in the power-analytics column it already beats Strava and
Runalyze outright and matches much of GoldenCheetah with 1% of the code. But
"better in numbers than all three" is not yet true, for two reasons:

1. **Model confidence is missing.** GC tells you how good the CP fit is;
   Runalyze corrects race predictions for demonstrated endurance. This tool
   prints a single number and (to its credit) a caveat in prose.
2. **Power-source fragility.** 7 of 15 sections require a power stream. Per
   the scope decision above, the target audience always has one — but a
   single power-less stream (treadmill, corrupt file) crashes the report
   instead of being skipped, and a mix of Stryd and Garmin-native watts
   (10–20% different scales) silently corrupts the shared CP fit.

## 4. What "better in numbers" requires — prioritized

Each of these follows the existing pattern (pure function + reference-value
test + module or extension of one):

1. **Power-source integrity**: tag each stream's power source
   (Stryd CIQ vs native `directPower`), fit CP per source or warn loudly on
   a mix (the scales differ 10–20%, and one mixed run in `mmp_curve`
   skews CP for every downstream module); power modules skip a power-less
   run with one printed line instead of crashing the report.
2. **Critical Speed from pace** (`cs.py`): the same math as CP
   (v = CS + D′/t) on the speed stream. Deprioritized as a *fallback* by the
   scope decision, but still worth having as a cross-check on power-based CP
   — CS is the original, well-validated running model, and Garmin native
   power is itself modeled largely from pace/grade/weight.
3. **CP fit diagnostics**: R² and standard error of CP/W′ from the linear
   fit, points-in-window count, and a staleness warning ("no maximal 12–20 min
   effort in 6 weeks — CP unreliable; go test"). Cheap, high trust value.
4. **ACWR**: rolling 7-day / 28-day load ratio with the 0.8–1.3 "sweet spot"
   band — the standard injury-risk number; a natural extra line in `load.py`.
5. **Endurance-corrected race predictions**: fit the athlete's personal
   Riegel exponent from their own fastest splits (data already in
   `runs.csv`), blend with Daniels; report both ("aerobic ceiling" vs
   "endurance-corrected") instead of the current prose caveat.
6. **Polarization index**: collapse the 5 zones to Seiler's 3, print
   easy/moderate/hard % and an 80/20 verdict — one function on existing
   time-in-zone data.
7. **PR progression timeline**: fastest 1k/5k/10k *per month* (columns
   already downloaded), not just all-time — this is Strava's most-loved
   feature and it's a groupby away.
8. **W/kg + Running Effectiveness (RE = speed / (power/kg)) + Leg Spring
   Stiffness** once weight lands in the athlete profile (§2.1). RE ≈ 1.0 is
   a benchmarkable, publishable number Stryd users know.
9. **Readiness score**: combine HRV-vs-baseline, RHR delta, sleep into one
   0–100 morning number (the pieces are all in `recovery.py` already).
10. **Heat-adjusted pace/efficiency**: regress m/beat on temperature (data
    present), report temperature-neutral trend — kills the biggest confounder
    in the summer fitness chart.
11. **GCT balance**: add `directGroundContactBalance` to the stream download
    KEYS — left/right asymmetry is an injury flag no free tool surfaces well.
12. **Race pacing plan**: given CP/W′ and a target distance, emit per-segment
    target power/pace with predicted W'bal trajectory — turns the models into
    an actionable plan, which none of the three competitors do for running.

## 5. The 50+ runs problem: per-run tables everywhere

Nine modules print one row per run. At 50 runs that's ~9 × 50 table rows per
report; at 200 runs the report is unreadable and the charts (fixed 8×4 in)
smear. The information design fix, in order of value:

1. **One shared helper, used by every module** (in `common.py`):

   ```python
   def print_rows(rows, fmt, head=6, tail=6, full="--full" in sys.argv):
       """Print all rows if few or --full; else head + '… n more …' + tail."""
   ```

   Default output shows the first 6 and last 6 runs with
   `… 38 more runs (--full for all) …` between. Oldest rows are the least
   interesting; newest are what the athlete checks daily. One change,
   nine modules fixed, and `--full` preserves today's behavior.

2. **Aggregate when n is large.** Above ~30 runs, per-run tables in
   `vo2max`, `fitness`, `wbal`, `decoupling` switch to *weekly* rows
   (mean/min/max) — trends are what those tables communicate anyway; the
   correlation engine keeps the per-run resolution for people who dig.

3. **Verdict-first sections.** Each module already computes a verdict line
   (form verdict, decoupling average, pacing %). Print the verdict and
   top-3 notable runs *first*, table after — so a truncated table costs
   nothing for skim-readers.

4. **Collapsible HTML.** In `report.py --html`, wrap each `<pre>` block in
   `<details><summary>full output</summary>…</details>` (markdown passes raw
   HTML through). The HTML stays complete but one page tall; the PDF gets the
   compact tables; the `.md` keeps whatever the terminal printed.

5. **Time-window the report.** `python -m analysis.report --last 90d`
   (default: everything) so multi-year archives produce a "this season"
   report; long-horizon trends (PMC, VO2max, PR progression) always use full
   history regardless of the window.

Related scaling issue worth fixing in the same pass: **derived-metrics
cache**. `mmp_curve` re-reads every stream JSON, and `correlate.build`
recomputes TRIMP + decoupling + W'bal for every run, in every module, on
every invocation. Persist a per-activity row (mmp values, trimp, decoupling,
wbal_depl, dynamics means) to `data/derived.csv` keyed by `activityId`,
invalidated the same way the downloaders already do incrementality. Report
generation stays seconds at 1,000 runs.

## 6. Roadmap to a free open-source tool for athletes

MIT license is already in place ✅. Suggested phases:

**Phase 1 — de-personalize & package (release blocker)**
- Athlete profile + config (§2.1); name on the report; `--privacy` strips it
- `pyproject.toml` with pinned deps + `running-ops` console entry points
  (`sync`, `analyze`, `report`)
- Cross-platform PDF: search PATH for `chromium/chrome/brave/edge` on
  Linux/Windows/macOS; clear message naming what to install
- Delete `analyze_runs.py`; fix "all 25 runs"; move athlete-specific facts
  out of docstrings/CLAUDE.md into the profile
- GitHub Actions: unittest matrix (3.10–3.13)
- Ship an anonymized sample dataset (`--privacy` zip of ~15 runs) +
  `make demo` so anyone can render a report in 30 seconds

**Phase 2 — robustness within the power-watch scope**
- Power-source integrity + fail-soft on power-less streams (§4.1)
- Full-history sync (append-based `runs.json`, resumable)
- FIT file import as an alternative to Garmin Connect API (same watches,
  no cloud dependency; `common.py` is already the single choke point)
- Units option (km/mi) in config
- *(descoped: HR+pace fallback lane for non-power watches — see scope
  decision at top)*

**Phase 3 — win on numbers** (§4 items 3–12, roughly in that order)

**Phase 4 — community**
- `docs/METHODS.md`: every formula with its literature reference (the test
  suite already encodes them — write them down)
- CONTRIBUTING.md: "a new metric = pure function + reference test + module
  registration" — the architecture makes this a genuinely easy pitch
- Report scaling work from §5

---

## Appendix: small nitpicks found during review

- `report.py:74` `chart_cp` halves runs by row position but labels halves by
  date — same off-by-feel as `cp.main`; harmless, but both should split on
  the date midpoint for irregular training gaps.
- `zones.py` histogram bins (100–500 W, 100–200 bpm) clip athletes outside
  those ranges; derive bins from data quantiles.
- `wbal.py` W'bal loop is O(n) Python per run; fine now, vectorize or cache
  when the derived-metrics cache lands.
- `intervals.interval_metrics` `pace_s` divides by mean speed without a
  guard; a stream with speed dropouts inside an interval yields inf.
- `load.py` `daily_load` anchors HRrest on the *mean* of all wellness RHR —
  a multi-year archive should use a rolling recent mean.
- `download_wellness.py` swallows all exceptions per day; a 401 (expired
  tokens) silently writes empty rows for every remaining day.
- `common.load_runs` computes `m_per_beat` unguarded; a treadmill run with
  missing `averageHR` propagates NaN fine, but `distance=0` yields inf pace.
- `README` quick-start installs no pinned versions; one `garminconnect`
  breaking release breaks the one-liner (fixed by Phase 1 packaging).
