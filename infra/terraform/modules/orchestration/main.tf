# STUB — resolved by Plan 05 (orchestration decision spike).
# Deliberately creates nothing so the platform provisions runtime-agnostically.
# Future: Composer env / Cloud Run job / Astronomer resources gated on var.enabled.

variable "enabled" {
  type        = bool
  default     = false
  description = "Toggled true by Plan 05 once the runtime is chosen."
}

variable "project_id" {
  type        = string
  description = "GCP project for the (future) orchestration runtime."
}
