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
}
