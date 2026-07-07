variable "project_id" {
  type        = string
  description = "GCP project that owns the datasets."
}

variable "location" {
  type        = string
  description = "BigQuery location (US, EU, or a region). Must match the source project."
}

variable "datasets" {
  type = map(object({
    description                = string
    delete_contents_on_destroy = bool
  }))
  description = "BigQuery datasets keyed by dataset_id. Ids must match dbt source.yml schemas."
  default = {
    loom_sync = {
      description                = "Raw source tables (Faker-seeded); dbt source schema."
      delete_contents_on_destroy = true
    }
    dev_warehouse = {
      description                = "dbt dev target + eBay landing (ebay_transformed)."
      delete_contents_on_destroy = true
    }
    warehouse = {
      description                = "dbt prod target."
      delete_contents_on_destroy = false
    }
  }
}
