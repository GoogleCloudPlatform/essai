# Copyright 2022 Google LLC
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

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "4.53.0"
    }
    shell = {
      source  = "scottwinkler/shell"
      version = "~> 1.0"
    }
  }

  backend "gcs" {
    bucket      = "{your-gcs-bucket-name}"
    prefix      = "terraform/state"
    credentials = "./svc.json"
  }
}

provider "google" {
  credentials = file(var.gcp_auth_file)
  project     = var.project_id
  region      = var.region
  zone        = var.main_zone
}

module "google_services" {
  source     = "./enable-apis"
  project_id = var.project_id
  for_each   = var.destroy_module ? toset(["value"]) : toset([])
}

module "google_cloud_iam" {
  source     = "./iam"
  project_id = var.project_id
  email      = var.email
  depends_on = [module.google_services]
}

resource "null_resource" "gcloud_registry" {
  provisioner "local-exec" {
    command = <<EOT
      gcloud auth activate-service-account ${var.service_account} --key-file=${var.path_svc_iac} --project=${var.project_id}
      cd ${var.path_backend}
      gcloud builds submit --region=${var.region} --tag southamerica-east1-docker.pkg.dev/${var.project_id}/apps/${var.shared_cloud_run}:latest 
          EOT
  }
  depends_on = [module.google_registry, module.google_cloud_iam, module.google_services]
}

resource "null_resource" "gcloud_frontend" {
  provisioner "local-exec" {
    command = <<EOT
      gcloud auth activate-service-account ${var.service_account} --key-file=${var.path_svc_iac} --project=${var.project_id}                                        
      cd ${var.path_frontend}      
      gcloud run deploy frontend --source . --region=${var.region} --project=${var.project_id} --allow-unauthenticated --memory=2Gi --port=8501
      EOT
  }
  depends_on = [module.google_registry, module.google_cloud_iam, module.google_services]
}

module "google_registry" {
  source     = "./registry"
  region     = var.region
  depends_on = [module.google_services]
}

module "google_networks" {
  source        = "./db-vpc"
  project_id    = var.project_id
  region        = var.region
  network_name  = var.network_name
  subnet_name   = var.subnet_name
  cloudsql_name = var.cloudsql_name
  depends_on    = [module.google_services]
}

module "google_storage" {
  source             = "./storage"
  cloud_storage_name = var.cloud_storage_name
  region             = var.region
  depends_on         = [module.google_services]
}

module "google_cloud_pub-sub" {
  source     = "./pub-sub"
  pubsub     = var.pubsub
  depends_on = [module.google_services]
}

module "google_cloud_user" {
  source        = "./user-database"
  name_user_sql = var.name_user_sql
  cloudsql_name = var.cloudsql_name
  depends_on    = [module.google_services, module.google_networks]
}

module "google_compute_engine" {
  source       = "./compute-engine"
  project_id   = var.project_id
  region       = var.region
  network_name = var.network_name
  subnet_name  = var.subnet_name
  machine_type = var.machine_type
  depends_on   = [module.google_services, module.google_networks, module.google_cloud_user]
}

module "google_cloud_run" {
  source           = "./cloudrun"
  project_id       = var.project_id
  region           = var.region
  network_name     = var.network_name
  cloudsql_name    = var.cloudsql_name
  email_svc        = var.email_svc
  pubsub           = var.pubsub
  shared_cloud_run = var.shared_cloud_run
  depends_on       = [module.google_services, module.google_compute_engine, module.google_networks, module.google_registry]
}

module "google_cloud_function" {
  source        = "./function"
  project_id    = var.project_id
  network_name  = var.network_name
  function_name = var.function_name
  pubsub        = var.pubsub
  email_svc     = var.email_svc
  region        = var.region
  depends_on    = [module.google_services, module.google_cloud_pub-sub, module.google_networks]
}