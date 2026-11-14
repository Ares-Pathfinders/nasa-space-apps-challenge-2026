from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["System"])

@router.get("/health")
async def health_check():
    return {
        "status": "operational",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "subsystems": {
            "api": "healthy",
            "pathfinding_engine": "online",
            "telemetry_proxy": "online"
        }
    }
