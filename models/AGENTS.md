# Model instructions

Follow root `AGENTS.md` and `PROGRESS.md`. Modeling is Phase 4 work.
Use validated summary tables, explicit observed targets, past-only features,
temporal splits, simple baselines, and uv. Document coverage, confounders,
parameter constraints, uncertainty, and whether physiology parameters can be
identified. Compare predictions against held-out outcomes; do not infer exact
recovery rates from an unconstrained fit. Keep personal artifacts out of Git.

Apply the root coding conventions: keep feature selection, temporal splitting,
preprocessing, fitting, prediction, and evaluation explicit and easy to follow.
Explain model assumptions and parameters in plain-language comments/docstrings.
When models are introduced, add a folder README describing each model's target,
features, baseline, validation approach, outputs, and uv commands.
