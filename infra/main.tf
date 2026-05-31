terraform {
  required_version = ">= 1.7.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.110"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "sttfstateclientagent"
    container_name       = "tfstate"
    key                  = "client-agent.tfstate"
  }
}

provider "azurerm" {
  features {}
}

locals {
  tags = {
    project     = "client-agent"
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "azurerm_resource_group" "main" {
  name     = "rg-client-agent-${var.environment}"
  location = var.location
  tags     = local.tags
}

module "acr" {
  source              = "./modules/acr"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  name_suffix         = var.name_suffix
  tags                = local.tags
}

module "cosmos" {
  source              = "./modules/cosmos"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  name_suffix         = var.name_suffix
  db_name             = "clientagent"
  # Master DB only — per-client databases are created dynamically by the app
  containers = [
    { name = "clients", partition_key = "/id" }
  ]
  tags = local.tags
}

module "search" {
  source              = "./modules/search"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  name_suffix         = var.name_suffix
  sku                 = "standard"
  tags                = local.tags
}

module "app_insights" {
  source              = "./modules/app_insights"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  name_suffix         = var.name_suffix
  tags                = local.tags
}

module "container_apps" {
  source              = "./modules/container_apps"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  name_suffix         = var.name_suffix
  acr_login_server    = module.acr.login_server
  acr_admin_username  = module.acr.admin_username
  acr_admin_password  = module.acr.admin_password
  image_tag           = var.image_tag

  backend_env_vars = {
    AZURE_OPENAI_ENDPOINT             = var.azure_openai_endpoint
    AZURE_OPENAI_DEPLOYMENT           = var.azure_openai_deployment
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT = var.azure_openai_embedding_deployment
    AZURE_OPENAI_API_VERSION          = "2024-08-01-preview"
    AZURE_SEARCH_ENDPOINT             = module.search.endpoint
    AZURE_SEARCH_INDEX_NAME           = "client-knowledge"
    COSMOS_ENDPOINT                   = module.cosmos.endpoint
    COSMOS_DB_NAME                    = "clientagent"
    ENTRA_TENANT_ID                   = var.entra_tenant_id
    ENTRA_CLIENT_ID                   = var.entra_client_id
    LOCAL_MODE                        = "false"
    ONEDRIVE_SYNC_PATH                = "/mnt/onedrive"
    LOG_LEVEL                         = "INFO"
  }

  backend_secrets = {
    AZURE_OPENAI_API_KEY                  = var.azure_openai_api_key
    AZURE_SEARCH_API_KEY                  = module.search.api_key
    COSMOS_KEY                            = module.cosmos.primary_key
    APPLICATIONINSIGHTS_CONNECTION_STRING = module.app_insights.connection_string
  }

  log_analytics_workspace_id = module.app_insights.log_analytics_workspace_id
  tags                       = local.tags
}
