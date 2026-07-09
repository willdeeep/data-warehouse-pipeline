# loom-datagen — synthetic source data for the Loom warehouse

A **standalone** Faker-based generator that populates the 10 `loom_sync` source tables in
BigQuery with referentially-consistent fake data matching
`pipeline/dbt/models/sources/source.yml`.

> **Run it once, after Terraform.** This is **not** part of the pipeline. It simulates the
> customer-generated state that real activity would have produced, so dbt has something to
> build on. Real ongoing data would come from application events, not Faker.

## Prerequisites

- Plan 01 applied (the `loom_sync` dataset exists).
- `gcloud auth application-default login` (ADC — no keyfiles).
- Python 3.13 + `uv`.

## Usage

```bash
cd data_generation
uv sync --extra dev

# Preview row counts without touching BigQuery
uv run loom-datagen generate --scale small --dry-run

# Generate + load into BigQuery (idempotent WRITE_TRUNCATE)
export LOOM_PROJECT_ID=<your-project>
export LOOM_SOURCE_DATASET=dev_loom_sync   # env-prefixed dataset (#29); loom_sync for prod
uv run loom-datagen generate --scale small

# Confirm integrity + accepted values on the loaded data
uv run loom-datagen validate --scale small
```

## Scale presets

`--scale {small,medium,large}` (see `config/default.yaml`). Override any field via `LOOM_*`
env vars (e.g. `LOOM_N_USERS`, `LOOM_SEED`, `LOOM_START_DATE`).

## Design

- **Deterministic** under a fixed `seed` (`LOOM_SEED`, default 42).
- **Pure generators** (`build_all` → dict of DataFrames) — no BigQuery I/O; fully unit-tested.
- **Topological build order:** catalog → users → sessions → transactions → line items →
  events / returns → ad-spend, so every foreign key resolves.
- Only `loader.py` and `validate.py` touch BigQuery (ADC).

## Tests

```bash
uv run pytest              # unit tests (referential integrity, accepted values, reproducibility)
LOOM_PROJECT_ID=<p> uv run pytest -m integration   # round-trip against real BigQuery
```
