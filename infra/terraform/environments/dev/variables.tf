variable "project_id" {
  type        = string
  description = "GCP project id (owned by the person running this). Also the BigQuery/source project."
}

variable "region" {
  type        = string
  description = "Default GCP region for regional resources."
  default     = "us-central1"
}

variable "bq_location" {
  type        = string
  description = "BigQuery + GCS multi-region location (US, EU) or region."
  default     = "US"
}

variable "state_bucket_name" {
  type        = string
  description = "Globally-unique GCS bucket name for Terraform remote state."
}

variable "github_repository" {
  type        = string
  default     = "willdeeep/data-warehouse-pipeline"
  description = "owner/repo allowed to federate via Workload Identity (issue #28)."
}
