# Repository instructions

These instructions apply to all work in this repository.

## Git workflow

At the successful completion of every meaningful project task or stage, manage version control automatically:

1. Inspect `git status`.
2. Run the relevant tests or scientific validation.
3. Verify generated outputs, update the README/documentation when appropriate, and update `logs/pipeline_log.md` when the scientific pipeline changes.
4. Stage the appropriate tracked/generated project files without bypassing `.gitignore`.
5. Group related changes into one meaningful commit with a concise descriptive message; do not commit every tiny edit.
6. Push normally to `origin main`.
7. Report what was completed, validation performed, commit message, commit hash, push status, and files deliberately kept local.

Examples of appropriate task-level commit messages:

- `Add 84k HEA ingestion pipeline`
- `Validate SRO definition for HEA dataset`
- `Add FCC and BCC exploratory analysis`
- `Add feature engineering pipeline`
- `Add phase-specific ML models`
- `Update thesis figures and model comparison`

## Git safety and exclusions

- Respect `.gitignore` at all times.
- Never use `git add -f` to bypass ignore rules.
- Never commit `data/raw/`, large downloaded datasets, `.venv/`, Python caches, temporary files, secrets/tokens/passwords/API keys, very large intermediate files, or unnecessary trained-model binaries.
- If a newly generated file is unusually large, keep it local and mention it in the task summary.
- Do not rewrite history, force-push, use `reset --hard`, or delete remote branches unless the user explicitly requests it.
- Do not create a misleading successful commit when a task or scientific validation fails. Fix the issue first, or clearly label an incomplete commit only when retaining the work is useful.
- Scientific correctness takes priority over committing quickly.

## Research outputs to track when reasonably sized

- Source code and tests
- `README.md`, `SOURCES.md`, `sources.yaml`, and `data_dictionary.md`
- `reports/` and curated pipeline logs
- Important figures, `thesis_outputs/`, figure captions, and analysis summaries
- Small result CSV files

The configured repository is `https://github.com/abhinavDev-iit/SRO_ML_UGP.git`; the normal destination is `origin/main`.
