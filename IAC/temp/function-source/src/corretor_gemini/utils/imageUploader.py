# Copyright 2022 Google LLC
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

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from google.cloud import storage
import io
import re



def _download_file(real_file_id):
    try:
        # create drive api client
        service = build("drive", "v3")
        request = service.files().get_media(fileId=real_file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

    except HttpError as error:
        print(f"An error occurred: {error}")
        file = None

    return file.getvalue()


def _upload_blob(bucket, file_bytes, destination_blob_name):
    """Uploads a file to the bucket."""
    blob = bucket.blob(destination_blob_name)
    image = io.BytesIO(file_bytes)
    blob.upload_from_file(image)


def _regex_url_gdrive(url_original):
        reg_url_gdrive = (
            r"https:\/\/drive.google.com\/file\/d\/([A-Za-z0-9_.]+)\/.*"
        )
        try:
            return re.search(reg_url_gdrive, url_original).group(1)
        except:
            return None


class ImageUploader:

    def __init__(self, url_original, bucket_name='imagens-redacaopr'):
        self.url_original = url_original
        self.real_file_id = _regex_url_gdrive(self.url_original)
        if self.real_file_id is None:
            self.fail = True
            return
            
        self.url_cloudstorage = (
            f"gs://{bucket_name}/ImagensRedacao/{self.real_file_id}.png"
        )

        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

        image_exists = storage.Blob.from_string(self.url_cloudstorage).exists(
            self.client
        )
        if not image_exists:
            image = _download_file(self.real_file_id)
            _upload_blob(self.bucket, image, self.url_cloudstorage)

