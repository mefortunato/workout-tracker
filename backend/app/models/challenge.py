from datetime import datetime
from typing import Optional, List, Literal, Union
from pydantic import BaseModel, Field
from app.utils.dates import utc_now

ChallengeType = Literal["total_volume", "daily_streak"]


class ChallengeParticipant(BaseModel):
    user_id: str
    name: str
    email: Optional[str] = None
    avatar: Optional[str] = None
    joined_at: datetime = Field(default_factory=utc_now)


class ChallengeParticipantProgress(BaseModel):
    user_id: str
    name: str
    avatar: Optional[str] = None
    joined_at: datetime
    completed_reps: Union[int, float] = 0
    target_reps: Union[int, float] = 0
    days_completed: int = 0
    target_days: int = 0
    current_streak: int = 0
    progress_percentage: float = 0.0
    is_completed: bool = False
    rank: int = 1
    last_active: Optional[datetime] = None
    unit: str = "reps"  # "reps", "minutes"


TargetUnit = Literal["reps", "minutes"]


class ChallengeBase(BaseModel):
    title: str
    description: Optional[str] = ""
    challenge_type: ChallengeType = "total_volume"
    exercise_name: Optional[str] = "Push-ups"
    target_value: int  # Total reps/minutes (for total_volume) or daily reps/minutes (for daily_streak)
    target_unit: str = "reps"  # "reps", "minutes"
    start_date: str    # YYYY-MM-DD
    end_date: str      # YYYY-MM-DD


class ChallengeCreate(ChallengeBase):
    title: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default="", max_length=2000)
    exercise_name: Optional[str] = Field(default="Push-ups", max_length=100)
    target_value: int = Field(gt=0, le=10_000_000)
    target_unit: Optional[TargetUnit] = "reps"
    start_date: str = Field(max_length=10)
    end_date: str = Field(max_length=10)


class ChallengeJoinRequest(BaseModel):
    invite_code: str = Field(min_length=1, max_length=20)


class ChallengeResponse(ChallengeBase):
    id: str = Field(alias="_id")
    creator_id: str
    creator_name: str
    invite_code: str
    participants_count: int = 0
    is_user_joined: bool = False
    user_progress: Optional[ChallengeParticipantProgress] = None
    leaderboard: List[ChallengeParticipantProgress] = []
    days_remaining: int = 0
    status: str = "active"  # "active", "completed", "upcoming"
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {
        "populate_by_name": True
    }
