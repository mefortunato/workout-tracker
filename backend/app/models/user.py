from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.utils.dates import utc_now


class UserPreferences(BaseModel):
    weight_unit: str = "kg"  # "kg" or "lbs"
    theme: str = "dark"
    daily_pushup_target: int = 50
    daily_situp_target: int = 50


class UserBase(BaseModel):
    email: EmailStr
    name: str
    picture: Optional[str] = None


class UserCreate(UserBase):
    google_id: Optional[str] = None


class UserPublic(UserBase):
    id: str = Field(alias="_id")
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {
        "populate_by_name": True
    }


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
