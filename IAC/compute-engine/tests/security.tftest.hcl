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

variables {
  project_id                       = "test-project"
  region                           = "southamerica-east1"
  network_name                     = "test-vpc"
  subnet_name                      = "test-subnet"
  machine_type                     = "e2-micro"
  email_svc                        = "essai-setup@test-project.iam.gserviceaccount.com"
  name_user_sql                    = "essai-setup@test-project.iam"
  cloudsql_root_password_secret_id = "test-postgres-root-password"
}

run "fetches_db_password_from_secret_manager_and_uses_safe_psql_quoting" {
  command = plan

  assert {
    condition     = google_secret_manager_secret_iam_member.psql_vm_secret_accessor.role == "roles/secretmanager.secretAccessor"
    error_message = "Setup VM service account must be granted least-privilege roles/secretmanager.secretAccessor."
  }

  assert {
    condition     = google_secret_manager_secret_iam_member.psql_vm_secret_accessor.secret_id == "test-postgres-root-password"
    error_message = "Secret accessor IAM binding must be scoped to the configured Cloud SQL root password secret."
  }

  assert {
    condition     = google_compute_instance.psql-instance.service_account[0].email == "essai-setup@test-project.iam.gserviceaccount.com"
    error_message = "Setup VM must attach the configured service account."
  }

  assert {
    condition     = can(regex("gcloud secrets versions access latest --secret=\"test-postgres-root-password\"", google_compute_instance.psql-instance.metadata_startup_script))
    error_message = "Startup script must fetch Cloud SQL password at runtime from Secret Manager."
  }

  assert {
    condition     = !can(regex("export PGPASSWORD=", google_compute_instance.psql-instance.metadata_startup_script))
    error_message = "Startup script must never embed a literal export PGPASSWORD assignment."
  }

  assert {
    condition     = can(regex("-v db_user=\"essai-setup@test-project\\.iam\"", google_compute_instance.psql-instance.metadata_startup_script))
    error_message = "Startup script must pass SQL username via psql -v variable binding."
  }
}

run "rejects_injectable_sql_user_name" {
  command = plan

  variables {
    name_user_sql = "user\"; DROP SCHEMA public; --"
  }

  expect_failures = [
    var.name_user_sql,
  ]
}

run "rejects_unreplaced_placeholder_sql_user_name" {
  command = plan

  variables {
    name_user_sql = "{your-compute-service-account-name}@developer"
  }

  expect_failures = [
    var.name_user_sql,
  ]
}

run "rejects_injectable_secret_id" {
  command = plan

  variables {
    cloudsql_root_password_secret_id = "bad;id"
  }

  expect_failures = [
    var.cloudsql_root_password_secret_id,
  ]
}
