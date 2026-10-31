from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field
from app.utils.dates import utc_now


GoalPeriod = Literal["daily", "weekly", "monthly"]
GoalUnit = Literal["reps", "workouts", "seconds"]


class GoalBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)  # e.g., "100 Push-ups Daily"
    exercise_name: Optional[str] = Field(default="Push-ups", max_length=100)  # None for all workouts
    period: GoalPeriod = "daily"
    target_value: int = Field(default=100, ge=1, le=1_000_000)  # e.g. 100 reps
    unit: GoalUnit = "reps"
    is_active: bool = True


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    exercise_name: Optional[str] = Field(default=None, max_length=100)
    period: Optional[GoalPeriod] = None
    target_value: Optional[int] = Field(default=None, ge=1, le=1_000_000)
    unit: Optional[GoalUnit] = None
    is_active: Optional[bool] = None


class GoalResponse(GoalBase):
    id: str = Field(alias="_id")
    user_id: str
    current_value: int = 0
    progress_percentage: float = 0.0
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {
        "populate_by_name": True
    }
