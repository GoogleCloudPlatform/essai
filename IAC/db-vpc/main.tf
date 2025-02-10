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

locals {
  network_name = var.network_name
  subnet_name  = var.subnet_name
}

resource "null_resource" "wait_for_network" {
  provisioner "local-exec" {
    command = "sleep 40"
  }
}

resource "google_compute_network" "vpc_redacao" {
  name                            = local.network_name
  auto_create_subnetworks         = false
  routing_mode                    = var.prefix_network[0]
  delete_default_routes_on_create = true
  depends_on                      = [null_resource.wait_for_network]
}

resource "google_compute_subnetwork" "subnet_redacao" {
  name                     = local.subnet_name
  ip_cidr_range            = var.prefix_subnetwork[0]
  region                   = var.region
  network                  = var.network_name
  private_ip_google_access = true

  depends_on = [google_compute_network.vpc_redacao, null_resource.wait_for_network]
}

resource "google_compute_global_address" "private_ip_block" {
  name          = var.peering[0]
  purpose       = var.peering[1]
  address_type  = var.peering[2]
  ip_version    = var.peering[3]
  prefix_length = 24
  address       = "10.221.84.0"
  network       = var.network_name

  depends_on = [google_compute_network.vpc_redacao,
    google_compute_subnetwork.subnet_redacao,
  ]
}

resource "google_service_networking_connection" "private_vpc_connection" {
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_block.name]
  network                 = var.network_name

  depends_on = [google_compute_network.vpc_redacao,
    google_compute_subnetwork.subnet_redacao,
  ]
}

resource "google_compute_route" "egress_internet" {
  name             = var.egress_internet[0]
  dest_range       = var.egress_internet[1]
  network          = var.network_name
  next_hop_gateway = var.egress_internet[2]
  depends_on       = [google_compute_network.vpc_redacao]
}

resource "google_compute_router" "router" {
  name    = "${local.network_name}-router"
  region  = google_compute_subnetwork.subnet_redacao.region
  network = google_compute_network.vpc_redacao.name
}

resource "google_compute_router_nat" "nat_router" {
  name                               = "${google_compute_subnetwork.subnet_redacao.name}-nat-router"
  router                             = google_compute_router.router.name
  region                             = google_compute_router.router.region
  nat_ip_allocate_option             = var.nat_router[0]
  source_subnetwork_ip_ranges_to_nat = var.nat_router[1]

  subnetwork {
    name                    = google_compute_subnetwork.subnet_redacao.name
    source_ip_ranges_to_nat = [var.nat_router[2]]
  }

  log_config {
    enable = true
    filter = var.nat_router[3]
  }
}

resource "null_resource" "wait_for_database" {
  provisioner "local-exec" {
    command = "sleep 300"
  }
}

resource "google_sql_database_instance" "postgresql" {
  name                = var.cloudsql_name
  region              = var.region
  database_version    = "POSTGRES_15"
  deletion_protection = false
  root_password       = "hn48278$rPlA"

  depends_on = [google_service_networking_connection.private_vpc_connection,
  google_compute_subnetwork.subnet_redacao, null_resource.wait_for_database]

  settings {
    tier              = var.database[0]
    availability_type = var.database[1]
    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
    ip_configuration {
      require_ssl     = false
      ipv4_enabled    = false
      private_network = replace("${google_compute_network.vpc_redacao.self_link}", "https://www.googleapis.com/compute/v1/", "")
    }
    backup_configuration {
      enabled = true
    }
  }
}

resource "google_dns_managed_zone" "private_zone" {
  name     = "cloudsql-zone"
  dns_name = "local.poc.br."

  visibility = "private"

  private_visibility_config {
    networks {
      network_url = google_compute_network.vpc_redacao.self_link
    }
  }
}

resource "google_dns_record_set" "a" {
  name         = "postgresql.local.poc.br."
  type         = "A"
  ttl          = 300
  rrdatas      = [google_sql_database_instance.postgresql.private_ip_address]
  managed_zone = google_dns_managed_zone.private_zone.name
}