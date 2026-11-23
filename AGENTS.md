# EssAI — Repository Rules

Experimental open-source ENEM essay grader powered by Google Gemini on GCP (PoC, not an official Google Cloud product).

## Structure

Three **independent** runtime paths (not one unified app), each with its own diverged copy of `corretor_gemini` and prompts—edits do not propagate across them:

| Path | Directories | Role, Grading Stack & Rubric | Toolchain |
|---|---|---|---|
| **Async GCP Pipeline** | `Backend/`, `IAC/`, `IAC/temp/function-source/` | FastAPI (`POST /grade`, `GET /grade/{id}`, `POST /grade/bulk`, `POST /feedback`, `GET /health`) -> Cloud SQL Postgres 15 + Pub/Sub -> Cloud Functions Gen2 (`promptweaver==0.1.13`, Vertex AI, C2–C5 max 800, Paraná 0–60, `validate_essay()`) | `Backend/`: Python `>=3.12`, `uv`; Function: `python310`, CRLF |
| **Streamlit Demo** | `Frontend/` | `main.py` -> `st_pages/corrigir.py` + `data/exemplo-*.json`. **Bypasses `Backend/`**; calls Vertex AI directly (`promptweaver==0.1.15`, C1–C5 max 1000) | `requirements.txt` |
| **ADK Agentic Stack** | `Agent/ADK/agents/`, `Agent/ADK/api/` | Google ADK (`ProfessorEnemAgent` -> `sumarizador_enem`, Vertex AI Agent Engine) -> standalone FastAPI `POST /corrigir-redacao/` (`google-genai`, plain `.txt`/`.json` prompts, C1–C5 max 1000) | Python `3.10-slim`, separate `requirements.txt` (`google-adk==0.5.0`, `google-genai==1.16.1`) |

## Patterns & Conventions

- **ENEM scoring**: Gemini scores sub-criteria `0–10`; Python maps each competency to multiples of `40` (`0..200`). `Frontend/` and Function round up (`np.ceil(sum / (len * 2)) * 40`); `Agent/ADK/api/main.py` floors (`(sum / len // 2) * 40`). Keep `Correcao.get_nota_comptencias()` spelled as-is unless updating all 3 copies.
- **Backend auth & IDOR (`Backend/` + `IAC/cloudrun/`)**: Fail-closed Google OIDC Bearer auth (`OIDC_AUDIENCE` required, optional `ALLOWED_CALLER_EMAILS` in `app/auth.py`), method allow-list + security headers + sliding-window rate limits (`app/security.py`), and `requisicao.owner_id` ownership checks (`app/crud/cloudsql.py`; `owner_id IS NULL` returns `404`). `IAC/cloudrun/` restricts ingress (`internal`/`internal-and-cloud-load-balancing`) and forbids `allUsers`/`allAuthenticatedUsers`.
- **Fail-closed secrets & config (test-enforced)**:
  - Never commit `.env`, `.env.*` (except `.env.example`), `.secrets.toml`, API/PEM keys, numeric compute SAs, or literal DB passwords (`Backend/tests/test_security_hardcoded_secrets.py` scans the entire repo).
  - ADK API requires `GEMINI_API_KEY`/`GOOGLE_API_KEY` or `GOOGLE_GENAI_USE_VERTEXAI=true` + `GCP_PROJECT`.
  - Function `settings.toml` holds only prompt paths and `DB_DATABASE`; `GCP_PROJECT_ID`, `GCP_LOCATION`, `DB_USER`, and `INSTANCE_CONNECTION_NAME` come from env (`DYNACONF_*` or unprefixed) via `require_setting()`. Drive image staging (`imageUploader.py`) is **fail-closed** (`DRIVE_IMAGE_FETCH_ENABLED=false` by default; requires `IMAGES_BUCKET_NAME`, at least one `ALLOWED_DRIVE_*` allowlist, size cap <= 10 MiB, and PNG/JPEG/WEBP magic bytes; lazy-imports `googleapiclient`).
  - `IAC/db-vpc/main.tf` generates the Cloud SQL root password into Secret Manager; `IAC/compute-engine/main.tf` reads it via `gcloud secrets versions access`.
- **Dependencies, language & licensing**: `Backend/Dockerfile` runs `uv sync --frozen --no-cache`—run `uv lock` after changing `pyproject.toml` (ignore stale `Backend/requirements.txt`). Domain models, DB schema (`requisicao`, `correcoes`, `feedback`), and prompts are pt-BR; docs, `Backend/` response schemas (`criteria_2..5`, `final_reason`), and `config.py` are English. Preserve `# Copyright 2025 Google LLC` Apache-2.0 headers in `Backend/`, `Frontend/`, and `IAC/`; external PRs require a Google CLA (`CONTRIBUTING.md`).

## Test, Lint & Run Commands

No CI exists. `Backend/tests/` runs 40 `unittest` guards (Backend auth/IDOR, ADK & Function config, Drive confused-deputy protection, repo secret scan, and IaC invariants).

```bash
# Backend security tests & lockfile
cd Backend && PYTHONPATH=src uv run --frozen python -m unittest discover -s tests -v
cd Backend && uv lock

# Backend lint (6 pre-existing errors in src/app/crud/__init__.py & src/app/models.py)
cd Backend && uv run --frozen ruff check src tests

# Terraform validate & security tests (from IAC/ or submodules, NOT repo root)
cd IAC && terraform init -backend=false && terraform validate
for m in cloudrun db-vpc compute-engine function; do
  (cd "IAC/$m" && terraform init -backend=false && terraform test)
done

# Local runs (CWD matters for relative Prompts/, data/, ../.env paths)
cd Backend && OIDC_AUDIENCE=https://example.local uv run fastapi dev src/app/main.py --port 8080
cd Frontend && PROJECT_ID=<gcp-project-id> streamlit run main.py --server.port=8501
cd Agent/ADK/api && GEMINI_API_KEY=<key> uvicorn main:app --host 0.0.0.0 --port 8000
cd Agent/ADK/agents && python3 deploy_vertex.py
```

## Things a Newcomer Will Get Wrong

- **Do not delete `IAC/temp/`**: `IAC/temp/function-source/` is the live Cloud Function source zipped by `IAC/function/main.tf`.
- **Docs contradict the code**: `docs/concepts-architecture.md` shows Streamlit -> `Backend/` (false); `docs/deploying-essai.md` runs Terraform from repo root (root is `IAC/`); `docs/translating-responses.md` references a non-existent line 298; `Agent/ADK/README.md` runs `deploy_vertex.py` from `Agent/ADK/` (needs CWD `Agent/ADK/agents/`).
- **Templates & tracked junk**: `IAC/svc.json` and `IAC/terraform.tfvars` are committed templates—never fill them with live secrets. Legacy `:Zone.Identifier` and `__pycache__` files are already tracked under `Agent/ADK/api/`; don't add new ones.
- **Backend DB traps**: `Backend/docker-compose.yaml` local Postgres is unused (`database.py` hardcodes Cloud SQL Private IP + IAM auth); `create_db_and_tables()` is commented out in `app/__init__.py`; existing DBs need `ALTER TABLE requisicao ADD COLUMN owner_id VARCHAR;` (+ index).
- **IaC & Function sharp edges**: `southamerica-east1` is hardcoded in Artifact Registry URLs (`IAC/main.tf`, `IAC/cloudrun/main.tf`) and Eventarc trigger (`IAC/function/variables.tf`); `IAC/iam/main.tf` uses authoritative `google_project_iam_binding`; `IAC/function/main.tf` still sets `allUsers` invoker (under `ALLOW_INTERNAL_ONLY`) and `IAC/main.tf` deploys `Frontend` with `--allow-unauthenticated`; `IAC/db-vpc/main.tf` has `sleep 40`/`sleep 300` waits; enabling Drive fetching requires `google-api-python-client` (not in `IAC/temp/function-source/requirements.txt`).
- **Known broken/unfinished paths**:
  - `InboundSchema.IdTurma` is absent from `models.Requisicao` (dropped); `enums.NStars` uses `:` instead of `=`.
  - Essays `< 150` chars hit missing `'invalida'` prompts (`FileNotFoundError`) in `Frontend/` and `Agent/ADK/api/`; `Agent/ADK/api/Prompts/Sumarizador/` is also missing (returns `""`); `Agent/ADK/api/corretor_gemini/gemini_corretor.py` writes `output_teste.json` to CWD per request.
  - `Frontend/var_environment.py` is unused (`corrigir.py` reads `PROJECT_ID` env, hardcodes `us-central1`); `Frontend/Procfile` uses `-` instead of `--`; `Frontend/Prompts/template-correcao-enem.yml.j2` has Portuguese accents stripped.
  - `Backend/Makefile` (undefined `mkfile_path`, stale `api/`) and `Agent/ADK/agents/Dockerfile` (`gunicorn main:app`, no `main.py`) are broken.
  - Retry loops in `Frontend/` and Function `gemini_corretor.py` omit `.text` on `generate_content(...)`.
