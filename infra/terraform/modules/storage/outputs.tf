output "bucket_names" {
  value       = { for k, b in google_storage_bucket.buckets : k => b.name }
  description = "Created bucket names keyed by logical name."
}
