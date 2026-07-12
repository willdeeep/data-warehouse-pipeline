# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is
[SemVer](https://semver.org/) via git tags (`vX.Y.Z`), resolved dynamically by
`uv-dynamic-versioning`. Entries accrue under **Unreleased** and are stamped at each release.

## [Unreleased]

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

### Security
- Removed the committed service-account keyfile; standardised on OAuth2/ADC and
  Workload Identity Federation (no long-lived keys) (#3, #28).
- Least-privilege service accounts get `serviceusage.serviceUsageConsumer` to run BigQuery
  jobs; enabled the Service Usage API; documented the human ADC prerequisite (#35).

[Unreleased]: https://github.com/willdeeep/data-warehouse-pipeline/commits/dev
