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

"""Fail-closed Google Drive image fetcher and GCS stager for motivational texts.

Prevents confused-deputy exfiltration (CWE-441 / CWE-918) by requiring explicit
server-side opt-in (`DRIVE_IMAGE_FETCH_ENABLED=true`), a configured destination
bucket (`IMAGES_BUCKET_NAME`), at least one server-side Drive trust boundary
(`ALLOWED_DRIVE_FILE_IDS`, `ALLOWED_DRIVE_IDS`, `ALLOWED_DRIVE_FOLDER_IDS`, or
`ALLOWED_DRIVE_OWNER_EMAILS`), strict URL/fileId validation, metadata + magic-byte
image verification, and both pre-download and streaming byte caps.
"""

from dataclasses import dataclass, replace
import io
import logging
import os
import re
from typing import Mapping, Optional
from urllib.parse import parse_qsl, urlsplit
import uuid

log = logging.getLogger(__name__)

DEFAULT_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MiB
HARD_MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MiB hard ceiling
DEFAULT_MAX_LINKS_PER_REQUEST = 5
HARD_MAX_LINKS_PER_REQUEST = 20
_DOWNLOAD_CHUNK_SIZE = 256 * 1024  # 256 KiB

DRIVE_FILE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,128}$")
DRIVE_PATH_RE = re.compile(r"^/file/d/([A-Za-z0-9_-]{10,128})/view$")
DRIVE_SHARE_URL_RE = re.compile(
    r"https://drive\.google\.com/file/d/[A-Za-z0-9_-]{10,128}/view"
    r"(?:\?usp=(?:sharing|drive_link))?"
)
GCS_BUCKET_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]$")
SAFE_BLOB_NAME_RE = re.compile(r"^ImagensRedacao/[a-f0-9]{32}\.(png|jpg|webp)$")

ALLOWED_IMAGE_MIME_TYPES: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}
_ALLOWED_QUERY_USP_VALUES = frozenset({"sharing", "drive_link"})
_TRUTHY_VALUES = frozenset({"1", "true", "yes"})


class DriveFetchSecurityError(ValueError):
    """Raised when a Drive fetch violates server-side trust or safety boundaries."""


class _BoundedBytesIO(io.BytesIO):
    """In-memory buffer that aborts immediately if writes exceed max_bytes."""

    def __init__(self, max_bytes: int) -> None:
        super().__init__()
        self._max_bytes = max_bytes
        self._written = 0

    def write(self, b) -> int:
        chunk_len = len(memoryview(b))
        if self._written + chunk_len > self._max_bytes:
            raise DriveFetchSecurityError(
                f"Drive file download exceeded maximum allowed size ({self._max_bytes} bytes)."
            )
        written = super().write(b)
        self._written += written
        return written


def _parse_csv_set(raw: object, *, lowercase: bool = False) -> frozenset[str]:
    if raw is None:
        return frozenset()
    if isinstance(raw, (list, tuple, set, frozenset)):
        items = [str(item).strip() for item in raw]
    else:
        items = [part.strip() for part in str(raw).split(",")]
    if lowercase:
        items = [item.lower() for item in items]
    return frozenset(item for item in items if item)


def _lookup_setting(
    key: str,
    env: Mapping[str, str],
    settings_obj: Optional[object] = None,
) -> Optional[object]:
    prefixed = env.get(f"DYNACONF_{key}")
    if prefixed is not None and str(prefixed).strip() != "":
        return prefixed
    direct = env.get(key)
    if direct is not None and str(direct).strip() != "":
        return direct
    if settings_obj is not None and hasattr(settings_obj, "get"):
        val = settings_obj.get(key)
        if val is not None and str(val).strip() != "":
            return val
    return None


def _parse_strict_positive_int(
    raw: Optional[object],
    *,
    default: int,
    name: str,
) -> int:
    if raw is None or str(raw).strip() == "":
        return default
    try:
        parsed = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise DriveFetchSecurityError(f"Invalid integer configuration for '{name}'.") from exc
    if parsed <= 0:
        raise DriveFetchSecurityError(f"Configuration '{name}' must be positive.")
    return parsed


@dataclass(frozen=True)
class DriveFetchPolicy:
    """Server-side policy governing Google Drive fetches for motivational images."""

    enabled: bool = False
    bucket_name: Optional[str] = None
    allowed_file_ids: frozenset[str] = frozenset()
    allowed_drive_ids: frozenset[str] = frozenset()
    allowed_folder_ids: frozenset[str] = frozenset()
    allowed_owner_emails: frozenset[str] = frozenset()
    max_bytes: int = DEFAULT_MAX_IMAGE_BYTES
    max_links_per_request: int = DEFAULT_MAX_LINKS_PER_REQUEST

    @property
    def has_trust_boundary(self) -> bool:
        return bool(
            self.allowed_file_ids
            or self.allowed_drive_ids
            or self.allowed_folder_ids
            or self.allowed_owner_emails
        )

    @classmethod
    def from_env(
        cls,
        env: Optional[Mapping[str, str]] = None,
        settings_obj: Optional[object] = None,
    ) -> "DriveFetchPolicy":
        source_env = os.environ if env is None else env
        raw_enabled = _lookup_setting("DRIVE_IMAGE_FETCH_ENABLED", source_env, settings_obj)
        enabled = str(raw_enabled or "").strip().lower() in _TRUTHY_VALUES

        raw_bucket = _lookup_setting("IMAGES_BUCKET_NAME", source_env, settings_obj)
        bucket_name = str(raw_bucket).strip() if raw_bucket is not None else None
        if bucket_name == "":
            bucket_name = None

        max_bytes = _parse_strict_positive_int(
            _lookup_setting("DRIVE_IMAGE_MAX_BYTES", source_env, settings_obj),
            default=DEFAULT_MAX_IMAGE_BYTES,
            name="DRIVE_IMAGE_MAX_BYTES",
        )
        max_links = _parse_strict_positive_int(
            _lookup_setting("MAX_DRIVE_LINKS_PER_REQUEST", source_env, settings_obj),
            default=DEFAULT_MAX_LINKS_PER_REQUEST,
            name="MAX_DRIVE_LINKS_PER_REQUEST",
        )

        return cls(
            enabled=enabled,
            bucket_name=bucket_name,
            allowed_file_ids=_parse_csv_set(
                _lookup_setting("ALLOWED_DRIVE_FILE_IDS", source_env, settings_obj)
            ),
            allowed_drive_ids=_parse_csv_set(
                _lookup_setting("ALLOWED_DRIVE_IDS", source_env, settings_obj)
            ),
            allowed_folder_ids=_parse_csv_set(
                _lookup_setting("ALLOWED_DRIVE_FOLDER_IDS", source_env, settings_obj)
            ),
            allowed_owner_emails=_parse_csv_set(
                _lookup_setting("ALLOWED_DRIVE_OWNER_EMAILS", source_env, settings_obj),
                lowercase=True,
            ),
            max_bytes=max_bytes,
            max_links_per_request=max_links,
        )

    def validate_for_fetch(self) -> None:
        """Fail closed unless explicit opt-in, trust boundary, bucket, and caps are valid."""
        if not self.enabled:
            raise DriveFetchSecurityError(
                "Google Drive image fetching is disabled (set DRIVE_IMAGE_FETCH_ENABLED=true "
                "with explicit allowlists to enable)."
            )
        if not self.has_trust_boundary:
            raise DriveFetchSecurityError(
                "Google Drive image fetching requires at least one trust boundary allowlist "
                "(ALLOWED_DRIVE_FILE_IDS, ALLOWED_DRIVE_IDS, ALLOWED_DRIVE_FOLDER_IDS, "
                "or ALLOWED_DRIVE_OWNER_EMAILS)."
            )
        if not self.bucket_name or not GCS_BUCKET_NAME_RE.fullmatch(self.bucket_name):
            raise DriveFetchSecurityError(
                "A valid destination GCS bucket must be configured via IMAGES_BUCKET_NAME."
            )
        if not (1 <= self.max_bytes <= HARD_MAX_IMAGE_BYTES):
            raise DriveFetchSecurityError(
                f"DRIVE_IMAGE_MAX_BYTES must be between 1 and {HARD_MAX_IMAGE_BYTES}."
            )
        if not (1 <= self.max_links_per_request <= HARD_MAX_LINKS_PER_REQUEST):
            raise DriveFetchSecurityError(
                f"MAX_DRIVE_LINKS_PER_REQUEST must be between 1 and {HARD_MAX_LINKS_PER_REQUEST}."
            )


def _regex_url_gdrive(url_original: str) -> str | None:
    """Strictly parse a Google Drive file share URL and return its validated fileId."""
    if not isinstance(url_original, str) or not url_original:
        return None
    if any(ch.isspace() or ord(ch) < 32 for ch in url_original):
        return None

    parsed = urlsplit(url_original)
    if parsed.scheme.lower() != "https":
        return None
    if (parsed.hostname or "").lower() != "drive.google.com":
        return None
    if parsed.port is not None or parsed.username is not None or parsed.password is not None:
        return None
    if parsed.fragment:
        return None

    if parsed.query:
        query_items = parse_qsl(parsed.query, keep_blank_values=True)
        if len(query_items) != 1:
            return None
        key, value = query_items[0]
        if key != "usp" or value not in _ALLOWED_QUERY_USP_VALUES:
            return None

    match = DRIVE_PATH_RE.fullmatch(parsed.path)
    if not match:
        return None

    file_id = match.group(1)
    if not DRIVE_FILE_ID_RE.fullmatch(file_id):
        return None
    return file_id


def _detect_image_type(data: bytes) -> tuple[str, str] | None:
    """Inspect magic bytes to verify the payload is a supported raster image."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ("image/png", "png")
    if data.startswith(b"\xff\xd8\xff"):
        return ("image/jpeg", "jpg")
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ("image/webp", "webp")
    return None


def _verify_drive_metadata(
    service,
    real_file_id: str,
    policy: DriveFetchPolicy,
) -> tuple[str, int]:
    """Fetch and enforce ownership, driveId, folder, MIME, and size checks before download."""
    metadata = (
        service.files()
        .get(
            fileId=real_file_id,
            fields="id,mimeType,size,driveId,parents,owners(emailAddress),trashed",
            supportsAllDrives=True,
        )
        .execute()
    )
    if not isinstance(metadata, dict):
        raise DriveFetchSecurityError("Invalid Drive metadata response.")

    if metadata.get("id") != real_file_id:
        raise DriveFetchSecurityError("Drive metadata fileId mismatch.")

    if metadata.get("trashed") is True:
        raise DriveFetchSecurityError("Refusing to fetch a trashed Drive file.")

    if policy.allowed_drive_ids:
        drive_id = metadata.get("driveId")
        if not isinstance(drive_id, str) or drive_id not in policy.allowed_drive_ids:
            raise DriveFetchSecurityError("Drive file is not in an allowed Shared Drive.")

    if policy.allowed_folder_ids:
        parents = metadata.get("parents")
        if not isinstance(parents, list) or not any(
            isinstance(parent, str) and parent in policy.allowed_folder_ids
            for parent in parents
        ):
            raise DriveFetchSecurityError("Drive file is not inside an allowed parent folder.")

    if policy.allowed_owner_emails:
        owners = metadata.get("owners")
        owner_emails: set[str] = set()
        if isinstance(owners, list):
            for owner in owners:
                if isinstance(owner, dict):
                    email = owner.get("emailAddress")
                    if isinstance(email, str) and email.strip():
                        owner_emails.add(email.strip().lower())
        if not owner_emails or not owner_emails.issubset(policy.allowed_owner_emails):
            raise DriveFetchSecurityError("Drive file owner is not in ALLOWED_DRIVE_OWNER_EMAILS.")

    mime_type = str(metadata.get("mimeType") or "").strip().lower()
    if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise DriveFetchSecurityError(
            f"Unsupported Drive file MIME type '{mime_type or 'unknown'}'."
        )

    raw_size = metadata.get("size")
    try:
        declared_size = int(raw_size)
    except (TypeError, ValueError) as exc:
        raise DriveFetchSecurityError(
            "Drive file metadata is missing a valid numeric byte size."
        ) from exc

    if declared_size <= 0 or declared_size > policy.max_bytes:
        raise DriveFetchSecurityError(
            f"Drive file size ({declared_size} bytes) violates allowed cap "
            f"(1..{policy.max_bytes} bytes)."
        )

    return (mime_type, declared_size)


def _download_file(
    real_file_id: str,
    policy: DriveFetchPolicy | None = None,
    drive_service=None,
) -> tuple[bytes, str, str]:
    """Download a validated, policy-authorized Drive image with strict size and magic checks."""
    resolved_policy = policy if policy is not None else DriveFetchPolicy.from_env()
    resolved_policy.validate_for_fetch()

    if not isinstance(real_file_id, str) or not DRIVE_FILE_ID_RE.fullmatch(real_file_id):
        raise DriveFetchSecurityError("Invalid Google Drive fileId format.")

    if resolved_policy.allowed_file_ids and real_file_id not in resolved_policy.allowed_file_ids:
        raise DriveFetchSecurityError("Drive fileId is not in ALLOWED_DRIVE_FILE_IDS.")

    # Lazy-import googleapiclient only after fail-closed policy checks pass.
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaIoBaseDownload

    service = (
        drive_service
        if drive_service is not None
        else build("drive", "v3", cache_discovery=False)
    )

    try:
        declared_mime, _declared_size = _verify_drive_metadata(
            service, real_file_id, resolved_policy
        )
        request = service.files().get_media(fileId=real_file_id, supportsAllDrives=True)
        bounded_buffer = _BoundedBytesIO(max_bytes=resolved_policy.max_bytes)
        downloader = MediaIoBaseDownload(
            bounded_buffer,
            request,
            chunksize=min(_DOWNLOAD_CHUNK_SIZE, resolved_policy.max_bytes),
        )
        done = False
        while not done:
            _status, done = downloader.next_chunk()
    except DriveFetchSecurityError:
        raise
    except HttpError as exc:
        raise DriveFetchSecurityError("Google Drive API request failed.") from exc

    payload = bounded_buffer.getvalue()
    if not payload or len(payload) > resolved_policy.max_bytes:
        raise DriveFetchSecurityError("Downloaded Drive file size is outside allowed bounds.")

    detected = _detect_image_type(payload)
    if detected is None:
        raise DriveFetchSecurityError("Downloaded Drive file failed image magic-byte validation.")

    detected_mime, ext = detected
    if detected_mime != declared_mime:
        raise DriveFetchSecurityError(
            "Downloaded Drive file magic bytes do not match declared MIME type."
        )

    return (payload, detected_mime, ext)


def _upload_blob(
    bucket,
    file_bytes: bytes,
    destination_blob_name: str,
    content_type: str,
) -> None:
    """Upload validated image bytes to a safe, non-traversal GCS blob path."""
    if not SAFE_BLOB_NAME_RE.fullmatch(destination_blob_name):
        raise DriveFetchSecurityError("Unsafe destination GCS blob name.")
    if content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise DriveFetchSecurityError("Unsupported upload content type.")

    # TODO(security): Add antivirus/malware scanning and image re-encoding (CDR)
    # before staging if uploads are ever expanded beyond admin-curated Drive sources.
    blob = bucket.blob(destination_blob_name)
    blob.content_disposition = "attachment"
    blob.cache_control = "no-store"
    blob.upload_from_file(io.BytesIO(file_bytes), content_type=content_type)


class ImageUploader:
    """Policy-enforced Drive-to-GCS image stager (fail-closed by default)."""

    def __init__(
        self,
        url_original: str,
        bucket_name: str | None = None,
        policy: DriveFetchPolicy | None = None,
        drive_service=None,
        storage_client=None,
    ) -> None:
        self.url_original = url_original
        self.real_file_id: str | None = None
        self.blob_name: str | None = None
        self.url_cloudstorage: str | None = None
        self.fail = False
        self.error_reason: str | None = None

        try:
            resolved_policy = policy if policy is not None else DriveFetchPolicy.from_env()
            if bucket_name is not None and policy is None:
                resolved_policy = replace(resolved_policy, bucket_name=bucket_name.strip() or None)

            resolved_policy.validate_for_fetch()

            self.real_file_id = _regex_url_gdrive(self.url_original)
            if self.real_file_id is None:
                raise DriveFetchSecurityError("Invalid or disallowed Google Drive URL.")

            image_bytes, detected_mime, ext = _download_file(
                self.real_file_id,
                policy=resolved_policy,
                drive_service=drive_service,
            )

            self.blob_name = f"ImagensRedacao/{uuid.uuid4().hex}.{ext}"
            self.url_cloudstorage = f"gs://{resolved_policy.bucket_name}/{self.blob_name}"

            if storage_client is None:
                from google.cloud import storage

                client = storage.Client()
            else:
                client = storage_client

            self.client = client
            self.bucket = client.bucket(resolved_policy.bucket_name)
            _upload_blob(self.bucket, image_bytes, self.blob_name, content_type=detected_mime)
        except DriveFetchSecurityError as exc:
            self.fail = True
            self.error_reason = str(exc)
            self.blob_name = None
            self.url_cloudstorage = None
            log.warning("Rejected Google Drive image fetch: %s", exc)
        except Exception as exc:
            self.fail = True
            self.error_reason = "Unexpected error during Google Drive image fetch."
            self.blob_name = None
            self.url_cloudstorage = None
            log.warning("Failed Google Drive image fetch: %s", type(exc).__name__)


def rewrite_motivator_drive_links(
    textos_motivadores: str,
    policy: DriveFetchPolicy | None = None,
    drive_service=None,
    storage_client=None,
) -> str:
    """Safely rewrite allowlisted Drive image URLs in TextosMotivadores to GCS URIs.

    Fail-closed by default: when Drive fetching is disabled or lacks a valid trust
    boundary, returns the input text untouched without invoking Drive or GCS APIs.
    """
    if not isinstance(textos_motivadores, str) or not textos_motivadores:
        return "" if textos_motivadores is None else textos_motivadores

    try:
        resolved_policy = policy if policy is not None else DriveFetchPolicy.from_env()
        if not resolved_policy.enabled:
            return textos_motivadores
        resolved_policy.validate_for_fetch()
    except DriveFetchSecurityError as exc:
        log.warning("Skipping Google Drive image staging: %s", exc)
        return textos_motivadores

    raw_links = DRIVE_SHARE_URL_RE.findall(textos_motivadores)
    if not raw_links:
        return textos_motivadores

    unique_links = list(dict.fromkeys(raw_links))
    if len(unique_links) > resolved_policy.max_links_per_request:
        log.warning(
            "Truncating Drive links in TextosMotivadores from %d to max %d.",
            len(unique_links),
            resolved_policy.max_links_per_request,
        )
        unique_links = unique_links[: resolved_policy.max_links_per_request]

    texto_adaptado = textos_motivadores
    for link in unique_links:
        img = ImageUploader(
            link,
            policy=resolved_policy,
            drive_service=drive_service,
            storage_client=storage_client,
        )
        if not img.fail and img.url_cloudstorage:
            texto_adaptado = texto_adaptado.replace(img.url_original, img.url_cloudstorage)

    return texto_adaptado
