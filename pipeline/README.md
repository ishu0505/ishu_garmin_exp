# Local discovery and deterministic pipeline

`discover_export.py` is the Phase 1 entry point. It inventories JSON and ZIP/FIT
files, detects record collections, profiles field presence/types, checks dates,
and reports duplicates and coverage. It reads original files without changing
them; ZIP members are decoded in memory rather than extracted to disk.

## Run from the repo root

uv is currently installed at `.tools/uv` in this checkout. If uv is on your PATH,
replace `.tools/uv --cache-dir .uv-cache` below with `uv`.

```bash
.tools/uv --cache-dir .uv-cache sync --extra sync
.tools/uv --cache-dir .uv-cache run --offline python pipeline/discover_export.py
.tools/uv --cache-dir .uv-cache run --offline python -m unittest discover -s pipeline -p 'test_*.py'
```

The default source is `ishu_garmin_data/` and output is the ignored local file
`data/reports/discovery.json`. Override with `--source` and `--output` if needed;
keep output in a private, ignored directory. Console output contains aggregated
metadata only. Per-file schema profiles and hashes remain in the local report.
It excludes raw values, identifiers, filenames, GPS, and account details.

The report includes source numeric ranges to investigate scaling; those ranges
do not prove units. It profiles known export wrappers and selected date fields,
not every possible Garmin schema. Unknown FIT messages remain unknown; they
are not reinterpreted as workout tracks. A nonzero exit means a file failed
inspection; inspect the redacted error types before trusting coverage.

`test_discovery.py` uses synthetic temporary files to check date gaps, wrappers,
placeholder sleep rows, missing fields, duplicate IDs, null metrics, and privacy.
No credentials or private export are needed to run these tests.

## Build Phase 2 summaries

```bash
.tools/uv --cache-dir .uv-cache run --offline python pipeline/run_pipeline.py --verification data/reports/verification.json
```

`run_pipeline.py` reads the original JSON export and writes ignored outputs:

- `data/processed/activities_summary.csv`: one accepted row per activity ID.
- `data/processed/recovery_summary.csv`: continuous daily observations and recorded
  activity counts; non-running days are valid and never marked missing workouts.
- `data/processed/pipeline_report.json`: private provenance, settings, evidence,
  reconciliation, quality counts, code versions and output hashes.

Execution flow: `export_sources.py` loads recognized collections with true source
indexes; duplicate resolution merges identical records and quarantines conflicts;
`summaries.py` handles activity units, sleep stages, daily joins and past-only HRV
features; `run_pipeline.py` validates, sorts and writes stable outputs.

`settings.toml` records Singapore analysis dates, **three intended runs/week**,
and the agreed 7/28-day HRV windows. Missing activity is not a proven rest day
or missing workout. A private verification file checks the externally supplied
September 30 distance and all three durations. Without `--verification`, the
pipeline still runs but marks activity conversions provisional and leaves EF null.

HRV-derived features stay null until evidence verifies the source metric's
nightly meaning and units. Health HR is not daily RHR. Drift/TRIMP are unavailable.
See `../docs/DATA_CONTRACT.md` for all definitions and validation gates and
`../docs/PIPELINE_VALIDATION.md` for current results and limitations.

Optional verification JSON supports these documented keys:

```json
{
  "activity": {
    "activity_id": "replace-with-known-private-ID",
    "source_local_date": "2026-01-02",
    "distance_m": 5000,
    "duration_s": 1800,
    "moving_duration_s": 1800,
    "elapsed_duration_s": 1800,
    "source_reference": "Garmin display/API evidence for this activity"
  }
}
```

This is a synthetic format example, not real verification evidence. A separate
optional `hrv` object requires `meaning: nightly_average`, `units: ms`, and a
`source_reference` establishing this export field's interpretation. Do not add
that attestation based merely on a plausible numeric range.

`test_pipeline.py` extends synthetic discovery checks with contract, privacy,
temporal alignment, duplicate handling, unit verification, and repeatability
checks. Both test files run with the unittest command above. Override source,
output or settings with `--source`, `--output-dir`, or `--settings`; outputs must
not overlap source directories. Models and account sync remain later work.
