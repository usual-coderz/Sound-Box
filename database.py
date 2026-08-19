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

db = mongo[DB_NAME]

sounds = db.sounds


# ============================================================
# INIT DATABASE
# ============================================================

async def init_db():

    # --------------------------------------------------------
    # Test MongoDB connection
    # --------------------------------------------------------

    try:

        await mongo.admin.command(
            "ping"
        )

    except Exception as e:

        print(
            f"❌ MongoDB connection failed: {e}"
        )

        raise


    # --------------------------------------------------------
    # Existing indexes
    # --------------------------------------------------------

    existing_indexes = {}

    async for index in sounds.list_indexes():

        name = index.get("name")

        key = index.get("key")

        if name:
            existing_indexes[name] = {
                "key": key,
                "unique": index.get(
                    "unique",
                    False
                ),
                "sparse": index.get(
                    "sparse",
                    False
                )
            }


    # --------------------------------------------------------
    # NAME INDEX
    # --------------------------------------------------------
    #
    # Existing database already has:
    #
    # name_1
    #
    # So don't blindly create another index.
    #

    name_index = None

    for index_name, info in existing_indexes.items():

        key = info["key"]

        if (
            list(key.items())
            == [("name", 1)]
        ):

            name_index = index_name
            break


    if name_index:

        print(
            f"✅ Name index exists: "
            f"{name_index}"
        )

    else:

        await sounds.create_index(
            [("name", 1)],
            unique=True,
            name="sound_name_unique"
        )

        print(
            "✅ Created name index."
        )


    # --------------------------------------------------------
    # SOUND ID INDEX
    # --------------------------------------------------------

    sound_id_index = None

    for index_name, info in existing_indexes.items():

        key = info["key"]

        if (
            list(key.items())
            == [("sound_id", 1)]
        ):

            sound_id_index = index_name
            break


    if sound_id_index:

        print(
            f"✅ Sound ID index exists: "
            f"{sound_id_index}"
        )

    else:

        await sounds.create_index(
            [("sound_id", 1)],
            unique=True,
            sparse=True,
            name="sound_id_unique"
        )

        print(
            "✅ Created sound ID index."
        )


    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    print(
        f"✅ MongoDB connected: {DB_NAME}"
    )


# ============================================================
# SAVE
# ============================================================

async def save_sound(data):

    return await sounds.insert_one(
        data
    )


# ============================================================
# GET BY NAME
# ============================================================

async def get_sound(name):

    return await sounds.find_one({
        "name": name.lower()
    })


# ============================================================
# GET BY ID
# ============================================================

async def get_sound_by_id(
    sound_id: int
):

    return await sounds.find_one({
        "sound_id": int(sound_id)
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

async def delete_sound(name):

    return await sounds.delete_one({
        "name": name.lower()
    })


# ============================================================
# DELETE BY ID
# ============================================================

async def delete_sound_by_id(
    sound_id: int
):

    return await sounds.delete_one({
        "sound_id": int(sound_id)
    })