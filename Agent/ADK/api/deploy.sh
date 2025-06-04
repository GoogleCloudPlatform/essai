#!/bin/bash
# Purpose: To deploy the App to Cloud Run.

# Carrega variáveis do .env se existir
if [ -f ../.env ]; then
  export $(grep -v '^#' ../.env | xargs)
fi

PROJECT=${GCP_PROJECT:-hugotestebot2}
LOCATION=${GCP_LOCATION:-us-east1}
API_NAME=${API_NAME:-api-bot-redacao}

# Deploy app from source code
gcloud run deploy $API_NAME --source . --region=$LOCATION --project=$PROJECT --allow-unauthenticated --memory=2Gi --port=8080