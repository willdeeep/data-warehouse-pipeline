resource "google_bigquery_dataset" "datasets" {
  for_each = var.datasets

  dataset_id                 = each.key
  project                    = var.project_id
  location                   = var.location
  description                = each.value.description
  delete_contents_on_destroy = each.value.delete_contents_on_destroy
}
