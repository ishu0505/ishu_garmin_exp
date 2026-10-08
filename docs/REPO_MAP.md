# What lives where

Start with the root `README.md` for the project overview and `PROGRESS.md` for
the current phase. This map describes the repo after Phase 2. Discovery and
CSV summaries are implemented; models and active training plans are planned.

## Root files

| Path | Purpose |
| --- | --- |
| `README.md` | Project overview, navigation, layout, and tooling conventions |
| `AGENTS.md` | Canonical instructions, including readable code and documentation rules |
| `CLAUDE.md` | Claude entry point to the shared instructions |
| `PROGRESS.md` | Phase status, authorization, completion evidence, and open decisions |
| `.gitignore` | Exclusions for private data, credentials, environments, and generated artifacts |
| `pyproject.toml`, `uv.lock` | Python project configuration and reproducible dependencies; optional sync extra |
| `.tools/`, `.venv/`, `.uv-cache/` | Ignored local uv binary, project environment, and cache |

## Folders

| Path | What belongs here | Current contents / state |
| --- | --- | --- |
| `ishu_garmin_data/` | Original private Garmin export | Fitness, Wellness, and User folders; inspected locally, unchanged |
| `data/` | Reproducible derived data | Private discovery/verification reports, activity/recovery CSVs, pipeline report, README/instructions |
| `pipeline/` | Local discovery, parsing, feature calculations, and later authorized sync | Discovery script, `run_pipeline.py`, `export_sources.py`, `summaries.py`, settings, synthetic tests, README/instructions |
| `models/` | Baselines, model fitting, and evaluation | Folder instructions only; implementation planned |
| `experiments/` | Proposed protocols and experiment evaluations | Folder instructions only; no active experiment |
| `plans/` | User-reviewed training blocks | Folder instructions only; no active schedule |
| `docs/` | Project design, role guidance, and navigation | Project plan, role handbook, map, discovery findings, and data contract |

The data, pipeline, models, experiments, and plans folders each have an
`AGENTS.md` for local rules and a `CLAUDE.md` pointing to shared/local rules.
These are instruction files; folder READMEs explain available implementations
and how to run them. Data and pipeline READMEs are available now.

## Documentation guide

- `docs/PROJECT_PLAN.md`: roadmap, phase gates, and proposed data contract.
- `docs/AGENT_ROLES.md`: role responsibilities and handoff expectations.
- `docs/REPO_MAP.md`: directory purpose, current contents, and navigation.
- `docs/DISCOVERY.md`: observed coverage, missingness, scaling checks, and FIT limits.
- `docs/DATA_CONTRACT.md`: schema v0.2, temporal alignment, metric availability, and validation.
- `docs/PIPELINE_VALIDATION.md`: Phase 2 counts, external activity-unit verification, checks, and limitations.

## Planned workflow

Local deterministic tools will read the private export and write validated
summaries under `data/processed/`. Baseline analysis and models will consume
those summaries. Findings will inform proposed experiments and user-reviewed
training plans. Raw records stay outside LLM context and Git.

As implementations arrive, update this map and add folder READMEs with actual
entry points, inputs/outputs, execution order, and uv examples. Clearly separate
available behavior from future work.
