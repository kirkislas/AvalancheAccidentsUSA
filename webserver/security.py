from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Security
from custom_exceptions import InvalidAPIKeyError
from fastapi.security.api_key import APIKeyHeader
import os

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response


FAST_API_KEY = os.environ.get('PROD_FAST_API_KEY') 
API_KEY_NAME = "access_token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def api_key_auth(api_key: str = Security(api_key_header)):
    if api_key != FAST_API_KEY:
        raise InvalidAPIKeyError()
    return True  