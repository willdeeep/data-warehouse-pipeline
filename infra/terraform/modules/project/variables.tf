variable "project_id" {
  type        = string
  description = "GCP project on which to enable APIs."
}

variable "enabled_apis" {
  type        = list(string)
  description = "Google Cloud APIs to enable for the data platform."
  default = [
    "bigquery.googleapis.com",
    "storage.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ]
}
