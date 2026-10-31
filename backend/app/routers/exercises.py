import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.database import get_db
from app.utils.auth_dep import get_current_user
from app.models.exercise import ExerciseCreate, ExerciseResponse
from app.utils.security import exact_name_regex

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exercises", tags=["Exercises"])


@router.get("", response_model=List[ExerciseResponse])
async def list_exercises(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Returns library of default exercises plus user's custom exercises."""
    db = get_db()
    cursor = db.exercises.find({
        "$or": [
            {"is_default": True},
            {"user_id": current_user["_id"]}
        ]
    }).sort([("is_default", -1), ("name", 1)])

    exercises = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        exercises.append(ExerciseResponse(**doc))
    return exercises


@router.post("", response_model=ExerciseResponse, status_code=status.HTTP_201_CREATED)
async def create_exercise(
    payload: ExerciseCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Creates a custom exercise for the current user."""
    db = get_db()
    
    # Check if duplicate name for this user
    existing = await db.exercises.find_one({
        "name": exact_name_regex(payload.name),
        "$or": [{"is_default": True}, {"user_id": current_user["_id"]}]
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An exercise named '{payload.name}' already exists."
        )

    doc = payload.model_dump()
    doc["name"] = payload.name.strip()
    doc["user_id"] = current_user["_id"]
    doc["is_default"] = False

    res = await db.exercises.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return ExerciseResponse(**doc)


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise(
    exercise_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Deletes a custom exercise created by the user."""
    db = get_db()
    try:
        obj_id = ObjectId(exercise_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid exercise ID")

    doc = await db.exercises.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Exercise not found")

    if doc.get("is_default"):
        raise HTTPException(status_code=403, detail="Cannot delete system default exercises")

    if doc.get("user_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this exercise")

    await db.exercises.delete_one({"_id": obj_id})
    return None
