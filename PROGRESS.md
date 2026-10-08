# Project progression

Updated: **2026-10-08 (Asia/Singapore)**

**Current phase: Phase 2 — Deterministic pipeline**  
**Status: Complete for available metrics; Phase 3 awaits user authorization**

## Authorization record

- 2026-10-08: User requested repository instructions and phase tracking only,
  with uv for Python tooling and work proceeding phase by phase.
- 2026-10-08: User requested readable Python/ML conventions, clear comments
  and docstrings, and maintained documentation explaining the repository layout.
- 2026-10-08: User authorized Phase 1 discovery/data contract and requested the
  Garmin Python package for future incremental downloads. No account login or
  later phase was authorized at that point.
- 2026-10-08: User authorized Phase 2 and specified three intended runs/week,
  not daily running. Days without runs must not be treated as missing workouts.
- 2026-10-08: User supplied September 30 Garmin distance and timer/moving/elapsed
  values for external activity-unit verification. No account login is authorized.

## Phase board

| Phase | Deliverable / exit evidence | Status |
| --- | --- | --- |
| 0 — Setup | Shared and folder instructions, privacy exclusions, roadmap, tracker | Complete |
| 1 — Discovery & data contract | Redacted inventory, coverage and schema report, units/time alignment/metric decisions, uv project configuration | Complete (v0.1 with explicit verification gates) |
| 2 — Deterministic pipeline | Reproducible activity and recovery summaries, quality flags, provenance, meaningful validation | Complete (supported metrics; unsupported fields explicitly null) |
| 3 — Descriptive baseline | Coverage-aware trends, load/recovery summaries, suitable benchmark and confounder report | Not started |
| 4 — Modeling | Validated simple baselines; optional physiology/predictive models with temporal evaluation and uncertainty | Not started |
| 5 — Experiment design | User-reviewed hypothesis, protocol, outcomes, confounders, and recovery review policy | Not started |
| 6 — Experiment evaluation | Recorded adherence, outcomes versus baseline, limitations, and user-reviewed next block | Not started |
| 7 — Incremental updates | User-authorized local sync/export workflow, safe credentials, deduplication, audit trail | Not started |

Each phase requires the user's instruction to start. Later phases may be revised
or skipped based on evidence; update the board and decision log first.

## Phase 0 checklist

- [x] Read the supplied project proposal.
- [x] Identify source export location without reading raw record contents.
- [x] Establish canonical root AGENTS.md and Claude entry point.
- [x] Add folder guidance for data, pipeline, models, experiments, and plans.
- [x] Document roles without installing speculative skills or automatic agents.
- [x] Protect source exports, derived private data, and credentials from Git.
- [x] Define phase gates and retain the setup-only boundary.
- [x] Check instruction consistency and Git ignore behavior.
- [x] Add readable Python/ML and documentation conventions plus a repo map.

## Prerequisites and unresolved decisions

- uv 0.12.23 is now installed in ignored `.tools/`; Python 3.14.8 is managed
  through the uv project environment. No other Python package manager was used.
- `fitdecode` 0.11.0 and optional `garminconnect` 0.3.17 are installed and locked.
- Activity distance and timer/moving/elapsed units are verified against the
  user's September 30 Garmin display values. Speed follows the distance/time
  scale and retains cross-field consistency checks.
- HRV semantics remain unverified. Source-labeled HRV is preserved; nightly
  HRV in ms, rolling means and z-scores remain null until evidence is available.
- Current export lacks standard workout FIT records. Decoupling remains null
  until individual activity tracks become available through later authorized sync.
- Daily RHR and TRIMP definitions remain unverified; v0.2 explicitly leaves
  these unavailable instead of inventing inputs or substituting health HR.
- Model suitability, history requirements, and training interventions remain
  decisions for later phases; no personal physiological values are assumed.

## Decision log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-10-08 | Root AGENTS.md is canonical; CLAUDE.md files route to it | Keep Claude and other agents aligned |
| 2026-10-08 | Use folder guidance and role handbook; defer reusable skills | Actual workflows do not exist yet |
| 2026-10-08 | Preserve existing export under ishu_garmin_data/ | Avoid duplicating or moving private source data |
| 2026-10-08 | Defer Python configuration and dependencies to Phase 1 | Setup-only scope; uv unavailable |
| 2026-10-08 | Require clear code, comments/docstrings, and maintained repo/folder documentation | Make the project easy to understand and navigate |
| 2026-10-08 | Install local uv and optional Garmin sync dependency | User authorized Phase 1 setup and requested future download support |
| 2026-10-08 | Use Singapore analysis dates while retaining original offsets | Activities include both +8 and +7; sleep waking dates match Singapore |
| 2026-10-08 | Contract v0.1 preserves missing stages and marks unsupported/unverified metrics | Avoid fabricated sleep totals, drift, RHR, load, or unit certainty |
| 2026-10-08 | Store intended frequency as three runs/week; no absent-workout alarms | User does not run daily; wellness coverage is a separate concern |
| 2026-10-08 | Verify cm/ms activity scales from supplied September 30 values | Distance within 4.26 m and all times within 0.17 s of Garmin display |
| 2026-10-08 | Implement contract v0.2 CSVs with source/output hashes and conflict quarantine | Reproducible tables with auditable missingness; unsupported metrics remain null |

## Completion evidence

Phase 0: documentation and scaffolding created; Git ignore checks confirm that
raw export and representative private output/credential paths are excluded.
No source export contents were read, no implementation was added, and no
Python environment or dependencies were created.

Phase 1: all 26 files inspected without inspection errors; 66 unique activities,
179 matched dated sleep/health records, 26 undated sleep placeholders, and a
nonstandard FIT archive identified. `docs/DISCOVERY.md` records findings and
`docs/DATA_CONTRACT.md` defines schema v0.1. Five synthetic unittest checks pass;
Garmin import/version check passes without login. Git excludes raw exports,
private reports, local binaries/environments/cache, and credentials. Sources
remain unchanged; discovery metadata is not a Phase 2 analytical table.

Phase 2: `pipeline/run_pipeline.py` produces 66 activity rows and a continuous
204-day recovery calendar, with 179 sleep and 179 health dates. Twenty-six
undated sleep placeholders are counted/excluded; 149 dates have all three
measured sleep stages. Fifty-nine activities have next-day dated sleep/health
observations with a valid sleep window/date. No conflicting record groups were
found. Unit evidence is private; the three-run weekly preference is documented
in tracked settings and instructions. Seventeen synthetic tests pass. Repeated
real-data builds produce identical bytes for both CSVs and the quality report;
all 26 source hashes match Phase 1. Git ignores outputs and verification evidence.
`docs/PIPELINE_VALIDATION.md` details retained quality flags and unavailable metrics.

**Next action:** on user authorization, begin Phase 3 coverage-aware descriptive
baselines using validated fields and the three-run weekly preference. Resolve
HRV semantics before physiological HRV features; account sync remains later work.
