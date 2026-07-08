# Workload Identity Federation for GitHub Actions -> GCP (keyless CI deploys, issue #28).
# Lets the deploy service account be impersonated by GitHub Actions runs from THIS repo,
# with no long-lived key. Bootstrapped by a human `terraform apply` (dev env); CI then
# uses it to `terraform apply` prod.

data "google_project" "this" {
  project_id = var.project_id
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = var.pool_id
  display_name              = "GitHub Actions"
  description               = "OIDC federation for GitHub Actions deploys"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = var.provider_id
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  # Only tokens from this exact repository are accepted.
  attribute_condition = "assertion.repository == '${var.github_repository}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Allow GitHub Actions runs from this repo to impersonate the deploy SA.
resource "google_service_account_iam_member" "wif_impersonation" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${var.deploy_sa_email}"
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

# Project roles the deploy SA needs to `terraform apply` the platform.
resource "google_project_iam_member" "deploy_roles" {
  for_each = toset(var.deploy_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${var.deploy_sa_email}"
}
