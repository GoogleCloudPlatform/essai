
# EssAI - An ENEM Essay Correction Agent – API & Agent

This project provides a complete solution for ENEM essay correction using Google Vertex AI and a FastAPI-based API. The deployment is designed for Google Cloud (Cloud Run + Vertex AI), but can also be run locally for development.

---

## **Environment Variables (.env)**

Create a `.env` file in the project root with the following variables (example values below):

```env
# Google Cloud project and region
GCP_PROJECT=your-gcp-project-id
GCP_LOCATION=us-central1

# Cloud Run API service name
API_NAME=api-bot-redacao

# API configuration
API_HOST=0.0.0.0
API_PORT=8080

# URL for essay correction (will be set automatically after API deploy)
CORRECAO_API_URL=https://your-api-url.a.run.app/corrigir-redacao/

# Vertex AI model
LLM_MODEL=gemini-2.5-flash-preview-05-20

# Agent (Vertex AI) configuration
REQUIREMENTS_FILE=requirements.txt
EXTRA_PACKAGES=essai
GCS_SUBDIR_NAME=
AGENT_DISPLAY_NAME=ENEM Essai Agent
AGENT_DESCRIPTION=Agent for ENEM essay correction with structured feedback.
GCP_VERTEX_BUCKET=gs://your-vertex-bucket
```

---

## **How to Deploy**

### **1. Deploy the API to Cloud Run**

1. **Build and deploy the API:**
   ```bash
   cd api
   bash deploy.sh
   ```
   This script will:
   - Load variables from your `.env`
   - Build and deploy the API to Cloud Run

2. **Get the public URL of your API:**
   ```bash
   gcloud run services describe $API_NAME --region $GCP_LOCATION --project $GCP_PROJECT --format='value(status.url)'
   ```
   Update the `CORRECAO_API_URL` in your `.env` with the value:  
   `https://your-api-url.a.run.app/corrigir-redacao/`

---

### **2. Deploy the Agent (Vertex AI)**

1. **Update your `.env` with the correct `CORRECAO_API_URL` (see above).**
2. **Deploy the agent:**
   ```bash
   python3 agents/deploy_vertex.py
   ```
   This script will:
   - Read all configuration from your `.env`
   - Deploy the agent to Vertex AI using the correct API endpoint

---

## **Local Development**

You can run the API locally for testing:

```bash
cd api
uvicorn main:app --host=0.0.0.0 --port=8000
```

Or using Docker:

```bash
docker build -t enem-api .
docker run -p 8080:8080 --env-file ../.env enem-api
```

---

## **Notes**

- Make sure your Google Cloud credentials are set up (`gcloud auth application-default login` or set `GOOGLE_APPLICATION_CREDENTIALS`).
- The agent will only work if the API is accessible at the URL specified in `CORRECAO_API_URL`.
- All configuration is centralized in the `.env` file for easy management.
- You must update the line 15 in the file "deploy_vertex.py" with your actual API endpoint.

---

## **Project Structure**

```
.
├── api/                # FastAPI app for essay correction
│   ├── main.py
│   ├── Dockerfile
│   ├── deploy.sh
│   └── ...
├── agents/             # Vertex AI agent deploy script and code
│   ├── deploy_vertex.py
│   └── ...
├── .env                # Environment variables (not committed)
└── README.md           # This file
```