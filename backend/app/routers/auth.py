import logging
import secrets
import urllib.parse
from datetime import timedelta
from typing import Dict, Any, Optional, Literal
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from app.utils.dates import utc_now

from app.config import settings
from app.database import get_db
from app.services.auth_service import (
    create_user_token,
    verify_google_credential,
    exchange_google_code,
    get_or_create_user,
    register_email_user,
    authenticate_email_user
)
from fastapi.security import HTTPAuthorizationCredentials
from app.utils.auth_dep import get_current_user, security as bearer_scheme
from app.utils.security import (
    OAUTH_STATE_COOKIE_NAME,
    auth_limiter,
    clear_auth_cookie,
    get_client_ip,
    set_auth_cookie,
)
from app.models.user import (
    UserPublic,
    TokenResponse,
    EmailRegisterRequest,
    EmailLoginRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

DEMO_EMAIL = "athlete@workout-tracker.app"


class GoogleVerifyRequest(BaseModel):
    credential: str = Field(min_length=1, max_length=4096)


class PreferencesUpdateRequest(BaseModel):
    weight_unit: Optional[Literal["kg", "lbs"]] = None
    theme: Optional[Literal["dark", "light"]] = None
    daily_pushup_target: Optional[int] = Field(default=None, ge=0, le=100_000)
    daily_situp_target: Optional[int] = Field(default=None, ge=0, le=100_000)


@router.get("/config")
async def get_auth_config():
    """Returns public auth configuration for the frontend (e.g. Google Client ID)."""
    return {
        "google_client_id": settings.GOOGLE_CLIENT_ID or "",
        "google_auth_enabled": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        "dev_login_enabled": settings.ALLOW_DEV_LOGIN
    }


@router.post("/register", response_model=TokenResponse)
async def register_with_email(body: EmailRegisterRequest, request: Request, response: Response):
    """Registers a new athlete account using email and password."""
    auth_limiter.check(f"register:{get_client_ip(request)}")
    try:
        user = await register_email_user(name=body.name, email=body.email, password=body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    token = create_user_token(user)
    set_auth_cookie(response, token)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserPublic(**user)
    )


@router.post("/login", response_model=TokenResponse)
async def login_with_email(body: EmailLoginRequest, request: Request, response: Response):
    """Authenticates an existing athlete using email and password."""
    # Limit per client IP and per target account to slow password guessing.
    auth_limiter.check(f"login-ip:{get_client_ip(request)}", f"login-email:{body.email.lower()}")
    try:
        user = await authenticate_email_user(email=body.email, password=body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    
    token = create_user_token(user)
    set_auth_cookie(response, token)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserPublic(**user)
    )


@router.get("/google/login")
async def google_login(request: Request):
    """Generates the Google OAuth authorization URL and redirects the user."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GOOGLE_CLIENT_ID is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env."
        )
    
    redirect_uri = f"{settings.FRONTEND_URL}/api/auth/google/callback"
    # `state` ties the callback to this browser, preventing login CSRF (an attacker
    # completing the flow with their own code to sign the victim into their account).
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account"
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    redirect = RedirectResponse(url=url)
    redirect.set_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        max_age=600,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/api/auth/google",
    )
    return redirect


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """Callback endpoint for Google OAuth authorization code exchange."""
    failure = RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error=oauth_failed")
    failure.delete_cookie(OAUTH_STATE_COOKIE_NAME, path="/api/auth/google")

    expected_state = request.cookies.get(OAUTH_STATE_COOKIE_NAME)
    if error or not code or not state or not expected_state or not secrets.compare_digest(state, expected_state):
        logger.warning("Google OAuth callback rejected (missing code or state mismatch)")
        return failure

    redirect_uri = f"{settings.FRONTEND_URL}/api/auth/google/callback"
    user_info = await exchange_google_code(code, redirect_uri)
    if not user_info:
        return failure

    try:
        user = await get_or_create_user(user_info)
    except ValueError:
        return failure
    token = create_user_token(user)

    # Redirect to home with cookie set
    redirect = RedirectResponse(url=f"{settings.FRONTEND_URL}/?auth_success=1")
    redirect.delete_cookie(OAUTH_STATE_COOKIE_NAME, path="/api/auth/google")
    set_auth_cookie(redirect, token)
    return redirect


@router.post("/google/verify", response_model=TokenResponse)
async def verify_google_token(body: GoogleVerifyRequest, request: Request, response: Response):
    """Verifies a Google ID token from frontend Google Identity Services and logs in user."""
    auth_limiter.check(f"google-verify:{get_client_ip(request)}")
    user_info = await verify_google_credential(body.credential)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not verify Google ID token with Google identity servers."
        )

    try:
        user = await get_or_create_user(user_info)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    token = create_user_token(user)
    set_auth_cookie(response, token)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserPublic(**user)
    )


@router.post("/demo-login", response_model=TokenResponse)
async def demo_login(request: Request, response: Response):
    """Demo login allows instant access to test all app features without Google Cloud setup."""
    if not settings.ALLOW_DEV_LOGIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Demo login disabled")
    auth_limiter.check(f"demo:{get_client_ip(request)}")
    
    demo_user_info = {
        "email": DEMO_EMAIL,
        "name": "Demo Athlete",
        "picture": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
        "google_id": "demo-google-id-001"
    }
    user = await get_or_create_user(demo_user_info)
    db = get_db()
    
    # Check if demo user has workouts; if not, seed realistic workout history!
    workout_count = await db.workouts.count_documents({"user_id": user["_id"]})
    if workout_count == 0:
        now = utc_now()
        sample_workouts = [
            {
                "user_id": user["_id"],
                "date": now - timedelta(days=2),
                "title": "Upper Body & Push-up Challenge",
                "notes": "Felt strong today, high intensity sets.",
                "duration_minutes": 35,
                "created_at": now - timedelta(days=2),
                "exercises": [
                    {
                        "exercise_name": "Push-ups",
                        "category": "Upper Body",
                        "type": "reps",
                        "sets": [
                            {"set_number": 1, "reps": 25, "weight": 0, "duration_seconds": 0, "completed": True},
                            {"set_number": 2, "reps": 25, "weight": 0, "duration_seconds": 0, "completed": True},
                            {"set_number": 3, "reps": 20, "weight": 0, "duration_seconds": 0, "completed": True},
                            {"set_number": 4, "reps": 20, "weight": 0, "duration_seconds": 0, "completed": True},
                        ],
                        "total_reps": 90,
                        "total_volume": 0
                    },
                    {
                        "exercise_name": "Dips",
                        "category": "Upper Body",
                        "type": "reps",
                        "sets": [
                            {"set_number": 1, "reps": 15, "weight": 0, "duration_seconds": 0, "completed": True},
                            {"set_number": 2, "reps": 15, "weight": 0, "duration_seconds": 0, "completed": True},
                        ],
                        "total_reps": 30,
                        "total_volume": 0
                    }
                ]
            },
            {
                "user_id": user["_id"],
                "date": now - timedelta(days=1),
                "title": "Core Blast & Sit-ups",
                "notes": "Focused on controlled reps and core engagement.",
                "duration_minutes": 25,
                "created_at": now - timedelta(days=1),
                "exercises": [
                    {
                        "exercise_name": "Sit-ups",
                        "category": "Core",
                        "type": "reps",
                        "sets": [
                            {"set_number": 1, "reps": 30, "weight": 0, "duration_seconds": 0, "completed": True},
                            {"set_number": 2, "reps": 30, "weight": 0, "duration_seconds": 0, "completed": True},
                            {"set_number": 3, "reps": 25, "weight": 0, "duration_seconds": 0, "completed": True},
                        ],
                        "total_reps": 85,
                        "total_volume": 0
                    },
                    {
                        "exercise_name": "Plank",
                        "category": "Core",
                        "type": "duration",
                        "sets": [
                            {"set_number": 1, "reps": 0, "weight": 0, "duration_seconds": 60, "completed": True},
                            {"set_number": 2, "reps": 0, "weight": 0, "duration_seconds": 60, "completed": True},
                        ],
                        "total_reps": 0,
                        "total_volume": 0
                    }
                ]
            },
            {
                "user_id": user["_id"],
                "date": now,
                "title": "Daily Morning Push-ups & Sit-ups",
                "notes": "Morning routine consistency.",
                "duration_minutes": 20,
                "created_at": now,
                "exercises": [
                    {
                        "exercise_name": "Push-ups",
                        "category": "Upper Body",
                        "type": "reps",
                        "sets": [
                            {"set_number": 1, "reps": 30, "weight": 0, "duration_seconds": 0, "completed": True},
                            {"set_number": 2, "reps": 25, "weight": 0, "duration_seconds": 0, "completed": True},
                        ],
                        "total_reps": 55,
                        "total_volume": 0
                    },
                    {
                        "exercise_name": "Sit-ups",
                        "category": "Core",
                        "type": "reps",
                        "sets": [
                            {"set_number": 1, "reps": 30, "weight": 0, "duration_seconds": 0, "completed": True},
                            {"set_number": 2, "reps": 30, "weight": 0, "duration_seconds": 0, "completed": True},
                        ],
                        "total_reps": 60,
                        "total_volume": 0
                    }
                ]
            }
        ]
        await db.workouts.insert_many(sample_workouts)

    token = create_user_token(user)
    set_auth_cookie(response, token)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserPublic(**user)
    )


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns the current authenticated user profile."""
    return UserPublic(**current_user)


@router.put("/preferences", response_model=UserPublic)
async def update_preferences(
    body: PreferencesUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Updates user preferences (units, theme, daily targets)."""
    db = get_db()
    prefs = current_user.get("preferences", {})
    if body.weight_unit is not None:
        prefs["weight_unit"] = body.weight_unit
    if body.theme is not None:
        prefs["theme"] = body.theme
    if body.daily_pushup_target is not None:
        prefs["daily_pushup_target"] = body.daily_pushup_target
    if body.daily_situp_target is not None:
        prefs["daily_situp_target"] = body.daily_situp_target

    await db.users.update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$set": {"preferences": prefs}}
    )
    current_user["preferences"] = prefs
    return UserPublic(**current_user)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """Clears the auth cookie and revokes all of the user's outstanding tokens."""
    try:
        user = await get_current_user(request, auth_header)
    except HTTPException:
        user = None
    # The demo account is shared, so one visitor logging out must not sign out everyone.
    if user and user.get("email") != DEMO_EMAIL:
        await get_db().users.update_one(
            {"_id": ObjectId(user["_id"])},
            {"$inc": {"token_version": 1}},
        )
    clear_auth_cookie(response)
    return {"message": "Logged out successfully"}


@router.get("/me/export")
async def export_my_data(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns all data stored about the current user (data portability)."""
    db = get_db()
    user_id = current_user["_id"]

    def clean(doc: Dict[str, Any]) -> Dict[str, Any]:
        doc["_id"] = str(doc["_id"])
        return doc

    profile = {k: v for k, v in current_user.items() if k not in ("hashed_password", "token_version")}
    workouts = [clean(d) async for d in db.workouts.find({"user_id": user_id}).sort("date", 1)]
    goals = [clean(d) async for d in db.goals.find({"user_id": user_id})]
    exercises = [clean(d) async for d in db.exercises.find({"user_id": user_id, "is_default": {"$ne": True}})]
    challenges = [
        {
            "_id": str(d["_id"]),
            "title": d.get("title"),
            "start_date": d.get("start_date"),
            "end_date": d.get("end_date"),
            "is_creator": str(d.get("creator_id")) == user_id,
        }
        async for d in db.challenges.find({"participants.user_id": user_id})
    ]
    return {
        "exported_at": utc_now(),
        "profile": profile,
        "workouts": workouts,
        "goals": goals,
        "custom_exercises": exercises,
        "challenges": challenges,
    }


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(response: Response, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Permanently deletes the current user's account and all of their data."""
    if settings.ALLOW_DEV_LOGIN and current_user.get("email") == DEMO_EMAIL:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The shared demo account cannot be deleted")

    db = get_db()
    user_id = current_user["_id"]
    await db.workouts.delete_many({"user_id": user_id})
    await db.goals.delete_many({"user_id": user_id})
    await db.exercises.delete_many({"user_id": user_id, "is_default": {"$ne": True}})
    # Challenges they created alone are removed; otherwise they just leave.
    await db.challenges.delete_many({"creator_id": user_id, "participants": {"$size": 1}})
    await db.challenges.update_many(
        {"participants.user_id": user_id},
        {"$pull": {"participants": {"user_id": user_id}}},
    )
    await db.users.delete_one({"_id": ObjectId(user_id)})
    clear_auth_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return None
