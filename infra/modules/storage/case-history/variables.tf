variable "name" {
  description = "Globally unique StorageV2 account name for case-history artifacts."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.name))
    error_message = "name MUST contain 3-24 lowercase alphanumeric characters."
  }
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "deployer_principal_id" {
  description = "Object id of the VNet-integrated Terraform runner identity."
  type        = string
}

variable "legacy_deployer_principal_id" {
  description = "Optional prior deployer object id retained during an additive role handoff."
  type        = string
  default     = ""
}

variable "runtime_principal_id" {
  description = "Object id of the FDAI runtime managed identity."
  type        = string
}

variable "runtime_role_definition_name" {
  description = "Blob data-plane role granted to the runtime principal."
  type        = string
  default     = "Storage Blob Data Contributor"

  validation {
    condition = contains(
      ["Storage Blob Data Reader", "Storage Blob Data Contributor"],
      var.runtime_role_definition_name,
    )
    error_message = "runtime_role_definition_name MUST be Reader or Contributor."
  }
}

variable "immutability_period_days" {
  description = "Optional time-based WORM period for the container."
  type        = number
  default     = 0

  validation {
    condition = (
      var.immutability_period_days == 0 ||
      (var.immutability_period_days >= 1 && var.immutability_period_days <= 365)
    )
    error_message = "immutability_period_days MUST be 0 or in [1, 365]."
  }
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace receiving case-history Blob access diagnostics."
  type        = string
}

variable "replication_type" {
  type    = string
  default = "ZRS"

  validation {
    condition     = contains(["LRS", "ZRS", "GRS", "GZRS", "RAGRS", "RAGZRS"], var.replication_type)
    error_message = "replication_type MUST be a supported standard Storage replication type."
  }
}

variable "public_network_access_enabled" {
  type    = bool
  default = false
}

variable "private_link_access" {
  description = "Private-link resource and tenant pairs allowed through storage network rules."
  type = map(object({
    endpoint_resource_id = string
    endpoint_tenant_id   = string
  }))
  default = {}
}

variable "container_name" {
  type    = string
  default = "case-history"

  validation {
    condition     = can(regex("^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])$", var.container_name))
    error_message = "container_name MUST be a valid lowercase Blob container name."
  }
}

variable "soft_delete_retention_days" {
  type    = number
  default = 30

  validation {
    condition     = var.soft_delete_retention_days >= 7 && var.soft_delete_retention_days <= 365
    error_message = "soft_delete_retention_days MUST be in [7, 365]."
  }
}

variable "version_retention_days" {
  type    = number
  default = 90

  validation {
    condition = (
      var.version_retention_days >= var.soft_delete_retention_days &&
      var.version_retention_days >= var.immutability_period_days
    )
    error_message = "version_retention_days MUST cover soft delete and immutability."
  }
}

variable "tags" {
  type    = map(string)
  default = {}
}
