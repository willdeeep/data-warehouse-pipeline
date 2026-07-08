resource "google_service_account" "accounts" {
  for_each = var.service_accounts

  account_id   = each.key
  display_name = each.value.display_name
  project      = var.project_id
}

resource "google_project_iam_member" "bindings" {
  for_each = { for b in var.role_bindings : "${b.sa}:${b.role}" => b }

  project = var.project_id
  role    = each.value.role
  member  = "serviceAccount:${google_service_account.accounts[each.value.sa].email}"
}
