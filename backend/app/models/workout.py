from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.utils.dates import utc_now


class ExerciseSet(BaseModel):
    set_number: int = 1
    reps: int = 0
    weight: float = 0.0
    duration_seconds: int = 0
    completed: bool = True


class WorkoutExercise(BaseModel):
    exercise_id: Optional[str] = None
    exercise_name: str
    category: str = "General"
    type: str = "reps"  # "reps", "weight_reps", "duration"
    sets: List[ExerciseSet] = Field(default_factory=list)
    total_reps: int = 0
    total_volume: float = 0.0


class WorkoutBase(BaseModel):
    date: datetime = Field(default_factory=utc_now)
    title: str = "Workout Session"
    notes: Optional[str] = ""
    duration_minutes: int = 0
    exercises: List[WorkoutExercise] = Field(default_factory=list)


class WorkoutCreate(WorkoutBase):
    pass


class WorkoutUpdate(BaseModel):
    date: Optional[datetime] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    duration_minutes: Optional[int] = None
    exercises: Optional[List[WorkoutExercise]] = None


class WorkoutResponse(WorkoutBase):
    id: str = Field(alias="_id")
    user_id: str
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {
        "populate_by_name": True
    }


class QuickLogRequest(BaseModel):
    exercise_name: str
    reps: int
    weight: float = 0.0
    duration_seconds: int = 0
    date: Optional[datetime] = None
    notes: Optional[str] = ""
