"""Authentication and authorization middleware"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT token validation and RBAC"""

    async def dispatch(self, request: Request, call_next):
        # Token validation logic will be implemented
        # For now, pass through
        response = await call_next(request)
        return response
