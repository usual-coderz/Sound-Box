import asyncio
import os
from datetime import datetime, timezone

import uvicorn
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from database import (
    init_db,
    save_sound,
    get_sound,
    get_sound_by_id,
    get_all_sounds,
    delete_sound,
)

from player import (
    start_player,
    play_file,
    stop,
    pause,
    resume,
    shutdown_player,
)

from web import app


# ============================================================
# ENV
# ============================================================

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]

OWNER_ID = int(
    os.environ["OWNER_ID"]
)

STORAGE_CHANNEL_ID = int(
    os.environ["STORAGE_CHANNEL_ID"]
)

DEFAULT_VC_CHAT_ID = int(
    os.environ["DEFAULT_VC_CHAT_ID"]
)

WEB_HOST = os.getenv(
    "WEB_HOST",
    "0.0.0.0"
)

WEB_PORT = int(
    os.getenv(
        "WEB_PORT",
        "8000"
    )
)


# ============================================================
# BOT
# ============================================================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


# ============================================================
# HELPERS
# ============================================================

def is_owner(
    message: Message
) -> bool:

    return (
        message.from_user is not None
        and
        message.from_user.id == OWNER_ID
    )


def is_private(
    message: Message
) -> bool:

    return (
        message.chat.type == "private"
    )


def extract_file(
    message: Message
):

    if message.audio:

        return {
            "file_id":
                message.audio.file_id,

            "unique_id":
                message.audio.file_unique_id,

            "type":
                "audio",

            "name":
                message.audio.file_name,

            "duration":
                message.audio.duration,
        }


    if message.voice:

        return {
            "file_id":
                message.voice.file_id,

            "unique_id":
                message.voice.file_unique_id,

            "type":
                "voice",

            "name":
                None,

            "duration":
                message.voice.duration,
        }


    if message.document:

        return {
            "file_id":
                message.document.file_id,

            "unique_id":
                message.document.file_unique_id,

            "type":
                "document",

            "name":
                message.document.file_name,

            "duration":
                None,
        }


    return None


# ============================================================
# START
# ============================================================

@dp.message(
    Command("start")
)
async def start_command(
    message: Message
):

    await message.answer(
        "🎵 <b>Sound Box</b>\n\n"

        "🎧 Playback:\n"
        "/play 1\n"
        "/play hello\n"
        "/stop\n"
        "/pause\n"
        "/resume\n\n"

        "📚 Sounds:\n"
        "/sounds\n"
        "/get hello\n\n"

        "👑 Owner:\n"
        "Reply audio + /add hello 1\n"
        "/delete hello",

        parse_mode="HTML"
    )


# ============================================================
# ADD SOUND
# ============================================================

@dp.message(
    Command("add")
)
async def add_sound_command(
    message: Message
):

    # Owner only
    if not is_owner(message):
        return


    # DM only
    if not is_private(message):

        await message.answer(
            "❌ /add sirf owner DM mein use karo."
        )

        return


    # Must reply
    if not message.reply_to_message:

        await message.answer(
            "❌ Audio ko reply karke use karo:\n\n"
            "<code>/add hello 1</code>",
            parse_mode="HTML"
        )

        return


    args = message.text.split()


    if len(args) < 2:

        await message.answer(
            "Example:\n"
            "<code>/add hello 1</code>",
            parse_mode="HTML"
        )

        return


    name = args[1].strip().lower()


    # Optional numeric ID
    sound_id = None


    if len(args) >= 3:

        try:

            sound_id = int(
                args[2]
            )

        except ValueError:

            await message.answer(
                "❌ Sound ID number hona chahiye."
            )

            return


    # Check duplicate name
    old = await get_sound(
        name
    )


    if old:

        await message.answer(
            "❌ Ye sound already exist karta hai."
        )

        return


    # Check duplicate ID
    if sound_id is not None:

        old_id = await get_sound_by_id(
            sound_id
        )

        if old_id:

            await message.answer(
                "❌ Ye sound ID already exist karti hai."
            )

            return


    # Extract media
    file = extract_file(
        message.reply_to_message
    )


    if not file:

        await message.answer(
            "❌ Audio, voice ya document reply karo."
        )

        return


    # ========================================================
    # COPY TO STORAGE CHANNEL
    # ========================================================

    try:

        sent = await bot.copy_message(

            chat_id=STORAGE_CHANNEL_ID,

            from_chat_id=message.chat.id,

            message_id=(
                message
                .reply_to_message
                .message_id
            )
        )

    except Exception as e:

        print(
            "Storage channel error:",
            repr(e)
        )

        await message.answer(
            "❌ Storage channel mein audio copy nahi hua.\n\n"
            "Check karo bot channel mein admin hai."
        )

        return


    # ========================================================
    # DATABASE
    # ========================================================

    data = {

        "name":
            name,

        "sound_id":
            sound_id,

        "bot_file_id":
            file["file_id"],

        "file_unique_id":
            file["unique_id"],

        "file_type":
            file["type"],

        "storage_chat_id":
            STORAGE_CHANNEL_ID,

        "storage_message_id":
            sent.message_id,

        "file_name":
            file["name"],

        "duration":
            file["duration"],

        "created_by":
            OWNER_ID,

        "created_at":
            datetime.now(
                timezone.utc
            ),
    }


    try:

        await save_sound(
            data
        )

    except Exception as e:

        print(
            "MongoDB save error:",
            repr(e)
        )

        await message.answer(
            f"❌ MongoDB error:\n<code>{e}</code>",
            parse_mode="HTML"
        )

        return


    await message.answer(

        "✅ <b>Sound saved!</b>\n\n"

        f"🎵 Name: "
        f"<code>{name}</code>\n"

        f"🔢 ID: "
        f"<code>{sound_id}</code>\n"

        f"📦 Storage message: "
        f"<code>{sent.message_id}</code>\n\n"

        "🌐 Web soundboard mein bhi automatically appear hoga.",

        parse_mode="HTML"
    )


# ============================================================
# SOUNDS
# ============================================================

@dp.message(
    Command("sounds")
)
async def sounds_command(
    message: Message
):

    data = await get_all_sounds()


    if not data:

        await message.answer(
            "📭 No sounds."
        )

        return


    text = (
        "🎵 <b>Sound Box</b>\n\n"
    )


    for sound in data:

        sound_id = sound.get(
            "sound_id"
        )

        name = sound.get(
            "name",
            "Unknown"
        )


        if sound_id is not None:

            text += (
                f"🔊 <code>{sound_id}</code>"
                f" — "
                f"<code>{name}</code>\n"
            )

        else:

            text += (
                f"• <code>{name}</code>\n"
            )


    await message.answer(
        text,
        parse_mode="HTML"
    )


# ============================================================
# GET SOUND
# ============================================================

@dp.message(
    Command("get")
)
async def get_command(
    message: Message
):

    args = message.text.split(
        maxsplit=1
    )


    if len(args) < 2:

        await message.answer(
            "Usage:\n"
            "<code>/get hello</code>",
            parse_mode="HTML"
        )

        return


    value = args[1].strip().lower()


    # First try ID
    sound = None


    try:

        sound_id = int(
            value
        )

        sound = await get_sound_by_id(
            sound_id
        )

    except ValueError:

        pass


    # Then try name
    if sound is None:

        sound = await get_sound(
            value
        )


    if not sound:

        await message.answer(
            "❌ Sound nahi mila."
        )

        return


    file_id = sound[
        "bot_file_id"
    ]


    try:

        if sound["file_type"] == "audio":

            await message.answer_audio(
                file_id
            )

        elif sound["file_type"] == "voice":

            await message.answer_voice(
                file_id
            )

        else:

            await message.answer_document(
                file_id
            )


    except Exception as e:

        await message.answer(
            f"❌ Send error:\n{e}"
        )


# ============================================================
# PLAY
# ============================================================

@dp.message(
    Command("play")
)
async def play_command(
    message: Message
):

    args = message.text.split(
        maxsplit=1
    )


    if len(args) < 2:

        await message.answer(
            "Usage:\n"
            "<code>/play 1</code>\n"
            "or\n"
            "<code>/play hello</code>",
            parse_mode="HTML"
        )

        return


    value = args[1].strip().lower()


    # ========================================================
    # FIND SOUND
    # ========================================================

    sound = None


    # Number = sound ID
    try:

        sound_id = int(
            value
        )

        sound = await get_sound_by_id(
            sound_id
        )

    except ValueError:

        pass


    # Name
    if sound is None:

        sound = await get_sound(
            value
        )


    if not sound:

        await message.answer(
            "❌ Sound nahi mila."
        )

        return


    # ========================================================
    # CACHE
    # ========================================================

    cache_dir = "cache"

    os.makedirs(
        cache_dir,
        mode=0o700,
        exist_ok=True
    )


    mongo_id = str(
        sound["_id"]
    )


    file_type = sound.get(
        "file_type"
    )


    if file_type == "audio":

        extension = ".mp3"

    elif file_type == "voice":

        extension = ".ogg"

    else:

        extension = ".bin"


    path = os.path.join(
        cache_dir,
        mongo_id + extension
    )


    # ========================================================
    # DOWNLOAD IF NEEDED
    # ========================================================

    try:

        if not os.path.exists(
            path
        ):

            print(
                "⬇️ Downloading sound:",
                sound["name"]
            )

            await bot.download(
                sound["bot_file_id"],
                destination=path
            )


        # ====================================================
        # PLAY
        # ====================================================

        await play_file(
            DEFAULT_VC_CHAT_ID,
            path
        )


        await message.answer(
            f"▶️ Playing: "
            f"<b>{sound['name']}</b>",
            parse_mode="HTML"
        )


    except Exception as e:

        print(
            "Playback error:",
            repr(e)
        )

        await message.answer(
            f"❌ Playback error:\n"
            f"<code>{e}</code>",
            parse_mode="HTML"
        )


# ============================================================
# STOP
# ============================================================

@dp.message(
    Command("stop")
)
async def stop_command(
    message: Message
):

    if not is_owner(message):
        return


    try:

        await stop(
            DEFAULT_VC_CHAT_ID
        )

        await message.answer(
            "⏹ Stopped."
        )

    except Exception as e:

        await message.answer(
            f"❌ Stop error:\n{e}"
        )


# ============================================================
# PAUSE
# ============================================================

@dp.message(
    Command("pause")
)
async def pause_command(
    message: Message
):

    if not is_owner(message):
        return


    try:

        await pause(
            DEFAULT_VC_CHAT_ID
        )

        await message.answer(
            "⏸ Paused."
        )

    except Exception as e:

        await message.answer(
            f"❌ Pause error:\n{e}"
        )


# ============================================================
# RESUME
# ============================================================

@dp.message(
    Command("resume")
)
async def resume_command(
    message: Message
):

    if not is_owner(message):
        return


    try:

        await resume(
            DEFAULT_VC_CHAT_ID
        )

        await message.answer(
            "▶️ Resumed."
        )

    except Exception as e:

        await message.answer(
            f"❌ Resume error:\n{e}"
        )


# ============================================================
# DELETE
# ============================================================

@dp.message(
    Command("delete")
)
async def delete_command(
    message: Message
):

    if not is_owner(message):
        return


    if not is_private(message):
        return


    args = message.text.split(
        maxsplit=1
    )


    if len(args) < 2:

        await message.answer(
            "Usage:\n"
            "<code>/delete hello</code>",
            parse_mode="HTML"
        )

        return


    value = args[1].strip().lower()


    # Name only for delete
    result = await delete_sound(
        value
    )


    if result.deleted_count == 0:

        await message.answer(
            "❌ Sound not found."
        )

        return


    await message.answer(
        f"🗑 Deleted: "
        f"<code>{value}</code>",
        parse_mode="HTML"
    )


# ============================================================
# WEB SERVER
# ============================================================

async def start_web():

    config = uvicorn.Config(

        app,

        host=WEB_HOST,

        port=WEB_PORT,

        loop="asyncio",

        log_level="info"
    )


    server = uvicorn.Server(
        config
    )


    await server.serve()


# ============================================================
# MAIN
# ============================================================

async def main():

    print(
        "🚀 Starting Sound Box..."
    )


    # MongoDB
    await init_db()

    print(
        "✅ MongoDB connected."
    )


    # Telegram user + PyTgCalls
    await start_player()


    print(
        "🎧 Player ready."
    )


    # Start web server in SAME asyncio loop
    web_task = asyncio.create_task(
        start_web()
    )


    print(
        f"🌐 Web server: "
        f"http://0.0.0.0:{WEB_PORT}"
    )


    try:

        # Bot polling
        await dp.start_polling(
            bot
        )

    finally:

        print(
            "🛑 Shutting down..."
        )


        web_task.cancel()

        try:

            await web_task

        except asyncio.CancelledError:

            pass


        await shutdown_player()

        await bot.session.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "👋 Stopped."
        )