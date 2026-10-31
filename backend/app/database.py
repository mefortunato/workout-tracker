import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings, redact_uri

logger = logging.getLogger(__name__)

client: AsyncIOMotorClient = None
db: AsyncIOMotorDatabase = None


def get_db() -> AsyncIOMotorDatabase:
    global db
    if db is None:
        raise RuntimeError("Database not initialized yet.")
    return db


DEFAULT_EXERCISES = [
    {
        "name": "Push-ups",
        "category": "Upper Body",
        "type": "reps",
        "description": "Standard floor push-up targeting chest, shoulders, and triceps.",
        "icon": "flame",
        "is_default": True,
    },
    {
        "name": "Sit-ups",
        "category": "Core",
        "type": "reps",
        "description": "Core abdominal flexion exercise.",
        "icon": "shield",
        "is_default": True,
    },
    {
        "name": "Pull-ups",
        "category": "Upper Body",
        "type": "reps",
        "description": "Overhand grip vertical pull for lats and biceps.",
        "icon": "activity",
        "is_default": True,
    },
    {
        "name": "Squats",
        "category": "Lower Body",
        "type": "reps",
        "description": "Bodyweight or weighted squat for quadriceps, glutes, and hips.",
        "icon": "zap",
        "is_default": True,
    },
    {
        "name": "Dips",
        "category": "Upper Body",
        "type": "reps",
        "description": "Parallel bar or bench dips for triceps and lower chest.",
        "icon": "target",
        "is_default": True,
    },
    {
        "name": "Burpees",
        "category": "Full Body",
        "type": "reps",
        "description": "Full body explosive conditioning movement.",
        "icon": "trending-up",
        "is_default": True,
    },
    {
        "name": "Lunges",
        "category": "Lower Body",
        "type": "reps",
        "description": "Unilateral leg exercise for quad and glute strength.",
        "icon": "zap",
        "is_default": True,
    },
    {
        "name": "Plank",
        "category": "Core",
        "type": "duration",
        "description": "Isometric core stability hold (measured in seconds).",
        "icon": "shield",
        "is_default": True,
    },
    {
        "name": "Mountain Climbers",
        "category": "Core",
        "type": "reps",
        "description": "Dynamic alternating plank knees-to-chest.",
        "icon": "activity",
        "is_default": True,
    },
    {
        "name": "Bench Press",
        "category": "Upper Body",
        "type": "weight_reps",
        "description": "Barbell or dumbbell chest press.",
        "icon": "flame",
        "is_default": True,
    },
]


async def init_db():
    global client, db
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client[settings.DATABASE_NAME]
        
        # Test connection
        await client.admin.command('ping')
        logger.info(f"Connected to MongoDB at {redact_uri(settings.MONGODB_URI)}")

        # Create indexes
        await db.users.create_index("email", unique=True)
        await db.workouts.create_index([("user_id", 1), ("date", -1)])
        await db.workouts.create_index([("user_id", 1), ("exercises.exercise_name", 1)])
        await db.goals.create_index([("user_id", 1), ("is_active", 1)])
        await db.exercises.create_index([("name", 1), ("user_id", 1)])
        await db.challenges.create_index("invite_code", unique=True)
        await db.challenges.create_index("participants.user_id")
        await db.challenges.create_index("creator_id")

        # Seed default exercises if none exist
        count = await db.exercises.count_documents({"is_default": True})
        if count == 0:
            logger.info("Seeding default exercise library...")
            for ex in DEFAULT_EXERCISES:
                await db.exercises.update_one(
                    {"name": ex["name"], "is_default": True},
                    {"$setOnInsert": {**ex, "user_id": None}},
                    upsert=True
                )
    except Exception as e:
        logger.warning(f"Could not connect to MongoDB at {redact_uri(settings.MONGODB_URI)}: {e}. Ensure MongoDB is running.")


async def close_db():
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed.")
