from dataclasses import dataclass
from hmac import compare_digest
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import settings


@dataclass(frozen=True)
class InternalAuthContext:
    user_id: str
    auth_mode: str


def get_internal_auth_context(
    x_service_token: Annotated[str | None, Header(alias="X-Service-Token")] = None,
    x_authenticated_user_id: Annotated[
        str | None,
        Header(alias="X-Authenticated-User-Id"),
    ] = None,
    x_dev_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> InternalAuthContext:
    """
    Production path:
    - Spring Boot sends X-Service-Token
    - Spring Boot sends X-Authenticated-User-Id

    Local dev path:
    - X-User-Id is allowed only when APP_ENV=local and ALLOW_DEV_USER_HEADER=true
    """

    if (
        settings.app_env == "local"
        and settings.allow_dev_user_header
        and x_dev_user_id
        and not x_service_token
    ):
        return InternalAuthContext(
            user_id=x_dev_user_id,
            auth_mode="local_dev_header",
        )

    if not settings.agent_service_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent service token is not configured.",
        )

    if not x_service_token or not compare_digest(
        x_service_token,
        settings.agent_service_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal service token.",
        )

    if not x_authenticated_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authenticated user ID.",
        )

    return InternalAuthContext(
        user_id=x_authenticated_user_id,
        auth_mode="internal_service_token",
    )