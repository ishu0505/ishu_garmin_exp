"""Synthetic contract tests for deterministic tables and safe calendar joins."""

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo

from export_sources import read_sources, resolve_duplicates
from run_pipeline import activity_key, build, load_settings, verification_state
from summaries import activity_summary, health_summary, number, recovery_calendar, rolling_hrv, sleep_summary

SETTINGS_PATH = Path(__file__).with_name("settings.toml")
SETTINGS = load_settings(SETTINGS_PATH)
ZONE = ZoneInfo("Asia/Singapore")


def activity_raw() -> dict:
    """Return a synthetic running activity with cm/ms units and +7 wall time."""
    start = datetime(2026, 1, 1, 16, 30, tzinfo=timezone.utc).timestamp() * 1000
    return {"activityId": 123, "activityType": "running", "startTimeGmt": start,
            "beginTimestamp": start, "startTimeLocal": start + 7 * 3600000,
            "duration": 1800000, "elapsedDuration": 1800000, "movingDuration": 1800000,
            "distance": 500000, "avgSpeed": 500000 / 1800000, "avgHr": 150, "maxHr": 170,
            **{f"hrTimeInZone_{index}": 1800000 if index == 2 else 0 for index in range(7)}}


def entry(raw: dict) -> dict:
    """Wrap a synthetic raw record in a private provenance reference."""
    return {"record": raw, "refs": [{"sha256": "synthetic", "collection": "$", "record_index": 0}]}


def sleep_raw(day: str = "2026-01-02") -> dict:
    """Return a complete 60-minute synthetic sleep window."""
    prior = (date.fromisoformat(day) - timedelta(days=1)).isoformat()
    return {"calendarDate": day, "sleepStartTimestampGMT": f"{prior}T16:00:00",
            "sleepEndTimestampGMT": f"{prior}T17:00:00", "deepSleepSeconds": 600,
            "lightSleepSeconds": 1800, "remSleepSeconds": 600, "awakeSleepSeconds": 600,
            "unmeasurableSeconds": 0}


class PipelineTests(unittest.TestCase):
    """Check transformations, verification gates, temporal leakage and privacy."""

    def test_timezone_and_unit_gate(self):
        raw = activity_raw()
        result = activity_summary(entry(raw), ZONE, False)
        self.assertEqual(result["analysis_date"], "2026-01-02")
        self.assertEqual(result["source_local_date"], "2026-01-01")
        self.assertEqual(result["source_utc_offset_hours"], 7)
        self.assertEqual(result["distance_m"], 5000)
        self.assertEqual(result["duration_s"], 1800)
        self.assertIsNone(result["ef_summary"])
        verified = activity_summary(entry(raw), ZONE, True)
        self.assertAlmostEqual(verified["ef_summary"], (5000 / 1800) / 150)
        self.assertIsNone(verified["decoupling_pct"])
        self.assertIsNone(verified["trimp"])

    def test_missing_rem_is_not_zero(self):
        raw = sleep_raw()
        del raw["remSleepSeconds"]
        result, flags = sleep_summary(raw, ZONE)
        self.assertIsNone(result["rem_sleep_minutes"])
        self.assertIsNone(result["sleep_minutes"])
        self.assertIn("missing_or_invalid_rem_sleep_minutes", flags)
        raw["remSleepSeconds"] = 0
        self.assertEqual(sleep_summary(raw, ZONE)[0]["sleep_minutes"], 40)

    def test_invalid_measurements_and_sleep_window(self):
        for invalid in (True, -1, float("nan"), float("inf"), "12"):
            self.assertIsNone(number(invalid))
        raw = sleep_raw()
        raw["sleepEndTimestampGMT"] = raw["sleepStartTimestampGMT"]
        self.assertIn("invalid_sleep_window", sleep_summary(raw, ZONE)[1])
        raw = activity_raw()
        raw["avgSpeed"] = 12
        result = activity_summary(entry(raw), ZONE, True)
        self.assertIn("speed_distance_duration_mismatch", json.loads(result["quality_flags"]))
        self.assertIsNone(result["ef_summary"])

    def test_duplicates_merge_and_conflicts_quarantine(self):
        refs = [{"record": activity_raw(), "ref": {"record_index": index}} for index in range(2)]
        accepted, quality = resolve_duplicates(refs, activity_key)
        self.assertEqual(len(accepted[0]["refs"]), 2)
        self.assertEqual(quality["exact_duplicate_records"], 1)
        refs[1]["record"]["duration"] = 999
        accepted, quality = resolve_duplicates(refs, activity_key)
        self.assertEqual(accepted, [])
        self.assertEqual(len(quality["conflicts"]), 1)

    def test_no_recorded_activity_is_not_a_missing_workout(self):
        activities = [activity_summary(entry(activity_raw()), ZONE, False)]
        health = [entry({"calendarDate": "2026-01-04", "metrics": []})]
        rows = recovery_calendar(activities, [entry(sleep_raw())], health,
                                 {"sleep": [], "health": []}, SETTINGS, False)
        self.assertEqual([row["date"] for row in rows], ["2026-01-02", "2026-01-03", "2026-01-04"])
        self.assertEqual(rows[1]["recorded_run_count"], 0)
        self.assertEqual(rows[1]["activity_status"], "no_recorded_activity")
        self.assertEqual(rows[1]["target_runs_per_week"], 3)
        self.assertFalse(any("workout" in flag for flag in json.loads(rows[1]["quality_flags"])))
        self.assertIsNone(rows[1]["sleep_minutes"])

    def test_hrv_gate_and_conflicting_metric(self):
        raw = {"metrics": [{"type": "HRV", "value": 40}, {"type": "HR", "value": 60}]}
        result, _ = health_summary(raw, False)
        self.assertEqual(result["hrv_source_value"], 40)
        self.assertIsNone(result["nightly_hrv_ms"])
        self.assertIsNone(result["resting_hr_bpm"])
        raw["metrics"].append({"type": "HRV", "value": 45})
        result, flags = health_summary(raw, True)
        self.assertIsNone(result["nightly_hrv_ms"])
        self.assertIn("conflicting_hrv_metrics", flags)

    def test_rolling_calendar_windows_exclude_current_and_future(self):
        rows = [{"nightly_hrv_ms": 40 + index} for index in range(30)]
        rows[25]["nightly_hrv_ms"] = None
        rolling_hrv(rows, SETTINGS)
        baseline_mean = rows[28]["hrv_prior_28d_mean_ms"]
        recent_mean = rows[28]["hrv_prior_7d_mean_ms"]
        self.assertEqual(rows[28]["hrv_prior_7d_valid_count"], 6)
        rows[28]["nightly_hrv_ms"] = 1000
        rows[29]["nightly_hrv_ms"] = 2000
        rolling_hrv(rows, SETTINGS)
        self.assertEqual(rows[28]["hrv_prior_28d_mean_ms"], baseline_mean)
        self.assertEqual(rows[28]["hrv_prior_7d_mean_ms"], recent_mean)
        constant = [{"nightly_hrv_ms": 40} for _ in range(30)]
        rolling_hrv(constant, SETTINGS)
        self.assertIsNone(constant[28]["hrv_z_score"])

    def test_known_activity_verification_checks_actual_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "verification.json"
            anchor = {"activity": {"activity_id": 123, "distance_m": 5000,
                                   "duration_s": 1800, "source_reference": "synthetic Garmin display"}}
            path.write_text(json.dumps(anchor))
            self.assertTrue(verification_state(path, [entry(activity_raw())])[0])
            anchor["activity"]["distance_m"] = 50
            path.write_text(json.dumps(anchor))
            with self.assertRaises(ValueError):
                verification_state(path, [entry(activity_raw())])

    def test_end_to_end_repeatability_sources_and_privacy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            raw = activity_raw()
            raw.update({"name": "private workout name", "startLatitude": 1.2345})
            (source / "activities.json").write_text(json.dumps([{"summarizedActivitiesExport": [raw]}]))
            (source / "sleep.json").write_text(json.dumps([{"retro": False}, sleep_raw(), sleep_raw("2026-01-03")]))
            (source / "health.json").write_text(json.dumps([{"calendarDate": "2026-01-03", "metrics": [{"type": "HRV", "value": 45}]}]))
            before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in source.iterdir()}
            report = build(source, root / "outputs", SETTINGS_PATH)
            first = {path.name: path.read_bytes() for path in (root / "outputs").iterdir()}
            build(source, root / "outputs", SETTINGS_PATH)
            second = {path.name: path.read_bytes() for path in (root / "outputs").iterdir()}
            self.assertEqual(first, second)
            self.assertEqual(before, {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in source.iterdir()})
            self.assertEqual(report["counts"]["activities_with_next_day_sleep_and_health"], 1)
            self.assertEqual(len(report["reconciliation"]["sleep"]["invalid_key_refs"]), 1)
            self.assertFalse(any(b"private workout name" in content or b"startLatitude" in content for content in first.values()))
            with self.assertRaises(ValueError):
                build(source, source / "outputs", SETTINGS_PATH)

    def test_source_parse_errors_prevent_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "broken.json").write_text("not JSON")
            self.assertTrue(read_sources(source)[2])
            with self.assertRaises(ValueError):
                build(source, root / "outputs", SETTINGS_PATH)
            self.assertFalse((root / "outputs").exists())

    def test_conflicting_activity_date_is_not_reported_as_no_activity(self):
        conflicts = {"sleep": [], "health": [], "activities": [{"key": "2026-01-02", "source_refs": []}]}
        rows = recovery_calendar([], [], [], conflicts, SETTINGS, False)
        self.assertEqual(rows[0]["activity_status"], "conflicting_activity_records")
        self.assertIn("conflicting_activity_records", json.loads(rows[0]["quality_flags"]))

    def test_conflicting_sleep_is_observed_but_not_usable(self):
        conflicts = {"sleep": [{"key": "2026-01-02", "source_refs": []}], "health": []}
        rows = recovery_calendar([], [], [], conflicts, SETTINGS, False)
        self.assertTrue(rows[0]["sleep_observed"])
        self.assertIsNone(rows[0]["sleep_minutes"])
        self.assertIn("conflicting_sleep_records", json.loads(rows[0]["quality_flags"]))


if __name__ == "__main__":
    unittest.main()
