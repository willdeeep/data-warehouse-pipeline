output "state_bucket" {
  value       = module.state.bucket
  description = "Terraform remote-state bucket."
}
