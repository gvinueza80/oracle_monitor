"""Structured logging middleware"""

import json
import logging
import uuid
from datetime import datetime

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging"""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = datetime.utcnow()

        response = await call_next(request)

        duration = (datetime.utcnow() - start_time).total_seconds()

        log_data = {
            'timestamp': start_time.isoformat(),
            'request_id': request_id,
            'method': request.method,
            'path': request.url.path,
            'status_code': response.status_code,
            'duration_seconds': duration,
            'client_ip': request.client.host if request.client else 'unknown'
        }

        logger.info(json.dumps(log_data))
        return response
