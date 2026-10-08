# Phase 1 discovery findings

Discovery completed on 2026-10-08 using `pipeline/discover_export.py` and
fitdecode 0.11.0. Detailed metadata lives in the ignored local report
`data/reports/discovery.json`; original files were not modified.

## Inventory and coverage

The supplied export is approximately 4.1 MiB: **25 JSON files and one ZIP**
across Fitness, Wellness, and User folders. All were inspected successfully.
One file has identical content to another; activity IDs themselves are unique.

| Collection | Observed coverage | Important limitation |
| --- | --- | --- |
| Activity summaries | 66 activities, 2026-03-18 through 2026-10-07; 60 runs, 5 pool swims, 1 strength session | Summaries are not per-second tracks |
| Sleep | 205 rows, 179 dated records, 2026-03-19 through 2026-10-07 | 26 undated placeholders; REM present on only 149 dated rows |
| Health metrics | 179 distinct days over the same date range as sleep | HRV, HR, respiration non-null; SpO2 and skin temperature always null |
| Fitness-age records | 168 dated rows, 2026-03-18 through 2026-10-07 | RHR field exists, but its last-entry date must be checked before calling it daily RHR |

Sleep and health metrics share exactly the same 179 dates. Across their 203-day
span, 24 calendar days are missing. The longest continuous observed stretch is
54 days. Of the 66 source-local activity dates, 55 have both sleep and health
metrics. These are same-day availability counts, not validated next-day targets.
Absent activity dates cannot automatically be labeled rest days.

## FIT limitation

The ZIP contains a single 11,888-byte FIT file. Its decoded file type is 74;
messages include device metadata and unknown types 79 and 140. There are **no
standard record, lap, session, or activity messages**. Unknown message 140 occurs
66 times; that count alone does not establish its meaning.

This archive therefore does not currently supply decoded workout time series.
Do not calculate cardiac drift/decoupling from it. Garmin's [activity FIT
documentation](https://developer.garmin.com/fit/articles/file-types/activity.html)
describes the record/session structure used for workout data. Individual
activity FIT downloads will be needed for the originally proposed drift analysis.
JSON split summaries exist for runs but are not equivalent to per-second tracks.

## Units and timestamp checks

- Source activity times are numeric epoch-like milliseconds. Local minus GMT
  is +8 hours for 64 activities and +7 for two. Preserve both rather than
  assigning Singapore time to every original local timestamp.
- All 179 sleep end timestamps, interpreted according to their GMT field name
  and converted to Asia/Singapore, match the supplied calendar date.
- Duration ranges and distance/speed relationships support **candidate** source
  units of milliseconds, centimeters, and centimeters per millisecond. Source
  `distance / duration` matches `avgSpeed` within 0.001 in 65 of 66 rows.
  This checks consistency, not absolute scale; conversions remain provisional
  until compared with a known activity's Garmin display or official metadata.
- HR zone-time totals are close to duration (median ratio 0.99995, range
  0.9861–1.0450), supporting the same candidate millisecond scale with some
  mismatch. Do not silently rescale zone times to force equality.
- HR fields are compatible with bpm. Health metric `HR` must not be relabeled
  daily resting HR; `HRV` must retain its source label until its aggregation
  meaning and units are confirmed.

## What the data can support next

Phase 2 can build quality-aware activity summaries and a daily calendar of sleep
and health observations. Trend interpretation belongs to Phase 3. Roughly seven
months of date span is useful history, but gaps and unavailable workout tracks
limit which analyses are defensible. No model, fitness claim, or training change
has been inferred from coverage alone.

## Garmin downloads

`garminconnect` **0.3.17** is installed through uv and locked as the optional
`sync` extra. Its import was verified. The [package's own
documentation](https://github.com/cyberjunky/python-garminconnect) describes
authenticated activity and health-data access.

Installation does not configure incremental downloading. No login, credentials,
account requests, scheduler, or sync script has been created. The later sync
phase will persist local tokens and import only missing/new data, with overlap
checks for updates; this should reduce repeated bulk exports for supported
data, subject to Garmin availability and authentication.
