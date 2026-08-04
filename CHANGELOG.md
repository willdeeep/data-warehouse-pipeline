# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is
[SemVer](https://semver.org/) via git tags (`vX.Y.Z`), resolved dynamically by
`uv-dynamic-versioning`. Entries accrue under **Unreleased** and are stamped at each release.

## [Unreleased]

### Added
- `AGENTS.md` — top-level agent onboarding guide for the repository.
- `invoke` task runner (`tasks.py`): `invoke build`/`seed`/`run`/`test`/`refresh`/`build-container`
  wrap the common dbt/container commands and auto-load `.env`.
- Local-first dbt paths: `.env`/`.env.example` now set `DBT_PROFILES_DIR`/`DBT_PROJECT_DIR` to
  `pipeline/dbt`; the Airflow container overrides them to `/opt/airflow/dbt` in
  `pipeline/docker-compose.yaml`. dbt runs locally with no `--profiles-dir`/`--project-dir` flags.

### Changed
- Renamed the eBay auth env var `CLIENT_SECRET` → `CLIENT_TOKEN` in `.env.example`.
- Renamed the dbt `intermediate/` layer to `core/` to reflect its role as the normalized,
  conformed star-schema core; standardized model names to strict dbt-Labs convention
  (facts `fact_`→`fct_`, marts to the `rpt_` prefix), and updated the `generate_schema_name`
  routing macro accordingly (#42).

## [0.1.0] — 2026-07-12

### Added

- Terraform data platform: BigQuery datasets, project APIs, IAM, GCS buckets, and a GCS
  remote-state backend, authenticated via OAuth2/ADC (#5, #6, #7).
- Standalone Faker synthetic data generator (`loom-datagen`) producing all 10 `loom_sync`
  source tables with referential integrity, a BigQuery loader, a validate gate, and a CLI
  (#8, #9, #10).
- CI/CD environment↔branch model: `pre-commit` dev gate, GitHub Actions CI matrix, a
  WIF-gated production deploy workflow, and a disabled staging workflow (#28).
- Workload Identity Federation Terraform module for keyless GitHub Actions → GCP deploys (#28).
- Tag-derived dynamic versioning (`uv-dynamic-versioning`) and this changelog (#31).
- dbt warehouse builds green end-to-end on live BigQuery (staging → intermediate → marts,
  `PASS=182 WARN=2 ERROR=0`); OAuth/ADC profiles, eBay landing seed, and a build-validation
  summary (#11, #12, #13).
- Top-level README with a verified "run it yourself" quickstart + architecture diagram (#23).

### Changed

- Rebuilt from the iOSphere training repo: renamed Prism → Loom, restructured into
  `infra/` `data_generation/` `pipeline/`, adopted `uv` + Python 3.13+ (#1, #2, #3, #4).
- Env-prefixed BigQuery datasets so dev/staging/prod coexist in one project — `dev_`/`stg_`,
  prod bare (#29).
- dbt runtime pinned to Python 3.12 (dbt lags newer Pythons); datagen emits numeric-castable
  ids to match the warehouse's INTEGER natural keys (#12).

### Fixed

- Staging/prod `terraform apply` no longer collides on project-global resources: `dev` is the
  bootstrap environment owning the state bucket, APIs, SAs, and WIF; staging/prod are thin
  (datasets + buckets only). Config flows from `.env` → `TF_VAR_*` — no hand-edited tfvars (#40).

### Security

- Removed the committed service-account keyfile; standardised on OAuth2/ADC and
  Workload Identity Federation (no long-lived keys) (#3, #28).
- Least-privilege service accounts get `serviceusage.serviceUsageConsumer` to run BigQuery
  jobs; enabled the Service Usage API; documented the human ADC prerequisite (#35).

[Unreleased]: https://github.com/willdeeep/data-warehouse-pipeline/compare/v0.1.0...dev
[0.1.0]: https://github.com/willdeeep/data-warehouse-pipeline/releases/tag/v0.1.0
