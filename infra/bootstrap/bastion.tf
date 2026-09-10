resource "azurerm_subnet" "bastion" {
  count                = var.enable_bastion ? 1 : 0
  name                 = "AzureBastionSubnet"
  resource_group_name  = azurerm_resource_group.ops.name
  virtual_network_name = azurerm_virtual_network.ops.name
  address_prefixes     = [var.bastion_subnet_prefix]
}

resource "azurerm_public_ip" "bastion" {
  count               = var.enable_bastion ? 1 : 0
  name                = "pip-bastion-${local.suffix}"
  location            = var.region
  resource_group_name = azurerm_resource_group.ops.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = merge(local.tags, { "fdai:component" = "operator-access" })
}

resource "azurerm_bastion_host" "runner" {
  count                  = var.enable_bastion ? 1 : 0
  name                   = "bas-runner-${local.suffix}"
  location               = var.region
  resource_group_name    = azurerm_resource_group.ops.name
  sku                    = "Standard"
  scale_units            = 2
  tunneling_enabled      = true
  file_copy_enabled      = true
  copy_paste_enabled     = false
  ip_connect_enabled     = false
  shareable_link_enabled = false
  tags                   = merge(local.tags, { "fdai:component" = "operator-access" })

  ip_configuration {
    name                 = "runner-access"
    subnet_id            = azurerm_subnet.bastion[0].id
    public_ip_address_id = azurerm_public_ip.bastion[0].id
  }
}
