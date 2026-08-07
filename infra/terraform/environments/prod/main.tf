provider "google" {
  project = var.project_id
  region  = var.region
}

# Authentication is Application Default Credentials (ADC):
#   gcloud auth application-default login
#
# `prod` is a THIN env: it only manages its (unprefixed) datasets + buckets. Project-global
# resources (state bucket, APIs, service accounts, WIF) are owned by the `dev`/bootstrap env
# and reused here. In a real deployment prod would be a separate project bootstrapping its own.

module "bigquery" {
  source                 = "../../modules/bigquery"
  project_id             = var.project_id
  location               = var.bq_location
  dataset_prefix         = "" # prod datasets are unprefixed
  allow_dataset_deletion = false
}

module "storage" {
  source                = "../../modules/storage"
  project_id            = var.project_id
  location              = var.bq_location
  bucket_prefix         = ""    # prod buckets are unprefixed
  allow_bucket_deletion = false # prod: a populated bucket cannot be force-destroyed
}

# Orchestration runtime is deferred to Plan 05; the stub creates nothing.
module "orchestration" {
  source     = "../../modules/orchestration"
  project_id = var.project_id
  enabled    = false
}
