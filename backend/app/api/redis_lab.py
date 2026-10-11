from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..config import get_settings
from ..redis_bridge import RedisBridgeError, execute_command, get_status

router = APIRouter(prefix="/redis", tags=["Redis Lab"])


class RedisCommandIn(BaseModel):
    command: list[str] = Field(min_length=1, max_length=3)


@router.get("/status")
def status():
    """Report whether the optional custom Java Redis service is reachable."""
    return get_status(get_settings())


@router.post("/command")
def command(payload: RedisCommandIn):
    """Run one allowlisted demonstration command against the custom Redis server."""
    settings = get_settings()
    try:
        normalized = payload.command
        result = execute_command(settings, normalized)
        return {
            "enabled": settings.redis_enabled,
            "ok": True,
            "command": normalized[0].upper(),
            "reply": result,
        }
    except RedisBridgeError as exc:
        return {
            "enabled": settings.redis_enabled,
            "ok": False,
            "command": payload.command[0].upper() if payload.command else "",
            "error": str(exc),
        }
