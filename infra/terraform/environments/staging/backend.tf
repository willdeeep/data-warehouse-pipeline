# Remote state backend (GCS) — partial config. The state bucket itself is owned by the
# dev/bootstrap env; staging just stores its state there under prefix "staging".
# Init with:  terraform init -backend-config="bucket=<your TF_STATE_BUCKET>"
terraform {
  backend "gcs" {
    prefix = "staging"
    # bucket supplied via -backend-config="bucket=..."
  }
}
