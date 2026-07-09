# Release & Deployment Model

The environment↔branch protection and deployment strategy for this repo (issue #28).
Code flows one way — `dev` → `staging` → `main` — following the staged-release-flow model.

## Branch ↔ environment map

| Branch | GitHub Environment | Terraform env | Branch protection | Deploy |
|--------|--------------------|---------------|-------------------|--------|
| `dev` | `dev` | `environments/dev` | **pre-commit only** (local hooks) | **manual** `terraform apply` |
| `staging` | `staging` | `environments/staging` | test + auto-deploy **authored but disabled** | **manual** `terraform apply` |
| `main` | `production` | `environments/prod` | **required** CI matrix (`ci.yml`) | **automated** `terraform apply` via WIF (`deploy-main.yml`) |

"Deploy" currently means **`terraform apply` of that environment's infrastructure**. The
pipeline-runtime deploy step is deferred to the orchestration spike (Plan 05).

## Intentional simplification — staging automation is OFF

To conserve GitHub Actions minutes, the staging **test** and **auto-deploy** workflows are
written but **disabled** (`.github/workflows/staging.yml.disabled` — the `.disabled` extension
stops GitHub from running it). **Staging deploys are performed manually.** This is a deliberate
cost trade-off, not an oversight. To enable later: rename the file to `staging.yml`, create the
`staging` GitHub Environment, and add branch protection on `staging`.

## Workflows

- **`ci.yml`** — the test matrix (ruff lint/format, `data_generation` unit tests, `terraform
  validate/fmt`). Runs on PRs to `dev`/`staging`/`main` and pushes to `main`. It is the
  **required status check** on `main`. Additional jobs (etl tests, dbt parse, DAG integrity) are
  present but gated `if: false` until Plans 03–04 land, then become required too.
- **`deploy-main.yml`** — on push to `main`: authenticate to GCP via Workload Identity
  Federation and `terraform apply` the prod environment.
- **`staging.yml.disabled`** — the disabled staging equivalent (see above).

## Authentication — Workload Identity Federation (keyless)

CI has no human ADC, so `deploy-main.yml` uses **WIF**: GitHub's OIDC token is exchanged for
short-lived GCP credentials — **no long-lived service-account key** is stored. The pool/provider
and the deploy-SA impersonation binding are created by the `github_wif` Terraform module
(bootstrapped by the human-run **dev** apply, since WIF resources are project-global).

### Required GitHub configuration (set once)

**Environment `production` variables** (Settings → Environments → production → Variables):

| Variable | Value |
|----------|-------|
| `WIF_PROVIDER` | `terraform output -raw wif_provider` (from dev env) |
| `DEPLOY_SA_EMAIL` | `terraform output -raw deploy_sa_email` (from dev env) |
| `GCP_PROJECT_ID` | your project id |
| `GCP_REGION` | e.g. `us-central1` |
| `BQ_LOCATION` | e.g. `US` |
| `TF_STATE_BUCKET` | your state bucket |
| `DAG_LOGS_BUCKET` / `DBT_ARTIFACTS_BUCKET` | your bucket names |

## Branch protection (configured via `gh`)

- `main`: require a PR + the `ci.yml` jobs (`lint`, `datagen-tests`, `terraform`) as required
  status checks; no direct pushes.
- `dev`: unprotected on the server — quality is enforced locally by `pre-commit` so feature
  branches can iterate and deploy to dev manually.
- `staging`: unprotected until its workflow is enabled.

## Multi-environment naming (decided — see #29)

To let `dev`/`staging`/`prod` coexist in **one GCP project**, resources use **purpose-based
names with an environment prefix** — `dev_`, `stg_`, and **no prefix for prod**:

| Env | Source dataset | Warehouse dataset |
|-----|----------------|-------------------|
| dev | `dev_loom_sync` | `dev_warehouse` |
| staging | `stg_loom_sync` | `stg_warehouse` |
| prod | `loom_sync` | `warehouse` |

(In a real deployment prod would be a **separate GCP project** for fully isolated,
version-labelled releases; here prod is distinguished by the absence of a prefix.)

This migration — parametrizing the Terraform modules, retargeting the datagen, and aligning
dbt — is **executed at the start of Plan 03** (issue **#29**), bundled with a clean data
reload. Until then, `dev` uses the current unprefixed `loom_sync`; the automated prod deploy
must not run against this single project until #29 lands.

## Manual deploy (dev / staging)

```bash
cd infra/terraform/environments/<env>
cp terraform.tfvars.example terraform.tfvars   # fill in
terraform init -backend-config="bucket=<TF_STATE_BUCKET>"
terraform apply
```

## Versioning & CHANGELOG (#31)

**Tag-derived — no version file to bump.** The git tag `vX.Y.Z` is the single source of truth;
`data_generation` resolves its version dynamically via `uv-dynamic-versioning` (hatchling
backend). Untagged commits build as a PEP 440 dev version (e.g. `0.1.0.post3.dev0+g1238da4`);
that hash suffix is expected. Read it at runtime from package metadata
(`loom_datagen.__version__`), never hard-coded.

Tag scheme (staged-release-flow):

| Stage | Tag |
|-------|-----|
| `dev` | `vX.Y.Z-alpha.N` |
| `staging` | `vX.Y.Z-rc.N` |
| `main` | `vX.Y.Z` |

Release = tag the commit, then push: `git tag vX.Y.Z && git push origin vX.Y.Z`. CI checkouts
use `fetch-depth: 0` + `fetch-tags: true` so builds resolve the real version.

**CHANGELOG discipline** (`CHANGELOG.md`, Keep a Changelog): every working-branch PR adds an
entry under `## [Unreleased]`. At the main-release gate, stamp `[Unreleased]` to
`## [X.Y.Z] — YYYY-MM-DD` **on `dev` first**, then promote `dev → staging → main` so all
branches carry the same stamped changelog (keeps the post-release back-merge conflict-free).

## Local quality gate

```bash
uv tool install pre-commit
pre-commit install          # runs ruff + terraform fmt/validate + hygiene on every commit
pre-commit run --all-files  # check the whole tree
```
