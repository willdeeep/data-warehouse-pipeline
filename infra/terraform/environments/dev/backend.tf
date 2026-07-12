# Remote state backend (GCS) — partial configuration.
#
# BOOTSTRAP SEQUENCE (first run only):
#   1. First apply runs with this block COMMENTED (state stored locally); the
#      `state` module creates the bucket.
#   2. Uncomment the block below, then migrate, passing YOUR bucket at init time:
#        terraform init -migrate-state \
#          -backend-config="bucket=<your TF_STATE_BUCKET>"
#      The bucket is intentionally NOT hardcoded so the repo stays portable.
#
terraform {
  backend "gcs" {
    prefix = "dev"
    # bucket supplied via -backend-config="bucket=..."
  }
}
