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

### Changed
- Rebuilt from the iOSphere training repo: renamed Prism → Loom, restructured into
  `infra/` `data_generation/` `pipeline/`, adopted `uv` + Python 3.13+ (#1, #2, #3, #4).

### Security
- Removed the committed service-account keyfile; standardised on OAuth2/ADC and
  Workload Identity Federation (no long-lived keys) (#3, #28).

[Unreleased]: https://github.com/willdeeep/data-warehouse-pipeline/commits/dev
