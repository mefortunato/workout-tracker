from typing import Optional
from pydantic import BaseModel, Field

from app.models.workout import ExerciseType


class ExerciseBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str = Field(default="General", max_length=50)  # e.g., Upper Body, Lower Body, Core, Full Body, Cardio
    type: ExerciseType = "reps"
    description: Optional[str] = Field(default="", max_length=1000)
    icon: Optional[str] = Field(default="activity", max_length=50)


class ExerciseCreate(ExerciseBase):
    pass


class ExerciseResponse(ExerciseBase):
    id: str = Field(alias="_id")
    is_default: bool = False
    user_id: Optional[str] = None

    model_config = {
        "populate_by_name": True
    }
