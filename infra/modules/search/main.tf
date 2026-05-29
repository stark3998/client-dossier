resource "azurerm_search_service" "main" {
  name                = "search-client-agent-${var.name_suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku
  replica_count       = 1
  partition_count     = 1
  tags                = var.tags
}
