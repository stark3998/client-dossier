# backend/app/api/auth.py
import logging
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings

logger = logging.getLogger(__name__)

LOCAL_USER = {
    "oid": "local-dev-user",
    "upn": "dev@localhost",
    "name": "Local Developer",
    "tid": "local-tenant",
    "roles": ["admin"],
}

UNPROTECTED_PATHS = {"/health", "/ready", "/docs", "/redoc", "/openapi.json"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in UNPROTECTED_PATHS or path.startswith("/docs"):
            return await call_next(request)

        settings = get_settings()

        if settings.LOCAL_MODE or settings.BYPASS_AUTH:
            request.state.user = LOCAL_USER
            return await call_next(request)

        # Production: validate JWT
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            # Check query param for WebSocket
            token = request.query_params.get("token", "")
            if not token:
                return JSONResponse(status_code=401, content={"detail": "Missing authorization"})
        else:
            token = auth_header[7:]

        user = await _validate_token(token, settings)
        if user is None:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        request.state.user = user
        response = await call_next(request)
        if user.get("token_v1"):
            response.headers["X-Token-Version"] = "1"
        return response


async def _validate_token(token: str, settings) -> Optional[dict]:
    try:
        import jwt
        from jwt import PyJWKClient

        jwks_url = f"https://login.microsoftonline.com/{settings.ENTRA_TENANT_ID}/discovery/v2.0/keys"
        jwk_client = PyJWKClient(jwks_url)
        signing_key = jwk_client.get_signing_key_from_jwt(token)

        # v2.0 tokens: aud = plain GUID; v1.0 tokens: aud = api://<guid>
        valid_audiences = [
            settings.ENTRA_CLIENT_ID,
            f"api://{settings.ENTRA_CLIENT_ID}",
        ]
        # v2.0 issuer vs v1.0 issuer (sts.windows.net)
        valid_issuers = {
            f"https://login.microsoftonline.com/{settings.ENTRA_TENANT_ID}/v2.0",
            f"https://sts.windows.net/{settings.ENTRA_TENANT_ID}/",
        }

        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=valid_audiences,
            options={"verify_iss": False},
        )

        iss = decoded.get("iss", "")
        if iss not in valid_issuers:
            logger.warning("Token issuer not accepted: %s", iss)
            return None

        is_v1 = decoded.get("ver", "2.0") == "1.0" or "sts.windows.net" in iss

        return {
            "oid": decoded.get("oid", ""),
            "upn": decoded.get("preferred_username", decoded.get("upn", "")),
            "name": decoded.get("name", ""),
            "tid": decoded.get("tid", ""),
            "roles": decoded.get("roles", []),
            "token_v1": is_v1,
        }
    except Exception as e:
        logger.warning("Token validation failed: %s", e)
        return None
