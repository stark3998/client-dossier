variable "environment" {
  type    = string
  default = "dev"
}

variable "location" {
  type    = string
  default = "australiaeast"
}

variable "name_suffix" {
  type = string
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "azure_openai_endpoint" {
  type = string
}

variable "azure_openai_api_key" {
  type      = string
  sensitive = true
}

variable "azure_openai_deployment" {
  type    = string
  default = "gpt-4o"
}

variable "azure_openai_embedding_deployment" {
  type    = string
  default = "text-embedding-3-large"
}

variable "entra_tenant_id" {
  type = string
}

variable "entra_client_id" {
  type = string
}

