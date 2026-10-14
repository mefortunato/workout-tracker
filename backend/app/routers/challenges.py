import logging
import secrets
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.database import get_db
from app.utils.auth_dep import get_current_user
from app.utils.dates import utc_now
from app.models.challenge import (
    ChallengeCreate,
    ChallengeJoinRequest,
    ChallengeResponse,
    ChallengeParticipantProgress,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/challenges", tags=["Challenges"])


def generate_invite_code() -> str:
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    part1 = "".join(secrets.choice(alphabet) for _ in range(3))
    part2 = "".join(secrets.choice(alphabet) for _ in range(3))
    return f"FIT-{part1}{part2}"


async def calculate_challenge_progress(
    challenge_doc: Dict[str, Any], current_user_id: str
) -> ChallengeResponse:
    db = get_db()
    c_id = str(challenge_doc["_id"])
    c_type = challenge_doc.get("challenge_type", "total_volume")
    target_value = challenge_doc.get("target_value", 100)
    target_ex = challenge_doc.get("exercise_name")
    start_str = challenge_doc.get("start_date")
    end_str = challenge_doc.get("end_date")

    try:
        start_d = date.fromisoformat(start_str)
        end_d = date.fromisoformat(end_str)
    except Exception:
        today = utc_now().date()
        start_d = today
        end_d = today + timedelta(days=30)
        start_str = start_d.isoformat()
        end_str = end_d.isoformat()

    start_dt = datetime.combine(start_d, time.min)
    end_dt = datetime.combine(end_d, time.max)
    today = utc_now().date()

    # Timeframe calculation
    days_remaining = max(0, (end_d - today).days)
    if today < start_d:
        status_val = "upcoming"
    elif today > end_d:
        status_val = "completed"
    else:
        status_val = "active"

    total_challenge_days = max(1, (end_d - start_d).days + 1)
    participants = challenge_doc.get("participants", [])

    leaderboard_list: List[ChallengeParticipantProgress] = []

    for p in participants:
        p_user_id = str(p.get("user_id"))
        p_name = p.get("name") or "Athlete"
        p_avatar = p.get("avatar")
        p_joined_at = p.get("joined_at") or utc_now()

        # Gather workouts in challenge timeframe
        cursor = db.workouts.find({
            "user_id": p_user_id,
            "date": {"$gte": start_dt, "$lte": end_dt}
        })

        reps_by_day: Dict[date, int] = {}
        last_active: Optional[datetime] = None

        async for w in cursor:
            w_date = w.get("date")
            if not isinstance(w_date, datetime):
                continue
            if last_active is None or w_date > last_active:
                last_active = w_date

            day_key = w_date.date()
            day_reps = 0

            for ex in w.get("exercises", []):
                ex_name = ex.get("exercise_name", "")
                if not target_ex or target_ex.lower() == "all" or target_ex.lower() in ex_name.lower():
                    reps = ex.get("total_reps", 0)
                    if reps == 0:
                        reps = sum(
                            s.get("reps", 0)
                            for s in ex.get("sets", [])
                            if s.get("completed", True)
                        )
                    day_reps += reps

            reps_by_day[day_key] = reps_by_day.get(day_key, 0) + day_reps

        # Compute metrics based on challenge type
        if c_type == "daily_streak":
            achieved_days = {d for d, reps in reps_by_day.items() if reps >= target_value}
            days_completed = len(achieved_days)
            progress_pct = min(100.0, round((days_completed / total_challenge_days) * 100, 1))
            is_completed = days_completed >= total_challenge_days

            # Calculate current consecutive streak up to today
            streak = 0
            check_d = today
            # If today has not been achieved yet, check if yesterday was achieved
            if check_d not in achieved_days and (check_d - timedelta(days=1)) in achieved_days:
                check_d = check_d - timedelta(days=1)

            while check_d >= start_d and check_d in achieved_days:
                streak += 1
                check_d -= timedelta(days=1)

            entry = ChallengeParticipantProgress(
                user_id=p_user_id,
                name=p_name,
                avatar=p_avatar,
                joined_at=p_joined_at,
                completed_reps=sum(reps_by_day.values()),
                target_reps=target_value * total_challenge_days,
                days_completed=days_completed,
                target_days=total_challenge_days,
                current_streak=streak,
                progress_percentage=progress_pct,
                is_completed=is_completed,
                rank=1,
                last_active=last_active,
            )
        else:
            # Default: total_volume
            completed_reps = sum(reps_by_day.values())
            progress_pct = min(100.0, round((completed_reps / max(target_value, 1)) * 100, 1))
            is_completed = completed_reps >= target_value

            entry = ChallengeParticipantProgress(
                user_id=p_user_id,
                name=p_name,
                avatar=p_avatar,
                joined_at=p_joined_at,
                completed_reps=completed_reps,
                target_reps=target_value,
                days_completed=len(reps_by_day),
                target_days=total_challenge_days,
                current_streak=0,
                progress_percentage=progress_pct,
                is_completed=is_completed,
                rank=1,
                last_active=last_active,
            )

        leaderboard_list.append(entry)

    # Sort leaderboard
    if c_type == "daily_streak":
        leaderboard_list.sort(
            key=lambda x: (x.days_completed, x.current_streak, x.completed_reps),
            reverse=True
        )
    else:
        leaderboard_list.sort(
            key=lambda x: (x.completed_reps, x.progress_percentage),
            reverse=True
        )

    # Assign ranks
    for rank_idx, item in enumerate(leaderboard_list, 1):
        item.rank = rank_idx

    # Find current user's progress
    user_prog = next((item for item in leaderboard_list if item.user_id == current_user_id), None)
    is_joined = user_prog is not None

    return ChallengeResponse(
        _id=c_id,
        title=challenge_doc.get("title", "Workout Challenge"),
        description=challenge_doc.get("description", ""),
        challenge_type=c_type,
        exercise_name=target_ex,
        target_value=target_value,
        start_date=start_str,
        end_date=end_str,
        creator_id=str(challenge_doc.get("creator_id")),
        creator_name=challenge_doc.get("creator_name", "Athlete"),
        invite_code=challenge_doc.get("invite_code", ""),
        participants_count=len(participants),
        is_user_joined=is_joined,
        user_progress=user_prog,
        leaderboard=leaderboard_list,
        days_remaining=days_remaining,
        status=status_val,
        created_at=challenge_doc.get("created_at") or utc_now(),
    )


@router.post("", response_model=ChallengeResponse, status_code=status.HTTP_201_CREATED)
async def create_challenge(
    data: ChallengeCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    db = get_db()
    user_id = str(current_user["_id"])
    user_name = current_user.get("name") or current_user.get("email", "Athlete").split("@")[0]
    user_avatar = current_user.get("picture")

    # Validate dates
    try:
        s_date = date.fromisoformat(data.start_date)
        e_date = date.fromisoformat(data.end_date)
        if e_date < s_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date cannot be earlier than start date."
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dates must be in ISO format (YYYY-MM-DD)."
        )

    if data.target_value <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target value must be greater than zero."
        )

    # Generate unique invite code
    invite_code = generate_invite_code()
    for _ in range(5):
        existing = await db.challenges.find_one({"invite_code": invite_code})
        if not existing:
            break
        invite_code = generate_invite_code()

    challenge_doc = {
        "title": data.title.strip(),
        "description": (data.description or "").strip(),
        "challenge_type": data.challenge_type,
        "exercise_name": data.exercise_name or "Push-ups",
        "target_value": data.target_value,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "creator_id": user_id,
        "creator_name": user_name,
        "invite_code": invite_code,
        "participants": [
            {
                "user_id": user_id,
                "name": user_name,
                "email": current_user.get("email"),
                "avatar": user_avatar,
                "joined_at": utc_now(),
            }
        ],
        "created_at": utc_now(),
    }

    result = await db.challenges.insert_one(challenge_doc)
    challenge_doc["_id"] = result.inserted_id

    return await calculate_challenge_progress(challenge_doc, user_id)


@router.get("", response_model=List[ChallengeResponse])
async def get_my_challenges(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    db = get_db()
    user_id = str(current_user["_id"])

    # Fetch challenges where user is creator or participant
    cursor = db.challenges.find({
        "$or": [
            {"participants.user_id": user_id},
            {"creator_id": user_id}
        ]
    }).sort("created_at", -1)

    challenges = []
    async for doc in cursor:
        challenges.append(await calculate_challenge_progress(doc, user_id))

    return challenges


@router.post("/join", response_model=ChallengeResponse)
async def join_challenge_by_code(
    payload: ChallengeJoinRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    db = get_db()
    user_id = str(current_user["_id"])
    code = payload.invite_code.strip().upper()

    challenge_doc = await db.challenges.find_one({"invite_code": code})
    if not challenge_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge with invite code '{code}' was not found. Please verify the code."
        )

    # Check if already joined
    participants = challenge_doc.get("participants", [])
    already_joined = any(str(p.get("user_id")) == user_id for p in participants)

    if not already_joined:
        user_name = current_user.get("name") or current_user.get("email", "Athlete").split("@")[0]
        user_avatar = current_user.get("picture")

        new_participant = {
            "user_id": user_id,
            "name": user_name,
            "email": current_user.get("email"),
            "avatar": user_avatar,
            "joined_at": utc_now(),
        }

        await db.challenges.update_one(
            {"_id": challenge_doc["_id"]},
            {"$push": {"participants": new_participant}}
        )
        challenge_doc["participants"].append(new_participant)

    return await calculate_challenge_progress(challenge_doc, user_id)


@router.get("/{challenge_id}", response_model=ChallengeResponse)
async def get_challenge_detail(
    challenge_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    db = get_db()
    try:
        obj_id = ObjectId(challenge_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid challenge ID")

    challenge_doc = await db.challenges.find_one({"_id": obj_id})
    if not challenge_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

    user_id = str(current_user["_id"])
    return await calculate_challenge_progress(challenge_doc, user_id)


@router.post("/{challenge_id}/leave")
async def leave_challenge(
    challenge_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    db = get_db()
    try:
        obj_id = ObjectId(challenge_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid challenge ID")

    challenge_doc = await db.challenges.find_one({"_id": obj_id})
    if not challenge_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

    user_id = str(current_user["_id"])
    participants = challenge_doc.get("participants", [])
    is_participant = any(str(p.get("user_id")) == user_id for p in participants)

    if not is_participant:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not a member of this challenge")

    # If creator is the only participant, delete the challenge
    if str(challenge_doc.get("creator_id")) == user_id and len(participants) <= 1:
        await db.challenges.delete_one({"_id": obj_id})
        return {"message": "Challenge deleted as creator was the only member."}

    # Otherwise remove user from participants list
    await db.challenges.update_one(
        {"_id": obj_id},
        {"$pull": {"participants": {"user_id": user_id}}}
    )

    return {"message": "Successfully left the group challenge."}


@router.delete("/{challenge_id}")
async def delete_challenge(
    challenge_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    db = get_db()
    try:
        obj_id = ObjectId(challenge_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid challenge ID")

    challenge_doc = await db.challenges.find_one({"_id": obj_id})
    if not challenge_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

    user_id = str(current_user["_id"])
    if str(challenge_doc.get("creator_id")) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the challenge creator can delete it")

    await db.challenges.delete_one({"_id": obj_id})
    return {"message": "Challenge deleted successfully."}
