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

variable "network_name" {
  type = string
}

variable "subnet_name" {
  type = string
}

variable "machine_type" {
  type = string
}

variable "email_svc" {
  type        = string
  description = "Service account email attached to the setup VM with least-privilege Secret Manager access."
}

variable "name_user_sql" {
  type        = string
  description = "Cloud SQL IAM database user to grant CREATE on schema public."

  validation {
    condition     = can(regex("^[a-zA-Z0-9._@-]+$", var.name_user_sql))
    error_message = "name_user_sql must contain only valid PostgreSQL IAM username characters ([a-zA-Z0-9._@-])."
  }
}

variable "cloudsql_root_password_secret_id" {
  type        = string
  description = "Secret Manager secret ID storing the Cloud SQL PostgreSQL root password."

  validation {
    condition     = can(regex("^[a-zA-Z0-9_-]+$", var.cloudsql_root_password_secret_id))
    error_message = "cloudsql_root_password_secret_id must be a valid Secret Manager secret ID ([a-zA-Z0-9_-])."
  }
}
