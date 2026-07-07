variable "project_id" {
  type        = string
  description = "GCP project that owns the service accounts."
}

variable "service_accounts" {
  type = map(object({
    display_name = string
  }))
  description = "Service accounts keyed by account_id. For CI/CD + deployed runtime (local dev uses human ADC)."
  default = {
    loom-dbt = {
      display_name = "Loom dbt runner (CI/deploy)"
    }
    loom-pipeline = {
      display_name = "Loom eBay ETL pipeline (CI/deploy)"
    }
  }
}

variable "role_bindings" {
  type = list(object({
    sa   = string
    role = string
  }))
  description = "Project-level role bindings; sa references a key in service_accounts."
  default = [
    { sa = "loom-dbt", role = "roles/bigquery.dataEditor" },
    { sa = "loom-dbt", role = "roles/bigquery.jobUser" },
    { sa = "loom-pipeline", role = "roles/bigquery.dataEditor" },
    { sa = "loom-pipeline", role = "roles/bigquery.jobUser" },
    { sa = "loom-pipeline", role = "roles/storage.objectAdmin" },
  ]
}
