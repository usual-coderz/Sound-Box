import os
from typing import Any, Optional

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError


# ============================================================
# ENV
# ============================================================

load_dotenv()

MONGO_URI = os.environ["MONGO_URI"]

DB_NAME = os.environ.get(
    "DB_NAME",
    "soundbox"
)


# ============================================================
# MONGODB
# ============================================================

mongo = AsyncIOMotorClient(
    MONGO_URI,
    serverSelectionTimeoutMS=10000,
)

db = mongo[DB_NAME]

sounds = db["sounds"]


# ============================================================
# HELPERS
# ============================================================

def normalize_name(name: str) -> str:
    """
    Normalize sound names so:
        Hello
        HELLO
        hello

    all refer to the same sound.
    """

    return " ".join(
        str(name).strip().lower().split()
    )


# ============================================================
# INIT DATABASE
# ============================================================

async def init_db():
    """
    Check MongoDB connection and create indexes.
    """

    try:

        await mongo.admin.command(
            "ping"
        )

        await sounds.create_index(
            "name",
            unique=True,
            name="unique_sound_name",
        )

        await sounds.create_index(
            "sound_id",
            unique=True,
            sparse=True,
            name="unique_sound_id",
        )

        await sounds.create_index(
            "created_at",
            name="created_at_index",
        )

        print(
            f"✅ MongoDB connected: {DB_NAME}"
        )

    except Exception as e:

        print(
            f"❌ MongoDB connection failed: {e}"
        )

        raise


# ============================================================
# SAVE SOUND
# ============================================================

async def save_sound(
    data: dict[str, Any]
):
    """
    Save a sound document.

    Raises DuplicateKeyError if the name or ID
    already exists.
    """

    if "name" not in data:
        raise ValueError(
            "Sound name is required."
        )

    data["name"] = normalize_name(
        data["name"]
    )

    return await sounds.insert_one(
        data
    )


# ============================================================
# GET SOUND BY NAME
# ============================================================

async def get_sound(
    name: str
) -> Optional[dict]:

    name = normalize_name(
        name
    )

    return await sounds.find_one({

        "name": name

    })


# ============================================================
# GET SOUND BY ID
# ============================================================

async def get_sound_by_id(
    sound_id: int
) -> Optional[dict]:

    try:

        sound_id = int(
            sound_id
        )

    except (
        TypeError,
        ValueError
    ):

        return None

    return await sounds.find_one({

        "sound_id": sound_id

    })


# ============================================================
# GET ALL SOUNDS
# ============================================================

async def get_all_sounds():

    cursor = (
        sounds
        .find({})
        .sort(
            [
                (
                    "sound_id",
                    1
                ),
                (
                    "name",
                    1
                )
            ]
        )
    )

    return await cursor.to_list(
        length=1000
    )


# ============================================================
# DELETE BY NAME
# ============================================================

async def delete_sound(
    name: str
):

    name = normalize_name(
        name
    )

    return await sounds.delete_one({

        "name": name

    })


# ============================================================
# DELETE BY ID
# ============================================================

async def delete_sound_by_id(
    sound_id: int
):

    try:

        sound_id = int(
            sound_id
        )

    except (
        TypeError,
        ValueError
    ):

        return None

    return await sounds.delete_one({

        "sound_id": sound_id

    })


# ============================================================
# UPDATE SOUND
# ============================================================

async def update_sound(
    sound_id: int,
    updates: dict[str, Any]
):

    try:

        sound_id = int(
            sound_id
        )

    except (
        TypeError,
        ValueError
    ):

        return None

    if "name" in updates:

        updates["name"] = normalize_name(
            updates["name"]
        )

    return await sounds.update_one(

        {
            "sound_id": sound_id
        },

        {
            "$set": updates
        }

    )


# ============================================================
# COUNT SOUNDS
# ============================================================

async def count_sounds():

    return await sounds.count_documents({})


# ============================================================
# CLOSE DATABASE
# ============================================================

async def close_db():

    mongo.close()

    print(
        "🔌 MongoDB connection closed."
    )