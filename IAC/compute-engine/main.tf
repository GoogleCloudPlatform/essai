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

resource "google_compute_instance" "psql-instance" {
  name         = "psql"
  machine_type = var.machine_type

  metadata_startup_script = <<-EOF

    #!/bin/bash 
    
    sudo apt update -y

    sudo apt-get install wget sudo curl gnupg2 -y
    
    sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

    sudo wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

    sudo apt -y update

    sudo apt-get install postgresql-15 -y
    
    sudo systemctl start postgresql

    sudo systemctl enable postgresql

    export PGPASSWORD='hn48278$rPlA'

    psql -h postgresql.local.poc.br -p 5432 -U postgres -d postgres -c "GRANT CREATE ON SCHEMA public TO \"{your-compute-service-account-name}@developer"\";

    EOF


  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  network_interface {
    network    = var.network_name
    subnetwork = var.subnet_name
  }
}

