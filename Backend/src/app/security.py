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

from collections import defaultdict, deque
import math
import threading
import time

from fastapi import Depends, HTTPException, Request, status
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.auth import CallerIdentity, get_current_caller
from app.config import get_settings

ALLOWED_HTTP_METHODS = frozenset({"GET", "POST", "HEAD", "OPTIONS"})

_SECURITY_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    (b"cache-control", b"no-store"),
    (b"referrer-policy", b"no-referrer"),
)


class SecurityHeadersAndMethodsMiddleware:
    """Enforce an HTTP method allow-list and attach defensive security headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "").upper()
        if method not in ALLOWED_HTTP_METHODS:
            response = JSONResponse(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                content={"detail": "Method not allowed"},
                headers={
                    "Allow": ", ".join(sorted(ALLOWED_HTTP_METHODS)),
                    **{k.decode(): v.decode() for k, v in _SECURITY_HEADERS},
                },
            )
            await response(scope, receive, send)
            return

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {name.lower() for name, _ in headers}
                for name, value in _SECURITY_HEADERS:
                    if name not in existing:
                        headers.append((name, value))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


class SlidingWindowRateLimiter:
    """In-memory per-key sliding-window rate limiter.

    TODO(security): For multi-instance Cloud Run autoscaling, pair this with
    distributed rate limiting at Cloud Armor / Load Balancer or a shared store
    (e.g., Memorystore Redis).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, max_requests: int, window_seconds: int) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= max_requests:
                retry_after = max(1, math.ceil(window_seconds - (now - bucket[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


_rate_limiter = SlidingWindowRateLimiter()


def reset_rate_limiter() -> None:
    """Clear in-memory rate-limiter state (intended for tests)."""
    _rate_limiter.reset()


def enforce_caller_rate_limit(
    caller: CallerIdentity = Depends(get_current_caller),
) -> None:
    """Rate limit authenticated requests per verified caller subject."""
    settings = get_settings()
    _rate_limiter.check(
        key=f"caller:{caller.subject}",
        max_requests=settings.RATE_LIMIT_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )


def enforce_ip_rate_limit(request: Request) -> None:
    """Rate limit unauthenticated probe endpoints per client host."""
    settings = get_settings()
    client_host = request.client.host if request.client else "unknown"
    _rate_limiter.check(
        key=f"ip:{client_host}",
        max_requests=settings.RATE_LIMIT_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )
