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
mock_provider "null" {}

variables {
  project_id    = "test-project"
  region        = "southamerica-east1"
  cloudsql_name = "test-postgres"
  network_name  = "test-vpc"
  subnet_name   = "test-subnet"
}

run "defaults_generate_random_password_and_store_in_secret_manager" {
  command = plan

  assert {
    condition     = length(random_password.cloudsql_root_password) == 1
    error_message = "Expected random_password to be created when cloudsql_root_password is null."
  }

  assert {
    condition     = random_password.cloudsql_root_password[0].length >= 24
    error_message = "Generated Cloud SQL root password must be at least 24 characters long."
  }

  assert {
    condition     = google_secret_manager_secret.cloudsql_root_password.secret_id == "test-postgres-root-password"
    error_message = "Cloud SQL root password must be stored in a dedicated Secret Manager secret."
  }
}

run "rejects_short_custom_root_password" {
  command = plan

  variables {
    cloudsql_root_password = "too-short-123"
  }

  expect_failures = [
    var.cloudsql_root_password,
  ]
}

run "rejects_placeholder_custom_root_password" {
  command = plan

  variables {
    cloudsql_root_password = "password-placeholder-12345"
  }

  expect_failures = [
    var.cloudsql_root_password,
  ]
}

run "accepts_strong_custom_root_password_without_random_resource" {
  command = plan

  variables {
    cloudsql_root_password = "Tr0ng!Custom-Secret-Value-9988"
  }

  assert {
    condition     = length(random_password.cloudsql_root_password) == 0
    error_message = "random_password should not be created when a strong custom password is supplied."
  }
}
