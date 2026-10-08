"""Read known Garmin JSON collections and retain private record provenance.

Account records and unknown collections are skipped. Raw sources are never
modified. This module returns records to local code, never to console logs.
"""

from collections import defaultdict
import hashlib
import json
from pathlib import Path


def read_sources(root: Path) -> tuple[dict, list[dict], list[dict]]:
    """Load activity, sleep and health records with exact source array indexes.

    Return collection entries, an anonymous file manifest, and redacted errors.
    Each entry has a raw record and a reference consisting of digest, JSON
    collection path and record index. Sleep placeholders remain counted.
    """
    groups = {"activities": [], "sleep": [], "health": []}
    manifest = []
    errors = []
    for source_number, path in enumerate(sorted(root.rglob("*.json")), 1):
        try:
            payload = path.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            manifest.append({"source_number": source_number, "sha256": digest, "bytes": len(payload)})
            value = json.loads(payload)
            if not isinstance(value, list):
                continue
            for wrapper_index, wrapper in enumerate(value):
                if isinstance(wrapper, dict) and "summarizedActivitiesExport" in wrapper:
                    add_entries(groups["activities"], wrapper["summarizedActivitiesExport"], digest,
                                f"$[{wrapper_index}].summarizedActivitiesExport")
            if any(isinstance(row, dict) and "sleepStartTimestampGMT" in row for row in value):
                add_entries(groups["sleep"], value, digest, "$")
            if any(isinstance(row, dict) and "metrics" in row and "calendarDate" in row for row in value):
                add_entries(groups["health"], value, digest, "$")
        except (OSError, ValueError, TypeError) as error:
            errors.append({"source_number": source_number, "error_type": type(error).__name__})
    return groups, manifest, errors


def add_entries(target: list, rows: object, digest: str, collection: str) -> None:
    """Keep true source indexes; reject malformed recognized record collections."""
    if not isinstance(rows, list):
        raise ValueError("Expected an array")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError("Expected an object record")
        target.append({"record": row, "ref": {
            "sha256": digest, "collection": collection, "record_index": index,
        }})


def resolve_duplicates(entries: list[dict], key_function) -> tuple[list[dict], dict]:
    """Merge exact duplicates and quarantine conflicting records by key.

    No conflicting value wins arbitrarily. Quarantined keys retain only private
    references in the report; their raw values remain in the original sources.
    Entries with invalid/missing keys are rejected and counted separately.
    """
    grouped = defaultdict(list)
    invalid = []
    for entry in entries:
        key = key_function(entry["record"])
        if key is None:
            invalid.append(entry["ref"])
        else:
            grouped[key].append(entry)
    accepted = []
    conflicts = []
    duplicate_count = 0
    for key in sorted(grouped):
        matches = grouped[key]
        refs = [entry["ref"] for entry in matches]
        if any(entry["record"] != matches[0]["record"] for entry in matches[1:]):
            conflicts.append({"key": key, "source_refs": refs})
        else:
            duplicate_count += len(matches) - 1
            accepted.append({"record": matches[0]["record"], "refs": refs})
    return accepted, {"input_records": len(entries), "accepted_records": len(accepted),
                      "exact_duplicate_records": duplicate_count, "invalid_key_refs": invalid,
                      "conflicts": conflicts}
