"""Minimal Supabase JWT verification bridge for saved-report endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import Request
from jwt import PyJWKClient

from ..config import get_settings
from ..utils.errors import AppError

_ALLOWED_ALGORITHMS = {"RS256", "ES256"}


@dataclass(frozen=True)
class SupabasePrincipal:
    user_id: str
    access_token: str


@lru_cache(maxsize=2)
def _jwk_client(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True, lifespan=300)


def verify_supabase_access_token(token: str) -> SupabasePrincipal:
    settings = get_settings()
    if not settings.supabase_url:
        raise AppError("saved_reports_not_configured", "Saved research reports are not configured for this deployment.", 503)
    try:
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg")
        if algorithm not in _ALLOWED_ALGORITHMS:
            raise jwt.InvalidAlgorithmError("Unsupported signing algorithm")
        issuer = settings.supabase_url.rstrip("/") + "/auth/v1"
        key = _jwk_client(issuer + "/.well-known/jwks.json").get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience=settings.supabase_jwt_audience,
            issuer=issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
        if claims.get("role") != "authenticated":
            raise jwt.InvalidTokenError("Authenticated role required")
        user_id = str(UUID(str(claims["sub"])))
    except (jwt.PyJWTError, ValueError, KeyError):
        raise AppError("authentication_required", "A valid, unexpired Supabase session is required.", 401)
    return SupabasePrincipal(user_id=user_id, access_token=token)


async def require_supabase_user(request: Request) -> SupabasePrincipal:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AppError("authentication_required", "Sign in to access saved research reports.", 401)
    return verify_supabase_access_token(token.strip())
