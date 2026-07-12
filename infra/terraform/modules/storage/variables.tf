variable "project_id" {
  type        = string
  description = "GCP project that owns the buckets."
}

variable "location" {
  type        = string
  description = "GCS location for the buckets."
}

variable "buckets" {
  type = map(object({
    name           = string
    retention_days = number
    force_destroy  = bool
  }))
  description = "GCS buckets keyed by logical name; each maps to a globally-unique bucket name."
}
