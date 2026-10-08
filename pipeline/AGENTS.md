# Pipeline instructions

Follow root `AGENTS.md`, `PROGRESS.md`, and the agreed data contract.
Discovery begins in Phase 1; parser implementation begins in Phase 2, each
only after user authorization. Use uv for all Python work. Prefer deterministic,
idempotent processing with explicit units, timestamp rules, duplicates,
missingness, provenance, and quality flags. Validate compressed file handling
and meaningful edge cases before trusting derived metrics. Keep raw content
and secrets out of logs. Add no account sync before Phase 7 authorization.

Apply the root coding conventions: use small, readable parsing and calculation
functions, explain units and exclusion rules in docstrings/comments, and keep
the transformations easy to follow. When scripts are introduced, add a folder
README with their purpose, input/output paths, execution order, and uv commands.
