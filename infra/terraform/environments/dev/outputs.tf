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

output "wif_provider" {
  value       = module.github_wif.provider_resource_name
  description = "Set as GitHub Actions var WIF_PROVIDER for keyless deploys."
}

output "deploy_sa_email" {
  value       = module.iam.service_account_emails["loom-pipeline"]
  description = "Set as GitHub Actions var DEPLOY_SA_EMAIL."
}
