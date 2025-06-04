import os
from google.cloud import aiplatform
from vertexai import agent_engines
from vertexai import init
import essai.agent  # ou o caminho do seu root_agent
from dotenv import load_dotenv

load_dotenv("../.env")

# Defina os requisitos
requirements = os.environ.get("REQUIREMENTS_FILE", "requirements.txt")

# Defina variáveis de ambiente para o deploy
env_vars = {
    "CORRECAO_API_URL": os.environ.get("CORRECAO_API_URL", "http://your-api-url/correct-essay/")
}

# Pacotes extras
extra_packages = os.environ.get("EXTRA_PACKAGES", "essai").split(",")

# Nome do subdiretório no GCS
_gcs_dir_name = os.environ.get("GCS_SUBDIR_NAME", "")
gcs_dir_name = _gcs_dir_name if _gcs_dir_name else None

# Metadados
_display_name = os.environ.get("AGENT_DISPLAY_NAME", "ENEM Essai Agent")
display_name = _display_name if _display_name else None
_description = os.environ.get("AGENT_DESCRIPTION", "Agent for ENEM essay correction with structured feedback.")
description = _description if _description else None

# Vertex AI config
project = os.environ.get("GCP_PROJECT", "your-gcp-project-id")
location = os.environ.get("GCP_LOCATION", "us-central1")
staging_bucket = os.environ.get("GCP_VERTEX_BUCKET", "gs://your-vertex-bucket")

init(
    project=project,
    location=location,
    staging_bucket=staging_bucket
)

# Deploy!
remote_agent = agent_engines.create(
    essai.agent.root_agent,  # ou o nome do seu agente principal
    requirements=requirements,
    extra_packages=extra_packages,
    env_vars=env_vars,
    gcs_dir_name=gcs_dir_name,
    display_name=display_name,
    description=description,
)
print("Agente publicado! resource_name:", remote_agent.resource_name)
