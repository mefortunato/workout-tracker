import asyncio
import hashlib
import logging
import secrets
from datetime import timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import httpx
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.config import settings
from app.database import get_db
from app.utils.dates import utc_now
from app.utils.security import exact_name_regex
from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)


GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = utc_now()
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_user_token(user: Dict[str, Any]) -> str:
    """Issues a session token bound to the user's current token_version."""
    return create_access_token({
        "sub": str(user["_id"]),
        "ver": user.get("token_version", 0),
    })


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require_exp": True, "require_sub": True},
        )
    except JWTError as e:
        logger.info(f"JWT decode error: {e}")
        return None


def _google_profile(info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalizes verified Google claims, rejecting accounts without a verified email."""
    email = info.get("email")
    email_verified = info.get("email_verified")
    if isinstance(email_verified, str):
        email_verified = email_verified.lower() == "true"
    if not email or not email_verified or not info.get("sub"):
        logger.warning("Rejected Google identity without a verified email address")
        return None
    return {
        "google_id": info.get("sub"),
        "email": email.strip().lower(),
        "name": info.get("name") or email.split("@")[0],
        "picture": info.get("picture"),
    }


async def verify_google_credential(credential: str) -> Optional[Dict[str, Any]]:
    """Verifies a Google ID token from the frontend Google Identity Services button.

    The token must have been issued for *this* app (aud == GOOGLE_CLIENT_ID); otherwise
    any ID token a user handed to some other Google-integrated site could be replayed
    here to sign in as them.
    """
    if not settings.GOOGLE_CLIENT_ID:
        logger.warning("Google ID token received but GOOGLE_CLIENT_ID is not configured")
        return None

    try:
        idinfo = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
        return _google_profile(idinfo)
    except ValueError as e:
        # Signature, audience, issuer or expiry check failed: the token is invalid.
        logger.warning(f"Google ID token rejected: {e}")
        return None
    except Exception as e:
        logger.warning(f"Google library verification unavailable: {e}. Trying tokeninfo endpoint.")

    # Fallback (e.g. cert fetch failed): Google's tokeninfo endpoint validates the
    # signature and expiry, but we must still check audience and issuer ourselves.
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": credential},
                timeout=10.0
            )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("aud") != settings.GOOGLE_CLIENT_ID or data.get("iss") not in GOOGLE_ISSUERS:
            logger.warning("Google tokeninfo audience/issuer mismatch")
            return None
        return _google_profile(data)
    except Exception as ex:
        logger.error(f"Google tokeninfo endpoint failed: {ex}")
    return None


async def exchange_google_code(code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
    """Exchanges an authorization code for tokens and fetches user profile."""
    try:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(token_url, data=data, timeout=10.0)
            if token_resp.status_code != 200:
                logger.error(f"Token exchange failed with status {token_resp.status_code}")
                return None
            token_data = token_resp.json()
            access_token = token_data.get("access_token")

            # Fetch user profile
            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0
            )
            if userinfo_resp.status_code != 200:
                logger.error(f"Failed to fetch Google userinfo (status {userinfo_resp.status_code})")
                return None

            return _google_profile(userinfo_resp.json())
    except Exception as e:
        logger.error(f"Exception during Google code exchange: {e}")
        return None


def _new_user_doc(email: str, name: str, **extra: Any) -> Dict[str, Any]:
    now = utc_now()
    return {
        "email": email,
        "name": name,
        "picture": extra.pop("picture", "") or "",
        "created_at": now,
        "last_login": now,
        "token_version": 0,
        "preferences": {
            "weight_unit": "kg",
            "theme": "dark",
            "daily_pushup_target": 100,
            "daily_situp_target": 100
        },
        **extra,
    }


async def _create_starter_goals(db, user_id: str) -> None:
    await db.goals.insert_many([
        {
            "user_id": user_id,
            "title": "Daily 100 Push-ups",
            "exercise_name": "Push-ups",
            "period": "daily",
            "target_value": 100,
            "unit": "reps",
            "is_active": True,
            "created_at": utc_now()
        },
        {
            "user_id": user_id,
            "title": "Daily 50 Sit-ups",
            "exercise_name": "Sit-ups",
            "period": "daily",
            "target_value": 50,
            "unit": "reps",
            "is_active": True,
            "created_at": utc_now()
        }
    ])


async def get_or_create_user(user_info: Dict[str, Any]) -> Dict[str, Any]:
    """Finds existing user by email or creates a new one, then returns the user document."""
    db = get_db()
    email = user_info["email"].strip().lower()
    # Case-insensitive lookup also matches accounts stored before emails were normalized.
    existing = await db.users.find_one({"email": exact_name_regex(email)})

    if existing:
        google_id = user_info.get("google_id")
        if google_id and existing.get("google_id") and existing["google_id"] != google_id:
            # Same email but a different Google account (e.g. a recycled Workspace address).
            raise ValueError("This email is linked to a different Google account.")

        update_fields = {"last_login": utc_now()}
        if user_info.get("picture") and not existing.get("picture"):
            update_fields["picture"] = user_info["picture"]
        if google_id and not existing.get("google_id"):
            update_fields["google_id"] = google_id

        await db.users.update_one({"_id": existing["_id"]}, {"$set": update_fields})
        existing["_id"] = str(existing["_id"])
        return existing
    
    # Create new user
    new_user = _new_user_doc(
        email,
        user_info.get("name") or email.split("@")[0],
        picture=user_info.get("picture"),
        google_id=user_info.get("google_id"),
    )
    result = await db.users.insert_one(new_user)
    new_user["_id"] = str(result.inserted_id)
    await _create_starter_goals(db, new_user["_id"])
    return new_user


PBKDF2_ITERATIONS = 600_000  # OWASP 2023 recommendation for PBKDF2-HMAC-SHA256
_LEGACY_PBKDF2_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${key.hex()}"


def _parse_hash(hashed_password: str):
    if hashed_password.startswith("pbkdf2_sha256$"):
        _, iterations, salt, key_hex = hashed_password.split("$", 3)
        return int(iterations), salt, key_hex
    # Legacy format: "<salt>:<hex>" with 100k iterations
    salt, key_hex = hashed_password.split(":", 1)
    return _LEGACY_PBKDF2_ITERATIONS, salt, key_hex


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if not hashed_password:
            return False
        iterations, salt, key_hex = _parse_hash(hashed_password)
        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return secrets.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


def password_needs_rehash(hashed_password: str) -> bool:
    try:
        return _parse_hash(hashed_password)[0] < PBKDF2_ITERATIONS
    except Exception:
        return True


async def register_email_user(name: str, email: str, password: str) -> Dict[str, Any]:
    """Registers a new user with email and password."""
    db = get_db()
    email_clean = email.strip().lower()
    existing = await db.users.find_one({"email": email_clean})
    if existing:
        raise ValueError("An account with this email already exists.")

    hashed = await asyncio.to_thread(hash_password, password)
    new_user = _new_user_doc(email_clean, name.strip(), hashed_password=hashed)
    try:
        result = await db.users.insert_one(new_user)
    except DuplicateKeyError:
        raise ValueError("An account with this email already exists.")
    new_user["_id"] = str(result.inserted_id)
    await _create_starter_goals(db, new_user["_id"])
    return new_user


_DUMMY_HASH = hash_password(secrets.token_hex(16))


async def authenticate_email_user(email: str, password: str) -> Dict[str, Any]:
    """Authenticates an existing user via email and password."""
    db = get_db()
    email_clean = email.strip().lower()
    user = await db.users.find_one({"email": email_clean})
    if not user:
        # Spend comparable time hashing so response timing doesn't reveal unknown emails.
        await asyncio.to_thread(verify_password, password, _DUMMY_HASH)
        raise ValueError("Invalid email or password.")

    # Use one generic error for unknown email, Google-only account and wrong
    # password so the endpoint can't be used to discover registered emails.
    hashed = user.get("hashed_password")
    if not hashed or not await asyncio.to_thread(verify_password, password, hashed):
        raise ValueError("Invalid email or password.")

    update_fields: Dict[str, Any] = {"last_login": utc_now()}
    if password_needs_rehash(hashed):
        update_fields["hashed_password"] = await asyncio.to_thread(hash_password, password)
    await db.users.update_one({"_id": user["_id"]}, {"$set": update_fields})
    user["_id"] = str(user["_id"])
    return user
