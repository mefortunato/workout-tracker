import logging
from datetime import datetime, time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from bson import ObjectId

from app.database import get_db
from app.utils.auth_dep import get_current_user
from app.utils.dates import utc_now
from app.models.workout import (
    WorkoutCreate,
    WorkoutUpdate,
    WorkoutResponse,
    QuickLogRequest,
    WorkoutExercise,
    ExerciseSet,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workouts", tags=["Workouts"])


def calculate_exercise_totals(exercise: WorkoutExercise) -> WorkoutExercise:
    total_reps = sum(s.reps for s in exercise.sets if s.completed)
    total_volume = sum(s.reps * s.weight for s in exercise.sets if s.completed)
    exercise.total_reps = total_reps
    exercise.total_volume = total_volume
    return exercise


@router.get("", response_model=List[WorkoutResponse])
async def list_workouts(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    exercise_name: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Lists logged workouts for the current user with date and exercise filters."""
    db = get_db()
    query: Dict[str, Any] = {"user_id": current_user["_id"]}

    if start_date or end_date:
        query["date"] = {}
        if start_date:
            query["date"]["$gte"] = start_date
        if end_date:
            query["date"]["$lte"] = end_date

    if exercise_name:
        query["exercises.exercise_name"] = exercise_name

    cursor = db.workouts.find(query).sort("date", -1).skip(skip).limit(limit)
    workouts = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        workouts.append(WorkoutResponse(**doc))
    return workouts


@router.post("", response_model=WorkoutResponse, status_code=status.HTTP_201_CREATED)
async def create_workout(
    payload: WorkoutCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Creates a new workout log session."""
    db = get_db()
    
    # Recalculate totals
    for ex in payload.exercises:
        calculate_exercise_totals(ex)

    doc = payload.model_dump()
    doc["user_id"] = current_user["_id"]
    doc["created_at"] = utc_now()

    res = await db.workouts.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return WorkoutResponse(**doc)


@router.get("/today", response_model=Optional[WorkoutResponse])
async def get_today_workout(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Gets the workout session for today if one exists."""
    db = get_db()
    today_start = datetime.combine(utc_now().date(), time.min)
    today_end = datetime.combine(utc_now().date(), time.max)

    doc = await db.workouts.find_one({
        "user_id": current_user["_id"],
        "date": {"$gte": today_start, "$lte": today_end}
    }, sort=[("date", -1)])

    if not doc:
        return None
    doc["_id"] = str(doc["_id"])
    return WorkoutResponse(**doc)


@router.post("/quick-log", response_model=WorkoutResponse)
async def quick_log(
    payload: QuickLogRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Rapid 1-tap logging for push-ups, sit-ups, etc.
    Finds today's workout or creates a new one, appending or incrementing the exercise set.
    """
    db = get_db()
    target_date = payload.date or utc_now()
    day_start = datetime.combine(target_date.date(), time.min)
    day_end = datetime.combine(target_date.date(), time.max)

    existing = await db.workouts.find_one({
        "user_id": current_user["_id"],
        "date": {"$gte": day_start, "$lte": day_end}
    }, sort=[("date", -1)])

    if existing:
        workout_id = existing["_id"]
        exercises = existing.get("exercises", [])
        
        # Check if exercise already exists in this workout
        found = False
        for ex in exercises:
            if ex.get("exercise_name", "").lower() == payload.exercise_name.lower():
                found = True
                sets = ex.get("sets", [])
                new_set_num = len(sets) + 1
                new_set = {
                    "set_number": new_set_num,
                    "reps": payload.reps,
                    "weight": payload.weight,
                    "duration_seconds": payload.duration_seconds,
                    "completed": True
                }
                sets.append(new_set)
                ex["sets"] = sets
                ex["total_reps"] = sum(s["reps"] for s in sets if s.get("completed", True))
                ex["total_volume"] = sum(s["reps"] * s.get("weight", 0) for s in sets if s.get("completed", True))
                break
        
        if not found:
            # Exercise doesn't exist yet in today's workout, add it
            new_ex = {
                "exercise_name": payload.exercise_name,
                "category": "Core" if "sit" in payload.exercise_name.lower() else "Upper Body",
                "type": "duration" if payload.duration_seconds > 0 else "reps",
                "sets": [{
                    "set_number": 1,
                    "reps": payload.reps,
                    "weight": payload.weight,
                    "duration_seconds": payload.duration_seconds,
                    "completed": True
                }],
                "total_reps": payload.reps,
                "total_volume": payload.reps * payload.weight
            }
            exercises.append(new_ex)

        notes = existing.get("notes", "")
        if payload.notes:
            notes = f"{notes}\n{payload.notes}".strip()

        await db.workouts.update_one(
            {"_id": workout_id},
            {"$set": {"exercises": exercises, "notes": notes}}
        )
        existing["exercises"] = exercises
        existing["notes"] = notes
        existing["_id"] = str(workout_id)
        return WorkoutResponse(**existing)
    else:
        # Create new workout for today
        new_workout = {
            "user_id": current_user["_id"],
            "date": target_date,
            "title": f"Workout - {target_date.strftime('%b %d, %Y')}",
            "notes": payload.notes or "Quick logged session",
            "duration_minutes": 15,
            "created_at": utc_now(),
            "exercises": [
                {
                    "exercise_name": payload.exercise_name,
                    "category": "Core" if "sit" in payload.exercise_name.lower() else "Upper Body",
                    "type": "duration" if payload.duration_seconds > 0 else "reps",
                    "sets": [{
                        "set_number": 1,
                        "reps": payload.reps,
                        "weight": payload.weight,
                        "duration_seconds": payload.duration_seconds,
                        "completed": True
                    }],
                    "total_reps": payload.reps,
                    "total_volume": payload.reps * payload.weight
                }
            ]
        }
        res = await db.workouts.insert_one(new_workout)
        new_workout["_id"] = str(res.inserted_id)
        return WorkoutResponse(**new_workout)


@router.get("/{workout_id}", response_model=WorkoutResponse)
async def get_workout(
    workout_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Retrieves a single workout by ID."""
    db = get_db()
    try:
        obj_id = ObjectId(workout_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workout ID format")

    doc = await db.workouts.find_one({"_id": obj_id, "user_id": current_user["_id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    doc["_id"] = str(doc["_id"])
    return WorkoutResponse(**doc)


@router.put("/{workout_id}", response_model=WorkoutResponse)
async def update_workout(
    workout_id: str,
    payload: WorkoutUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Updates an existing workout log."""
    db = get_db()
    try:
        obj_id = ObjectId(workout_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workout ID format")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if "exercises" in update_data and update_data["exercises"]:
        # Recalculate totals
        processed_ex = []
        for ex in update_data["exercises"]:
            total_reps = sum(s.get("reps", 0) for s in ex.get("sets", []) if s.get("completed", True))
            total_volume = sum(s.get("reps", 0) * s.get("weight", 0) for s in ex.get("sets", []) if s.get("completed", True))
            ex["total_reps"] = total_reps
            ex["total_volume"] = total_volume
            processed_ex.append(ex)
        update_data["exercises"] = processed_ex

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    res = await db.workouts.find_one_and_update(
        {"_id": obj_id, "user_id": current_user["_id"]},
        {"$set": update_data},
        return_document=True
    )
    if not res:
        raise HTTPException(status_code=404, detail="Workout not found")

    res["_id"] = str(res["_id"])
    return WorkoutResponse(**res)


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(
    workout_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Deletes a workout log."""
    db = get_db()
    try:
        obj_id = ObjectId(workout_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workout ID format")

    res = await db.workouts.delete_one({"_id": obj_id, "user_id": current_user["_id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Workout not found")
    return None
