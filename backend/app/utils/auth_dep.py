from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId
from bson.errors import InvalidId
from app.database import get_db
from app.services.auth_service import decode_access_token
from app.utils.security import AUTH_COOKIE_NAME, CSRF_HEADER_NAME

security = HTTPBearer(auto_error=False)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    token = None
    from_cookie = False

    # 1. Check Bearer token in header
    if auth_header and auth_header.credentials:
        token = auth_header.credentials
    # 2. Check cookie if header not present
    elif AUTH_COOKIE_NAME in request.cookies:
        token = request.cookies.get(AUTH_COOKIE_NAME)
        from_cookie = True

    if not token:
        raise _unauthorized("Authentication credentials not provided")

    # Cookies are attached by the browser automatically, so state-changing requests
    # authenticated by cookie must prove they came from our own frontend.
    if from_cookie and request.method not in SAFE_METHODS and not request.headers.get(CSRF_HEADER_NAME):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing CSRF protection header",
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise _unauthorized("Invalid or expired authentication token")

    try:
        user_obj_id = ObjectId(payload["sub"])
    except (InvalidId, TypeError):
        raise _unauthorized("Invalid or expired authentication token")

    db = get_db()
    user = await db.users.find_one({"_id": user_obj_id})
    if not user:
        raise _unauthorized("User not found")

    # Tokens are revoked by bumping the user's token_version (logout, password change, ...)
    if payload.get("ver", 0) != user.get("token_version", 0):
        raise _unauthorized("Session has been revoked. Please sign in again.")

    user["_id"] = str(user["_id"])
    return user


async def get_optional_user(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    try:
        return await get_current_user(request, auth_header)
    except HTTPException:
        return None
