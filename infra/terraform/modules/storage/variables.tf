variable "project_id" {
  type        = string
  description = "GCP project that owns the buckets."
}

variable "location" {
  type        = string
  description = "GCS location for the buckets."
}

variable "bucket_prefix" {
  type        = string
  default     = ""
  description = "Environment prefix for bucket names: 'dev-', 'stg-', or '' for prod."
}

variable "buckets" {
  type = map(object({
    retention_days = number
    force_destroy  = bool
  }))
  description = "Buckets keyed by logical suffix; full name is <project>-<prefix><suffix>."
  default = {
    "dag-logs"      = { retention_days = 30, force_destroy = true }
    "dbt-artifacts" = { retention_days = 90, force_destroy = true }
  }
}
