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
  project_id       = "test-project"
  region           = "southamerica-east1"
  network_name     = "test-vpc"
  cloudsql_name    = "test-sql"
  pubsub           = "test-topic"
  email_svc        = "backend@test-project.iam.gserviceaccount.com"
  shared_cloud_run = "essai-backend"
  invoker_members  = ["serviceAccount:caller@test-project.iam.gserviceaccount.com"]
  oidc_audience    = "https://essai-backend.internal.example"
}

run "defaults_enforce_restricted_ingress_and_explicit_invoker" {
  command = plan

  assert {
    condition     = google_cloud_run_service.default.metadata[0].annotations["run.googleapis.com/ingress"] == "internal-and-cloud-load-balancing"
    error_message = "Expected default Cloud Run ingress to be internal-and-cloud-load-balancing."
  }

  assert {
    condition     = !contains(google_cloud_run_service_iam_binding.default.members, "allUsers")
    error_message = "Cloud Run invoker binding must never include allUsers."
  }

  assert {
    condition     = contains(google_cloud_run_service_iam_binding.default.members, "serviceAccount:caller@test-project.iam.gserviceaccount.com")
    error_message = "Cloud Run invoker binding must grant access to the configured service account."
  }
}

run "rejects_public_ingress_all" {
  command = plan

  variables {
    ingress = "all"
  }

  expect_failures = [
    var.ingress,
  ]
}

run "rejects_all_users_invoker" {
  command = plan

  variables {
    invoker_members = ["allUsers"]
  }

  expect_failures = [
    var.invoker_members,
  ]
}

run "rejects_all_authenticated_users_invoker" {
  command = plan

  variables {
    invoker_members = ["allAuthenticatedUsers"]
  }

  expect_failures = [
    var.invoker_members,
  ]
}

run "rejects_empty_invoker_members" {
  command = plan

  variables {
    invoker_members = []
  }

  expect_failures = [
    var.invoker_members,
  ]
}
