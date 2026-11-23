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

variable "function_name" {
  type = string
}

variable "pubsub" {
  type = string
}

variable "email_svc" {
  type = string
}

variable "cloudsql_name" {
  type = string
}

variable "db_database" {
  type    = string
  default = "postgres"
}

variable "function" {
  type    = list(string)
  default = ["python310", "handler"]
}

variable "trigger" {
  type    = list(string)
  default = ["southamerica-east1", "google.cloud.pubsub.topic.v1.messagePublished", "RETRY_POLICY_RETRY"]
}

variable "vpc_connector" {
  type    = list(string)
  default = ["function-serveless", "10.8.0.0/28", "PRIVATE_RANGES_ONLY"]
}

variable "images_bucket_name" {
  type        = string
  default     = ""
  description = "Destination GCS bucket for staging allowlisted motivational images (never hardcoded)."
}

variable "drive_image_fetch_enabled" {
  type        = bool
  default     = false
  description = "Explicit opt-in for Google Drive image staging in the Cloud Function (fail-closed by default)."
}

variable "allowed_drive_file_ids" {
  type        = list(string)
  default     = []
  description = "Optional allowlist of authorized Google Drive fileIds."
}

variable "allowed_drive_ids" {
  type        = list(string)
  default     = []
  description = "Optional allowlist of authorized Google Shared Drive IDs (driveId)."
}

variable "allowed_drive_folder_ids" {
  type        = list(string)
  default     = []
  description = "Optional allowlist of authorized Google Drive parent folder IDs."
}

variable "allowed_drive_owner_emails" {
  type        = list(string)
  default     = []
  description = "Optional allowlist of authorized Google Drive owner emails."
}

variable "drive_image_max_bytes" {
  type        = number
  default     = 5242880
  description = "Maximum allowed size in bytes for fetched Drive images (default 5 MiB, max 10 MiB)."

  validation {
    condition     = var.drive_image_max_bytes >= 1 && var.drive_image_max_bytes <= 10485760
    error_message = "drive_image_max_bytes must be between 1 and 10485760 (10 MiB)."
  }
}