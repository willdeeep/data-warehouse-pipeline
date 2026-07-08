output "provider_resource_name" {
  value       = google_iam_workload_identity_pool_provider.github.name
  description = "Full provider name — set as the GitHub Actions var WIF_PROVIDER."
}

output "pool_name" {
  value       = google_iam_workload_identity_pool.github.name
  description = "Workload identity pool resource name."
}
