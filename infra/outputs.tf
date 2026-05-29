output "acr_login_server" {
  value = module.acr.login_server
}

output "cosmos_endpoint" {
  value = module.cosmos.endpoint
}

output "search_endpoint" {
  value = module.search.endpoint
}

output "app_insights_connection_string" {
  value     = module.app_insights.connection_string
  sensitive = true
}

output "frontend_fqdn" {
  value = module.container_apps.frontend_fqdn
}

output "backend_fqdn" {
  value = module.container_apps.backend_fqdn
}
