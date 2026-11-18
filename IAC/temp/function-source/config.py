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

import os

from dynaconf import Dynaconf

_ENV_SETTING_KEYS = (
    "GCP_PROJECT_ID",
    "GCP_LOCATION",
    "DB_USER",
    "DB_DATABASE",
    "INSTANCE_CONNECTION_NAME",
)


def load_settings() -> Dynaconf:
    """Load non-sensitive defaults from settings.toml and runtime GCP config from env."""
    cfg = Dynaconf(
        envvar_prefix="DYNACONF",
        settings_files=["settings.toml", ".secrets.toml"],
    )
    # Also honor unprefixed runtime environment variables when DYNACONF_* is not set.
    for key in _ENV_SETTING_KEYS:
        if not cfg.get(key):
            env_value = os.environ.get(key)
            if env_value:
                cfg.set(key, env_value)
    return cfg


def require_setting(cfg: Dynaconf, key: str) -> str:
    """Return a required runtime configuration setting or fail closed."""
    value = cfg.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(
            f"Missing required runtime configuration '{key}'. "
            f"Set environment variable '{key}' or 'DYNACONF_{key}'."
        )
    return value.strip()


settings = load_settings()
