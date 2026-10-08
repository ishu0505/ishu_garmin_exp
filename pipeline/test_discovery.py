"""Synthetic checks for discovery behavior; no private Garmin data is needed."""

import json
from pathlib import Path
import tempfile
import unittest

from discover_export import collections, coverage, date_text, discover, profile_records


class DiscoveryTests(unittest.TestCase):
    """Check missing dates, wrapper layouts, source scaling and privacy boundaries."""

    def test_dates_and_gaps(self):
        self.assertIsNone(date_text("2026-02-30"))
        self.assertIsNone(date_text(None))
        self.assertIsNone(date_text(123))
        self.assertEqual(date_text(1767225600000), "2026-01-01")
        result = coverage(["2026-01-01", "2026-01-03", "2026-01-03", None])
        self.assertEqual(result["missing_dates_in_span"], 1)
        self.assertEqual(result["repeated_date_records"], 1)
        self.assertEqual(result["longest_consecutive_days"], 1)

    def test_wrapper_and_absent_fields(self):
        rows = [{"calendarDate": "2026-01-01", "remSleepSeconds": 0}, {"retro": False}]
        groups = collections([{"sleep": rows}])
        result = profile_records(groups[1][0], groups[1][1])
        self.assertEqual(result["fields"]["remSleepSeconds"]["non_null"], 1)
        self.assertEqual(result["date_coverage"]["calendarDate"]["valid_date_records"], 1)

    def test_first_sleep_row_can_be_a_placeholder(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [{"retro": False}, {"sleepStartTimestampGMT": "2026-01-01T22:00:00", "calendarDate": "2026-01-02"}]
            (root / "private-name.json").write_text(json.dumps(rows))
            report = discover(root)
            self.assertEqual(report["combined"]["sleep"]["records"], 2)
            self.assertEqual(report["quality"]["sleep_rows_without_date"], 1)
            self.assertNotIn("private-name", json.dumps(report))

    def test_sensitive_values_and_errors_are_not_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "account.json").write_text(json.dumps({"emailAddress": "private@example.test"}))
            (root / "broken.json").write_text("invalid sensitive contents")
            report = discover(root)
            text = json.dumps(report)
            self.assertNotIn("private@example.test", text)
            self.assertNotIn("invalid sensitive contents", text)
            self.assertEqual(report["errors"][0]["error_type"], "JSONDecodeError")

    def test_metric_nulls_and_duplicate_ids(self):
        metrics = profile_records("metrics", [{"calendarDate": "2026-01-01", "metrics": [{"type": "HRV", "value": None}]}])
        self.assertEqual(metrics["metric_types"]["HRV"]["non_null_values"], 0)
        activities = profile_records("activities", [{"activityId": 1}, {"activityId": 1}])
        self.assertEqual(activities["duplicate_activity_ids"], 1)


if __name__ == "__main__":
    unittest.main()
