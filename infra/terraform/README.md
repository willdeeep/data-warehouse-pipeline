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

Each environment is its own root module (its own `versions.tf` + backend). Datasets
`raw`/`dev_warehouse`/`warehouse` names match `pipeline/dbt/models/sources/source.yml`.

## First run — bootstrap the remote state bucket

The state bucket is created by Terraform, so the first apply uses **local** state,
then migrates:

```bash
cd environments/dev
cp terraform.tfvars.example terraform.tfvars   # fill in project_id + unique bucket names

# 1. Backend is commented out in backend.tf — apply with local state:
terraform init
terraform apply                                 # creates state bucket, datasets, IAM, GCS

# 2. Uncomment the backend block in backend.tf, set bucket = <your TF_STATE_BUCKET>:
terraform init -migrate-state                    # moves local state into GCS
```

Repeat per environment (`staging`, `prod`), each with its own `terraform.tfvars` and
backend `prefix`.

## Everyday use

```bash
cd environments/dev
terraform fmt -recursive ../..
terraform validate
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

## What gets created

| Module | Resources |
|--------|-----------|
| project | Enables BigQuery, Storage, IAM, Cloud Resource Manager APIs |
| bigquery | `loom_sync`, `dev_warehouse`, `warehouse` datasets |
| iam | `loom-dbt`, `loom-pipeline` SAs + BigQuery/Storage role bindings |
| storage | `dag_logs` (30d), `dbt_artifacts` (90d) buckets |
| state | Versioned, `prevent_destroy` remote-state bucket |
| orchestration | **Nothing yet** — un-stubbed in Plan 05 |

## Orchestration is deferred

The `orchestration` module is a no-op stub. The choice of Astronomer vs Cloud Composer
vs Cloud Run is made in Plan 05 (orchestration decision spike), which un-stubs this
module for the chosen runtime. Everything else provisions runtime-agnostically.
