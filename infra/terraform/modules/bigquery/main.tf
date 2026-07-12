resource "google_bigquery_dataset" "datasets" {
  for_each = var.datasets

  dataset_id                 = "${var.dataset_prefix}${each.key}"
  project                    = var.project_id
  location                   = var.location
  description                = each.value
  delete_contents_on_destroy = var.allow_dataset_deletion
}
