# Agent role handbook

These roles structure tasks; they do not install agents, invoke models, or
authorize delegation. All roles follow root and folder instructions plus the
active phase recorded in `PROGRESS.md`. Skills can be added later when a stable
repeated workflow benefits from one.

| Role | Responsibilities | Required handoff |
| --- | --- | --- |
| Data engineer | Bounded discovery, data contract, deterministic parsing, timestamps, provenance, quality checks, later authorized sync | Schema/units, changes, validation, exclusions, reproducible uv commands |
| Physiology analyst | Interpret validated summary metrics, assess confounders and coverage, evaluate descriptive baselines and model limits | Evidence-linked findings, uncertainty, limitations, open questions |
| Experiment designer | Draft one intervention, baseline/comparison, outcomes, adherence and review rules; evaluate later results | Reviewable protocol, evidence needed, user decisions, next phase boundary |

If the user requests subagents, each task must state its role, phase, allowed
files, bounded inputs, expected output, validation, and completion criteria.
Use summaries instead of raw exports as analytical context. Assign one owner
per edited file and integrate results before updating the phase tracker.

Example future task brief:

> Phase 2 / data engineer: implement the agreed wellness summary contract in
> pipeline/. Read raw records only through local code. Return redacted quality
> counts and tests via uv; do not fit models or propose training changes.
