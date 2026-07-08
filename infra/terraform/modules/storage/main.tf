resource "google_storage_bucket" "buckets" {
  for_each = var.buckets

  name                        = each.value.name
  project                     = var.project_id
  location                    = var.location
  uniform_bucket_level_access = true
  force_destroy               = each.value.force_destroy

  lifecycle_rule {
    condition {
      age = each.value.retention_days
    }
    action {
      type = "Delete"
    }
  }
}
