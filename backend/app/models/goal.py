from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.utils.dates import utc_now


class GoalBase(BaseModel):
    title: str  # e.g., "100 Push-ups Daily", "50 Sit-ups Daily"
    exercise_name: Optional[str] = "Push-ups"  # specific exercise or None for all workouts
    period: str = "daily"  # "daily", "weekly", "monthly"
    target_value: int = 100  # e.g. 100 reps
    unit: str = "reps"  # "reps", "workouts", "seconds"
    is_active: bool = True


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    exercise_name: Optional[str] = None
    period: Optional[str] = None
    target_value: Optional[int] = None
    unit: Optional[str] = None
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
