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