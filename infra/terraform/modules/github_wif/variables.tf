variable "project_id" {
  type        = string
  description = "GCP project hosting the workload identity pool + deploy SA."
}

variable "github_repository" {
  type        = string
  description = "owner/repo allowed to federate (e.g. willdeeep/data-warehouse-pipeline)."
}

variable "deploy_sa_email" {
  type        = string
  description = "Service account GitHub Actions impersonates to run terraform apply."
}

variable "pool_id" {
  type        = string
  default     = "github-actions"
  description = "Workload identity pool id."
}

variable "provider_id" {
  type        = string
  default     = "github"
  description = "Workload identity pool provider id."
}

variable "deploy_roles" {
  type        = list(string)
  description = "Project roles granted to the deploy SA so it can apply the platform."
  default = [
    "roles/serviceusage.serviceUsageAdmin",
    "roles/bigquery.admin",
    "roles/storage.admin",
    "roles/iam.serviceAccountAdmin",
    "roles/resourcemanager.projectIamAdmin",
    "roles/iam.workloadIdentityPoolAdmin",
  ]
}
