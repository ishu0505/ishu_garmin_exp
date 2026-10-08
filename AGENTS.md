# Shared project instructions

## Aim and current authorization

Create a reproducible personal Garmin training analysis lab supporting sub-20
5K, sub-45 10K, and sub-1:35 half marathon goals. Prioritize data reliability,
interpretable analysis, and measurable experiments.

Read `PROGRESS.md` first, then `docs/PROJECT_PLAN.md`, and the instructions in
the folder you will change. **Phase 2 deterministic pipeline is authorized.**
Do not begin data discovery, extraction, coding, modeling, training prescription,
or account integration outside the currently authorized phase.
Completing one phase does not authorize the next. Preserve this rule when
updating status files; record new authorization when it arrives.

## Tooling

- Use uv exclusively for Python environments, packages, scripts, and checks.
  Examples: `uv sync`, `uv add <package>`, `uv run pytest`, `uv run <script>`.
- Do not invoke pip, pipx, Poetry, Conda, bare python/python3, or standalone venv.
- If uv is unavailable, report the prerequisite. Do not substitute another
  Python package manager or install tools silently.
- Add dependencies only when required by the active authorized phase. When
  Python configuration is introduced, commit `pyproject.toml` and `uv.lock`.
- Ordinary file editing, searching, and Git commands are allowed; the uv rule
  covers Python execution and dependency management.

## Coding and documentation conventions

- Write simple, easy-to-understand Python and ML code. Prefer explicit steps,
  descriptive names, small focused functions, and straightforward control flow.
  Avoid clever one-liners, unnecessary classes, and abstractions without a
  concrete need. Add complexity only when it solves a documented problem.
- Use meaningful variable names and include units where useful, such as
  `distance_m` and `sleep_minutes`. Use type hints for function inputs and
  outputs where they clarify the contract.
- Add plain-language module docstrings explaining purpose and place in the
  workflow. Give public functions and non-obvious helpers docstrings covering
  what they do, inputs, outputs, units, assumptions, and important errors or
  edge cases. Keep documentation proportional to the function's complexity.
- Write clear comments explaining why a calculation, exclusion, or design
  choice exists. Explain unfamiliar ML or physiology terms when introduced.
  Avoid comments that simply repeat the code, and update comments/docstrings
  when behavior changes.
- Make ML workflows readable as named steps: choose the target and features,
  split by time, fit preprocessing on training data, train, predict, and evaluate
  against a baseline. Explain feature meaning, target timing, leakage prevention,
  parameters, seeds where relevant, and what each evaluation metric measures.
- Keep the whole repo navigable. Maintain the root README as the entry point
  and `docs/REPO_MAP.md` as the directory/document map. When a folder gains
  implementation, add a short README describing its purpose, main files,
  inputs/outputs, dependencies on other folders, and runnable uv examples.
- Update relevant documentation in the same change as code or layout changes.
  Label planned components as planned; describe actual files and supported
  behavior accurately. Keep schemas/units in the data contract and phase status
  in `PROGRESS.md`, linking to them instead of copying competing definitions.
- Before completing a change, check that a new reader can find the entry point,
  understand the workflow, and reproduce the documented commands. Use synthetic
  or redacted examples so documentation does not expose private data.

## Data handling

- `ishu_garmin_data/` is the existing source export. Preserve it in place;
  never overwrite, delete, rename, or modify source data.
- Do not assume that its layout matches the pasted bulk-export example. The
  observed top level has Fitness, Wellness, and User folders; verify structure
  with code in Phase 1 before choosing parsers.
- Never feed raw FIT binaries, full raw JSON, GPS tracks, or account records
  into LLM context. Future discovery scripts may read raw data locally and
  return bounded schemas, counts, date ranges, and redacted samples.
- Keep raw and derived personal data, health records, authentication material,
  and precise location information out of Git and shared reports. Gitignore
  is a safeguard; inspect staged changes before any commit.
- Agent analysis should use validated aggregated outputs with provenance and
  quality flags. Preserve missing values; do not fabricate measurements.
- Retain source timestamps and offsets. Choose and document the analysis time
  zone and sleep-to-day alignment before creating daily joins. Asia/Singapore
  is the initial candidate, subject to export evidence and travel history.

## Analysis discipline

- The user runs or intends to run **three times per week**, not daily. Do not
  classify days without recorded running as missing workouts or prescribe daily
  running. Missing wellness observations are separate from workout frequency.
  No recorded activity does not prove a confirmed rest day or complete exports.
- Definitions, units, assumptions, exclusions, and provenance belong in the
  data contract before implementation. See `docs/PROJECT_PLAN.md`.
- Treat the pasted plan as a proposal. Suggested time constants, minimum data
  windows, HRV thresholds, and interval protocols are not established personal
  parameters or automatically authorized prescriptions.
- Descriptive summaries do not establish causality. Physiological proxies do
  not directly measure lactate threshold, diagnosis, or exact recovery rates.
- Use temporal validation and past-only features; disclose missing coverage,
  confounders, uncertainty, and limits of identifiability.
- Start with simple baselines. Add model complexity only when coverage and
  validation support it. Verify scientific sources when analysis begins.
- Training changes require an explicit user review of the proposed protocol.
  Flag concerning recovery patterns for review using a documented policy;
  do not hardcode an unvalidated HRV threshold as a medical rule.

## Roles and phase tracking

Use `docs/AGENT_ROLES.md` for role responsibilities. Role names are task labels,
not automatically installed Claude agents or a prompt-prefix routing system.
Do not spawn subagents unless the user explicitly requests delegation or
parallel agent work. If requested, assign bounded tasks with phase, allowed
files, required evidence, and a clear handoff; prevent concurrent file edits.

Update `PROGRESS.md` after meaningful milestones: current phase, status,
completed work, validation evidence, open decisions, and next authorized action.
Never mark a phase complete without its exit evidence. Keep instructions in
this file canonical; `CLAUDE.md` and folder entry points should reference them
instead of maintaining competing rules.
