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

import logging

from google.cloud import pubsub_v1

from app.config import get_settings
from app import schemas


log = logging.getLogger("uvicorn")

_publisher: pubsub_v1.PublisherClient | None = None


def get_publisher() -> pubsub_v1.PublisherClient:
    global _publisher
    if _publisher is None:
        _publisher = pubsub_v1.PublisherClient()
    return _publisher


def submit_to_queue(data: schemas.InProgress) -> None:
    """create entry on pubsub topic"""
    topic = get_settings().PUBSUB_TOPIC_NAME
    log.info(f"publishing id '{data.id}'")
    get_publisher().publish(
        topic=topic,
        data=str(data.id).encode("utf-8"),
    )

