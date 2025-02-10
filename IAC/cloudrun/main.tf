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
  name          = "cloudrun-vpc-connector"
  region        = var.region
  project       = var.project_id
  ip_cidr_range = "10.9.0.0/28"
  network       = var.network_name
}

resource "google_cloud_run_service" "default" {
  name     = var.shared_cloud_run
  location = var.region
  project  = var.project_id

  metadata {
    annotations = {
      "run.googleapis.com/ingress" : "all"
    }
  }
  template {
    metadata {
      annotations = {
        "run.googleapis.com/vpc-access-connector" : google_vpc_access_connector.connector.name
      }
    }
    spec {
      containers {
        image = "southamerica-east1-docker.pkg.dev/${var.project_id}/apps/${var.shared_cloud_run}:latest"
        env {
          name  = "POSTGRES_DB"
          value = "postgres"
        }
        env {
          name  = "IAM_USER"
          value = var.email_svc
        }
        env {
          name  = "INSTANCE_CONNECTION_NAME"
          value = "${var.project_id}:${var.region}:${var.cloudsql_name}"
        }
        env {
          name  = "MAX_IDS_BULK_READ"
          value = "100"
        }
        env {
          name  = "PUBSUB_TOPIC_NAME"
          value = "projects/${var.project_id}/topics/${var.pubsub}"
        }
      }
    }
  }
}

resource "google_cloud_run_service_iam_binding" "default" {
  depends_on = [google_cloud_run_service.default]
  location   = google_cloud_run_service.default.location
  service    = google_cloud_run_service.default.name
  role       = "roles/run.invoker"
  members = [
    "allUsers"
  ]
}

