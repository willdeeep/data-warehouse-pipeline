# Loom Data Platform — Terraform (EAC)

Provisions the GCP data platform for the Loom warehouse: enabled APIs, BigQuery
datasets, IAM service accounts, GCS buckets, and a remote Terraform state bucket.
This is **separate from the containerised pipeline** — it stands up the infrastructure
the pipeline and the data generator run against.

## Authentication (OAuth2 / ADC — no keyfiles)

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project <your-project-id>
gcloud auth application-default set-quota-project <your-project-id>
```

Terraform uses your Application Default Credentials. No service-account keyfiles are
used or committed. (The CI/deploy service accounts this module creates are for GitHub
Actions later — see Plan 06.)

### Prerequisite: your identity needs project permissions

The account you use for ADC must be **Owner** on the project — or **Editor** plus
`roles/serviceusage.serviceUsageConsumer` (for `serviceusage.services.use`, needed to run
BigQuery jobs and set a quota project). If you created the project you're already Owner.

> ⚠️ **Common gotcha:** `gcloud auth login` and `gcloud auth application-default login` open a
> browser account picker independently — it's easy to select a *different* Google account for
> ADC than the one that owns the project. If you hit
> `does not have the "serviceusage.services.use" permission`, you almost certainly authenticated
> ADC as the wrong account. Re-run `gcloud auth application-default login` and pick the owner
> account (confirm with `gcloud auth list` and `gcloud config get-value account`).

The `loom-dbt` / `loom-pipeline` service accounts get `serviceUsageConsumer` too, so they can
run BigQuery jobs when used by CI/deploy.

## Layout

```
infra/terraform/
├── modules/
│   ├── project/        # Google Cloud API enablement
│   ├── bigquery/       # datasets: loom_sync, dev_warehouse, warehouse
│   ├── iam/            # service accounts + role bindings (CI/deploy)
│   ├── storage/        # GCS buckets: dag logs, dbt artifacts
│   ├── state/          # remote-state bucket (bootstrap)
│   └── orchestration/  # STUB — resolved in Plan 05
└── environments/{dev,staging,prod}/   # one Terraform root each
```

Each environment is its own root module (its own `versions.tf` + backend).

### Global vs per-env (single-project layout)

To let `dev`/`staging`/`prod` coexist in one project, resources split in two:

- **Project-global** (state bucket, API enablement, service accounts, WIF) — created **once**
  by the **`dev`/bootstrap** env. `staging`/`prod` reuse them and do **not** re-create them.
- **Per-env** (BigQuery datasets + GCS buckets) — each env owns its own, name-prefixed:
  `dev_`/`stg_` (datasets) and `dev-`/`stg-` (buckets); **prod is unprefixed**.

### Configuration — `.env` → `TF_VAR_*` (no tfvars)

Terraform variables come from the repo-root `.env` via `TF_VAR_*` (no hand-edited
`terraform.tfvars`). Fill `.env`, then export it before any Terraform command:

```bash
cp .env.example .env && $EDITOR .env      # GCP_PROJECT_ID, TF_STATE_BUCKET, etc.
set -a && source .env && set +a           # exposes TF_VAR_project_id, TF_VAR_state_bucket_name, ...
```

## First run — bootstrap (dev)

The `dev` env creates the shared state bucket, so its first apply uses **local** state, then
migrates to GCS:

```bash
cd environments/dev
set -a && source ../../../../.env && set +a
# backend.tf is uncommented (partial config); bootstrap with local state first:
terraform init -backend=false && terraform apply     # state bucket, APIs, SAs, WIF, dev datasets/buckets
terraform init -migrate-state -backend-config="bucket=$TF_STATE_BUCKET"   # move state to GCS
```

## Deploying staging / prod (thin envs)

The state bucket + SAs already exist (dev), so these just create their own datasets/buckets:

```bash
cd environments/staging   # or prod
set -a && source ../../../../.env && set +a
terraform init -backend-config="bucket=$TF_STATE_BUCKET"
terraform apply
```

## Everyday use

```bash
set -a && source .env && set +a
terraform -chdir=infra/terraform/environments/dev plan
terraform -chdir=infra/terraform/environments/dev apply
```

## What gets created

| Scope | Module | Resources |
|-------|--------|-----------|
| global (dev only) | project | Enables BigQuery, Storage, IAM, Service Usage, CRM APIs |
| global (dev only) | iam | `loom-dbt`, `loom-pipeline` SAs + role bindings |
| global (dev only) | github_wif | Workload Identity pool/provider for keyless CI deploys |
| global (dev only) | state | Versioned, `prevent_destroy` remote-state bucket |
| per-env | bigquery | `<prefix>loom_sync`, `<prefix>warehouse` datasets |
| per-env | storage | `<project>-<prefix>dag-logs` (30d), `-dbt-artifacts` (90d) buckets |
| per-env | orchestration | **Nothing yet** — un-stubbed in Plan 05 |

## Orchestration is deferred

The `orchestration` module is a no-op stub. The choice of Astronomer vs Cloud Composer
vs Cloud Run is made in Plan 05 (orchestration decision spike), which un-stubs this
module for the chosen runtime. Everything else provisions runtime-agnostically.
