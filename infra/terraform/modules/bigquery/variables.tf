variable "project_id" {
  type        = string
  description = "GCP project that owns the datasets."
}

variable "location" {
  type        = string
  description = "BigQuery location (US, EU, or a region). Must match the source project."
}

variable "dataset_prefix" {
  type        = string
  default     = ""
  description = "Environment prefix for dataset ids: 'dev_', 'stg_', or '' for prod."
}

variable "allow_dataset_deletion" {
  type        = bool
  default     = false
  description = "Whether datasets may be dropped with contents (true for dev/staging, false for prod)."
}

variable "datasets" {
  type        = map(string)
  description = "Purpose-based dataset names -> description. Prefixed per environment."
  default = {
    loom_sync = "Raw source tables (Faker-seeded); dbt source schema."
    warehouse = "dbt target (staging/intermediate/marts) + eBay landing (ebay_transformed)."
  }
}
