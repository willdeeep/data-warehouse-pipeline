provider "google" {
  project = var.project_id
  region  = var.region
}

# Authentication is Application Default Credentials (ADC):
#   gcloud auth application-default login
#
# `staging` is a THIN env: it only manages its env-prefixed datasets + buckets.
# Project-global resources (state bucket, APIs, service accounts, WIF) are owned by the
# `dev`/bootstrap env and reused here — so this root creates nothing that would collide.

module "bigquery" {
  source                 = "../../modules/bigquery"
  project_id             = var.project_id
  location               = var.bq_location
  dataset_prefix         = "stg_"
  allow_dataset_deletion = true
}

module "storage" {
  source                = "../../modules/storage"
  project_id            = var.project_id
  location              = var.bq_location
  bucket_prefix         = "stg-"
  allow_bucket_deletion = true # staging is disposable (UAT)
}

# Orchestration runtime is deferred to Plan 05; the stub creates nothing.
module "orchestration" {
  source     = "../../modules/orchestration"
  project_id = var.project_id
  enabled    = false
}
