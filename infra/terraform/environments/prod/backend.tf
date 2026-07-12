# Remote state backend (GCS) — partial config. The state bucket itself is owned by the
# dev/bootstrap env; prod just stores its state there under prefix "prod".
# Init with:  terraform init -backend-config="bucket=<your TF_STATE_BUCKET>"
terraform {
  backend "gcs" {
    prefix = "prod"
    # bucket supplied via -backend-config="bucket=..."
  }
}
