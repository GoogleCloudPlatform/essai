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

variable "main_zone" {
  type = string
}

variable "service_account" {
  type = string
}

variable "gcp_auth_file" {
  type = string
}

variable "network_name" {
  type = string
}

variable "subnet_name" {
  type = string
}

variable "cloud_storage_name" {
  type = string
}

variable "cloudsql_name" {
  type = string
}

variable "pubsub" {
  type = string
}

variable "email_svc" {
  type = string
}

variable "machine_type" {
  type = string
}

variable "shared_cloud_run" {
  type = string
}

variable "function_name" {
  type = string
}

variable "name_user_sql" {
  type = string
}

variable "email" {
  type = string
}

variable "path_backend" {
  type = string
}

variable "path_frontend" {
  type = string
}

variable "path_svc_iac" {
  type = string
}

variable "destroy_module" {
  type    = bool
  default = true
}

variable "cloudrun_ingress" {
  type        = string
  default     = "internal-and-cloud-load-balancing"
  description = "Cloud Run ingress setting for the Backend API ('internal' or 'internal-and-cloud-load-balancing')."

  validation {
    condition     = contains(["internal", "internal-and-cloud-load-balancing"], var.cloudrun_ingress)
    error_message = "cloudrun_ingress must be 'internal' or 'internal-and-cloud-load-balancing' (not 'all')."
  }
}

variable "cloudrun_invoker_members" {
  type        = list(string)
  default     = []
  description = "Explicit IAM principals allowed to invoke the Backend Cloud Run service. Defaults to [var.email] when empty."

  validation {
    condition = (
      !contains(var.cloudrun_invoker_members, "allUsers") &&
      !contains(var.cloudrun_invoker_members, "allAuthenticatedUsers")
    )
    error_message = "cloudrun_invoker_members must not include allUsers or allAuthenticatedUsers."
  }
}

variable "cloudrun_oidc_audience" {
  type        = string
  default     = ""
  description = "Expected OIDC token audience (aud claim) validated by the Backend API."
}

variable "cloudrun_allowed_caller_emails" {
  type        = list(string)
  default     = []
  description = "Optional allow-list of verified caller emails permitted by the Backend API."
}

variable "cloudsql_root_password" {
  type        = string
  default     = null
  sensitive   = true
  description = "Optional custom root password for Cloud SQL PostgreSQL (prefer leaving null to auto-generate and store in Secret Manager; never commit to terraform.tfvars)."

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