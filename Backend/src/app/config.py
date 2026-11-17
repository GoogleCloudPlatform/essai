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

from functools import lru_cache
from pydantic_settings import BaseSettings


tags_metadata = [
    {
        "name": "inbound",
        "description": "Interface for inputing new essay corretion requests",
    },
    {
        "name": "outbound",
        "description": """Interface for fetching results.""",
    },
]

SUMMARY = r"""
Interface between GCP services and UI backend.

Serves endpoints for: 1 Essay submission, 2 Fetching results (single and bulk) and 3 User feedback submission.
"""


class Settings(BaseSettings):
    ENVIRONMENT: str = "skip"
    IAM_USER: str = "test_user"
    POSTGRES_DB: str = "test_db"
    INSTANCE_CONNECTION_NAME: str = "test_project:test_region:test_instance"

    MAX_IDS_BULK_READ: int = 100

    PUBSUB_TOPIC_NAME: str = "test_topic"

    # Google OIDC Bearer token verification (fail-closed if unset)
    OIDC_AUDIENCE: str = ""
    ALLOWED_CALLER_EMAILS: str = ""

    # Per-caller sliding-window rate limiting
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    @property
    def allowed_caller_emails_set(self) -> frozenset[str]:
        return frozenset(
            email.strip().lower()
            for email in self.ALLOWED_CALLER_EMAILS.split(",")
            if email.strip()
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
