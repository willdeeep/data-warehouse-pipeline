output "bucket" {
  value       = google_storage_bucket.tf_state.name
  description = "Name of the Terraform remote-state bucket."
}
