output "dataset_ids" {
  value       = module.bigquery.dataset_ids
  description = "BigQuery datasets created for the warehouse (stg_-prefixed)."
}

output "bucket_names" {
  value       = module.storage.bucket_names
  description = "GCS buckets for DAG logs and dbt artifacts (stg--prefixed)."
}
