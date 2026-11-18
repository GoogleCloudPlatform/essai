#!/bin/bash
# Purpose: To deploy the App to Cloud Run.
set -euo pipefail

# Carrega variáveis do .env se existir
if [ -f ../.env ]; then
  set -a
  # shellcheck disable=SC1091
  source ../.env
  set +a
fi

: "${GCP_PROJECT:?GCP_PROJECT must be set in the environment or ../.env}"
PROJECT="${GCP_PROJECT}"
LOCATION="${GCP_LOCATION:-us-central1}"
API_NAME="${API_NAME:-api-bot-redacao}"

# Deploy app from source code
gcloud run deploy "${API_NAME}" --source . --region="${LOCATION}" --project="${PROJECT}" --memory=2Gi --port=8080