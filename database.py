import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

mongo = AsyncIOMotorClient(os.environ["MONGO_URI"])
db = mongo[os.environ.get("DB_NAME", "soundbox")]

sounds = db.sounds


async def init_db():
    await sounds.create_index("name", unique=True)
    await sounds.create_index("sound_id", unique=True, sparse=True)


async def save_sound(data):
    return await sounds.insert_one(data)


async def get_sound(name):
    return await sounds.find_one({
        "name": name.lower()
    })


async def get_all_sounds():
    cursor = sounds.find({}).sort("sound_id", 1)
    return await cursor.to_list(length=1000)


async def delete_sound(name):
    return await sounds.delete_one({
        "name": name.lower()
    })