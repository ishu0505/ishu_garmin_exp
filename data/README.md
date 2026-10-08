# Private data and outputs

- Original sources live in `../ishu_garmin_data/` and remain untouched.
- `reports/discovery.json` is the local Phase 1 inventory/schema/coverage report.
- `processed/activities_summary.csv` holds accepted activity rows.
- `processed/recovery_summary.csv` holds the continuous daily calendar, sleep/health
  observations, recorded activity counts, and intended three-run weekly frequency.
- `processed/pipeline_report.json` holds private reconciliation, source/output
  hashes, settings, versions, quality flags and verification evidence.
- `reports/verification.json` records user-provided activity unit evidence;
  pass it with `--verification` when rebuilding tables.
- `interim/` is reserved for reproducible intermediate outputs if needed.

Reports, interim files, and processed personal data are ignored by Git. Only
instruction files, this README, and the processed placeholder belong in Git.
Use `pipeline/discover_export.py` for inventory and `pipeline/run_pipeline.py`
for tables, through uv; see
`../pipeline/README.md`. Schemas and transformation rules are documented in
`../docs/DATA_CONTRACT.md`.
