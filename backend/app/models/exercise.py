from typing import Optional
from pydantic import BaseModel, Field


class ExerciseBase(BaseModel):
    name: str
    category: str = "General"  # e.g., Upper Body, Lower Body, Core, Full Body, Cardio
    type: str = "reps"  # "reps", "weight_reps", "duration"
    description: Optional[str] = ""
    icon: Optional[str] = "activity"


class ExerciseCreate(ExerciseBase):
    pass


class ExerciseResponse(ExerciseBase):
    id: str = Field(alias="_id")
    is_default: bool = False
    user_id: Optional[str] = None

    model_config = {
        "populate_by_name": True
    }
