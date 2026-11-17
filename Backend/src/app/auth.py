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

from dataclasses import dataclass
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.config import get_settings

log = logging.getLogger("uvicorn")

_VALID_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})
_bearer_scheme = HTTPBearer(auto_error=False)
_google_request: google_requests.Request | None = None


@dataclass(frozen=True)
class CallerIdentity:
    """Server-verified caller identity extracted from a Google OIDC ID token."""

    subject: str
    email: str | None = None


def _get_google_request() -> google_requests.Request:
    global _google_request
    if _google_request is None:
        _google_request = google_requests.Request()
    return _google_request


def verify_oidc_token(token: str, audience: str) -> dict:
    """Verify a Google OIDC ID token signature, issuer, audience, and expiration.

    Uses Google's RS256 JWKS verification (rejects 'none' and untrusted algorithms).
    """
    return id_token.verify_oauth2_token(token, _get_google_request(), audience=audience)


def get_current_caller(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CallerIdentity:
    """Authenticate caller via Google OIDC Bearer token (fail-closed)."""
    settings = get_settings()
    audience = settings.OIDC_AUDIENCE.strip()
    if not audience:
        log.error("OIDC_AUDIENCE is not configured; denying request (fail-closed).")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )

    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not credentials.credentials.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = verify_oidc_token(credentials.credentials.strip(), audience=audience)
    except Exception:
        # Do not log raw tokens or expose token verification internals.
        log.warning("Rejected request with invalid or expired OIDC Bearer token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    issuer = claims.get("iss")
    subject = claims.get("sub")
    if (
        issuer not in _VALID_ISSUERS
        or not isinstance(subject, str)
        or not subject.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = claims.get("email")
    email_verified = claims.get("email_verified") is True
    verified_email = (
        email.strip().lower()
        if (isinstance(email, str) and email_verified)
        else None
    )

    allowed_emails = settings.allowed_caller_emails_set
    if allowed_emails and (
        verified_email is None or verified_email not in allowed_emails
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Caller is not authorized to access this service",
        )

    return CallerIdentity(subject=subject.strip(), email=verified_email)
