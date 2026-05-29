variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "name_suffix" { type = string }
variable "acr_login_server" { type = string }
variable "acr_admin_username" { type = string }

variable "acr_admin_password" {
  type      = string
  sensitive = true
}

variable "image_tag" { type = string }
variable "backend_env_vars" { type = map(string) }

variable "backend_secrets" {
  type      = map(string)
  sensitive = true
}

variable "log_analytics_workspace_id" { type = string }
variable "tags" { type = map(string) }
