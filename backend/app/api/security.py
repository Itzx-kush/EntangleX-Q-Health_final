import secrets
from fastapi import Request
from ..config import get_settings
from ..utils.errors import AppError

async def authorize(request: Request) -> None:
    settings = get_settings()
    origin = request.headers.get("origin")
    if origin is not None and origin not in [x.strip() for x in settings.cors_origins.split(",")]:
        # CORS alone does not prevent simple cross-origin write requests.
        raise AppError("origin_not_allowed", "This request origin is not allowed.", 403)
    if settings.api_token:
        supplied = request.headers.get("authorization", "")
        expected = f"Bearer {settings.api_token}"
        if not secrets.compare_digest(supplied.encode(), expected.encode()):
            raise AppError("authentication_required", "A valid local API bearer token is required.", 401)
