import logging
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query
from app.database import get_db
from app.utils.auth_dep import get_current_user
from app.utils.dates import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stats", tags=["Stats"])


@router.get("/summary")
async def get_stats_summary(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Computes lifetime workout stats, pushup/situp totals, and streaks."""
    db = get_db()
    user_id = current_user["_id"]

    cursor = db.workouts.find({"user_id": user_id}).sort("date", 1)
    
    total_workouts = 0
    total_pushups = 0
    total_situps = 0
    total_reps = 0
    total_duration_minutes = 0
    unique_active_days = set()

    today = utc_now().date()

    async for doc in cursor:
        total_workouts += 1
        total_duration_minutes += doc.get("duration_minutes", 0)
        workout_date = doc.get("date")
        if isinstance(workout_date, datetime):
            unique_active_days.add(workout_date.date())

        for ex in doc.get("exercises", []):
            name = ex.get("exercise_name", "").lower()
            ex_reps = ex.get("total_reps", 0)
            # If total_reps is 0, compute from sets
            if ex_reps == 0:
                ex_reps = sum(s.get("reps", 0) for s in ex.get("sets", []) if s.get("completed", True))

            total_reps += ex_reps
            if "push" in name:
                total_pushups += ex_reps
            elif "sit" in name:
                total_situps += ex_reps

    # Calculate current streak and longest streak
    sorted_days = sorted(list(unique_active_days))
    current_streak = 0
    longest_streak = 0

    if sorted_days:
        # Check current streak
        check_date = today
        # If user hasn't worked out today yet, check starting yesterday
        if check_date not in unique_active_days:
            check_date = today - timedelta(days=1)
        
        while check_date in unique_active_days:
            current_streak += 1
            check_date -= timedelta(days=1)

        # Longest streak calculation
        temp_streak = 0
        prev_day = None
        for day in sorted_days:
            if prev_day is None or day == prev_day + timedelta(days=1):
                temp_streak += 1
            elif day != prev_day:
                temp_streak = 1
            if temp_streak > longest_streak:
                longest_streak = temp_streak
            prev_day = day

    # Today's stats specifically
    today_start = datetime.combine(today, time.min)
    today_end = datetime.combine(today, time.max)
    today_cursor = db.workouts.find({
        "user_id": user_id,
        "date": {"$gte": today_start, "$lte": today_end}
    })
    today_pushups = 0
    today_situps = 0
    today_total_reps = 0

    async for doc in today_cursor:
        for ex in doc.get("exercises", []):
            name = ex.get("exercise_name", "").lower()
            reps = ex.get("total_reps", 0)
            if reps == 0:
                reps = sum(s.get("reps", 0) for s in ex.get("sets", []) if s.get("completed", True))
            today_total_reps += reps
            if "push" in name:
                today_pushups += reps
            elif "sit" in name:
                today_situps += reps

    return {
        "total_workouts": total_workouts,
        "total_pushups": total_pushups,
        "total_situps": total_situps,
        "total_reps": total_reps,
        "total_duration_minutes": total_duration_minutes,
        "current_streak_days": current_streak,
        "longest_streak_days": max(longest_streak, current_streak),
        "today": {
            "pushups": today_pushups,
            "situps": today_situps,
            "total_reps": today_total_reps
        }
    }


@router.get("/prs")
async def get_personal_records(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Computes Personal Records (PRs) per exercise: max reps in a single set and max reps in one day."""
    db = get_db()
    user_id = current_user["_id"]

    cursor = db.workouts.find({"user_id": user_id})
    records: Dict[str, Dict[str, Any]] = {}
    daily_reps_by_exercise: Dict[str, Dict[str, int]] = {}

    async for doc in cursor:
        workout_date = doc.get("date")
        date_str = workout_date.strftime("%Y-%m-%d") if isinstance(workout_date, datetime) else str(workout_date)[:10]

        for ex in doc.get("exercises", []):
            name = ex.get("exercise_name", "Unknown")
            if name not in records:
                records[name] = {
                    "exercise_name": name,
                    "max_set_reps": 0,
                    "max_daily_reps": 0,
                    "max_weight": 0.0,
                    "max_duration_seconds": 0,
                    "total_sessions": 0,
                }
            records[name]["total_sessions"] += 1

            if name not in daily_reps_by_exercise:
                daily_reps_by_exercise[name] = {}

            # Process sets
            set_sum = 0
            for s in ex.get("sets", []):
                reps = s.get("reps", 0)
                weight = s.get("weight", 0.0)
                duration = s.get("duration_seconds", 0)

                if reps > records[name]["max_set_reps"]:
                    records[name]["max_set_reps"] = reps
                if weight > records[name]["max_weight"]:
                    records[name]["max_weight"] = weight
                if duration > records[name]["max_duration_seconds"]:
                    records[name]["max_duration_seconds"] = duration
                
                set_sum += reps

            daily_reps_by_exercise[name][date_str] = daily_reps_by_exercise[name].get(date_str, 0) + set_sum

    # Update max daily reps
    for ex_name, dates in daily_reps_by_exercise.items():
        if dates and ex_name in records:
            records[ex_name]["max_daily_reps"] = max(dates.values())

    return list(records.values())


@router.get("/chart-data")
async def get_chart_data(
    days: int = Query(14, ge=7, le=90),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Returns time-series daily aggregated reps for the last N days,
    breaking down Push-ups, Sit-ups, and Others.
    """
    db = get_db()
    user_id = current_user["_id"]

    start_date = utc_now() - timedelta(days=days)
    cursor = db.workouts.find({
        "user_id": user_id,
        "date": {"$gte": start_date}
    }).sort("date", 1)

    # Initialize daily map for all dates in the range
    daily_map: Dict[str, Dict[str, int]] = {}
    for i in range(days + 1):
        d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        daily_map[d] = {
            "date": d,
            "pushups": 0,
            "situps": 0,
            "other_reps": 0,
            "total_reps": 0
        }

    async for doc in cursor:
        dt = doc.get("date")
        if not isinstance(dt, datetime):
            continue
        d_str = dt.strftime("%Y-%m-%d")
        if d_str not in daily_map:
            daily_map[d_str] = {
                "date": d_str,
                "pushups": 0,
                "situps": 0,
                "other_reps": 0,
                "total_reps": 0
            }

        for ex in doc.get("exercises", []):
            name = ex.get("exercise_name", "").lower()
            reps = ex.get("total_reps", 0)
            if reps == 0:
                reps = sum(s.get("reps", 0) for s in ex.get("sets", []) if s.get("completed", True))

            daily_map[d_str]["total_reps"] += reps
            if "push" in name:
                daily_map[d_str]["pushups"] += reps
            elif "sit" in name:
                daily_map[d_str]["situps"] += reps
            else:
                daily_map[d_str]["other_reps"] += reps

    return sorted(list(daily_map.values()), key=lambda x: x["date"])
