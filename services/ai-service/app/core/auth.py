# Owner: B (PIC 5) | Status: COMPLETE | Ref: SA §8.1, §8.2 (internal_caller); PRD NFR-01.05
"""Dependency autentikasi internal: header X-Internal-Token dibandingkan constant-time."""

import hmac
from typing import Annotated

from fastapi import Header

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode


# Menolak permintaan tanpa X-Internal-Token yang valid dengan 401 UNAUTHENTICATED.
def internal_caller(x_internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None) -> None:
    expected = get_settings().internal_api_token.get_secret_value()
    if not x_internal_token or not hmac.compare_digest(x_internal_token.encode("utf-8"), expected.encode("utf-8")):
        raise AppError(ErrorCode.UNAUTHENTICATED)
