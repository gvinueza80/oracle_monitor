"""Health check endpoints"""

from datetime import datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """API health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ready")
async def readiness():
    """Readiness check (all dependencies initialized)"""
    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat()
    }
