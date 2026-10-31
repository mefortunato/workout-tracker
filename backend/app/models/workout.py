from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from app.utils.dates import utc_now


# Upper bounds keep a single request from storing absurd values that would
# skew stats or let someone trivially top a challenge leaderboard.
MAX_REPS_PER_SET = 10_000
MAX_WEIGHT = 2_000.0
MAX_DURATION_SECONDS = 24 * 60 * 60

ExerciseType = Literal["reps", "weight_reps", "duration"]


class ExerciseSet(BaseModel):
    set_number: int = Field(default=1, ge=1, le=1000)
    reps: int = Field(default=0, ge=0, le=MAX_REPS_PER_SET)
    weight: float = Field(default=0.0, ge=0, le=MAX_WEIGHT)
    duration_seconds: int = Field(default=0, ge=0, le=MAX_DURATION_SECONDS)
    completed: bool = True


class WorkoutExercise(BaseModel):
    exercise_id: Optional[str] = Field(default=None, max_length=64)
    exercise_name: str = Field(min_length=1, max_length=100)
    category: str = Field(default="General", max_length=50)
    type: ExerciseType = "reps"
    sets: List[ExerciseSet] = Field(default_factory=list, max_length=100)
    total_reps: int = 0
    total_volume: float = 0.0


class WorkoutBase(BaseModel):
    date: datetime = Field(default_factory=utc_now)
    title: str = Field(default="Workout Session", max_length=200)
    notes: Optional[str] = Field(default="", max_length=5000)
    duration_minutes: int = Field(default=0, ge=0, le=24 * 60)
    exercises: List[WorkoutExercise] = Field(default_factory=list, max_length=50)


class WorkoutCreate(WorkoutBase):
    pass


class WorkoutUpdate(BaseModel):
    date: Optional[datetime] = None
    title: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=5000)
    duration_minutes: Optional[int] = Field(default=None, ge=0, le=24 * 60)
    exercises: Optional[List[WorkoutExercise]] = Field(default=None, max_length=50)


class WorkoutResponse(WorkoutBase):
    id: str = Field(alias="_id")
    user_id: str
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {
        "populate_by_name": True
    }


class QuickLogRequest(BaseModel):
    exercise_name: str = Field(min_length=1, max_length=100)
    reps: int = Field(ge=0, le=MAX_REPS_PER_SET)
    weight: float = Field(default=0.0, ge=0, le=MAX_WEIGHT)
    duration_seconds: int = Field(default=0, ge=0, le=MAX_DURATION_SECONDS)
    date: Optional[datetime] = None
    notes: Optional[str] = Field(default="", max_length=1000)
