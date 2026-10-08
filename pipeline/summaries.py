"""Convert Garmin records to simple activity and daily recovery dictionaries.

Unit conversions are provisional until externally verified. Unsupported metrics
stay null. Non-running days are valid calendar rows, not missing workout errors.
"""

from collections import Counter
from datetime import date, datetime, timedelta, timezone
import json
import math
import statistics
from zoneinfo import ZoneInfo

SCHEMA_VERSION = "0.2"


def number(value: object, *, positive: bool = False) -> float | None:
    """Return a finite nonnegative number, or null for missing/invalid input.

    Booleans are not measurements. Use positive=True for HR and timer duration;
    zero distance and zero sleep stages are allowed when explicitly recorded.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        return None
    return float(value)


def calendar_date(value: object) -> str | None:
    """Accept only an exact valid ISO calendar date, not an ambiguous timestamp."""
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
        return parsed.isoformat() if value == parsed.isoformat() else None
    except ValueError:
        return None


def epoch_ms(value: object) -> datetime | None:
    """Parse explicit epoch milliseconds as UTC, bounded to years 2000–2100."""
    numeric = number(value)
    if numeric is None or not 946684800000 <= numeric <= 4102444800000:
        return None
    return datetime.fromtimestamp(numeric / 1000, timezone.utc)


def gmt_text(value: object) -> datetime | None:
    """Parse a GMT-labeled ISO timestamp, treating a missing offset as UTC."""
    if not isinstance(value, str) or "T" not in value and " " not in value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def json_cell(value: object) -> str:
    """Encode structured private provenance/flags as stable CSV JSON cells."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def activity_summary(entry: dict, analysis_zone: ZoneInfo, units_verified: bool) -> dict:
    """Normalize one unique activity; retain flags and explicit source units.

    Distance cm -> m, timer ms -> s, and speed cm/ms -> m/s are candidate scales.
    EF is produced only for running with verified units and valid source checks.
    """
    raw = entry["record"]
    flags = {"missing_workout_timeseries", "load_definition_pending"}
    if not units_verified:
        flags.add("units_unverified")
    start = epoch_ms(raw.get("startTimeGmt"))
    begin = epoch_ms(raw.get("beginTimestamp"))
    local = epoch_ms(raw.get("startTimeLocal"))  # Wall clock encoded numerically, not a UTC instant.
    if start is None:
        flags.add("invalid_start_timestamp")
    if begin is None:
        flags.add("missing_begin_timestamp")
    elif start and abs((start - begin).total_seconds()) > 1:
        flags.add("start_timestamp_mismatch")
    if local is None:
        flags.add("invalid_source_local_timestamp")
    offset = (local - start).total_seconds() / 3600 if local and start else None
    if offset is not None and not -12 <= offset <= 14:
        flags.add("invalid_source_offset")
    sport = raw.get("activityType")
    if not isinstance(sport, str):
        sport = None
        flags.add("missing_sport")
    output = {
        "schema_version": SCHEMA_VERSION, "activity_id": str(raw["activityId"]),
        "sport": sport, "start_utc": start.isoformat() if start else None,
        "analysis_date": start.astimezone(analysis_zone).date().isoformat() if start else None,
        "source_local_date": local.date().isoformat() if local else None,
        "source_utc_offset_hours": offset, "activity_units_verified": units_verified,
        "decoupling_pct": None, "trimp": None,
    }
    scales = {"distance_m": ("distance", 0.01), "duration_s": ("duration", 0.001),
              "elapsed_duration_s": ("elapsedDuration", 0.001),
              "moving_duration_s": ("movingDuration", 0.001), "avg_speed_m_s": ("avgSpeed", 10),
              "avg_hr_bpm": ("avgHr", 1), "max_hr_bpm": ("maxHr", 1)}
    for field, (source, scale) in scales.items():
        value = number(raw.get(source), positive=field in {"duration_s", "avg_hr_bpm", "max_hr_bpm"})
        output[field] = value * scale if value is not None else None
        if value is None:
            flags.add(f"invalid_or_missing_{field}")
    duration, elapsed, moving = (output[key] for key in ("duration_s", "elapsed_duration_s", "moving_duration_s"))
    if duration is not None and elapsed is not None and duration > elapsed + 1:
        flags.add("timer_exceeds_elapsed")
    if moving is not None and elapsed is not None and moving > elapsed + 1:
        flags.add("moving_exceeds_elapsed")
    distance, speed = output["distance_m"], output["avg_speed_m_s"]
    if duration and distance is not None and speed is not None and abs(distance / duration - speed) > 0.01:
        flags.add("speed_distance_duration_mismatch")
    for index in range(7):
        value = number(raw.get(f"hrTimeInZone_{index}"))
        output[f"hr_zone_{index}_s"] = value / 1000 if value is not None else None
        if value is None:
            flags.add("incomplete_hr_zone_times")
    zone_times = [output[f"hr_zone_{index}_s"] for index in range(7)]
    if duration and all(value is not None for value in zone_times) and abs(sum(zone_times) - duration) > max(1, 0.01 * duration):
        flags.add("hr_zone_duration_mismatch")
    hr, max_hr = output["avg_hr_bpm"], output["max_hr_bpm"]
    if hr and max_hr and hr > max_hr:
        flags.add("avg_hr_exceeds_max_hr")
    ef_valid = units_verified and sport == "running" and speed and hr
    if flags & {"speed_distance_duration_mismatch", "avg_hr_exceeds_max_hr", "timer_exceeds_elapsed"}:
        ef_valid = False
    output["ef_summary"] = speed / hr if ef_valid else None
    output["source_sha256"] = entry["refs"][0]["sha256"]
    output["source_collection"] = entry["refs"][0]["collection"]
    output["source_record_index"] = entry["refs"][0]["record_index"]
    output["source_refs"] = json_cell(entry["refs"])
    output["quality_flags"] = json_cell(sorted(flags))
    return output


def sleep_summary(raw: dict, analysis_zone: ZoneInfo) -> tuple[dict, set[str]]:
    """Convert measured sleep stages in seconds to minutes without filling gaps."""
    flags = set()
    output = {}
    fields = {"deep_sleep_minutes": "deepSleepSeconds", "light_sleep_minutes": "lightSleepSeconds",
              "rem_sleep_minutes": "remSleepSeconds", "awake_minutes": "awakeSleepSeconds",
              "unmeasurable_minutes": "unmeasurableSeconds"}
    for field, key in fields.items():
        value = number(raw.get(key))
        output[field] = value / 60 if value is not None else None
        if value is None:
            flags.add(f"missing_or_invalid_{field}")
    stages = [output[key] for key in ("deep_sleep_minutes", "light_sleep_minutes", "rem_sleep_minutes")]
    output["sleep_minutes"] = sum(stages) if all(value is not None for value in stages) else None
    start, end = gmt_text(raw.get("sleepStartTimestampGMT")), gmt_text(raw.get("sleepEndTimestampGMT"))
    output["sleep_start_utc"] = start.isoformat() if start else None
    output["sleep_end_utc"] = end.isoformat() if end else None
    output["sleep_window_minutes"] = None
    if start and end and end > start:
        output["sleep_window_minutes"] = (end - start).total_seconds() / 60
        if end.astimezone(analysis_zone).date().isoformat() != raw.get("calendarDate"):
            flags.add("sleep_waking_date_mismatch")
        all_parts = list(output[key] for key in fields)
        if all(value is not None for value in all_parts) and abs(sum(all_parts) - output["sleep_window_minutes"]) > 1:
            flags.add("sleep_stage_window_mismatch")
    else:
        flags.add("invalid_sleep_window")
    return output, flags


def health_summary(raw: dict, hrv_verified: bool) -> tuple[dict, set[str]]:
    """Retain source HR/HRV values; promote HRV only after semantic verification.

    Duplicate metric types are ambiguous and are left null. Health HR is never
    substituted for resting HR. Confirmation of nightly HRV requires evidence.
    """
    metrics = raw.get("metrics")
    if not isinstance(metrics, list):
        metrics = []
    output = {}
    flags = set()
    for kind, field in (("HRV", "hrv_source_value"), ("HR", "health_hr_source_value")):
        matches = [item for item in metrics if isinstance(item, dict) and item.get("type") == kind]
        output[field] = number(matches[0].get("value"), positive=True) if len(matches) == 1 else None
        if len(matches) > 1:
            flags.add(f"conflicting_{kind.lower()}_metrics")
        if output[field] is None:
            flags.add(f"missing_or_invalid_{kind.lower()}")
    output["nightly_hrv_ms"] = output["hrv_source_value"] if hrv_verified else None
    if not hrv_verified:
        flags.add("hrv_semantics_unverified")
    output["resting_hr_bpm"] = None
    flags.add("daily_rhr_unverified")
    return output, flags


def rolling_hrv(rows: list[dict], settings: dict) -> None:
    """Add past-only HRV windows and z-scores to a complete ordered calendar.

    Uses sample SD and minimum counts from settings. Missing/zero-variance
    baselines remain null; current and future values never enter the baseline.
    """
    for index, row in enumerate(rows):
        recent = [r["nightly_hrv_ms"] for r in rows[max(0, index - settings["hrv_recent_days"]):index] if r["nightly_hrv_ms"] is not None]
        baseline = [r["nightly_hrv_ms"] for r in rows[max(0, index - settings["hrv_baseline_days"]):index] if r["nightly_hrv_ms"] is not None]
        row["hrv_prior_7d_valid_count"] = len(recent)
        row["hrv_prior_28d_valid_count"] = len(baseline)
        row["hrv_prior_7d_mean_ms"] = statistics.mean(recent) if len(recent) >= settings["hrv_recent_min_count"] else None
        enough = len(baseline) >= settings["hrv_baseline_min_count"]
        row["hrv_prior_28d_mean_ms"] = statistics.mean(baseline) if enough else None
        row["hrv_prior_28d_sd_ms"] = statistics.stdev(baseline) if enough and len(baseline) > 1 else None
        sd = row["hrv_prior_28d_sd_ms"]
        row["hrv_z_score"] = (row["nightly_hrv_ms"] - row["hrv_prior_28d_mean_ms"]) / sd if row["nightly_hrv_ms"] is not None and sd else None


def recovery_calendar(activities: list[dict], sleep_entries: list[dict], health_entries: list[dict],
                      conflicts: dict, settings: dict, hrv_verified: bool) -> list[dict]:
    """Join validated observations to daily dates without assuming daily running.

    The calendar spans source activity/recovery dates and conflict dates. Zero
    activity count means none recorded, not confirmed rest. Three runs/week is
    a preference, never an expectation applied to each date or past week.
    """
    sleep = {entry["record"]["calendarDate"]: entry for entry in sleep_entries}
    health = {entry["record"]["calendarDate"]: entry for entry in health_entries}
    dates = set(sleep) | set(health) | {row["analysis_date"] for row in activities if row["analysis_date"]}
    for conflict_list in conflicts.values():
        dates.update(item["key"] for item in conflict_list)
    if not dates:
        raise ValueError("No valid dated observations")
    start, end = date.fromisoformat(min(dates)), date.fromisoformat(max(dates))
    activity_counts = Counter(row["analysis_date"] for row in activities if row["analysis_date"])
    run_counts = Counter(row["analysis_date"] for row in activities if row["analysis_date"] and row["sport"] == "running")
    output = []
    conflict_maps = {kind: {item["key"]: item for item in items} for kind, items in conflicts.items()}
    for offset in range((end - start).days + 1):
        day = (start + timedelta(days=offset)).isoformat()
        flags = set()
        refs = {}
        row = {"schema_version": SCHEMA_VERSION, "date": day,
               "recorded_activity_count": activity_counts[day], "recorded_run_count": run_counts[day],
               "activity_status": "recorded_activity" if activity_counts[day] else "no_recorded_activity",
               "target_runs_per_week": settings["target_runs_per_week"],
               "sleep_observed": day in sleep or day in conflict_maps["sleep"],
               "health_observed": day in health or day in conflict_maps["health"],
               "hrv_semantics_verified": hrv_verified}
        if day in conflict_maps.get("activities", {}):
            row["activity_status"] = "conflicting_activity_records"
            flags.add("conflicting_activity_records")
        sleep_output, sleep_flags = sleep_summary(sleep[day]["record"] if day in sleep else {}, ZoneInfo(settings["analysis_timezone"]))
        health_output, health_flags = health_summary(health[day]["record"] if day in health else {}, hrv_verified)
        row.update(sleep_output)
        row.update(health_output)
        flags.update(sleep_flags | health_flags)
        for kind, source_map in (("sleep", sleep), ("health", health)):
            if day in source_map:
                refs[kind] = source_map[day]["refs"]
            elif day in conflict_maps[kind]:
                refs[kind] = conflict_maps[kind][day]["source_refs"]
                flags.add(f"conflicting_{kind}_records")
            else:
                flags.add(f"missing_{kind}_observation")
        row["source_refs"] = json_cell(refs)
        row["quality_flags"] = json_cell(sorted(flags))
        output.append(row)
    rolling_hrv(output, settings)
    return output
