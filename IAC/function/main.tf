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

resource "google_vpc_access_connector" "connector" {
  name          = var.vpc_connector[0]
  ip_cidr_range = var.vpc_connector[1]
  network       = var.network_name
  min_instances = 2
  max_instances = 3
}

resource "random_id" "bucket_prefix" {
  byte_length = 8
}

resource "google_storage_bucket" "default" {
  name                        = "${random_id.bucket_prefix.hex}-redacao-gemini"
  location                    = "US"
  uniform_bucket_level_access = true
}

data "archive_file" "default" {
  type        = "zip"
  source_dir  = "./temp/function-source"
  output_path = "./temp/function-source.zip"
}

resource "google_storage_bucket_object" "default" {
  name   = "function-source.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.default.output_path
}

resource "google_cloudfunctions2_function" "default" {
  name     = var.function_name
  location = var.region

  build_config {
    runtime     = var.function[0]
    entry_point = var.function[1]
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.default.name
      }
    }
  }

  service_config {
    max_instance_count             = 3
    min_instance_count             = 1
    available_memory               = "1G"
    timeout_seconds                = 60
    ingress_settings               = "ALLOW_INTERNAL_ONLY"
    all_traffic_on_latest_revision = true
    service_account_email          = var.email_svc
    vpc_connector                  = google_vpc_access_connector.connector.name
    vpc_connector_egress_settings  = var.vpc_connector[2]
    environment_variables = {
      LOG_EXECUTION_ID = "true"
      GCP_PROJECT_ID   = "${var.project_id}"
      GCP_LOCATION     = "${var.region}"

    }
  }

  event_trigger {
    trigger_region = var.trigger[0]
    event_type     = var.trigger[1]
    retry_policy   = var.trigger[2]
    pubsub_topic   = "projects/${var.project_id}/topics/${var.pubsub}"

  }
}

resource "google_cloud_run_service_iam_binding" "default" {
  depends_on = [google_cloudfunctions2_function.default]
  location   = google_cloudfunctions2_function.default.location
  service    = google_cloudfunctions2_function.default.name
  role       = "roles/run.invoker"
  members = [
    "allUsers"
  ]
}