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

"""Security regression guards for hardcoded credentials and private GCP identifiers (CWE-798)."""

from __future__ import annotations

import ast
import importlib.util
import os
import pathlib
import re
import subprocess
import sys
import tomllib
import types
import unittest
from unittest.mock import MagicMock, patch

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
ADK_CORRETOR_PATH = REPO_ROOT / "Agent" / "ADK" / "api" / "corretor_gemini" / "gemini_corretor.py"
ADK_API_MAIN_PATH = REPO_ROOT / "Agent" / "ADK" / "api" / "main.py"
ADK_DEPLOY_SH_PATH = REPO_ROOT / "Agent" / "ADK" / "api" / "deploy.sh"
FUNCTION_DIR = REPO_ROOT / "IAC" / "temp" / "function-source"
FUNCTION_SETTINGS_TOML = FUNCTION_DIR / "settings.toml"
FUNCTION_CONFIG_PY = FUNCTION_DIR / "config.py"

BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".pyc", ".zip"}

# Structural secret patterns (deliberately no leaked credential literals).
GOOGLE_API_KEY_RE = re.compile(r"AIza[0-9A-Za-z\-_]{20,}")
PRIVATE_KEY_PEM_RE = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
TF_HARDCODED_ROOT_PASSWORD_RE = re.compile(r'\broot_password\s*=\s*"([^"]+)"')
LITERAL_PGPASSWORD_RE = re.compile(r"""\bPGPASSWORD\s*=\s*(?:'([^']+)'|"([^"$]+)")""")
NUMERIC_COMPUTE_SA_RE = re.compile(r"\b\d{8,}-compute@developer\.gserviceaccount\.com\b")


def _tracked_repo_files() -> list[pathlib.Path]:
    """Return all git-tracked files that currently exist on disk."""
    out = subprocess.check_output(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        text=True,
    )
    return [REPO_ROOT / line for line in out.splitlines() if line and (REPO_ROOT / line).is_file()]


def _repo_source_files() -> list[pathlib.Path]:
    """Return tracked and non-ignored untracked repository files."""
    out = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        text=True,
    )
    return [REPO_ROOT / line for line in out.splitlines() if line and (REPO_ROOT / line).is_file()]


def _load_adk_corretor_module():
    """Import Agent/ADK/api/corretor_gemini/gemini_corretor.py with mocked external SDKs."""
    fake_vertexai = types.ModuleType("vertexai")
    fake_vertexai.init = MagicMock()
    fake_preview = types.ModuleType("vertexai.preview")
    fake_gen_models = types.ModuleType("vertexai.preview.generative_models")
    fake_gen_models.GenerativeModel = MagicMock()

    fake_pandas = types.ModuleType("pandas")
    fake_pandas.DataFrame = MagicMock()

    fake_genai_types = types.ModuleType("google.genai.types")
    fake_genai_types.GenerateContentConfig = MagicMock()
    fake_genai = types.ModuleType("google.genai")
    fake_genai.Client = MagicMock()
    fake_genai.types = fake_genai_types

    fake_google = types.ModuleType("google")
    fake_google.genai = fake_genai

    fake_helpers = types.ModuleType("corretor_gemini.utils.helpers")
    fake_helpers.calcular_nota_competencia = MagicMock()
    fake_helpers.agregar_descricoes = MagicMock()

    stubs = {
        "vertexai": fake_vertexai,
        "vertexai.preview": fake_preview,
        "vertexai.preview.generative_models": fake_gen_models,
        "pandas": fake_pandas,
        "google": fake_google,
        "google.genai": fake_genai,
        "google.genai.types": fake_genai_types,
        "corretor_gemini": types.ModuleType("corretor_gemini"),
        "corretor_gemini.utils": types.ModuleType("corretor_gemini.utils"),
        "corretor_gemini.utils.helpers": fake_helpers,
    }

    spec = importlib.util.spec_from_file_location("adk_gemini_corretor_under_test", ADK_CORRETOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module, fake_genai, fake_vertexai


def _load_function_config_module(env_overrides: dict[str, str]):
    """Import IAC/temp/function-source/config.py with a stdlib-backed Dynaconf stub."""

    class _FakeDynaconf:
        def __init__(self, envvar_prefix: str = "DYNACONF", settings_files=None):
            self._data: dict[str, object] = {}
            for filename in settings_files or []:
                path = FUNCTION_DIR / filename
                if path.is_file():
                    with path.open("rb") as handle:
                        self._data.update(tomllib.load(handle))
            prefix = f"{envvar_prefix}_" if envvar_prefix else ""
            for key, value in os.environ.items():
                if prefix and key.startswith(prefix):
                    self._data[key[len(prefix) :]] = value

        def get(self, key: str, default=None):
            return self._data.get(key, default)

        def set(self, key: str, value) -> None:
            self._data[key] = value

        def __getattr__(self, name: str):
            if name in self._data:
                return self._data[name]
            raise AttributeError(name)

    fake_dynaconf = types.ModuleType("dynaconf")
    fake_dynaconf.Dynaconf = _FakeDynaconf

    spec = importlib.util.spec_from_file_location("function_config_under_test", FUNCTION_CONFIG_PY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, env_overrides, clear=True), patch.dict(
        sys.modules, {"dynaconf": fake_dynaconf}
    ):
        spec.loader.exec_module(module)
    return module


class RepositorySecretScanTests(unittest.TestCase):
    """Ensure no hardcoded API keys, DB passwords, private keys, or live .env files are tracked."""

    def test_no_tracked_dotenv_or_secret_files(self) -> None:
        forbidden = []
        for path in _tracked_repo_files():
            name = path.name
            if name == ".secrets.toml":
                forbidden.append(str(path.relative_to(REPO_ROOT)))
            elif name == ".env" or (
                name.startswith(".env.")
                and name not in {".env.example", ".env.template", ".env.sample"}
            ):
                forbidden.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual(
            forbidden,
            [],
            f"Live environment/secret files must not be committed to git: {forbidden}",
        )

    def test_root_gitignore_blocks_secret_files(self) -> None:
        gitignore_path = REPO_ROOT / ".gitignore"
        self.assertTrue(gitignore_path.is_file(), "Root .gitignore must exist to prevent secret leaks.")
        lines = {line.strip() for line in gitignore_path.read_text(encoding="utf-8").splitlines()}
        for required_pattern in (".env", ".env.*", "!.env.example", ".secrets.toml", "*.tfstate"):
            self.assertIn(
                required_pattern,
                lines,
                f"Root .gitignore must include '{required_pattern}'",
            )

        for ignored_path in (
            ".env",
            "Agent/ADK/agents/essai/.env",
            "IAC/temp/function-source/.secrets.toml",
        ):
            res = subprocess.run(
                ["git", "check-ignore", "-q", ignored_path],
                cwd=REPO_ROOT,
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"Expected git to ignore '{ignored_path}'")

        example_res = subprocess.run(
            ["git", "check-ignore", "-q", "Agent/ADK/agents/essai/.env.example"],
            cwd=REPO_ROOT,
            check=False,
        )
        self.assertNotEqual(
            example_res.returncode,
            0,
            "Template file Agent/ADK/agents/essai/.env.example must remain trackable.",
        )

    def test_no_google_api_keys_or_private_keys_anywhere_in_repo(self) -> None:
        hits: list[str] = []
        for path in _repo_source_files():
            if path.suffix.lower() in BINARY_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            rel = path.relative_to(REPO_ROOT)
            for lineno, line in enumerate(text.splitlines(), start=1):
                if GOOGLE_API_KEY_RE.search(line):
                    hits.append(f"{rel}:{lineno} (Google API key)")
                if PRIVATE_KEY_PEM_RE.search(line):
                    hits.append(f"{rel}:{lineno} (PEM private key)")
                if NUMERIC_COMPUTE_SA_RE.search(line):
                    hits.append(f"{rel}:{lineno} (Hardcoded numeric compute service account)")

        self.assertEqual(hits, [], f"Detected hardcoded credentials/identifiers: {hits}")

    def test_no_hardcoded_db_passwords_in_terraform(self) -> None:
        hits: list[str] = []
        for path in _repo_source_files():
            if path.suffix != ".tf":
                continue
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(REPO_ROOT)
            for lineno, line in enumerate(text.splitlines(), start=1):
                m_root = TF_HARDCODED_ROOT_PASSWORD_RE.search(line)
                if m_root and not m_root.group(1).startswith("${"):
                    hits.append(f"{rel}:{lineno} (hardcoded root_password)")
                if LITERAL_PGPASSWORD_RE.search(line):
                    hits.append(f"{rel}:{lineno} (hardcoded PGPASSWORD)")

        self.assertEqual(hits, [], f"Detected hardcoded database passwords in Terraform: {hits}")


class AdkCorretorCredentialSecurityTests(unittest.TestCase):
    """Verify Agent/ADK API never hardcodes Gemini API keys or GCP projects and fails closed."""

    def test_no_literal_api_key_in_genai_client_call(self) -> None:
        tree = ast.parse(ADK_CORRETOR_PATH.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "api_key" and isinstance(kw.value, ast.Constant) and isinstance(
                        kw.value.value, str
                    ):
                        self.fail(
                            f"Hardcoded string literal passed to api_key at line {kw.lineno} "
                            f"in {ADK_CORRETOR_PATH.relative_to(REPO_ROOT)}"
                        )

    def test_adk_api_main_does_not_hardcode_gcp_project_literal(self) -> None:
        tree = ast.parse(ADK_API_MAIN_PATH.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Corretor":
                for kw in node.keywords:
                    if kw.arg in {"project", "api_key"} and isinstance(kw.value, ast.Constant) and isinstance(
                        kw.value.value, str
                    ):
                        self.fail(
                            f"Hardcoded string literal passed to Corretor({kw.arg}=...) at line {kw.lineno}"
                        )

    def test_adk_deploy_script_requires_gcp_project_without_hardcoded_default(self) -> None:
        script = ADK_DEPLOY_SH_PATH.read_text(encoding="utf-8")
        self.assertIsNone(
            re.search(r"\$\{GCP_PROJECT:-[^}]+\}", script),
            "deploy.sh must not fall back to a hardcoded GCP project ID.",
        )

    def test_corretor_fails_closed_without_credentials(self) -> None:
        module, fake_genai, _ = _load_adk_corretor_module()
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                module.Corretor(caminho_prompts="Prompts", corretor_path="Enem")
        fake_genai.Client.assert_not_called()

    def test_corretor_reads_api_key_from_environment(self) -> None:
        module, fake_genai, _ = _load_adk_corretor_module()
        with patch.dict(os.environ, {"GEMINI_API_KEY": "env-test-api-key"}, clear=True):
            module.Corretor(caminho_prompts="Prompts", corretor_path="Enem")
        fake_genai.Client.assert_called_once_with(api_key="env-test-api-key")

    def test_corretor_supports_google_api_key_env_var(self) -> None:
        module, fake_genai, _ = _load_adk_corretor_module()
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "google-env-test-key"}, clear=True):
            module.Corretor(caminho_prompts="Prompts", corretor_path="Enem")
        fake_genai.Client.assert_called_once_with(api_key="google-env-test-key")

    def test_corretor_supports_vertexai_mode_with_project_and_fails_closed_without_project(self) -> None:
        module, fake_genai, fake_vertexai = _load_adk_corretor_module()
        with patch.dict(
            os.environ,
            {
                "GOOGLE_GENAI_USE_VERTEXAI": "true",
                "GCP_PROJECT": "test-vertex-project",
                "GCP_LOCATION": "us-central1",
            },
            clear=True,
        ):
            module.Corretor(caminho_prompts="Prompts", corretor_path="Enem")
        fake_vertexai.init.assert_called_once_with(project="test-vertex-project", location="us-central1")
        fake_genai.Client.assert_called_once_with(
            vertexai=True,
            project="test-vertex-project",
            location="us-central1",
        )

        fake_genai.Client.reset_mock()
        with patch.dict(os.environ, {"GOOGLE_GENAI_USE_VERTEXAI": "true"}, clear=True):
            with self.assertRaises(ValueError):
                module.Corretor(caminho_prompts="Prompts", corretor_path="Enem")
        fake_genai.Client.assert_not_called()

    def test_corretor_dummy_mode_does_not_initialize_remote_client(self) -> None:
        module, fake_genai, _ = _load_adk_corretor_module()
        with patch.dict(os.environ, {}, clear=True):
            corretor = module.Corretor(caminho_prompts="Prompts", corretor_path="Enem", dummy=True)
        self.assertIsNone(corretor.client)
        fake_genai.Client.assert_not_called()


class FunctionConfigSecurityTests(unittest.TestCase):
    """Verify Cloud Function settings.toml has no hardcoded GCP/DB identifiers and config fails closed."""

    def test_settings_toml_contains_no_environment_specific_gcp_identifiers(self) -> None:
        with FUNCTION_SETTINGS_TOML.open("rb") as handle:
            parsed = tomllib.load(handle)

        for forbidden_key in ("GCP_PROJECT_ID", "GCP_LOCATION", "DB_USER", "INSTANCE_CONNECTION_NAME"):
            self.assertNotIn(
                forbidden_key,
                parsed,
                f"settings.toml must not hardcode environment-specific key '{forbidden_key}'",
            )
        self.assertIn("PROMPT_CORRECAO", parsed)
        self.assertIn("PROMPT_SUMARIZACAO", parsed)
        self.assertIn("PROMPT_VALIDACAO", parsed)

    def test_function_config_fails_closed_when_env_missing_and_accepts_runtime_env_vars(self) -> None:
        empty_cfg_mod = _load_function_config_module({})
        self.assertTrue(hasattr(empty_cfg_mod, "require_setting"))
        for key in ("GCP_PROJECT_ID", "GCP_LOCATION", "DB_USER", "INSTANCE_CONNECTION_NAME"):
            with self.assertRaises(RuntimeError):
                empty_cfg_mod.require_setting(empty_cfg_mod.settings, key)

        unprefixed_mod = _load_function_config_module(
            {
                "GCP_PROJECT_ID": "runtime-proj",
                "GCP_LOCATION": "southamerica-east1",
                "DB_USER": "sa@runtime-proj.iam.gserviceaccount.com",
                "INSTANCE_CONNECTION_NAME": "runtime-proj:southamerica-east1:pg-inst",
            }
        )
        self.assertEqual(unprefixed_mod.require_setting(unprefixed_mod.settings, "GCP_PROJECT_ID"), "runtime-proj")
        self.assertEqual(
            unprefixed_mod.require_setting(unprefixed_mod.settings, "INSTANCE_CONNECTION_NAME"),
            "runtime-proj:southamerica-east1:pg-inst",
        )

        prefixed_mod = _load_function_config_module(
            {
                "GCP_PROJECT_ID": "fallback-proj",
                "DYNACONF_GCP_PROJECT_ID": "dynaconf-proj",
            }
        )
        self.assertEqual(
            prefixed_mod.require_setting(prefixed_mod.settings, "GCP_PROJECT_ID"),
            "dynaconf-proj",
        )


class TerraformDatabaseSecretGuardTests(unittest.TestCase):
    """Static IaC guards ensuring Cloud SQL root password is generated & stored in Secret Manager."""

    def test_db_vpc_uses_random_password_and_secret_manager(self) -> None:
        db_vpc_main = (REPO_ROOT / "IAC" / "db-vpc" / "main.tf").read_text(encoding="utf-8")
        self.assertIn('resource "random_password" "cloudsql_root_password"', db_vpc_main)
        self.assertIn('resource "google_secret_manager_secret" "cloudsql_root_password"', db_vpc_main)
        self.assertIn('resource "google_secret_manager_secret_version" "cloudsql_root_password"', db_vpc_main)
        self.assertIn("root_password       = local.cloudsql_root_password", db_vpc_main)

    def test_compute_engine_fetches_password_from_secret_manager_not_metadata(self) -> None:
        ce_main = (REPO_ROOT / "IAC" / "compute-engine" / "main.tf").read_text(encoding="utf-8")
        self.assertIn("gcloud secrets versions access latest", ce_main)
        self.assertIn('role      = "roles/secretmanager.secretAccessor"', ce_main)
        self.assertIn("service_account {", ce_main)
        self.assertNotIn("{your-compute-service-account-name}", ce_main)

    def test_cloud_function_terraform_injects_dynaconf_runtime_env_vars(self) -> None:
        fn_main = (REPO_ROOT / "IAC" / "function" / "main.tf").read_text(encoding="utf-8")
        for key in (
            "DYNACONF_GCP_PROJECT_ID",
            "DYNACONF_GCP_LOCATION",
            "DYNACONF_DB_USER",
            "DYNACONF_INSTANCE_CONNECTION_NAME",
        ):
            self.assertIn(key, fn_main)


if __name__ == "__main__":
    unittest.main()
