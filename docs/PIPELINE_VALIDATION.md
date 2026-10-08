# Phase 2 pipeline validation

Completed 2026-10-08. Entry point: `pipeline/run_pipeline.py`. Schema version
0.2; processing version 0.2.0. Original export is unchanged. Outputs and detailed
quality reports are private and excluded from Git.

## Current output

| Result | Count |
| --- | --- |
| Accepted unique activities | 66 |
| Running activities | 60 |
| Continuous recovery calendar, March 18–October 7 | 204 days |
| Dated sleep observations | 179 |
| Dated health observations | 179 |
| Sleep observations with all three stages | 149 |
| Undated sleep placeholders excluded | 26 |
| Activities with next-day dated sleep and health, valid sleep window/date | 59 |

The calendar contains 25 dates without sleep/health observations, including
March 18 before the first recovery observation. Phase 1's 24 missing days used
the recovery-only span beginning March 19; these counts are consistent.

There are 138 calendar days with no recorded activity. They are valid dates,
not failed workouts. The user intends three runs/week; this preference is in
`pipeline/settings.toml`. No daily running expectation or adherence alert is applied.

## Unit verification

User-reported Garmin display values for September 30: 10.54 km, timer 58:54,
moving 58:48, elapsed 1:09:23. The export has a unique matching activity.
Distance matches within 4.26 m, and all time fields within 0.17 s. This confirms
the proposed centimeter/millisecond scales against an external display; speed
scale follows from distance/time consistency. The private verification file
is required on subsequent runs to preserve the verified status.

## Flags retained

- One activity has a speed/distance/timer mismatch.
- Two have HR-zone sums outside the documented 1% tolerance.
- One sleep observation has a stage/window discrepancy.
- Thirty dated sleep observations lack REM; their total measured sleep stays null.
- Cardiac drift lacks workout tracks; TRIMP lacks a verified load definition.
- Daily RHR and nightly HRV semantics are unverified. Source HR/HRV values are
  retained under source-specific names; HRV z-scores/rolling features stay null.

These limitations are visible in CSV quality flags and the report. No observed
metric is silently substituted for another or filled with an invented zero.

## Checks

Seventeen synthetic unittest checks cover discovery and pipeline behavior:
privacy, epoch/date parsing, offsets across midnight, verified/unverified units,
missing versus zero REM, finite measurements, conflicting/exact duplicates,
daily gaps, three-run preference, ambiguous HRV, past-only rolling windows,
zero-variance baselines, verification mismatch rejection, source errors,
source protection, next-day coverage, and identical outputs across repeated runs.

Real-data runs reconcile all recognized records, enforce unique activity IDs
and continuous calendar dates, and finish without source parse errors. Repeated
real-data builds produce identical CSV/report bytes; source hashes remain unchanged.
Git ignore checks protect outputs and verification evidence. No Garmin account
requests or training recommendations were made.
