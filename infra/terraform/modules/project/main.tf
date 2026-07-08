resource "google_project_service" "apis" {
  for_each = toset(var.enabled_apis)

  project                    = var.project_id
  service                    = each.value
  disable_dependent_services = false
  disable_on_destroy         = false
}
