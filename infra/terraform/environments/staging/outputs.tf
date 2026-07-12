output "state_bucket" {
  value       = module.state.bucket
  description = "Terraform remote-state bucket."
}

output "dataset_ids" {
  value       = module.bigquery.dataset_ids
  description = "BigQuery datasets created for the warehouse."
}

output "bucket_names" {
  value       = module.storage.bucket_names
  description = "GCS buckets for DAG logs and dbt artifacts."
}

output "service_account_emails" {
  value       = module.iam.service_account_emails
  description = "Service accounts for CI/deploy."
}
