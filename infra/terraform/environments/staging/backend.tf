# Remote state backend (GCS).
#
# BOOTSTRAP SEQUENCE (first run only):
#   1. Leave this backend block COMMENTED.
#   2. `terraform init && terraform apply` — the `state` module creates the bucket
#      locally (state stored on disk).
#   3. Uncomment this block, set `bucket` to your TF_STATE_BUCKET value.
#   4. `terraform init -migrate-state` to move local state into the bucket.
#
# terraform {
#   backend "gcs" {
#     bucket = "REPLACE_WITH_TF_STATE_BUCKET"
#     prefix = "staging"
#   }
# }
