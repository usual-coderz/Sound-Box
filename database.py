import os

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv


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
    MONGO_URI
)

db = mongo[
    DB_NAME
]

sounds = db.sounds


# ============================================================
# INIT
# ============================================================

async def init_db():

    await sounds.create_index(
        "name",
        unique=True
    )

    await sounds.create_index(
        "sound_id",
        unique=True,
        sparse=True
    )

    print(
        f"✅ MongoDB connected: {DB_NAME}"
    )


# ============================================================
# SAVE
# ============================================================

async def save_sound(
    data
):

    return await sounds.insert_one(
        data
    )


# ============================================================
# GET BY NAME
# ============================================================

async def get_sound(
    name
):

    return await sounds.find_one({

        "name":
            name.lower()

    })


# ============================================================
# GET BY ID
# ============================================================

async def get_sound_by_id(
    sound_id: int
):

    return await sounds.find_one({

        "sound_id":
            int(sound_id)

    })


# ============================================================
# GET ALL
# ============================================================

async def get_all_sounds():

    cursor = (
        sounds
        .find({})
        .sort(
            "sound_id",
            1
        )
    )

    return await cursor.to_list(
        length=1000
    )


# ============================================================
# DELETE BY NAME
# ============================================================

async def delete_sound(
    name
):

    return await sounds.delete_one({

        "name":
            name.lower()

    })


# ============================================================
# DELETE BY ID
# ============================================================

async def delete_sound_by_id(
    sound_id: int
):

    return await sounds.delete_one({

        "sound_id":
            int(sound_id)

    })