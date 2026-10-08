# Garmin Training Lab

Personal endurance training analysis for goals of **sub-20 5K, sub-45 10K,
and sub-1:35 half marathon**. Build reliable summaries from Garmin exports,
evaluate interpretable models, then use evidence to design training experiments.

**Current state: Phase 2 pipeline complete; Phase 3 has not started.**
See [PROGRESS.md](PROGRESS.md) for phase status and entry/exit criteria.

## Start here

- [AGENTS.md](AGENTS.md): shared instructions for agents and contributors.
- [CLAUDE.md](CLAUDE.md): Claude entry point into the same instructions.
- [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md): scope, phased roadmap, and metric decisions.
- [docs/AGENT_ROLES.md](docs/AGENT_ROLES.md): engineering, analysis, and experiment roles.
- [docs/REPO_MAP.md](docs/REPO_MAP.md): what lives where and how the folders connect.
- [docs/DISCOVERY.md](docs/DISCOVERY.md): export coverage, quality, and limitations.
- [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md): Phase 2 table definitions and validation rules.
- [docs/PIPELINE_VALIDATION.md](docs/PIPELINE_VALIDATION.md): current table counts, checks, and limitations.

## Layout

```text
ishu_garmin_data/   Existing private export; leave untouched and out of Git
data/processed/    Reproducible CSV summaries and quality report; private
pipeline/          Discovery, deterministic summaries, settings, and tests
models/            Future baselines, model fitting, and validation
experiments/       Hypotheses, protocols, and evidence
plans/             User-reviewed training blocks
docs/              Shared project design and role guidance
PROGRESS.md        Phase status, gates, decisions, and completion evidence
```

Python, dependencies, environments, scripts, and checks must use **uv**:
`uv sync`, `uv add <package>`, and `uv run <command>` once a Python project is
approved and configured. Do not use pip, Poetry, Conda, direct Python execution,
or a separate virtualenv workflow. File editing and Git operations are separate
from Python tooling.

## Run discovery and summaries

uv is installed locally at `.tools/uv`. If it is on your PATH, use `uv` in place
of `.tools/uv --cache-dir .uv-cache`.

```bash
.tools/uv --cache-dir .uv-cache sync --extra sync
.tools/uv --cache-dir .uv-cache run --offline python pipeline/discover_export.py
.tools/uv --cache-dir .uv-cache run --offline python pipeline/run_pipeline.py --verification data/reports/verification.json
.tools/uv --cache-dir .uv-cache run --offline python -m unittest discover -s pipeline -p 'test_*.py'
```

The report is written to ignored `data/reports/discovery.json`. See
[pipeline/README.md](pipeline/README.md) for inputs, outputs, and limitations.
`fitdecode` supports local FIT inspection; `garminconnect` is installed as the
optional `sync` extra for future downloads. Installation does not configure login
or sync. No models, training prescriptions, or account requests have been made.
Original export files remain unchanged.

The user runs or intends to run **three times a week**, not every day. The daily
recovery calendar tracks wellness without treating non-running days as missing
workouts. Missing wellness data and absence of recorded activity are separate.

## Coding conventions

Use simple Python and ML code with descriptive names, small functions,
plain-language comments, and helpful docstrings. Explain units, assumptions,
and unfamiliar concepts. Keep this README, the repo map, and relevant folder
documentation current whenever code or structure changes. Full conventions
live in [AGENTS.md](AGENTS.md#coding-and-documentation-conventions).
