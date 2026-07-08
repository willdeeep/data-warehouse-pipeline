provider "google" {
  project = var.project_id
  region  = var.region
}

# Authentication is Application Default Credentials (ADC):
#   gcloud auth application-default login
# No service-account keyfiles are used or committed.

module "state" {
  source            = "../../modules/state"
  project_id        = var.project_id
  state_bucket_name = var.state_bucket_name
  location          = var.bq_location
}

module "project" {
  source     = "../../modules/project"
  project_id = var.project_id
}

module "bigquery" {
  source     = "../../modules/bigquery"
  project_id = var.project_id
  location   = var.bq_location
  depends_on = [module.project]
}

module "iam" {
  source     = "../../modules/iam"
  project_id = var.project_id
  depends_on = [module.project]
}

# Orchestration runtime is deferred to Plan 05; the stub creates nothing.
module "orchestration" {
  source     = "../../modules/orchestration"
  project_id = var.project_id
  enabled    = false
}

module "storage" {
  source     = "../../modules/storage"
  project_id = var.project_id
  location   = var.bq_location
  buckets = {
    dag_logs = {
      name           = var.dag_logs_bucket
      retention_days = 30
      force_destroy  = true
    }
    dbt_artifacts = {
      name           = var.dbt_artifacts_bucket
      retention_days = 90
      force_destroy  = true
    }
  }
  depends_on = [module.project]
}
