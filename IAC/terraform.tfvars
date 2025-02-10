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

# GCP  Basic Settings

project_id      = "your-gcp-project-id"
gcp_auth_file   = "./svc.json"
service_account = "{your-manually-created-service-account-name}@{your-gcp-project-id}.iam.gserviceaccount.com"
region          = "your-gcp-region"
main_zone       = "your-gcp-main-zone-in-the-selected-region"

# Network
network_name = "your-network-name"
subnet_name  = "your-subnet-name"

# Cloud Storage 
cloud_storage_name = "your-storage-name"

# Pub Sub
pubsub = "your-pubsub-name"

# Compute Engine
machine_type = "t2d-standard-1"

# Cloud Run
shared_cloud_run = "your-cloud-run-base-name"

# Cloud Function
function_name = "your-function-name"

# Cloud SQL
cloudsql_name = "your-postgres-name"
name_user_sql = "{your-compute-service-account-name}@developer"

# Service Account
email_svc = "{your-compute-service-account-name}@developer.gserviceaccount.com"
email     = "serviceAccount:{your-compute-service-account-name}@developer.gserviceaccount.com"

# Path
path_backend  = "{your-absolute-path-to-backend-directory}/Backend"
path_svc_iac  = "{your-absolute-path-to-svc-file}/svc.json"
path_frontend = "{your-absolute-path-to-frontend-directory}/Frontend"