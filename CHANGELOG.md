# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is
[SemVer](https://semver.org/) via git tags (`vX.Y.Z`), resolved dynamically by
`uv-dynamic-versioning`. Entries accrue under **Unreleased** and are stamped at each release.

## [Unreleased]

### Documentation
- Refreshed the `docs/architecture/` docs to the current warehouse state ahead of the v0.2.0
  promotion: rewrote `erd.md` to the snowflaked ~3NF core (geo `country←region←geo`, product
  `brand`/`main_category←sub_category`, keys-only `dim_products`), integer/conformed keys (#36),
  per-unit `item_id` transaction grain (#56), and the real `rpt_` marts; rebuilt
  `business-metrics.md` so every query runs against the shipped marts/facts and reframed the
  production-scale figures as an explicitly illustrative business case (the warehouse is a
  ~500-user Faker seed). Fixed `dbt-build-summary.md` (intro now lists Plans 10/13/15 + #55/#56,
  resolved the 54-vs-880 transaction-row contradiction, staging count 10→11) and `RELEASE.md`
  (the #29 dataset-prefix migration and Plan 03 have landed — corrected the future-tense notes).
- Added GitHub-rendering architecture diagrams (#24): a Mermaid `erDiagram` of the core
  star + snowflake in `erd.md`, and a new `docs/architecture/overview.md` with a Mermaid system /
  data-flow diagram, the dbt layer lineage, and the canonical warehouse layer catalog (34 models).
- Refreshed `README.md`: the `invoke` task runner is now the recommended build path in the
  quickstart (`uv run invoke refresh`) with raw dbt kept as the explicit equivalent; added a
  `tasks.py` row and pointer to `overview.md`; corrected the eBay ETL / orchestration roadmap to
  v0.4.0 / v0.5.0.

### Added
- Real SCD Type 2 history for `dim_users`: the synthetic generator now emits versioned user
  profile history (a `valid_from` per version; ~35% of users change over time, oldest version
  anchored to `registration_date`), and `dim_users` derives `valid_from`/`valid_to`/`is_current`
  via a `LEAD()` window. `rpt_customer_activity`'s `profile_change` branch now populates and its
  guard test runs at `severity: error` again. No mart SQL changed — the transaction branch was
  already point-in-time-correct (Plan 13).
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
- Documented `rpt_customer_activity` intent (SCD-chronology mart) and added a singular guard
  test asserting both activity types are present. It runs at `severity: warn` for now because
  `dim_users` has no SCD2 history yet (the source `users` table is a single snapshot); it flips
  to `severity: error` once the dim-users-scd2 build-out lands (#43).

### Removed
- Deleted the redundant `marketing_metrics_mart` — a strict subset of
  `rpt_daily_channel_performance` that read `staging` directly and was undocumented (#43).

### Changed
- Standardized on integer surrogate keys: `*_key` / `user_/product_surrogate_key` / `platform_key` /
  `ad_key` are now deterministic `FARM_FINGERPRINT` **INT64** via a new `generate_int_surrogate_key`
  macro (was 32-char MD5 hex) — cheaper BigQuery storage/joins, conformed hashing (no lookup joins)
  preserved. Natural keys stay integer (fragile `stg_users` `LENGTH=7` guard removed in favour of an
  integer cast + `not_null` test); `session_id`/`user_cookie_id` stay string (#36).
- Snowflaked the geo hierarchy into `dim_country` ← `dim_region` ← `dim_geo` (city leaf) via an
  ephemeral `int_geo_locations` helper and conformed surrogate-hash FKs; `dim_geo` now carries
  `region_key` instead of inline region/country text. `fct_sessions` is unchanged (city join).
  Relationship tests enforce the hierarchy (`dim_geo.region_key` scoped `where region_key is not
  null` for the thin Faker geo) (#44).
- Snowflaked the product hierarchy into `dim_brand`, `dim_main_category` ← `dim_sub_category`;
  `dim_products` is now keys-only (`brand_key`, `sub_category_key`) with `rpt_transactions` and
  `rpt_customer_activity` re-joining the sub-dims for display names (verified 0 NULLs).
  Relationship tests enforce the hierarchy (#45).
- Transaction line-item grain is now **one row per unit sold**, keyed by a globally-unique `item_id`
  (the SKU moved to `product_id`). Two units of the same product in one transaction are now
  distinguishable, so returns reference a specific `item_id`. `fct_transactions` also joins
  `dim_users` **point-in-time** — this removes the SCD2 user-version fan-out that had made
  `(transaction_id, product_id)` non-unique. The `item_id` uniqueness test on
  `fct_transactions`/`rpt_transactions` now runs at `severity: error` (build back to WARN=2) (#56).

### Fixed (datagen)
- Session and transaction dates are now bounded to on/after each user's `registration_date`:
  registration is sampled within `[start_date − 365d, end_date]` and logged-in session dates are
  resampled into `[max(registration_date, window_start), window_end]`. Previously most users
  registered *after* the data window, so ~93% of transactions physically predated signup and were
  excluded from `rpt_customer_activity` by the SCD2 point-in-time join; the lifecycle mart now
  retains all transactions (#55).

### Fixed
- `rpt_daily_channel_performance`: replaced the hardcoded `2024-05..06` date filter with an
  optional var-gated window, and dropped the `device` grain that double-counted ad spend.
  Mart total `ad_spend` now equals `SUM(fct_advertising.cost)` exactly, at one row per
  date×channel×platform (#43).

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
