import logging
from datetime import timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import httpx
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.config import settings
from app.database import get_db
from app.utils.dates import utc_now
from bson import ObjectId

logger = logging.getLogger(__name__)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


async def verify_google_credential(credential: str) -> Optional[Dict[str, Any]]:
    """Verifies a Google ID token from frontend Google Identity Services button."""
    try:
        # First attempt official google-auth library
        if settings.GOOGLE_CLIENT_ID:
            idinfo = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )
            return {
                "google_id": idinfo.get("sub"),
                "email": idinfo.get("email"),
                "name": idinfo.get("name", "Athlete"),
                "picture": idinfo.get("picture"),
            }
    except Exception as e:
        logger.warning(f"Google library verification failed: {e}. Trying tokeninfo endpoint.")

    # Fallback to Google's public tokeninfo endpoint
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": credential},
                timeout=10.0
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "google_id": data.get("sub"),
                    "email": data.get("email"),
                    "name": data.get("name", "Athlete"),
                    "picture": data.get("picture"),
                }
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
                logger.error(f"Token exchange failed: {token_resp.text}")
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
                logger.error(f"Failed to fetch Google userinfo: {userinfo_resp.text}")
                return None
            
            info = userinfo_resp.json()
            return {
                "google_id": info.get("sub"),
                "email": info.get("email"),
                "name": info.get("name", "Athlete"),
                "picture": info.get("picture"),
            }
    except Exception as e:
        logger.error(f"Exception during Google code exchange: {e}")
        return None


async def get_or_create_user(user_info: Dict[str, Any]) -> Dict[str, Any]:
    """Finds existing user by email or creates a new one, then returns the user document."""
    db = get_db()
    email = user_info["email"]
    existing = await db.users.find_one({"email": email})
    
    if existing:
        update_fields = {"last_login": utc_now()}
        if user_info.get("picture") and not existing.get("picture"):
            update_fields["picture"] = user_info["picture"]
        if user_info.get("google_id") and not existing.get("google_id"):
            update_fields["google_id"] = user_info["google_id"]
        
        await db.users.update_one({"_id": existing["_id"]}, {"$set": update_fields})
        existing["_id"] = str(existing["_id"])
        return existing
    
    # Create new user
    new_user = {
        "email": email,
        "name": user_info.get("name", email.split("@")[0]),
        "picture": user_info.get("picture", ""),
        "google_id": user_info.get("google_id"),
        "created_at": utc_now(),
        "last_login": utc_now(),
        "preferences": {
            "weight_unit": "kg",
            "theme": "dark",
            "daily_pushup_target": 100,
            "daily_situp_target": 100
        }
    }
    result = await db.users.insert_one(new_user)
    new_user["_id"] = str(result.inserted_id)
    
    # Also create default goals for the new user
    await db.goals.insert_many([
        {
            "user_id": new_user["_id"],
            "title": "Daily 100 Push-ups",
            "exercise_name": "Push-ups",
            "period": "daily",
            "target_value": 100,
            "unit": "reps",
            "is_active": True,
            "created_at": utc_now()
        },
        {
            "user_id": new_user["_id"],
            "title": "Daily 50 Sit-ups",
            "exercise_name": "Sit-ups",
            "period": "daily",
            "target_value": 50,
            "unit": "reps",
            "is_active": True,
            "created_at": utc_now()
        }
    ])
    
    return new_user


def hash_password(password: str) -> str:
    import hashlib
    import secrets
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}:{key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    import hashlib
    import secrets
    try:
        if not hashed_password or ":" not in hashed_password:
            return False
        salt, key_hex = hashed_password.split(":", 1)
        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


async def register_email_user(name: str, email: str, password: str) -> Dict[str, Any]:
    """Registers a new user with email and password."""
    db = get_db()
    email_clean = email.strip().lower()
    existing = await db.users.find_one({"email": email_clean})
    if existing:
        raise ValueError("An account with this email already exists.")

    hashed = hash_password(password)
    new_user = {
        "email": email_clean,
        "name": name.strip(),
        "hashed_password": hashed,
        "picture": "",
        "created_at": utc_now(),
        "last_login": utc_now(),
        "preferences": {
            "weight_unit": "kg",
            "theme": "dark",
            "daily_pushup_target": 100,
            "daily_situp_target": 100
        }
    }
    result = await db.users.insert_one(new_user)
    new_user["_id"] = str(result.inserted_id)

    # Initialize starter goals
    await db.goals.insert_many([
        {
            "user_id": new_user["_id"],
            "title": "Daily 100 Push-ups",
            "exercise_name": "Push-ups",
            "period": "daily",
            "target_value": 100,
            "unit": "reps",
            "is_active": True,
            "created_at": utc_now()
        },
        {
            "user_id": new_user["_id"],
            "title": "Daily 50 Sit-ups",
            "exercise_name": "Sit-ups",
            "period": "daily",
            "target_value": 50,
            "unit": "reps",
            "is_active": True,
            "created_at": utc_now()
        }
    ])
    return new_user


async def authenticate_email_user(email: str, password: str) -> Dict[str, Any]:
    """Authenticates an existing user via email and password."""
    db = get_db()
    email_clean = email.strip().lower()
    user = await db.users.find_one({"email": email_clean})
    if not user:
        raise ValueError("Invalid email or password.")

    hashed = user.get("hashed_password")
    if not hashed:
        raise ValueError("This account was created with Google Sign-In. Please sign in with Google.")

    if not verify_password(password, hashed):
        raise ValueError("Invalid email or password.")

    await db.users.update_one({"_id": user["_id"]}, {"$set": {"last_login": utc_now()}})
    user["_id"] = str(user["_id"])
    return user
