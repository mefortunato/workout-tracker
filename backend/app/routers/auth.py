import logging
import urllib.parse
from datetime import timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from app.utils.dates import utc_now

from app.config import settings
from app.database import get_db
from app.services.auth_service import (
    create_access_token,
    verify_google_credential,
    exchange_google_code,
    get_or_create_user
)
from app.utils.auth_dep import get_current_user
from app.models.user import UserPublic, TokenResponse, UserPreferences

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class GoogleVerifyRequest(BaseModel):
    credential: str


class PreferencesUpdateRequest(BaseModel):
    weight_unit: Optional[str] = None
    theme: Optional[str] = None
    daily_pushup_target: Optional[int] = None
    daily_situp_target: Optional[int] = None


@router.get("/config")
async def get_auth_config():
    """Returns public auth configuration for the frontend (e.g. Google Client ID)."""
    return {
        "google_client_id": settings.GOOGLE_CLIENT_ID or "",
        "google_auth_enabled": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        "dev_login_enabled": settings.ALLOW_DEV_LOGIN
    }


@router.get("/google/login")
async def google_login(request: Request):
    """Generates the Google OAuth authorization URL and redirects the user."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GOOGLE_CLIENT_ID is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env."
        )
    
    redirect_uri = f"{settings.FRONTEND_URL}/api/auth/google/callback"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account"
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(code: str, response: Response):
    """Callback endpoint for Google OAuth authorization code exchange."""
    redirect_uri = f"{settings.FRONTEND_URL}/api/auth/google/callback"
    user_info = await exchange_google_code(code, redirect_uri)
    if not user_info:
        # Redirect to frontend with error query param
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error=oauth_failed")
    
    user = await get_or_create_user(user_info)
    token = create_access_token({"sub": user["_id"], "email": user["email"]})
    
    # Redirect to home with cookie set
    redirect = RedirectResponse(url=f"{settings.FRONTEND_URL}/?auth_success=1")
    redirect.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False  # allow localhost http
    )
    return redirect


@router.post("/google/verify", response_model=TokenResponse)
async def verify_google_token(body: GoogleVerifyRequest, response: Response):
    """Verifies a Google ID token from frontend Google Identity Services and logs in user."""
    user_info = await verify_google_credential(body.credential)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not verify Google ID token with Google identity servers."
        )
    
    user = await get_or_create_user(user_info)
    token = create_access_token({"sub": user["_id"], "email": user["email"]})
    
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False
    )
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserPublic(**user)
    )


@router.post("/demo-login", response_model=TokenResponse)
async def demo_login(response: Response):
    """Demo login allows instant access to test all app features without Google Cloud setup."""
    if not settings.ALLOW_DEV_LOGIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Demo login disabled")
    
    demo_user_info = {
        "email": "athlete@workout-tracker.app",
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

    token = create_access_token({"sub": user["_id"], "email": user["email"]})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False
    )
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

    from bson import ObjectId
    await db.users.update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$set": {"preferences": prefs}}
    )
    current_user["preferences"] = prefs
    return UserPublic(**current_user)


@router.post("/logout")
async def logout(response: Response):
    """Clears authentication cookie."""
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}
