# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "cloudsql_name" {
  type = string
}

variable "network_name" {
  type = string
}

variable "subnet_name" {
  type = string
}

variable "prefix_subnetwork" {
  type    = list(string)
  default = ["10.0.130.0/24"]
}

variable "prefix_network" {
  type    = list(string)
  default = ["GLOBAL"]
}

variable "peering" {
  type    = list(string)
  default = ["private-ip-block", "VPC_PEERING", "INTERNAL", "IPV4"]
}

variable "database" {
  type    = list(string)
  default = ["db-custom-2-7680", "REGIONAL", "from_cloud_sql", "US"]
}

variable "egress_internet" {
  default = ["egress-internet", "0.0.0.0/0", "default-internet-gateway"]
  type    = list(string)
}

variable "nat_router" {
  default = ["AUTO_ONLY", "LIST_OF_SUBNETWORKS", "ALL_IP_RANGES", "ERRORS_ONLY"]
  type    = list(string)
}

variable "cloudsql_root_password" {
  type        = string
  default     = null
  sensitive   = true
  description = "Optional custom root password for Cloud SQL PostgreSQL. When null (recommended), a random 24-character password is generated automatically and stored in Secret Manager."

  validation {
    condition = (
      var.cloudsql_root_password == null ? true : (
        length(trimspace(var.cloudsql_root_password)) >= 16 &&
        sha256(var.cloudsql_root_password) != "7d818ddded5b16b4fe60e1f519f8c1a3d47982287785b783a8b10364c6f4e103" &&
        !can(regex("^(password|postgres|admin|changeme|your-)", lower(trimspace(var.cloudsql_root_password))))
      )
    )
    error_message = "cloudsql_root_password must be null (auto-generated) or a strong secret of at least 16 characters that does not reuse leaked or placeholder passwords."
  }
}