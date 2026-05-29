variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "name_suffix" { type = string }
variable "db_name" { type = string }
variable "containers" {
  type = list(object({
    name          = string
    partition_key = string
  }))
}
variable "tags" { type = map(string) }
