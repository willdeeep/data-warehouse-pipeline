output "enabled_apis" {
  value       = [for s in google_project_service.apis : s.service]
  description = "APIs enabled on the project."
}
