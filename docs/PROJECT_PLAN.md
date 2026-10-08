# Project plan and data contract outline

## Aim

Support sub-20 5K, sub-45 10K, and sub-1:35 half marathon goals with a
reproducible Garmin data pipeline, cautious interpretation, and measurable
training experiments. This is a personal analytical project; performance
improvement is a goal, not a promised result.

The user runs or intends to run **three times per week**, not daily. Treat other
days as valid calendar days; absent activity is neither a missing workout nor
proof of confirmed rest. Keep wellness coverage separate from run frequency.

The supplied proposal motivates this roadmap. Its training protocols, suggested
8–12 week history, 2–3 week experiment windows, time constants, and HRV trigger
are hypotheses to evaluate later, not accepted personal facts.

## Phases and gates

0. **Setup:** instructions, privacy protections, roles, and progression tracker.
1. **Discovery and contract:** configure Python through uv; write bounded local
   discovery tools; report file types, coverage, schemas, duplicates, missingness,
   and timestamp behavior without exposing raw records. Agree on a data contract.
2. **Pipeline:** implement deterministic readers for formats actually present,
   activity/recovery summaries, provenance, quality reports, and repeatable output.
3. **Baseline:** analyze coverage and descriptive trends, decide eligible
   benchmark sessions, and document potential confounders and useful outcomes.
4. **Modeling:** evaluate simple baselines first; consider Ridge, Banister-style
   impulse response, or more complex predictors only when justified. Establish
   an observed performance outcome before fitting a performance model; report
   identifiability and uncertainty rather than claiming exact personal constants.
5. **Experiment design:** propose one clear intervention, comparison, outcomes,
   adherence log, and review policy. User reviews the protocol before activation.
6. **Evaluation:** record observed outcomes and adherence, quantify uncertainty,
   address weather/terrain/illness/life-stress confounders, then propose a next block.
7. **Updates:** after explicit authorization, add incremental export or account
   sync with secure local credentials, idempotent imports, and documented recovery.

Read `PROGRESS.md` for actual authorization and status. Stop at each phase gate
and present the completed deliverables before asking to start the next phase.

## Phase 1 contract decisions

Define table grain explicitly: activities have **one row per activity**, with
a separate daily aggregation if needed; recovery has one row per agreed local
date with documented sleep attribution. Do not collapse multiple activities
into one row without an explicit aggregation rule.

Proposed fields, subject to export availability:

| Output | Candidate fields |
| --- | --- |
| activities_summary | activity ID, UTC start, local date, sport, distance_m, duration_s, moving_duration_s, avg_hr_bpm, max_hr_bpm, load metric, EF, decoupling_pct, source reference, quality flags |
| recovery_summary | local date, resting_hr_bpm, nightly_hrv_ms, prior-history HRV baseline/z-score, sleep_minutes, deep_sleep_minutes, coverage, source reference, quality flags |

Metric decisions to settle before implementation:

- **EF:** speed in m/s divided by HR in bpm. Define eligible activity type,
  averaging, moving/stopped treatment, and matching speed/HR samples. Do not
  interchange pace with speed or compare unlike sports without justification.
- **Decoupling:** proposed sign convention is
  `100 * (EF_first_half - EF_second_half) / EF_first_half`. Specify warmup
  exclusions, elapsed versus moving halves, steady-session eligibility,
  terrain sensitivity, and invalid denominator/missing HR handling.
- **Load/TRIMP:** select a named variant, required personal HR inputs and units;
  do not invent HRmax/resting HR or silently replace missing load with zero.
- **HRV:** verify what Garmin measurement is available, units, validity, and
  collection consistency. Define window length, minimum history, mean/SD
  conventions, zero-SD behavior, and past-only baseline construction. Retain
  nightly values separately from rolling means and avoid future-data leakage.
- **Recovery policy:** define review triggers later with the user and supporting
  evidence. Do not activate the proposal's 1.5-SD rule during repository setup.

CSV outputs are now implemented under contract v0.2 in `docs/DATA_CONTRACT.md`;
this outline records the original design questions. See that contract for current
definitions and `docs/PIPELINE_VALIDATION.md` for evidence. Analysis reports must
identify their source table version. Parquet remains optional future work.
