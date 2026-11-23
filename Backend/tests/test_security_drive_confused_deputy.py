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

"""Regression guards for CWE-441/CWE-918 confused-deputy Google Drive fetch in Cloud Function."""

from __future__ import annotations

import importlib.util
import os
import pathlib
import re
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FUNCTION_DIR = REPO_ROOT / "IAC" / "temp" / "function-source"
FUNCTION_MAIN_PATH = FUNCTION_DIR / "main.py"
IMAGE_UPLOADER_PATH = (
    FUNCTION_DIR / "src" / "corretor_gemini" / "utils" / "imageUploader.py"
)

VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 64
VALID_WEBP_BYTES = b"RIFF\x24\x00\x00\x00WEBP" + b"\x00" * 32


def _load_image_uploader_module():
    spec = importlib.util.spec_from_file_location(
        "image_uploader_under_test", IMAGE_UPLOADER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _FakeBlob:
    def __init__(self, bucket_name: str, name: str, uploads: list[dict]) -> None:
        self.bucket_name = bucket_name
        self.name = name
        self.content_disposition: str | None = None
        self.cache_control: str | None = None
        self._uploads = uploads

    def upload_from_file(self, file_obj, content_type: str | None = None) -> None:
        self._uploads.append(
            {
                "bucket": self.bucket_name,
                "blob_name": self.name,
                "content_type": content_type,
                "content_disposition": self.content_disposition,
                "cache_control": self.cache_control,
                "data": file_obj.getvalue(),
            }
        )


class _FakeBucket:
    def __init__(self, name: str, uploads: list[dict]) -> None:
        self.name = name
        self._uploads = uploads

    def blob(self, name: str) -> _FakeBlob:
        return _FakeBlob(self.name, name, self._uploads)


class _FakeStorageClient:
    def __init__(self) -> None:
        self.uploads: list[dict] = []
        self.buckets_accessed: list[str] = []

    def bucket(self, name: str) -> _FakeBucket:
        self.buckets_accessed.append(name)
        return _FakeBucket(name, self.uploads)


def _build_fake_drive_stubs(
    metadata_by_id: dict[str, dict],
    chunks_by_id: dict[str, list[bytes]],
):
    """Build mocked googleapiclient modules + Drive v3 service recording every API call."""

    class FakeHttpError(Exception):
        pass

    get_calls: list[dict] = []
    get_media_calls: list[dict] = []

    class FakeMediaIoBaseDownload:
        def __init__(self, fh, request, chunksize=None) -> None:
            self._fh = fh
            self._chunks = list(chunks_by_id[request["fileId"]])
            self._idx = 0
            self.chunksize = chunksize

        def next_chunk(self):
            if self._idx < len(self._chunks):
                self._fh.write(self._chunks[self._idx])
                self._idx += 1
            return None, self._idx >= len(self._chunks)

    files_resource = MagicMock()

    def _fake_get(**kwargs):
        get_calls.append(kwargs)
        req = MagicMock()
        file_id = kwargs["fileId"]
        if file_id not in metadata_by_id:
            req.execute.side_effect = FakeHttpError("not found")
        else:
            req.execute.return_value = metadata_by_id[file_id]
        return req

    def _fake_get_media(**kwargs):
        get_media_calls.append(kwargs)
        return {"fileId": kwargs["fileId"]}

    files_resource.get.side_effect = _fake_get
    files_resource.get_media.side_effect = _fake_get_media

    drive_service = MagicMock()
    drive_service.files.return_value = files_resource

    fake_build = MagicMock(return_value=drive_service)

    fake_discovery = types.ModuleType("googleapiclient.discovery")
    fake_discovery.build = fake_build
    fake_errors = types.ModuleType("googleapiclient.errors")
    fake_errors.HttpError = FakeHttpError
    fake_http = types.ModuleType("googleapiclient.http")
    fake_http.MediaIoBaseDownload = FakeMediaIoBaseDownload

    stubs = {
        "googleapiclient": types.ModuleType("googleapiclient"),
        "googleapiclient.discovery": fake_discovery,
        "googleapiclient.errors": fake_errors,
        "googleapiclient.http": fake_http,
    }
    return stubs, drive_service, fake_build, get_calls, get_media_calls


class DriveConfusedDeputySecurityTests(unittest.TestCase):
    """Ensure untrusted TextosMotivadores URLs cannot abuse the Function's SA Drive access."""

    def setUp(self) -> None:
        self.mod = _load_image_uploader_module()

    def test_fail_closed_by_default_makes_zero_drive_or_gcs_calls(self) -> None:
        attacker_id = "1VictimSecretFileId_123456"
        attacker_url = f"https://drive.google.com/file/d/{attacker_id}/view?usp=sharing"
        stubs, _svc, fake_build, get_calls, get_media_calls = _build_fake_drive_stubs(
            metadata_by_id={
                attacker_id: {
                    "id": attacker_id,
                    "mimeType": "image/png",
                    "size": str(len(VALID_PNG_BYTES)),
                    "trashed": False,
                }
            },
            chunks_by_id={attacker_id: [VALID_PNG_BYTES]},
        )
        storage_client = _FakeStorageClient()

        with patch.dict(os.environ, {}, clear=True), patch.dict(sys.modules, stubs):
            uploader = self.mod.ImageUploader(attacker_url, storage_client=storage_client)
            rewritten = self.mod.rewrite_motivator_drive_links(
                f"Texto motivador {attacker_url}",
                storage_client=storage_client,
            )

        self.assertTrue(uploader.fail)
        self.assertIsNone(uploader.url_cloudstorage)
        self.assertEqual(rewritten, f"Texto motivador {attacker_url}")
        fake_build.assert_not_called()
        self.assertEqual(get_calls, [])
        self.assertEqual(get_media_calls, [])
        self.assertEqual(storage_client.uploads, [])

    def test_enabled_without_any_allowlist_fails_closed(self) -> None:
        attacker_id = "1VictimSecretFileId_123456"
        attacker_url = f"https://drive.google.com/file/d/{attacker_id}/view?usp=sharing"
        stubs, drive_service, fake_build, get_calls, get_media_calls = _build_fake_drive_stubs(
            metadata_by_id={},
            chunks_by_id={},
        )
        storage_client = _FakeStorageClient()

        env = {
            "DRIVE_IMAGE_FETCH_ENABLED": "true",
            "IMAGES_BUCKET_NAME": "trusted-essai-bucket",
        }
        with patch.dict(os.environ, env, clear=True), patch.dict(sys.modules, stubs):
            uploader = self.mod.ImageUploader(
                attacker_url,
                drive_service=drive_service,
                storage_client=storage_client,
            )

        self.assertTrue(uploader.fail)
        self.assertIn("allowlist", uploader.error_reason or "")
        fake_build.assert_not_called()
        self.assertEqual(get_calls, [])
        self.assertEqual(get_media_calls, [])
        self.assertEqual(storage_client.uploads, [])

    def test_enabled_without_configured_bucket_fails_closed(self) -> None:
        file_id = "1AllowedImageFileId_123456"
        url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        stubs, drive_service, _fake_build, get_calls, get_media_calls = _build_fake_drive_stubs(
            metadata_by_id={},
            chunks_by_id={},
        )
        storage_client = _FakeStorageClient()

        env = {
            "DRIVE_IMAGE_FETCH_ENABLED": "true",
            "ALLOWED_DRIVE_FILE_IDS": file_id,
        }
        with patch.dict(os.environ, env, clear=True), patch.dict(sys.modules, stubs):
            uploader = self.mod.ImageUploader(
                url,
                drive_service=drive_service,
                storage_client=storage_client,
            )

        self.assertTrue(uploader.fail)
        self.assertIn("IMAGES_BUCKET_NAME", uploader.error_reason or "")
        self.assertEqual(get_calls, [])
        self.assertEqual(get_media_calls, [])
        self.assertEqual(storage_client.uploads, [])

    def test_non_allowlisted_file_id_blocked_before_drive_api_call(self) -> None:
        allowed_id = "1AllowedCuratedImg_000001"
        victim_id = "1ConfidentialHRDoc_999999"
        victim_url = f"https://drive.google.com/file/d/{victim_id}/view?usp=sharing"
        stubs, drive_service, fake_build, get_calls, get_media_calls = _build_fake_drive_stubs(
            metadata_by_id={
                victim_id: {
                    "id": victim_id,
                    "mimeType": "image/png",
                    "size": str(len(VALID_PNG_BYTES)),
                    "trashed": False,
                }
            },
            chunks_by_id={victim_id: [VALID_PNG_BYTES]},
        )
        storage_client = _FakeStorageClient()

        env = {
            "DRIVE_IMAGE_FETCH_ENABLED": "true",
            "IMAGES_BUCKET_NAME": "trusted-essai-bucket",
            "ALLOWED_DRIVE_FILE_IDS": allowed_id,
        }
        with patch.dict(os.environ, env, clear=True), patch.dict(sys.modules, stubs):
            uploader = self.mod.ImageUploader(
                victim_url,
                drive_service=drive_service,
                storage_client=storage_client,
            )

        self.assertTrue(uploader.fail)
        fake_build.assert_not_called()
        self.assertEqual(get_calls, [])
        self.assertEqual(get_media_calls, [])
        self.assertEqual(storage_client.uploads, [])

    def test_unauthorized_drive_id_folder_owner_and_trashed_blocked_before_download(
        self,
    ) -> None:
        file_id = "1CandidateDriveFile_12345"
        url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

        cases = [
            (
                "wrong_drive_id",
                {"ALLOWED_DRIVE_IDS": "0AAllowedSharedDrive"},
                {
                    "id": file_id,
                    "mimeType": "image/png",
                    "size": str(len(VALID_PNG_BYTES)),
                    "driveId": "0AOthersPrivateDrive",
                    "trashed": False,
                },
            ),
            (
                "wrong_parent_folder",
                {"ALLOWED_DRIVE_FOLDER_IDS": "1AllowedFolder_001"},
                {
                    "id": file_id,
                    "mimeType": "image/png",
                    "size": str(len(VALID_PNG_BYTES)),
                    "parents": ["1SecretFolder_999"],
                    "trashed": False,
                },
            ),
            (
                "wrong_owner",
                {"ALLOWED_DRIVE_OWNER_EMAILS": "curriculum@school.edu.br"},
                {
                    "id": file_id,
                    "mimeType": "image/png",
                    "size": str(len(VALID_PNG_BYTES)),
                    "owners": [{"emailAddress": "attacker@evil.example"}],
                    "trashed": False,
                },
            ),
            (
                "mixed_trusted_and_untrusted_co_owner",
                {"ALLOWED_DRIVE_OWNER_EMAILS": "curriculum@school.edu.br"},
                {
                    "id": file_id,
                    "mimeType": "image/png",
                    "size": str(len(VALID_PNG_BYTES)),
                    "owners": [
                        {"emailAddress": "curriculum@school.edu.br"},
                        {"emailAddress": "external@evil.example"},
                    ],
                    "trashed": False,
                },
            ),
            (
                "conjunctive_drive_and_folder_partial_match_rejected",
                {
                    "ALLOWED_DRIVE_IDS": "0AAllowedSharedDrive",
                    "ALLOWED_DRIVE_FOLDER_IDS": "1AllowedFolder_001",
                },
                {
                    "id": file_id,
                    "mimeType": "image/png",
                    "size": str(len(VALID_PNG_BYTES)),
                    "driveId": "0AAllowedSharedDrive",
                    "parents": ["1DifferentFolder_002"],
                    "trashed": False,
                },
            ),
            (
                "trashed_file_rejected",
                {"ALLOWED_DRIVE_IDS": "0AAllowedSharedDrive"},
                {
                    "id": file_id,
                    "mimeType": "image/png",
                    "size": str(len(VALID_PNG_BYTES)),
                    "driveId": "0AAllowedSharedDrive",
                    "trashed": True,
                },
            ),
        ]

        for label, extra_env, meta in cases:
            with self.subTest(case=label):
                stubs, drive_service, _fb, get_calls, get_media_calls = (
                    _build_fake_drive_stubs(
                        metadata_by_id={file_id: meta},
                        chunks_by_id={file_id: [VALID_PNG_BYTES]},
                    )
                )
                storage_client = _FakeStorageClient()
                env = {
                    "DRIVE_IMAGE_FETCH_ENABLED": "true",
                    "IMAGES_BUCKET_NAME": "trusted-essai-bucket",
                    **extra_env,
                }
                with patch.dict(os.environ, env, clear=True), patch.dict(
                    sys.modules, stubs
                ):
                    uploader = self.mod.ImageUploader(
                        url,
                        drive_service=drive_service,
                        storage_client=storage_client,
                    )

                self.assertTrue(uploader.fail, msg=f"Expected rejection for {label}")
                self.assertEqual(len(get_calls), 1)
                self.assertEqual(
                    get_media_calls,
                    [],
                    msg=f"get_media must not be called for rejected case {label}",
                )
                self.assertEqual(storage_client.uploads, [])

    def test_size_caps_enforced_before_and_during_streaming_download(self) -> None:
        file_id = "1OversizedImageFile_12345"
        url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        base_env = {
            "DRIVE_IMAGE_FETCH_ENABLED": "true",
            "IMAGES_BUCKET_NAME": "trusted-essai-bucket",
            "ALLOWED_DRIVE_FILE_IDS": file_id,
            "DRIVE_IMAGE_MAX_BYTES": "128",
        }

        # 1) Metadata declares size > max_bytes -> blocked BEFORE get_media
        stubs, drive_service, _fb, _gets, get_media_calls = _build_fake_drive_stubs(
            metadata_by_id={
                file_id: {
                    "id": file_id,
                    "mimeType": "image/png",
                    "size": "999999",
                    "trashed": False,
                }
            },
            chunks_by_id={file_id: [VALID_PNG_BYTES]},
        )
        storage_client = _FakeStorageClient()
        with patch.dict(os.environ, base_env, clear=True), patch.dict(sys.modules, stubs):
            uploader = self.mod.ImageUploader(
                url, drive_service=drive_service, storage_client=storage_client
            )
        self.assertTrue(uploader.fail)
        self.assertEqual(get_media_calls, [])
        self.assertEqual(storage_client.uploads, [])

        # 2) Metadata lies (says 64 bytes), stream sends > 128 bytes -> aborted mid-stream
        stubs2, drive_service2, _fb2, _gets2, get_media_calls2 = _build_fake_drive_stubs(
            metadata_by_id={
                file_id: {
                    "id": file_id,
                    "mimeType": "image/png",
                    "size": "64",
                    "trashed": False,
                }
            },
            chunks_by_id={file_id: [VALID_PNG_BYTES, b"\x00" * 200]},
        )
        storage_client2 = _FakeStorageClient()
        with patch.dict(os.environ, base_env, clear=True), patch.dict(sys.modules, stubs2):
            uploader2 = self.mod.ImageUploader(
                url, drive_service=drive_service2, storage_client=storage_client2
            )
        self.assertTrue(uploader2.fail)
        self.assertEqual(len(get_media_calls2), 1)
        self.assertEqual(storage_client2.uploads, [])

        # 3) Configured DRIVE_IMAGE_MAX_BYTES above hard 10 MiB ceiling -> fails closed
        over_cap_env = {**base_env, "DRIVE_IMAGE_MAX_BYTES": str(20 * 1024 * 1024)}
        with patch.dict(os.environ, over_cap_env, clear=True), patch.dict(
            sys.modules, stubs
        ):
            uploader3 = self.mod.ImageUploader(
                url, drive_service=drive_service, storage_client=storage_client
            )
        self.assertTrue(uploader3.fail)

    def test_non_image_mime_and_spoofed_magic_bytes_are_rejected(self) -> None:
        file_id = "1SpoofedSecretFile_123456"
        url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        env = {
            "DRIVE_IMAGE_FETCH_ENABLED": "true",
            "IMAGES_BUCKET_NAME": "trusted-essai-bucket",
            "ALLOWED_DRIVE_FILE_IDS": file_id,
        }

        # 1) Non-image MIME (JSON/SVG/shortcut) rejected before get_media
        for bad_mime in (
            "application/json",
            "text/plain",
            "image/svg+xml",
            "application/vnd.google-apps.shortcut",
        ):
            with self.subTest(mime=bad_mime):
                stubs, drive_service, _fb, _gets, get_media_calls = (
                    _build_fake_drive_stubs(
                        metadata_by_id={
                            file_id: {
                                "id": file_id,
                                "mimeType": bad_mime,
                                "size": "64",
                                "trashed": False,
                            }
                        },
                        chunks_by_id={file_id: [b'{"secret": "value"}']},
                    )
                )
                storage_client = _FakeStorageClient()
                with patch.dict(os.environ, env, clear=True), patch.dict(
                    sys.modules, stubs
                ):
                    uploader = self.mod.ImageUploader(
                        url, drive_service=drive_service, storage_client=storage_client
                    )
                self.assertTrue(uploader.fail)
                self.assertEqual(get_media_calls, [])
                self.assertEqual(storage_client.uploads, [])

        # 2) Spoofed MIME (declared image/png, actual secret JSON bytes) rejected before GCS upload
        stubs_spoof, drive_service_spoof, _fb, _gets, _media = _build_fake_drive_stubs(
            metadata_by_id={
                file_id: {
                    "id": file_id,
                    "mimeType": "image/png",
                    "size": "48",
                    "trashed": False,
                }
            },
            chunks_by_id={file_id: [b'{"type":"service_account","private_key":"nope"}']},
        )
        storage_client = _FakeStorageClient()
        with patch.dict(os.environ, env, clear=True), patch.dict(
            sys.modules, stubs_spoof
        ):
            uploader = self.mod.ImageUploader(
                url, drive_service=drive_service_spoof, storage_client=storage_client
            )
        self.assertTrue(uploader.fail)
        self.assertEqual(storage_client.uploads, [])

    def test_strict_drive_url_parser_rejects_spoofed_hosts_and_traversal(self) -> None:
        bad_urls = [
            "https://driveXgoogleYcom/file/d/1234567890abcdef/view?usp=sharing",
            "http://drive.google.com/file/d/1234567890abcdef/view?usp=sharing",
            "https://evil.drive.google.com/file/d/1234567890abcdef/view?usp=sharing",
            "https://drive.google.com@evil.com/file/d/1234567890abcdef/view?usp=sharing",
            "https://drive.google.com:8443/file/d/1234567890abcdef/view?usp=sharing",
            "https://drive.google.com/file/d/../view?usp=sharing",
            "https://drive.google.com/file/d/123456..7890abcd/view?usp=sharing",
            "https://drive.google.com/file/d/short/view?usp=sharing",
            "https://drive.google.com/file/d/1234567890abcdef/view?usp=sharing&evil=1",
            "https://drive.google.com/file/d/1234567890abcdef/view#frag",
        ]
        for bad_url in bad_urls:
            with self.subTest(url=bad_url):
                self.assertIsNone(self.mod._regex_url_gdrive(bad_url))

        valid_id = "1U2nm8F0U77wgSLFJTQ-rA3x8rxZr40Gm"
        self.assertEqual(
            self.mod._regex_url_gdrive(
                f"https://drive.google.com/file/d/{valid_id}/view?usp=sharing"
            ),
            valid_id,
        )

    def test_allowlisted_valid_image_stages_safely_and_rewrites_text(self) -> None:
        file_id = "1AllowedCuratedImg_000001"
        url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        stubs, drive_service, _fb, get_calls, get_media_calls = _build_fake_drive_stubs(
            metadata_by_id={
                file_id: {
                    "id": file_id,
                    "mimeType": "image/png",
                    "size": str(len(VALID_PNG_BYTES)),
                    "driveId": "0AAllowedSharedDrive",
                    "parents": ["1AllowedFolder_001"],
                    "owners": [{"emailAddress": "curriculum@school.edu.br"}],
                    "trashed": False,
                }
            },
            chunks_by_id={file_id: [VALID_PNG_BYTES]},
        )
        storage_client = _FakeStorageClient()
        env = {
            "DRIVE_IMAGE_FETCH_ENABLED": "true",
            "IMAGES_BUCKET_NAME": "trusted-essai-bucket",
            "ALLOWED_DRIVE_FILE_IDS": file_id,
            "ALLOWED_DRIVE_IDS": "0AAllowedSharedDrive",
            "ALLOWED_DRIVE_FOLDER_IDS": "1AllowedFolder_001",
            "ALLOWED_DRIVE_OWNER_EMAILS": "Curriculum@School.Edu.Br",
        }
        source_text = f"Veja o grafico: {url} e compare com {url}"

        with patch.dict(os.environ, env, clear=True), patch.dict(sys.modules, stubs):
            rewritten = self.mod.rewrite_motivator_drive_links(
                source_text,
                drive_service=drive_service,
                storage_client=storage_client,
            )

        self.assertEqual(len(get_calls), 1)
        self.assertEqual(len(get_media_calls), 1)
        self.assertEqual(len(storage_client.uploads), 1)

        upload = storage_client.uploads[0]
        self.assertEqual(upload["bucket"], "trusted-essai-bucket")
        self.assertRegex(upload["blob_name"], r"^ImagensRedacao/[a-f0-9]{32}\.png$")
        self.assertNotIn(file_id, upload["blob_name"])
        self.assertNotIn("gs://", upload["blob_name"])
        self.assertEqual(upload["content_type"], "image/png")
        self.assertEqual(upload["content_disposition"], "attachment")
        self.assertEqual(upload["cache_control"], "no-store")
        self.assertEqual(upload["data"], VALID_PNG_BYTES)

        expected_uri = f"gs://trusted-essai-bucket/{upload['blob_name']}"
        self.assertEqual(rewritten, f"Veja o grafico: {expected_uri} e compare com {expected_uri}")

    def test_link_count_cap_prevents_multi_link_flooding(self) -> None:
        ids = [f"1AllowedImgCapTest_0000{i}" for i in range(5)]
        urls = [f"https://drive.google.com/file/d/{fid}/view?usp=sharing" for fid in ids]
        meta = {
            fid: {
                "id": fid,
                "mimeType": "image/jpeg",
                "size": str(len(VALID_JPEG_BYTES)),
                "trashed": False,
            }
            for fid in ids
        }
        chunks = {fid: [VALID_JPEG_BYTES] for fid in ids}
        stubs, drive_service, _fb, _gets, get_media_calls = _build_fake_drive_stubs(
            metadata_by_id=meta, chunks_by_id=chunks
        )
        storage_client = _FakeStorageClient()
        env = {
            "DRIVE_IMAGE_FETCH_ENABLED": "true",
            "IMAGES_BUCKET_NAME": "trusted-essai-bucket",
            "ALLOWED_DRIVE_FILE_IDS": ",".join(ids),
            "MAX_DRIVE_LINKS_PER_REQUEST": "2",
        }
        with patch.dict(os.environ, env, clear=True), patch.dict(sys.modules, stubs):
            rewritten = self.mod.rewrite_motivator_drive_links(
                " ".join(urls),
                drive_service=drive_service,
                storage_client=storage_client,
            )

        self.assertEqual(len(get_media_calls), 2)
        self.assertEqual(len(storage_client.uploads), 2)
        # First two replaced, remaining three untouched
        self.assertNotIn(urls[0], rewritten)
        self.assertNotIn(urls[1], rewritten)
        self.assertIn(urls[2], rewritten)

    def test_static_guards_no_hardcoded_bucket_and_main_uses_safe_helper(self) -> None:
        uploader_src = IMAGE_UPLOADER_PATH.read_text(encoding="utf-8")
        main_src = FUNCTION_MAIN_PATH.read_text(encoding="utf-8")

        self.assertNotIn("imagens-redacaopr", uploader_src)
        self.assertIn("rewrite_motivator_drive_links", main_src)
        self.assertIsNone(
            re.search(r"\bImageUploader\s*\(", main_src),
            "Cloud Function main.py must delegate to rewrite_motivator_drive_links, not call ImageUploader() directly.",
        )


if __name__ == "__main__":
    unittest.main()
