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

variable "allow_bucket_deletion" {
  type        = bool
  default     = false
  description = "Whether buckets may be destroyed with contents (force_destroy). true for dev/staging, false for prod so a misconfigured apply cannot delete a populated prod bucket."
}

variable "buckets" {
  type = map(object({
    retention_days = number
  }))
  description = "Buckets keyed by logical suffix; full name is <project>-<prefix><suffix>."
  default = {
    "dag-logs"      = { retention_days = 30 }
    "dbt-artifacts" = { retention_days = 90 }
  }
}
