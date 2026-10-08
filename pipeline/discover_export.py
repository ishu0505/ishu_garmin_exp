"""Inventory a Garmin export locally and emit bounded, redacted metadata.

This Phase 1 tool discovers formats and coverage; it does not build analytical
tables. It never includes source filenames, identifiers, GPS, or raw records in
its report. Full local reports are written to ignored data/reports/ by default.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import statistics
import zipfile
from zoneinfo import ZoneInfo

import fitdecode


def date_text(value: object) -> str | None:
    """Return an ISO date for supported text/epoch values; reject ambiguous data.

    Epoch timestamps may be milliseconds or seconds. Numeric timestamps are
    accepted only in a plausible 2000–2100 range; callers choose date fields.
    """
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}(?:$|[T ])", value):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = value / 1000 if value > 100_000_000_000 else value
        if 946684800 <= seconds <= 4102444800:
            return datetime.fromtimestamp(seconds, timezone.utc).date().isoformat()
    return None


def coverage(values: list[object]) -> dict:
    """Summarize observed dates, missing calendar days, and duplicate dates.

    A missing calendar day is a coverage gap, not evidence of a rest day.
    Duplicate dates may be valid for activity collections.
    """
    dates = [day for value in values if (day := date_text(value))]
    unique = sorted(set(dates))
    if not unique:
        return {"valid_date_records": 0}
    span = (datetime.fromisoformat(unique[-1]) - datetime.fromisoformat(unique[0])).days + 1
    observed = set(unique)
    current = longest = 0
    start = datetime.fromisoformat(unique[0])
    for offset in range(span):
        if (start + timedelta(days=offset)).date().isoformat() in observed:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return {
        "first_date": unique[0], "last_date": unique[-1],
        "valid_date_records": len(dates), "unique_dates": len(unique),
        "span_days": span, "missing_dates_in_span": span - len(unique),
        "repeated_date_records": len(dates) - len(unique),
        "longest_consecutive_days": longest,
    }


def collections(value: object, path: str = "$") -> list[tuple[str, list[dict]]]:
    """Find record lists in wrappers without recursively profiling nested records."""
    found = []
    if isinstance(value, list):
        records = [item for item in value if isinstance(item, dict)]
        if records:
            found.append((path, records))
        # Export wrappers typically contain a single dictionary of named lists.
        if len(value) == 1 and records:
            for key, child in records[0].items():
                if isinstance(child, list):
                    found.extend(collections(child, f"{path}[].{key}"))
    return found


def profile_records(path: str, records: list[dict]) -> dict:
    """Describe field presence/types and approved date/numeric metadata only."""
    keys = sorted({key for record in records for key in record})
    fields = {}
    for key in keys:
        values = [record[key] for record in records if key in record]
        fields[key] = {
            "present": len(values), "non_null": sum(value is not None for value in values),
            "types": dict(Counter(type(value).__name__ for value in values)),
        }
    date_keys = [key for key in keys if key.lower() in {
        "calendardate", "starttimegmt", "starttimelocal", "begintimestamp",
        "asofdategmt", "sleepstarttimestampgmt", "sleependtimestampgmt",
    }]
    dates = {key: coverage([record.get(key) for record in records]) for key in date_keys}
    # Aggregate ranges help detect source scaling, without exposing any raw row.
    numeric_ranges = {}
    for key in ("duration", "elapsedDuration", "movingDuration", "distance", "avgSpeed"):
        numbers = [r[key] for r in records if isinstance(r.get(key), (int, float))]
        if numbers:
            numeric_ranges[key] = {"min": min(numbers), "median": statistics.median(numbers), "max": max(numbers)}
    result = {"path": path, "records": len(records), "fields": fields,
              "date_coverage": dates, "source_numeric_ranges": numeric_ranges}
    if "activityId" in keys:
        ids = [r["activityId"] for r in records if r.get("activityId") is not None]
        result["duplicate_activity_ids"] = len(ids) - len(set(ids))
        result["activity_types"] = dict(Counter(
            str(r.get("activityType")) for r in records
            if isinstance(r.get("activityType"), (int, str))
            and re.fullmatch(r"[\w-]{1,40}", str(r["activityType"]))
        ))
        offsets = Counter()
        for record in records:
            gmt, local = record.get("startTimeGmt"), record.get("startTimeLocal")
            try:
                if isinstance(gmt, (int, float)) and isinstance(local, (int, float)):
                    offsets[str((local - gmt) / 3_600_000)] += 1
                elif isinstance(gmt, str) and isinstance(local, str):
                    offsets[str((datetime.fromisoformat(local) - datetime.fromisoformat(gmt)).total_seconds() / 3600)] += 1
            except (ValueError, TypeError):
                continue
        result["local_minus_gmt_hours"] = dict(offsets)
    if "metrics" in keys:
        metric_groups = defaultdict(list)
        for record in records:
            for metric in record.get("metrics") or []:
                kind = metric.get("type") if isinstance(metric, dict) else None
                if isinstance(kind, str) and re.fullmatch(r"[\w-]{1,50}", kind):
                    metric_groups[kind].append({"calendarDate": record.get("calendarDate"), "value": metric.get("value")})
        result["metric_types"] = {
            kind: {"records": len(rows), "non_null_values": sum(r["value"] is not None for r in rows),
                   "coverage": coverage([r["calendarDate"] for r in rows])}
            for kind, rows in sorted(metric_groups.items())
        }
    return result


def inspect_fit(payload: bytes) -> dict:
    """Read FIT messages in memory; report message kinds, fields, units and dates."""
    messages = Counter()
    fields = defaultdict(set)
    units = defaultdict(set)
    timestamps = []
    kinds = Counter()
    with fitdecode.FitReader(io.BytesIO(payload)) as reader:
        for frame in reader:
            if not isinstance(frame, fitdecode.FitDataMessage):
                continue
            messages[frame.name] += 1
            for field in frame.fields:
                fields[frame.name].add(field.name)
                if field.units:
                    units[f"{frame.name}.{field.name}"].add(field.units)
                if field.name == "timestamp" and isinstance(field.value, datetime):
                    timestamps.append(field.value.isoformat())
                if frame.name == "file_id" and field.name == "type":
                    kinds[str(field.value)] += 1
    return {"file_types": dict(kinds), "messages": dict(messages),
            "fields": {name: sorted(keys) for name, keys in fields.items()},
            "units": {name: sorted(values) for name, values in units.items()},
            "timestamp_coverage": coverage(timestamps)}


def discover(root: Path) -> dict:
    """Inventory source files without modifying them or extracting archives.

    SHA-256 digests are kept locally for duplicate detection. Archive reads are
    bounded to 100 MiB per member and 500 MiB total to avoid uncontrolled expansion.
    Errors report only exception type, never a potentially sensitive filename.
    """
    report = {"version": 1, "files": [], "errors": [], "duplicate_file_count": 0}
    hashes = Counter()
    for index, source in enumerate(sorted(p for p in root.rglob("*") if p.is_file()), 1):
        payload = source.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        hashes[digest] += 1
        top_folder = source.relative_to(root).parts[0]
        safe_folder = top_folder if top_folder in {"DI-Connect-Fitness", "DI-Connect-Wellness", "DI-Connect-User"} else "other"
        item = {"file_id": f"source_{index:03d}", "folder": safe_folder,
                "suffix": source.suffix.lower(), "bytes": len(payload), "sha256": digest}
        try:
            if source.suffix.lower() == ".json":
                value = json.loads(payload)
                item["root_type"] = type(value).__name__
                item["root_keys"] = sorted(value) if isinstance(value, dict) else []
                item["collections"] = [profile_records(path, records) for path, records in collections(value)]
            elif source.suffix.lower() == ".zip":
                with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                    members = archive.infolist()
                    item["archive_member_count"] = len(members)
                    item["archive_extensions"] = dict(Counter(Path(m.filename).suffix.lower() for m in members if not m.is_dir()))
                    if sum(m.file_size for m in members) > 500 * 1024 * 1024:
                        raise ValueError("Archive exceeds discovery limit")
                    item["fit_profiles"] = []
                    for member in members:
                        if member.file_size > 100 * 1024 * 1024:
                            raise ValueError("Member exceeds discovery limit")
                        if Path(member.filename).suffix.lower() == ".fit":
                            item["fit_profiles"].append(inspect_fit(archive.read(member)))
            elif source.suffix.lower() == ".fit":
                item["fit_profiles"] = [inspect_fit(payload)]
        except Exception as error:
            report["errors"].append({"file_id": item["file_id"], "error_type": type(error).__name__})
        report["files"].append(item)
    report["duplicate_file_count"] = sum(count - 1 for count in hashes.values())
    report["file_count"] = len(report["files"])
    report["extensions"] = dict(Counter(item["suffix"] for item in report["files"]))
    # Combine repeated export chunks to expose overlap and coverage across files.
    combined = defaultdict(list)
    for source in sorted(root.rglob("*.json")):
        try:
            value = json.loads(source.read_bytes())
            for path, rows in collections(value):
                signature = "activities" if "summarizedActivitiesExport" in path else None
                if any("sleepStartTimestampGMT" in row for row in rows):
                    signature = "sleep"
                if any("metrics" in row and "calendarDate" in row for row in rows):
                    signature = "health_metrics"
                if any("asOfDateGmt" in row and "rhr" in row for row in rows):
                    signature = "fitness_age"
                if signature:
                    combined[signature].extend(rows)
        except (ValueError, OSError):
            continue
    report["combined"] = {name: profile_records(name, rows) for name, rows in combined.items()}
    activities = combined.get("activities", [])
    sleep = combined.get("sleep", [])
    metrics = combined.get("health_metrics", [])
    sleep_dates = {date_text(row.get("calendarDate")) for row in sleep} - {None}
    metric_dates = {date_text(row.get("calendarDate")) for row in metrics} - {None}
    activity_dates = {date_text(row.get("startTimeLocal")) for row in activities} - {None}
    report["quality"] = {
        "sleep_rows_without_date": sum(date_text(row.get("calendarDate")) is None for row in sleep),
        "sleep_and_health_dates": len(sleep_dates & metric_dates),
        "activity_dates_with_sleep_and_health": len(activity_dates & sleep_dates & metric_dates),
        "sleep_dates_without_health": len(sleep_dates - metric_dates),
        "health_dates_without_sleep": len(metric_dates - sleep_dates),
        "activity_rows_with_positive_hr": sum(isinstance(row.get("avgHr"), (int, float)) and row["avgHr"] > 0 for row in activities),
        "speed_distance_duration_consistent": sum(
            abs(row["distance"] / row["duration"] - row["avgSpeed"]) < 0.001
            for row in activities if row.get("duration", 0) > 0 and row.get("avgSpeed") is not None
        ),
        "sleep_fields": {key: sum(row.get(key) is not None for row in sleep)
                         for key in ("deepSleepSeconds", "lightSleepSeconds", "remSleepSeconds", "awakeSleepSeconds", "unmeasurableSeconds")},
    }
    # Verify date attribution from sleep end rather than assuming UTC dates join.
    end_date_mismatches = 0
    for row in sleep:
        if not row.get("sleepEndTimestampGMT"):
            continue
        end = datetime.fromisoformat(row["sleepEndTimestampGMT"].replace("Z", "+00:00"))
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)  # The source explicitly labels this field GMT.
        local_day = end.astimezone(ZoneInfo("Asia/Singapore")).date().isoformat()
        end_date_mismatches += local_day != row.get("calendarDate")
    zone_ratios = [sum(row.get(f"hrTimeInZone_{index}", 0) for index in range(7)) / row["duration"]
                   for row in activities if row.get("duration", 0) > 0]
    report["quality"]["sleep_end_singapore_date_mismatches"] = end_date_mismatches
    report["quality"]["hr_zone_time_duration_ratio"] = {
        "min": min(zone_ratios), "median": statistics.median(zone_ratios), "max": max(zone_ratios)
    } if zone_ratios else None
    report["quality"]["fitness_age_rhr_non_null"] = sum(row.get("rhr") is not None for row in combined.get("fitness_age", []))
    return report


def main() -> None:
    """Write the private metadata report and print a compact aggregate summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("ishu_garmin_data"))
    parser.add_argument("--output", type=Path, default=Path("data/reports/discovery.json"))
    args = parser.parse_args()
    if not args.source.is_dir():
        parser.error("Source must be an existing directory")
    report = discover(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    summary = {key: report[key] for key in ("file_count", "extensions", "duplicate_file_count", "errors", "quality")}
    summary["combined"] = {
        name: {key: value for key, value in profile.items() if key != "fields"}
        for name, profile in report["combined"].items()
    }
    summary["fit"] = [{key: profile[key] for key in ("file_types", "messages", "timestamp_coverage")}
                      for item in report["files"] for profile in item.get("fit_profiles", [])]
    print(json.dumps(summary, indent=2))
    if report["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
