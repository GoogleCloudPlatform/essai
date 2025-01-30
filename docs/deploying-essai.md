# Deploying EssAI

EssAI depends on [Google Cloud Platform (GCP)](https://cloud.google.com/?hl=en) and [Terraform](https://cloud.google.com/docs/terraform) as Infrastructure as Code tool (IaC) to configure and implement all the elements of the non-functional architecture described [here](/docs/concepts-architecture.md). This doc provides guidance of how to configure and deploy the project itself.

## Prerequisits 

- Active account with [Google Cloud Platform](https://cloud.google.com/)
- [Terraform](https://www.terraform.io/) installed in the host machine
- Git client installed at the host machine

## Step 1: Initial configuration

### 1.1 Install GCloud SDK

1. Go to [Google Cloud SDK](https://cloud.google.com/sdk)'s official website.
2. Carefully follow through the installation instructions described there (according to the host machine's OS).
3. Once properly installed, open up a terminal and run the following:

```
gcloud init
```
4. Follow through the instructions provided by the SDK to get yourself logged in with your GCP account.

### 1.2 Enable required services APIs

1. Open up a browser tab/window and hit [GCP console](https://console.cloud.google.com).
2. Browse to the session "APIs & Services" and then, hit "Library".
3. Once there, enable the following APIs:
- **Cloud Resource Manager API**
- **Compute Engine API**

## Step 2: Storage configuration

### 2.1 Create a Storage Bucket

1. On GCP console, browse to "Cloud Storage" and then click over "Create Bucket".
2. Follow through the self declaratory set of steps to create a bucket. Don't forget to attribute an unique name to it.

### 2.2 Update the file 'main.tf'

1. Open up the root directory and then open up the file `main.tf` located under the IAC directory.
2. In that file, make sure to update the line below replacing "{your-gcs-bucket-name}" with the actual name of the bucket just created:

```
bucket = "{your-gcs-bucket-name}"
```

## Step 3: Configure service accounts

### 3.1 Create a new Service Account

1. In the Google Cloud console, go to "IAM & Admin" > "Service Accounts".

2. Click "Create Service Account" and fill in the required fields.

3. Assign the Owner role to the service account.

4. In the list of service accounts, click "Actions" > "Manage keys" for the new account.

5. Click "Add Key" > "Create New Key" and select the JSON format.

6. Save the generated key file.

### 3.2 Update the file 'svc.json'

1. Copy the contents of the JSON key file.

2. In the IAC directory, open the `svc.json` file and paste the copied contents.

## Step 4: Permissions and files configuration

### 4.1 Atualizar Conta de Serviço do Compute Engine

In the Google Cloud console, go to "IAM & Admin" > "IAM".
Find the service account managed by Compute Engine, which follows the pattern `name@developer.gserviceaccount.com`.

### 4.2 Update the file 'main.tf' under the directory 'compute-engine'

In the 'compute-engine' directory, open up the `main.tf` file. Then, replace the current Service Account on line 27 with the email address you copied on above step:

```
"nome@developer.gserviceaccount.com"
```

### 4.3 Update the file 'terraform.tfvars'

In the IAC directory, open the `terraform.tfvars` file and update the values of all variables with placeholders on its values.

```
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
```

## Step 5 - Updating 'main.tf' file under 'compute-engine' directory

Open up the file `main.tf` under the directory 'compute-engine'. Look for the **line 41** and then update the portion of the line that has a placeholder, as highlighted below.

```
    psql -h postgresql.local.poc.br -p 5432 -U postgres -d postgres -c "GRANT CREATE ON SCHEMA public TO \"{your-compute-service-account-name}@developer"\";
```

## Step 6 - Update frontend env variables

Finally, the last step before running terraform to deploy the application, is to update two environment variables in the frontend application.

To do that, open up the directory 'Frontend'. Then, from the, open the file `var_environment.py'. In there, update the values of the two variables with placeholders in its place, as you can see below.

```
var = {

    'project_id': "your-project-id",
    'location': 'your-gcp-region'
}
```

Save the file and then move to the next step.

## Step 7 - Run terraform commands to deploy the application

Once you have completed all of the steps above, you should be ready to deploy your project using Terraform. Be sure to follow security best practices and verify your configurations before proceeding to apply your infrastructure plans.

Go back to the root directory from your terminal and then type in the following commands in order.

```
terraform init
```

Once it finishes its pre-flight verification, run the following followed by "yes" when asked if you want to proceed.

```
terraform apply
```

It will take around 10-15 minutes for the whole application to deploy.