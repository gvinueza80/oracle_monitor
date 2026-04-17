"""
FastAPI application entry point for Oracle Monitoring System
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest

from app.config import settings
from app.middleware import auth, logging as log_middleware
from app.routers import metrics, alerts, instances, users, health

logger = logging.getLogger(__name__)

# Prometheus metrics
request_count = Counter(
    'api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status']
)

request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['endpoint', 'method']
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    logger.info("Oracle Monitor API starting")
    yield
    logger.info("Oracle Monitor API shutting down")


app = FastAPI(
    title="Oracle Database Monitoring API",
    description="Real-time Oracle database monitoring and alerting system",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(log_middleware.StructuredLoggingMiddleware)
app.add_middleware(auth.AuthenticationMiddleware)


@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(
        f"Unhandled exception",
        exc_info=exc,
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": 500
        }
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": getattr(request.state, 'request_id', 'unknown')
        }
    )


# Include routers
app.include_router(
    health.router,
    prefix="/api",
    tags=["Health"]
)

app.include_router(
    metrics.router,
    prefix="/api/metrics",
    tags=["Metrics"]
)

app.include_router(
    alerts.router,
    prefix="/api/alerts",
    tags=["Alerts"]
)

app.include_router(
    instances.router,
    prefix="/api/instances",
    tags=["Instances"]
)

app.include_router(
    users.router,
    prefix="/api/users",
    tags=["Users"]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
