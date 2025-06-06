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

FROM python:3.12-slim

WORKDIR /app

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy env definitions.
COPY ./pyproject.toml /app/.
COPY ./uv.lock /app/.

# Install the application dependencies.
RUN uv sync --frozen --no-cache

# Copy the application into the container.
COPY . /app

# Run the application.
CMD ["sh", "-c", ".venv/bin/fastapi run src/app/main.py --port $PORT"]