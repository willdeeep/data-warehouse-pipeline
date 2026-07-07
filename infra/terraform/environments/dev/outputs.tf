output "state_bucket" {
  value       = module.state.bucket
  description = "Terraform remote-state bucket."
}

output "dataset_ids" {
  value       = module.bigquery.dataset_ids
  description = "BigQuery datasets created for the warehouse."
}
