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
  source_dir  = "${path.module}/../temp/function-source"
  output_path = "${path.module}/../temp/function-source.zip"
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
      LOG_EXECUTION_ID                    = "true"
      GCP_PROJECT_ID                      = var.project_id
      GCP_LOCATION                        = var.region
      DB_USER                             = var.email_svc
      DB_DATABASE                         = var.db_database
      INSTANCE_CONNECTION_NAME            = "${var.project_id}:${var.region}:${var.cloudsql_name}"
      DRIVE_IMAGE_FETCH_ENABLED           = tostring(var.drive_image_fetch_enabled)
      IMAGES_BUCKET_NAME                  = var.images_bucket_name
      ALLOWED_DRIVE_FILE_IDS              = join(",", var.allowed_drive_file_ids)
      ALLOWED_DRIVE_IDS                   = join(",", var.allowed_drive_ids)
      ALLOWED_DRIVE_FOLDER_IDS            = join(",", var.allowed_drive_folder_ids)
      ALLOWED_DRIVE_OWNER_EMAILS          = join(",", var.allowed_drive_owner_emails)
      DRIVE_IMAGE_MAX_BYTES               = tostring(var.drive_image_max_bytes)
      DYNACONF_GCP_PROJECT_ID             = var.project_id
      DYNACONF_GCP_LOCATION               = var.region
      DYNACONF_DB_USER                    = var.email_svc
      DYNACONF_DB_DATABASE                = var.db_database
      DYNACONF_INSTANCE_CONNECTION_NAME   = "${var.project_id}:${var.region}:${var.cloudsql_name}"
      DYNACONF_DRIVE_IMAGE_FETCH_ENABLED  = tostring(var.drive_image_fetch_enabled)
      DYNACONF_IMAGES_BUCKET_NAME         = var.images_bucket_name
      DYNACONF_ALLOWED_DRIVE_FILE_IDS     = join(",", var.allowed_drive_file_ids)
      DYNACONF_ALLOWED_DRIVE_IDS          = join(",", var.allowed_drive_ids)
      DYNACONF_ALLOWED_DRIVE_FOLDER_IDS   = join(",", var.allowed_drive_folder_ids)
      DYNACONF_ALLOWED_DRIVE_OWNER_EMAILS = join(",", var.allowed_drive_owner_emails)
      DYNACONF_DRIVE_IMAGE_MAX_BYTES      = tostring(var.drive_image_max_bytes)
    }
  }

  event_trigger {
    trigger_region = var.trigger[0]
    event_type     = var.trigger[1]
    retry_policy   = var.trigger[2]
    pubsub_topic   = "projects/${var.project_id}/topics/${var.pubsub}"

  }

  lifecycle {
    precondition {
      condition = (
        !var.drive_image_fetch_enabled || (
          length(var.allowed_drive_file_ids) > 0 ||
          length(var.allowed_drive_ids) > 0 ||
          length(var.allowed_drive_folder_ids) > 0 ||
          length(var.allowed_drive_owner_emails) > 0
        )
      )
      error_message = "Enabling drive_image_fetch_enabled requires at least one Drive trust boundary allowlist (allowed_drive_file_ids, allowed_drive_ids, allowed_drive_folder_ids, or allowed_drive_owner_emails)."
    }

    precondition {
      condition     = !var.drive_image_fetch_enabled || trimspace(var.images_bucket_name) != ""
      error_message = "Enabling drive_image_fetch_enabled requires a non-empty images_bucket_name."
    }
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