# AGENTS.md

Loom — synthetic e-commerce data warehouse (portfolio rebuild of an iOSphere training repo).
Terraform provisions GCP, `loom-datagen` seeds BigQuery once, dbt builds staging → intermediate → marts.
Roadmap + locked design decisions: `.opencode/plans/00-roadmap.md`. Release model: `docs/RELEASE.md`.

## Active vs legacy code

- **Active (rebuilt):** `infra/terraform/`, `data_generation/`, `pipeline/dbt/`, `docs/`, `.github/workflows/`.
- **Legacy (pre-rebuild, awaiting Plans 04–06):** `pipeline/dags/`, `pipeline/etl/`, `scripts/`, root `tests/`, `pytest.ini`, `airflow_settings.yaml`. Don't extend or "fix" these unless the task is explicitly the Airflow/eBay rework.
- `pipeline/dbt/dbt_packages/` and `pipeline/dbt/target/` are generated (dbt deps/build) — never edit.

## Commands

```bash
uv sync                                        # root tooling (Python 3.13)
uvx ruff@0.14.2 check data_generation          # lint — version pinned to match CI + pre-commit
uvx ruff@0.14.2 format --check data_generation
cd data_generation && uv sync --extra dev && uv run pytest   # generator unit tests
terraform fmt -check -recursive infra/terraform
```

- `data_generation/` is a **standalone uv project with its own `uv.lock`** — not a root workspace member (workspace block in root `pyproject.toml` is intentionally commented out). Run its tests from inside that directory.
- Datagen integration tests are excluded by default (`addopts = -m 'not integration'`); they need ADC + `LOOM_PROJECT_ID`: `uv run pytest -m integration`.
- CI (`.github/workflows/ci.yml`) = required check on `main`: ruff (pinned), datagen tests, terraform validate/fmt, dbt parse. Some jobs are `if: false` placeholders — leave them gated until their subsystem lands.

## dbt quirks (all bite if ignored)

- dbt runs on **Python 3.12**, not the repo's 3.13: `uv tool install dbt-core --with dbt-bigquery --python 3.12`.
- Always run from repo root with **both** `--project-dir pipeline/dbt --profiles-dir pipeline/dbt`. The `.env` sets `DBT_PROFILES_DIR` to a container path (`/opt/airflow/dbt`), so `--profiles-dir` must override it locally.
- **Seed before build, and exclude the seed from build**: `dbt seed ...` then `dbt build ... --exclude transformed_competitor_data`. The eBay landing table is both a seed and a declared source; without this order source tests race the table creation.
- A green build ends `ERROR=0` with **2 intentional WARNs** (messy eBay competitor data) — don't "fix" those warnings.

## Environment & auth

- Load env with `set -a && source .env && set +a` — this also feeds Terraform via `TF_VAR_*`. There are no tfvars files (removed in #40); `.env` is the single source of config truth.
- Auth is **OAuth2/ADC for humans, WIF for CI. Never introduce service-account keyfiles** (pre-commit `detect-private-key` guards this).
- Datasets are env-prefixed in one GCP project: `dev_loom_sync`/`dev_warehouse`, `stg_*`, prod bare.
- Terraform: **`environments/dev` is the bootstrap env owning project-global resources** (state bucket, APIs, SAs, WIF); staging/prod are thin (datasets + buckets only). Don't add global resources to staging/prod.

## Versioning & release

- Version is **tag-derived** (`uv-dynamic-versioning`); there is no version field to bump — read via `loom_datagen.__version__`. CI needs `fetch-depth: 0` + `fetch-tags: true` to resolve it.
- Flow is `dev → staging → main` (staged-release-flow; tags `-alpha.N` / `-rc.N` / release). Every working-branch PR adds a `CHANGELOG.md` entry under `## [Unreleased]`.
- `.github/workflows/staging.yml.disabled` is **intentionally disabled** (Actions-minutes trade-off) — don't re-enable or delete it as cleanup.
- Install the local gate once: `uv tool install pre-commit && pre-commit install` (ruff + terraform fmt/validate; `dev` branch is unprotected server-side, so this is the only gate there).
