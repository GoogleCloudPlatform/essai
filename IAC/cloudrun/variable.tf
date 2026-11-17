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

variable "cloudsql_name" {
  type = string
}

variable "pubsub" {
  type = string
}

variable "email_svc" {
  type = string
}

variable "shared_cloud_run" {
  type = string
}

variable "ingress" {
  type        = string
  default     = "internal-and-cloud-load-balancing"
  description = "Cloud Run ingress setting. Direct public ingress ('all') is prohibited."

  validation {
    condition     = contains(["internal", "internal-and-cloud-load-balancing"], var.ingress)
    error_message = "Cloud Run ingress must be 'internal' or 'internal-and-cloud-load-balancing' (not 'all')."
  }
}

variable "invoker_members" {
  type        = list(string)
  description = "Explicit IAM principals granted roles/run.invoker on the Backend Cloud Run service."

  validation {
    condition = (
      length(var.invoker_members) > 0 &&
      !contains(var.invoker_members, "allUsers") &&
      !contains(var.invoker_members, "allAuthenticatedUsers")
    )
    error_message = "invoker_members must contain at least one explicit principal and must not include allUsers or allAuthenticatedUsers."
  }
}

variable "oidc_audience" {
  type        = string
  default     = ""
  description = "Expected OIDC token audience (aud claim) enforced by the Backend API."
}

variable "allowed_caller_emails" {
  type        = list(string)
  default     = []
  description = "Optional allow-list of verified caller emails permitted by the Backend API."
}