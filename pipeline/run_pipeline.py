"""Build deterministic private CSV summaries from an unchanged Garmin export.

Run from the repository root through uv. The pipeline uses the standard library,
quarantines conflicting records, and prints quality counts rather than raw data.
No account requests, training prescriptions, or models are involved.
"""

import argparse
from collections import Counter
import csv
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import tomllib
from zoneinfo import ZoneInfo

from export_sources import read_sources, resolve_duplicates
from summaries import SCHEMA_VERSION, activity_summary, calendar_date, epoch_ms, number, recovery_calendar

PIPELINE_VERSION = "0.2.0"
ACTIVITY_FIELDS = [
    "schema_version", "activity_id", "sport", "start_utc", "analysis_date",
    "source_local_date", "source_utc_offset_hours", "activity_units_verified",
    "distance_m", "duration_s", "elapsed_duration_s", "moving_duration_s",
    "avg_speed_m_s", "avg_hr_bpm", "max_hr_bpm", "ef_summary", "decoupling_pct", "trimp",
    *[f"hr_zone_{index}_s" for index in range(7)],
    "source_sha256", "source_collection", "source_record_index", "source_refs", "quality_flags",
]
RECOVERY_FIELDS = [
    "schema_version", "date", "recorded_activity_count", "recorded_run_count", "activity_status",
    "target_runs_per_week", "sleep_observed", "health_observed", "hrv_semantics_verified",
    "sleep_start_utc", "sleep_end_utc", "deep_sleep_minutes", "light_sleep_minutes",
    "rem_sleep_minutes", "awake_minutes", "unmeasurable_minutes", "sleep_minutes",
    "sleep_window_minutes", "hrv_source_value", "nightly_hrv_ms", "health_hr_source_value",
    "resting_hr_bpm", "hrv_prior_7d_valid_count", "hrv_prior_28d_valid_count",
    "hrv_prior_7d_mean_ms", "hrv_prior_28d_mean_ms", "hrv_prior_28d_sd_ms", "hrv_z_score",
    "source_refs", "quality_flags",
]


def load_settings(path: Path) -> dict:
    """Load supported calendar/window settings; reject ambiguous field labels."""
    settings = tomllib.loads(path.read_text())
    if settings["analysis_timezone"] != "Asia/Singapore":
        raise ValueError("Changing timezone requires a contract update")
    # Column names promise 7/28 calendar days; changing windows needs a schema change.
    if settings["hrv_recent_days"] != 7 or settings["hrv_baseline_days"] != 28:
        raise ValueError("Changing window lengths requires a schema update")
    for key in ("target_runs_per_week", "hrv_recent_min_count", "hrv_baseline_min_count"):
        if type(settings[key]) is not int or settings[key] < 1:
            raise ValueError("Settings require positive integer counts")
    if settings["hrv_recent_min_count"] > 7 or not 2 <= settings["hrv_baseline_min_count"] <= 28:
        raise ValueError("Invalid minimum HRV window counts")
    return settings


def verification_state(path: Path | None, activities: list[dict]) -> tuple[bool, bool, dict]:
    """Verify an optional local evidence file before promoting candidate fields.

    Activity evidence must match one known source ID, distance and timer duration
    from Garmin's display/API. HRV evidence must explicitly document that this
    export metric is an overnight average in ms. Evidence is a user-supplied
    attestation, not independently fetched or inferred from numerical ranges.
    """
    if path is None:
        return False, False, {}
    evidence = json.loads(path.read_text())
    units_verified = False
    hrv_verified = False
    if "activity" in evidence:
        anchor = evidence["activity"]
        matches = [entry["record"] for entry in activities if str(entry["record"]["activityId"]) == str(anchor["activity_id"])]
        if len(matches) != 1 or not str(anchor.get("source_reference", "")).strip():
            raise ValueError("Activity verification requires a unique ID and source reference")
        distance = number(anchor.get("distance_m"), positive=True)
        duration = number(anchor.get("duration_s"), positive=True)
        raw_distance, raw_duration = number(matches[0].get("distance")), number(matches[0].get("duration"))
        if None in (distance, duration, raw_distance, raw_duration):
            raise ValueError("Activity evidence requires positive numeric measurements")
        # A Garmin display rounded to 0.01 km can differ from the stored distance.
        if abs(raw_distance / 100 - distance) > 10 or abs(raw_duration / 1000 - duration) > 2:
            raise ValueError("Activity evidence does not match candidate unit conversions")
        for expected_field, source_field in (("moving_duration_s", "movingDuration"), ("elapsed_duration_s", "elapsedDuration")):
            if expected_field in anchor:
                expected, source_value = number(anchor[expected_field]), number(matches[0].get(source_field))
                if expected is None or source_value is None or abs(source_value / 1000 - expected) > 2:
                    raise ValueError("Additional activity duration evidence does not match")
        if "source_local_date" in anchor:
            local = epoch_ms(matches[0].get("startTimeLocal"))
            if local is None or local.date().isoformat() != anchor["source_local_date"]:
                raise ValueError("Activity evidence date does not match")
        units_verified = True
    if "hrv" in evidence:
        anchor = evidence["hrv"]
        if anchor.get("meaning") != "nightly_average" or anchor.get("units") != "ms" or not str(anchor.get("source_reference", "")).strip():
            raise ValueError("HRV requires evidence for nightly-average meaning and ms units")
        hrv_verified = True
    return units_verified, hrv_verified, evidence


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    """Write fixed-schema UTF-8 CSV, with nulls represented by empty cells."""
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def activity_key(raw: dict) -> str | None:
    """Accept integer/string Garmin activity IDs while rejecting bool/empty IDs."""
    value = raw.get("activityId")
    if isinstance(value, bool) or not isinstance(value, (int, str)) or not str(value).strip():
        return None
    return str(value)


def flag_counts(rows: list[dict]) -> dict:
    """Count quality flags without exposing personal row values."""
    return dict(sorted(Counter(flag for row in rows for flag in json.loads(row["quality_flags"])).items()))


def build(source: Path, output: Path, settings_path: Path, evidence_path: Path | None = None) -> dict:
    """Validate sources, build tables, and write a deterministic private manifest.

    Output cannot overlap sources. Invalid keys and conflicts are quarantined;
    JSON parse errors abort before overwriting outputs. Record-count reconciliation
    and calendar continuity are checked before writing any analytical tables.
    """
    source, output = source.resolve(), output.resolve()
    if not source.is_dir():
        raise ValueError("Source directory does not exist")
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Output and source directories must not overlap")
    settings = load_settings(settings_path)
    groups, sources, errors = read_sources(source)
    if errors:
        raise ValueError("Source inspection failed; no tables written")
    if not sources:
        raise ValueError("No JSON sources found")
    activities, activity_quality = resolve_duplicates(groups["activities"], activity_key)
    sleep, sleep_quality = resolve_duplicates(groups["sleep"], lambda row: calendar_date(row.get("calendarDate")))
    health, health_quality = resolve_duplicates(groups["health"], lambda row: calendar_date(row.get("calendarDate")))
    units_verified, hrv_verified, evidence = verification_state(evidence_path, activities)
    activity_rows = [activity_summary(entry, ZoneInfo(settings["analysis_timezone"]), units_verified) for entry in activities]
    activity_rows.sort(key=lambda row: (row["start_utc"] or "", row["activity_id"]))
    conflict_dates = {"sleep": sleep_quality["conflicts"], "health": health_quality["conflicts"], "activities": []}
    conflicting_ids = {item["key"] for item in activity_quality["conflicts"]}
    for entry in groups["activities"]:
        if activity_key(entry["record"]) in conflicting_ids:
            start = epoch_ms(entry["record"].get("startTimeGmt"))
            if start:
                conflict_dates["activities"].append({
                    "key": start.astimezone(ZoneInfo(settings["analysis_timezone"])).date().isoformat(),
                    "source_refs": [entry["ref"]],
                })
    recovery_rows = recovery_calendar(activity_rows, sleep, health, conflict_dates, settings, hrv_verified)
    # Quarantined activities are excluded and flagged in the private report;
    # no arbitrary duplicate is counted as a completed run.
    if len({row["activity_id"] for row in activity_rows}) != len(activity_rows):
        raise ValueError("Activity uniqueness check failed")
    if any(date.fromisoformat(right["date"]) - date.fromisoformat(left["date"]) != timedelta(days=1)
           for left, right in zip(recovery_rows, recovery_rows[1:])):
        raise ValueError("Daily calendar continuity check failed")
    for quality in (activity_quality, sleep_quality, health_quality):
        accounted = (quality["accepted_records"] + quality["exact_duplicate_records"]
                     + len(quality["invalid_key_refs"]) + sum(len(item["source_refs"]) for item in quality["conflicts"]))
        if accounted != quality["input_records"]:
            raise ValueError("Record reconciliation check failed")
    next_days = {row["date"]: row for row in recovery_rows}
    next_day_matched = 0
    for row in activity_rows:
        if row["analysis_date"]:
            next_date = (date.fromisoformat(row["analysis_date"]) + timedelta(days=1)).isoformat()
            next_row = next_days.get(next_date)
            next_flags = set(json.loads(next_row["quality_flags"])) if next_row else set()
            if next_row and next_row["sleep_observed"] and next_row["health_observed"] and not next_flags & {"conflicting_sleep_records", "conflicting_health_records", "invalid_sleep_window", "sleep_waking_date_mismatch"}:
                next_day_matched += 1
    report = {
        "schema_version": SCHEMA_VERSION, "pipeline_version": PIPELINE_VERSION,
        "settings": settings, "verification": {"activity_units_verified": units_verified, "hrv_semantics_verified": hrv_verified, "evidence": evidence},
        "source_manifest": sources, "reconciliation": {"activities": activity_quality, "sleep": sleep_quality, "health": health_quality},
        "counts": {"activities": len(activity_rows), "running_activities": sum(row["sport"] == "running" for row in activity_rows),
                   "recovery_calendar_days": len(recovery_rows), "sleep_observed_days": sum(row["sleep_observed"] for row in recovery_rows),
                   "health_observed_days": sum(row["health_observed"] for row in recovery_rows),
                   "complete_sleep_stage_days": sum(row["sleep_minutes"] is not None for row in recovery_rows),
                   "days_without_recorded_activity": sum(row["recorded_activity_count"] == 0 for row in recovery_rows),
                   "activity_rows_with_dated_start": sum(row["analysis_date"] is not None for row in activity_rows),
                   "activities_with_next_day_sleep_and_health": next_day_matched},
        "date_range": {"first": recovery_rows[0]["date"], "last": recovery_rows[-1]["date"]},
        "quality_flags": {"activities": flag_counts(activity_rows), "recovery": flag_counts(recovery_rows)},
    }
    code_dir = Path(__file__).parent
    report["code_hashes"] = {name: hashlib.sha256((code_dir / name).read_bytes()).hexdigest()
                             for name in ("run_pipeline.py", "export_sources.py", "summaries.py")}
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "activities_summary.csv", activity_rows, ACTIVITY_FIELDS)
    write_csv(output / "recovery_summary.csv", recovery_rows, RECOVERY_FIELDS)
    report["output_hashes"] = {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                               for name in ("activities_summary.csv", "recovery_summary.csv")}
    (output / "pipeline_report.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return report


def main() -> None:
    """Run locally and print only aggregate counts, verification states and flags."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("ishu_garmin_data"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--settings", type=Path, default=Path(__file__).with_name("settings.toml"))
    parser.add_argument("--verification", type=Path, help="Ignored local JSON with external unit/HRV evidence")
    args = parser.parse_args()
    try:
        report = build(args.source, args.output_dir, args.settings, args.verification)
    except (ValueError, OSError, KeyError, TypeError) as error:
        # Do not echo exceptions that might contain private source paths/values.
        parser.exit(1, f"Pipeline failed ({type(error).__name__}); check sources/settings.\n")
    print(json.dumps({key: report[key] for key in ("counts", "date_range", "quality_flags")}, indent=2))
    print("Activity units verified:", report["verification"]["activity_units_verified"])
    print("HRV semantics verified:", report["verification"]["hrv_semantics_verified"])


if __name__ == "__main__":
    main()
