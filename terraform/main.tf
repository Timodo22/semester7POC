provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "poc" {
  name     = "POC-Automatisering-RG"
  location = "West Europe"
}

# Netwerk
resource "azurerm_virtual_network" "vn" {
  name                = "poc-network"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.poc.location
  resource_group_name = azurerm_resource_group.poc.name
}

resource "azurerm_subnet" "sn" {
  name                 = "internal"
  resource_group_name  = azurerm_resource_group.poc.name
  virtual_network_name = azurerm_virtual_network.vn.name
  address_prefixes     = ["10.0.2.0/24"]
}

# Publieke IP's (4 stuks)
resource "azurerm_public_ip" "ips" {
  count               = 4
  name                = "ip-${count.index}"
  location            = azurerm_resource_group.poc.location
  resource_group_name = azurerm_resource_group.poc.name
  allocation_method   = "Dynamic"
}

# Netwerk Interfaces
resource "azurerm_network_interface" "nics" {
  count               = 4
  name                = "nic-${count.index}"
  location            = azurerm_resource_group.poc.location
  resource_group_name = azurerm_resource_group.poc.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.sn.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.ips[count.index].id
  }
}

# De 4 Virtual Machines (0=DB, 1=API, 2=Front, 3=Monitor)
resource "azurerm_linux_virtual_machine" "vms" {
  count               = 4
  name                = element(["db-server", "api-server", "frontend-server", "monitor-server"], count.index)
  resource_group_name = azurerm_resource_group.poc.name
  location            = azurerm_resource_group.poc.location
  size                = "Standard_B1s"
  admin_username      = "azureuser"
  network_interface_ids = [azurerm_network_interface.nics[count.index].id]

  admin_ssh_key {
    username   = "azureuser"
    public_key = file("id_rsa_poc.pub") # Zorg dat dit bestand bestaat!
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }
}

# Dit maakt automatisch het bestand aan dat Ansible nodig heeft
resource "local_file" "ansible_inventory" {
  content = <<EOF
[database]
${azurerm_public_ip.ips[0].ip_address} ansible_user=azureuser

[api]
${azurerm_public_ip.ips[1].ip_address} ansible_user=azureuser

[frontend]
${azurerm_public_ip.ips[2].ip_address} ansible_user=azureuser

[monitor]
${azurerm_public_ip.ips[3].ip_address} ansible_user=azureuser
EOF
  filename = "../inventory.ini"
}