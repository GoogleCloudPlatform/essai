# EssAI — Agent & Contributor Rules

Experimental open-source ENEM essay grader powered by Google Gemini on GCP (proof-of-concept, not an official Google Cloud product).

## Architecture & Repository Layout

This repo contains **three independent runtime paths**, not one unified application:

1. **Async GCP Pipeline** (`Backend/` + `IAC/` + `IAC/temp/function-source/`)
   - `Backend/`: FastAPI ingestion/query API (`POST /grade`, `GET /grade/{id}`, `POST /grade/bulk`, `POST /feedback`, `GET /health`). Writes requests to Cloud SQL Postgres 15 and publishes UUIDs to Pub/Sub.
   - `IAC/temp/function-source/`: **Live Cloud Functions Gen2 consumer source** (not scratch). Zipped directly by `IAC/function/main.tf`. Consumes Pub/Sub UUIDs, grades and validates essays via `promptweaver`, and writes rows to `correcoes`.
   - `IAC/`: Terraform root module provisioning VPC, Cloud SQL, Pub/Sub, Artifact Registry, Cloud Run (`Backend/` and `Frontend/`), Cloud Functions Gen2, IAM, and a setup GCE VM.
2. **Standalone Streamlit Demo** (`Frontend/`)
   - `main.py` -> `st_pages/corrigir.py` with sample pt-BR essays in `data/exemplo-*.json`.
   - **Bypasses `Backend/` completely**; calls Vertex AI Gemini directly via its own local `corretor_gemini/` and `Prompts/`.
3. **ADK Agentic Stack** (`Agent/ADK/`)
   - `Agent/ADK/agents/`: Google ADK multi-agent system (`ProfessorEnemAgent` -> `sumarizador_enem`), deployed to Vertex AI Agent Engine via `deploy_vertex.py`.
   - `Agent/ADK/api/`: Standalone FastAPI grading service (`POST /corrigir-redacao/`) called by the ADK agent. Uses `google-genai` directly with plain `.txt`/`.json` prompts (no `promptweaver`).

## Patterns & Conventions

- **Three diverged copies of `corretor_gemini` and prompts** — changes do not propagate automatically; update every applicable target:
  - `Frontend/corretor_gemini/` + `Frontend/Prompts/` (`promptweaver==0.1.15`, Vertex AI, C1–C5 prompt).
  - `IAC/temp/function-source/src/corretor_gemini/` + `.../src/prompts/` (`promptweaver==0.1.13`, Vertex AI, C2–C5 only, plus Paraná 0–60 conversion and `validate_essay()`).
  - `Agent/ADK/api/corretor_gemini/` + `.../Prompts/Enem/` (`google-genai`, plain text prompt + JSON schema/config, C1–C5).
- **ENEM grading conventions**:
  - Gemini grades sub-criteria `0–10`; Python maps each competency to ENEM multiples of `40` (`0, 40, 80, 120, 160, 200`).
  - `Backend/` and `IAC/temp/function-source/` evaluate **Competencies 2–5 only** (max 800); `Frontend/Prompts/` and `Agent/ADK/` evaluate **Competencies 1–5** (max 1000).
  - Rounding diverges: `Frontend/` and Cloud Function use `np.ceil(sum / (len * 2)) * 40`; `Agent/ADK/api/main.py` uses floor division `(sum / len // 2) * 40`.
  - Keep the method spelling `Correcao.get_nota_comptencias()` unless updating all callers across all copies.
- **Language mix**: Domain models, DB tables/columns (`requisicao`, `correcoes`, `feedback`), prompts, and most comments are in **pt-BR**; docs, `Backend/` response/feedback schemas (`criteria_2..5`, `final_reason`), and `Backend/src/app/config.py` are in English.
- **Toolchains & Python versions per subproject**:
  - `Backend/`: Python `>=3.12` (`.python-version` = `3.12`), managed with `uv` (`pyproject.toml` + `uv.lock`). `Backend/Dockerfile` runs `uv sync --frozen --no-cache` — run `uv lock` after editing dependencies.
  - `Frontend/`: `requirements.txt` (`promptweaver==0.1.15`).
  - `IAC/temp/function-source/`: Cloud Functions `python310` runtime, `requirements.txt` (`promptweaver==0.1.13`), CRLF line endings.
  - `Agent/ADK/api/` & `Agent/ADK/agents/`: Python `3.10-slim` Dockerfiles, separate `requirements.txt` (`google-adk==0.5.0`, `google-genai==1.16.1`).
- **Auth & DB boundary**: `Backend/` enforces fail-closed Google OIDC Bearer authentication (`app/auth.py`, requiring `OIDC_AUDIENCE` and optional `ALLOWED_CALLER_EMAILS`), per-caller rate limiting and security headers (`app/security.py`), and `owner_id` ownership checks in `app/crud/cloudsql.py` (preventing IDOR). `IAC/cloudrun/` restricts ingress (`internal-and-cloud-load-balancing`) and forbids `allUsers`/`allAuthenticatedUsers` in `roles/run.invoker`. Connects to Cloud SQL via `cloud-sql-python-connector` (`IPTypes.PRIVATE`, IAM auth).
- **Licensing**: Preserve `# Copyright 2025 Google LLC` Apache-2.0 headers in `Backend/`, `Frontend/`, and `IAC/`. External contributions require a Google CLA (`CONTRIBUTING.md`).

## Test, Lint & Run Commands

There is no CI pipeline in this repository. `Backend/tests/` contains `unittest` security regression guards; verify other components with `ruff`, `terraform validate`, and targeted local smoke checks.

```bash
# Backend security tests, lint & lockfile update
cd Backend && PYTHONPATH=src uv run --frozen python -m unittest discover -s tests -v
cd Backend && uv run --frozen ruff check src tests
cd Backend && uv lock

# Backend local dev (requires OIDC_AUDIENCE + GCP ADC for Cloud SQL & Pub/Sub calls)
cd Backend && OIDC_AUDIENCE=https://example.local uv run fastapi dev src/app/main.py --port 8080

# Frontend local run (CWD must be Frontend/ for relative Prompts/ and data/ paths)
cd Frontend && PROJECT_ID=<gcp-project-id> streamlit run main.py --server.port=8501

# ADK API local run (CWD must be Agent/ADK/api/ for relative Prompts/ path)
cd Agent/ADK/api && uvicorn main:app --host 0.0.0.0 --port 8000

# ADK Agent deploy (CWD must be Agent/ADK/agents/ for ../.env, essai, requirements.txt)
cd Agent/ADK/agents && python3 deploy_vertex.py

# Terraform syntax/schema validation & Cloud Run security tests (run from IAC/, NOT repo root)
cd IAC && terraform init -backend=false && terraform validate
cd IAC/cloudrun && terraform init -backend=false && terraform test
```

## Things a Newcomer Will Get Wrong

- **Do not delete `IAC/temp/`**: `IAC/temp/function-source/` is the live Cloud Function consumer deployed by `IAC/function/main.tf`.
- **No root `.gitignore` + tracked credential placeholders**: `IAC/svc.json` and `IAC/terraform.tfvars` are committed templates — never commit real GCP keys or project details. Avoid adding Windows `:Zone.Identifier` or `__pycache__` files (some are already tracked under `Agent/ADK/api/`).
- **Docs drift from reality**:
  - `docs/concepts-architecture.md` shows Streamlit talking to `Backend/`, but `Frontend/` calls Gemini directly.
  - `docs/deploying-essai.md` instructs running `terraform init/apply` from repo root — the Terraform root is `IAC/`.
  - `docs/translating-responses.md` references uncommenting `"Dê todos os resultados em inglês."` at line 298 — that line does not exist in any prompt file.
  - `Agent/ADK/README.md` runs `python3 agents/deploy_vertex.py` from `Agent/ADK/`, but `deploy_vertex.py` expects CWD = `Agent/ADK/agents/`.
- **Local DB vs. Cloud SQL in `Backend/`**: `Backend/docker-compose.yaml` defines a local `postgres` service, but `app/database.py` is hardcoded to Cloud SQL Connector (`IPTypes.PRIVATE`) and does not connect to it. `create_db_and_tables()` is commented out in `app/__init__.py`. Existing Postgres instances must add `requisicao.owner_id` (`ALTER TABLE requisicao ADD COLUMN owner_id VARCHAR;`); rows with `owner_id IS NULL` fail closed.
- **Hardcoded secrets, projects, regions & buckets**:
  - `Agent/ADK/api/corretor_gemini/gemini_corretor.py` hardcodes a `genai.Client(api_key=...)`; `Agent/ADK/api/main.py` hardcodes `project="key-range-436019-t9"`.
  - `IAC/temp/function-source/settings.toml` hardcodes `GCP_PROJECT_ID`, `DB_USER`, and `INSTANCE_CONNECTION_NAME`. `config.py` configures `Dynaconf(envvar_prefix="DYNACONF")`, while `IAC/function/main.tf` injects `GCP_PROJECT_ID`/`GCP_LOCATION` **without** the `DYNACONF_` prefix — so Terraform env vars do not override `settings.toml`.
  - `IAC/main.tf`, `IAC/cloudrun/main.tf`, and `IAC/function/variables.tf` hardcode `southamerica-east1` in Artifact Registry URLs and the Eventarc trigger even if `var.region` changes.
  - `IAC/iam/main.tf` uses authoritative `google_project_iam_binding`, overwriting all other project members for those admin roles.
  - `IAC/db-vpc/main.tf` and `IAC/compute-engine/main.tf` share a hardcoded Postgres `root_password` and use `sleep 40`/`sleep 300` `local-exec` waits.
  - `IAC/temp/function-source/src/corretor_gemini/utils/imageUploader.py` hardcodes `bucket_name='imagens-redacaopr'` and imports `googleapiclient` (missing from `IAC/temp/function-source/requirements.txt`).
- **Known broken or unfinished paths (do not assume they work as-is)**:
  - `Backend/src/app/schemas.py` (`InboundSchema`) includes `IdTurma`, which is absent from `models.Requisicao`; `Backend/src/app/enums.py` (`NStars`) uses type annotations (`UM: 1`) instead of assignments (`UM = 1`).
  - Both `Frontend/` and `Agent/ADK/api/` branch to an `'invalida'` prompt when `len(redacao_estudante) < 150`, but neither `template-correcao-enem-invalida.yml.j2` nor `Agent/ADK/api/Prompts/Invalida/` exists (`FileNotFoundError`). `Agent/ADK/api/Prompts/Sumarizador/` is also missing (silently returns `""`), and `Agent/ADK/api/corretor_gemini/gemini_corretor.py` writes `output_teste.json` to CWD on every request.
  - `Frontend/main.py` loads `var_environment.py` into unused variables while `st_pages/corrigir.py` reads `os.environ.get('PROJECT_ID')` and `Corretor` hardcodes `location="us-central1"`. `Frontend/Procfile` has single-dash flags (`- server.port=...`) instead of `--`. `Frontend/Prompts/template-correcao-enem.yml.j2` is ASCII with Portuguese accents stripped.
  - `Backend/Makefile` references an undefined `mkfile_path` and a stale `api/` directory; `Agent/ADK/agents/Dockerfile` runs `gunicorn main:app` though no `main.py` exists in `Agent/ADK/agents/`.
  - `IAC/temp/function-source/main.py` calls `texto_adaptado.replace(...)` without reassigning the result, and retry loops in both `Frontend/` and Cloud Function `gemini_corretor.py` omit `.text` on `generate_content(...)`.
