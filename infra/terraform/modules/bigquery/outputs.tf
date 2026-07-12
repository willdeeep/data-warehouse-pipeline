output "dataset_ids" {
  value       = [for d in google_bigquery_dataset.datasets : d.dataset_id]
  description = "Created BigQuery dataset ids."
}
