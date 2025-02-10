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

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import tags_metadata, SUMMARY
from app.routes import router
from app.database import create_db_and_tables


@asynccontextmanager
async def server_lifespan(app: FastAPI):
    """setup and cleanup function"""
    # create_db_and_tables()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=server_lifespan,
        title="""EssAI""",
        summary=SUMMARY,
        openapi_tags=tags_metadata,
    )

    app.include_router(router)

    return app
