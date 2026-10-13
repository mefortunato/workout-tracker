import logging
from datetime import datetime, timedelta, time
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.database import get_db
from app.utils.auth_dep import get_current_user
from app.utils.dates import utc_now
from app.models.goal import GoalCreate, GoalUpdate, GoalResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/goals", tags=["Goals"])


async def calculate_goal_progress(goal_doc: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    db = get_db()
    period = goal_doc.get("period", "daily")
    target_value = goal_doc.get("target_value", 1)
    target_ex = goal_doc.get("exercise_name")
    unit = goal_doc.get("unit", "reps")

    now = utc_now()
    if period == "daily":
        start = datetime.combine(now.date(), time.min)
        end = datetime.combine(now.date(), time.max)
    elif period == "weekly":
        # Start of current week (Monday)
        start = datetime.combine(now.date() - timedelta(days=now.weekday()), time.min)
        end = datetime.combine(now.date() + timedelta(days=6 - now.weekday()), time.max)
    elif period == "monthly":
        start = datetime(now.year, now.month, 1)
        # End of current month
        if now.month == 12:
            end = datetime(now.year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end = datetime(now.year, now.month + 1, 1) - timedelta(seconds=1)
    else:
        start = now - timedelta(days=1)
        end = now

    current_val = 0
    if unit == "workouts":
        current_val = await db.workouts.count_documents({
            "user_id": user_id,
            "date": {"$gte": start, "$lte": end}
        })
    else:
        cursor = db.workouts.find({
            "user_id": user_id,
            "date": {"$gte": start, "$lte": end}
        })
        async for doc in cursor:
            for ex in doc.get("exercises", []):
                ex_name = ex.get("exercise_name", "")
                if not target_ex or target_ex.lower() in ex_name.lower():
                    reps = ex.get("total_reps", 0)
                    if reps == 0:
                        reps = sum(s.get("reps", 0) for s in ex.get("sets", []) if s.get("completed", True))
                    current_val += reps

    goal_doc["current_value"] = current_val
    goal_doc["progress_percentage"] = min(100.0, round((current_val / max(target_value, 1)) * 100, 1))
    goal_doc["_id"] = str(goal_doc["_id"])
    return goal_doc


@router.get("", response_model=List[GoalResponse])
async def list_goals(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Lists user goals with calculated dynamic progress for current period."""
    db = get_db()
    cursor = db.goals.find({"user_id": current_user["_id"]}).sort("created_at", -1)
    
    results = []
    async for doc in cursor:
        updated_doc = await calculate_goal_progress(doc, current_user["_id"])
        results.append(GoalResponse(**updated_doc))
    return results


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: GoalCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Creates a new workout target or goal."""
    db = get_db()
    doc = payload.model_dump()
    doc["user_id"] = current_user["_id"]
    doc["created_at"] = utc_now()

    res = await db.goals.insert_one(doc)
    doc["_id"] = res.inserted_id
    updated_doc = await calculate_goal_progress(doc, current_user["_id"])
    return GoalResponse(**updated_doc)


@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    payload: GoalUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Updates an existing goal."""
    db = get_db()
    try:
        obj_id = ObjectId(goal_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid goal ID")

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    res = await db.goals.find_one_and_update(
        {"_id": obj_id, "user_id": current_user["_id"]},
        {"$set": updates},
        return_document=True
    )
    if not res:
        raise HTTPException(status_code=404, detail="Goal not found")

    updated_doc = await calculate_goal_progress(res, current_user["_id"])
    return GoalResponse(**updated_doc)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Deletes a goal."""
    db = get_db()
    try:
        obj_id = ObjectId(goal_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid goal ID")

    res = await db.goals.delete_one({"_id": obj_id, "user_id": current_user["_id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Goal not found")
    return None
