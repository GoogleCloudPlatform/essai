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

mock_provider "google" {}
mock_provider "random" {}
mock_provider "archive" {}

variables {
  project_id    = "test-project"
  region        = "southamerica-east1"
  network_name  = "test-vpc"
  function_name = "test-fn"
  pubsub        = "test-topic"
  email_svc     = "worker@test-project.iam.gserviceaccount.com"
  cloudsql_name = "test-sql"
}

run "injects_runtime_gcp_and_db_env_vars_with_dynaconf_prefix" {
  command = plan

  assert {
    condition     = google_cloudfunctions2_function.default.service_config[0].environment_variables["DYNACONF_GCP_PROJECT_ID"] == "test-project"
    error_message = "Cloud Function must inject DYNACONF_GCP_PROJECT_ID from var.project_id."
  }

  assert {
    condition     = google_cloudfunctions2_function.default.service_config[0].environment_variables["DYNACONF_GCP_LOCATION"] == "southamerica-east1"
    error_message = "Cloud Function must inject DYNACONF_GCP_LOCATION from var.region."
  }

  assert {
    condition     = google_cloudfunctions2_function.default.service_config[0].environment_variables["DYNACONF_DB_USER"] == "worker@test-project.iam.gserviceaccount.com"
    error_message = "Cloud Function must inject DYNACONF_DB_USER from var.email_svc."
  }

  assert {
    condition     = google_cloudfunctions2_function.default.service_config[0].environment_variables["DYNACONF_INSTANCE_CONNECTION_NAME"] == "test-project:southamerica-east1:test-sql"
    error_message = "Cloud Function must inject DYNACONF_INSTANCE_CONNECTION_NAME from project, region, and cloudsql_name."
  }

  assert {
    condition     = google_cloudfunctions2_function.default.service_config[0].environment_variables["DRIVE_IMAGE_FETCH_ENABLED"] == "false"
    error_message = "Drive image fetching must default to disabled (fail-closed)."
  }

  assert {
    condition     = google_cloudfunctions2_function.default.service_config[0].environment_variables["DYNACONF_DRIVE_IMAGE_FETCH_ENABLED"] == "false"
    error_message = "DYNACONF_DRIVE_IMAGE_FETCH_ENABLED must default to disabled (fail-closed)."
  }

  assert {
    condition     = google_cloudfunctions2_function.default.service_config[0].environment_variables["DRIVE_IMAGE_MAX_BYTES"] == "5242880"
    error_message = "Drive image max size must default to 5 MiB (5242880 bytes)."
  }
}

run "rejects_enabling_drive_fetch_without_allowlist" {
  command = plan

  variables {
    drive_image_fetch_enabled = true
    images_bucket_name        = "test-images-bucket"
  }

  expect_failures = [
    google_cloudfunctions2_function.default,
  ]
}

run "rejects_enabling_drive_fetch_without_bucket_name" {
  command = plan

  variables {
    drive_image_fetch_enabled = true
    allowed_drive_file_ids    = ["1AllowedFileId_00001"]
  }

  expect_failures = [
    google_cloudfunctions2_function.default,
  ]
}

run "rejects_excessive_drive_image_max_bytes" {
  command = plan

  variables {
    drive_image_max_bytes = 52428800
  }

  expect_failures = [
    var.drive_image_max_bytes,
  ]
}

run "allows_drive_fetch_with_explicit_bucket_and_allowlist" {
  command = plan

  variables {
    drive_image_fetch_enabled = true
    images_bucket_name        = "test-images-bucket"
    allowed_drive_ids         = ["0ADriveSharedId_12345"]
    allowed_drive_folder_ids  = ["1AllowedFolder_99999"]
    drive_image_max_bytes     = 2097152
  }

  assert {
    condition     = google_cloudfunctions2_function.default.service_config[0].environment_variables["DRIVE_IMAGE_FETCH_ENABLED"] == "true"
    error_message = "Explicitly allowlisted Drive fetch should set DRIVE_IMAGE_FETCH_ENABLED=true."
  }

  assert {
    condition     = google_cloudfunctions2_function.default.service_config[0].environment_variables["IMAGES_BUCKET_NAME"] == "test-images-bucket"
    error_message = "IMAGES_BUCKET_NAME must propagate from var.images_bucket_name."
  }

  assert {
    condition     = google_cloudfunctions2_function.default.service_config[0].environment_variables["ALLOWED_DRIVE_IDS"] == "0ADriveSharedId_12345"
    error_message = "ALLOWED_DRIVE_IDS must propagate from var.allowed_drive_ids."
  }

  assert {
    condition     = google_cloudfunctions2_function.default.service_config[0].environment_variables["DRIVE_IMAGE_MAX_BYTES"] == "2097152"
    error_message = "DRIVE_IMAGE_MAX_BYTES must propagate from var.drive_image_max_bytes."
  }
}
