resource "google_storage_bucket" "buckets" {
  for_each = var.buckets

  name                        = "${var.project_id}-${var.bucket_prefix}${each.key}"
  project                     = var.project_id
  location                    = var.location
  uniform_bucket_level_access = true
  force_destroy               = var.allow_bucket_deletion

  lifecycle_rule {
    condition {
      age = each.value.retention_days
    }
    action {
      type = "Delete"
    }
  }
}
