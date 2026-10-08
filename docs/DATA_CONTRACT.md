# Data contract v0.2

This specifies the implemented Phase 2 CSV outputs. Observed discovery coverage
is in `DISCOVERY.md`; pipeline validation is in `PIPELINE_VALIDATION.md`.
Activity distance/timer units have been checked against user-reported Garmin
values. HRV meaning/units and unsupported metrics retain explicit nulls/flags.
A future change to definitions increments the schema version.

## Shared rules

- Local outputs: `data/processed/activities_summary.csv` and
  `data/processed/recovery_summary.csv`; Parquet can be added when needed.
- `data/processed/pipeline_report.json` stores processing/code versions, input
  hashes, settings, private verification evidence, reconciliation and quality
  counts, and output hashes. It contains no generated-at timestamp so repeated
  runs with the same sources, code, settings and evidence produce identical bytes.
- Store schema version, source SHA-256, collection path, record index, processing
  version, and quality flags. IDs/hashes and detailed metadata stay private.
- Missing numeric values use null/empty CSV cells, never a made-up zero.
  Use ISO dates, UTC timestamps with offsets, and explicit units in field names.
- Duplicate activity IDs or dated recovery records require a documented conflict
  decision; do not sum duplicates or choose an arbitrary record silently.
- Keep source values in private provenance/interim records so transformations
  can be audited. Exclude names, email, profile IDs, location names, and GPS
  from analytical tables.

## Time alignment

Use **Asia/Singapore** as the analysis timezone. Derive `analysis_date` from
the UTC activity start in that zone. Also preserve the original source-local
date and offset, including observed +7-hour activities. `startTimeLocal` is a
wall-clock representation and must not be interpreted as a true UTC instant.
Convert `startTimeGmt`/`beginTimestamp` from epoch milliseconds and cross-check
their agreement. Flag discrepant values.

For recovery, use Garmin `calendarDate` as the date of the waking day. Interpret
sleep GMT fields as UTC, then check that the waking date in Singapore agrees.
It agrees for every dated record in the current export. Flag future mismatches
and travel ambiguity instead of silently shifting days.

Workouts on date D join to recovery on D+1 for next-day targets. Same-day sleep
represents the preceding night. Prediction features must only contain data
available at the stated prediction cutoff; future imports and later timestamps
must not leak into historical evaluation.

## Activities: one row per activity ID

| Output field | Source / transformation | Availability and rules |
| --- | --- | --- |
| `activity_id` | `activityId` | Required, unique, stored privately |
| `sport` | `activityType` | Keep runs, swimming, and strength distinct |
| `start_utc` | `startTimeGmt` | Epoch milliseconds to UTC; cross-check `beginTimestamp` |
| `analysis_date` | UTC start in Asia/Singapore | Daily aggregation key |
| `source_local_date`, `source_utc_offset_hours` | Source local timestamp and its difference from GMT | Preserve travel/timezone differences |
| `distance_m` | `distance / 100` | Centimeters verified against Garmin display; flag if evidence not supplied |
| `duration_s` | `duration / 1000` | Milliseconds verified; preserve timer duration separately from elapsed/moving |
| `elapsed_duration_s`, `moving_duration_s` | Matching source fields `/ 1000` | Verified millisecond scale; flag invalid/negative durations; do not interchange |
| `avg_speed_m_s` | `avgSpeed * 10` | Cm/ms inferred from verified distance/time and cross-field consistency; retain mismatches |
| `avg_hr_bpm`, `max_hr_bpm` | `avgHr`, `maxHr` | Positive values; null/flag invalid HR |
| `hr_zone_0_s` through `hr_zone_6_s` | Candidate source zone times `/ 1000` | Preserve zone 0/6; flag missing or inconsistent sums |
| `ef_summary` | `avg_speed_m_s / avg_hr_bpm` | Running only, positive speed/HR, verified units; whole-session proxy, not steady-state EF |
| `decoupling_pct` | Null in current export | `missing_workout_timeseries`; no drift estimate from whole-session averages |
| `trimp` | Null in v0.2 | `load_definition_pending`; no arbitrary formula or assumed personal HRmax |
| `activity_units_verified` | Evidence validation result | False by default; true only with accepted local evidence |
| `source_sha256`, `source_collection`, `source_record_index`, `source_refs`, `quality_flags` | Provenance and checks | Required; all references retained for exact duplicates |

The user supplied a September 30 activity shown as 10.54 km, timer 58:54, moving
58:48 and elapsed 1:09:23. Exactly one source activity matched that date. Candidate
distance differs by 4.26 m and times by less than 0.17 seconds, within display
rounding. Evidence is stored privately in `data/reports/verification.json`.

Default runs without `--verification` still flag `units_unverified` and leave EF
null. Evidence validation allows 10 m distance rounding and 2 seconds per time;
it checks the unique activity ID, source-local date, and optional moving/elapsed
times. This is one externally checked activity, not independent validation of
every sport or every possible Garmin export format. Keep cross-field flags.

TRIMP is deliberately unavailable: current HR settings are a snapshot without
proven historical calibration. Selecting a load variant and verifying required
inputs is a later metric decision, not a blocker for basic summaries.

Future decoupling requires matched speed/HR samples, a documented steady-run
eligibility rule, warmup exclusions, moving-time handling, and half definitions.
Use `100 * (EF_first_half - EF_second_half) / EF_first_half` only after those
requirements are met. No reconstructed per-second data from summaries.

## Recovery: one row per analysis-calendar date

Build a full calendar across the union of dated activities and recovery sources.
Keep missing days as rows with null observations and explicit coverage flags.
Discard undated placeholder rows from the daily join, while retaining their
counts in the quality report.

| Output field | Source / transformation | Rule |
| --- | --- | --- |
| `date` | Analysis-calendar date | Unique daily key |
| `recorded_activity_count`, `recorded_run_count` | Counts of accepted unique activity rows on analysis date | Zero means none recorded; it is not a claim of complete data or confirmed rest |
| `activity_status` | `recorded_activity`, `no_recorded_activity`, or `conflicting_activity_records` | Never use absent activity to flag a missing workout |
| `target_runs_per_week` | User preference: 3 | Intended frequency, not an assertion about historical adherence; no daily/weekly compliance alerts |
| `sleep_start_utc`, `sleep_end_utc` | Sleep GMT fields | Parse UTC; validate order and waking-date agreement |
| `deep_sleep_minutes`, `light_sleep_minutes`, `rem_sleep_minutes` | Matching `*SleepSeconds / 60` | Missing REM stays null; observed on only 149 of 179 dated rows |
| `awake_minutes`, `unmeasurable_minutes` | Corresponding seconds `/ 60` | Retain separately from measured sleep |
| `sleep_minutes` | Sum deep + light + REM minutes | Null if any stage is missing; never equate window length with measured sleep |
| `sleep_window_minutes` | Sleep end minus start | Separate field; includes awake/unmeasured time |
| `hrv_source_value` | Health metric `type=HRV`, `value` | Numeric source observation; retain source aggregation label |
| `nightly_hrv_ms` | From HRV only after meaning/unit verification | Otherwise null and `hrv_semantics_unverified` |
| `health_hr_source_value` | Health metric `type=HR`, `value` | Do not rename to daily RHR |
| `resting_hr_bpm` | No confirmed daily source yet | Null until `rhr` semantics/last-entry dates or another authoritative source are verified |
| `hrv_semantics_verified` | Explicit local evidence | False until source HRV aggregation and ms units are confirmed |
| `sleep_observed`, `health_observed`, `quality_flags` | Coverage and checks | Missing date, missing stage, conflicts, timestamp and unit flags |
| `source_refs` | Per-source digest, collection and record index | Preserve separate provenance for sleep and health |

The fitness-age collection's 168 `rhr` observations may reuse prior values.
Keep any future extraction in a separate source table with `rhrLastEntryDate`;
do not assign it to a daily resting-HR series without verifying effective dates.
SpO2 and skin temperature are currently entirely null and are not required fields.

## Rolling HRV features after semantic verification

- `hrv_prior_7d_mean_ms`: previous 7 **calendar** days, exclude current day;
  require at least 5 valid nightly observations and record the valid count.
- Baseline: previous 28 calendar days, exclude current day; require at least
  21 valid nightly observations. Use arithmetic mean and sample SD (`ddof=1`).
- `hrv_z_score`: `(current_nightly_hrv - prior_28d_mean) / prior_28d_sd`.
  Null if current value/history is missing or SD is zero. No filling gaps with zero.
- These window/count choices are project conventions, not medical thresholds.
  No automated recovery downgrade is enabled. Features depend on confirmed
  nightly units/meaning and availability at the prediction cutoff.

Rolling fields are implemented but remain null in current real outputs because
nightly HRV semantics are unverified. Counts of eligible verified nightly values
are stored in `hrv_prior_7d_valid_count` and `hrv_prior_28d_valid_count`.

## Duplicate, invalid-record and quality policy

Exact duplicate source records merge into one row with all references preserved.
Conflicting records for the same activity ID or recovery date are quarantined;
none wins arbitrarily. Their counts/refs are in the private report. Conflicting
recovery dates remain calendar rows with null observations and conflict flags.
Conflicting dated activities add calendar dates with a conflict status rather
than a false no-activity classification. Invalid keys are rejected and counted;
undated sleep placeholders are expected among these exclusions.

Non-finite, negative and boolean measurements become null. Zero is valid for
explicitly recorded distance/sleep stages, but not HR or timer duration. Use a
one-second tolerance for timer/moving-versus-elapsed checks, 0.01 m/s for
speed-versus-distance/timer, and max(1 second, 1% of timer) for HR-zone sums.
Sleep stage sums are checked against the window with one-minute tolerance.
These are QA conventions, not physiological thresholds. Flagged measurements
are retained for review; EF is withheld for speed/HR/timer inconsistencies.

The user intends to run three times a week. The complete recovery calendar
supports tracking wellness on other days without interpreting them as missing
runs. The pipeline does not prescribe a schedule or label rest as confirmed.

## Validation before Phase 2 completion

Check source-to-output row counts, ID uniqueness, calendar continuity, unit
conversion evidence, numeric/timestamp validity, source-local versus analysis
dates, duplicate handling, missing-stage propagation, and provenance. Add
synthetic cases for travel offsets, placeholders, gaps, and next-day alignment.
Require reproducible outputs from unchanged inputs and clear quality counts.
