variable "project_id" {
  type        = string
  description = "GCP project that owns the Terraform remote-state bucket."
}

variable "state_bucket_name" {
  type        = string
  description = "Globally-unique name for the GCS bucket holding Terraform state."
}

variable "location" {
  type        = string
  description = "GCS location for the state bucket (e.g. US, EU, us-central1)."
}
