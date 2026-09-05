from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Used by the Docker Compose healthcheck (NFR-05, ADR-0007)."""
    return {"status": "ok"}
