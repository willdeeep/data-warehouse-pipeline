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
