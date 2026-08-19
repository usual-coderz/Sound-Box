import os
import asyncio
from datetime import datetime, timezone

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from database import (
    init_db,
    save_sound,
    get_sound,
    get_all_sounds,
    delete_sound
)

from player import (
    start_player,
    play_file,
    stop,
    pause,
    resume,
    shutdown_player
)


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

def is_owner(message: Message) -> bool:

    return bool(
        message.from_user
        and message.from_user.id == OWNER_ID
    )


def is_private(message: Message) -> bool:

    return message.chat.type == "private"


def extract_file(message: Message):

    # Audio
    if message.audio:

        return {
            "file_id": message.audio.file_id,
            "unique_id": message.audio.file_unique_id,
            "type": "audio",
            "name": message.audio.file_name,
            "duration": message.audio.duration
        }

    # Voice
    if message.voice:

        return {
            "file_id": message.voice.file_id,
            "unique_id": message.voice.file_unique_id,
            "type": "voice",
            "name": None,
            "duration": message.voice.duration
        }

    # Document
    if message.document:

        return {
            "file_id": message.document.file_id,
            "unique_id": message.document.file_unique_id,
            "type": "document",
            "name": message.document.file_name,
            "duration": None
        }

    return None


# ============================================================
# START
# ============================================================

@dp.message(Command("start"))
async def start_command(message: Message):

    await message.answer(
        "🎵 <b>Sound Box</b>\n\n"

        "/sounds — sounds list\n"
        "/get &lt;name&gt; — get sound\n"
        "/play &lt;name&gt; — play in VC\n\n"

        "Owner:\n"
        "/add &lt;name&gt; &lt;id&gt;\n"
        "/delete &lt;name&gt;\n"
        "/stop\n"
        "/pause\n"
        "/resume",

        parse_mode="HTML"
    )


# ============================================================
# ADD SOUND
# ============================================================

@dp.message(Command("add"))
async def add_sound(message: Message):

    # Owner only
    if not is_owner(message):
        return

    # DM only
    if not is_private(message):

        await message.answer(
            "❌ /add sirf bot ke DM mein use kar sakte ho."
        )

        return

    # Must reply to audio
    if not message.reply_to_message:

        await message.answer(
            "❌ Pehle audio/voice ko reply karo.\n\n"
            "Example:\n"
            "/add hello 1"
        )

        return

    args = message.text.split()

    if len(args) < 2:

        await message.answer(
            "❌ Usage:\n"
            "/add hello 1"
        )

        return

    name = args[1].strip().lower()

    # Optional numeric ID
    sound_id = None

    if len(args) >= 3:

        try:
            sound_id = int(args[2])

        except ValueError:

            await message.answer(
                "❌ Sound ID number hona chahiye."
            )

            return

    # Extract Telegram file
    file_data = extract_file(
        message.reply_to_message
    )

    if not file_data:

        await message.answer(
            "❌ Replied message mein "
            "audio/voice/document nahi mila."
        )

        return

    # Check duplicate name
    existing = await get_sound(
        name
    )

    if existing:

        await message.answer(
            f"❌ <code>{name}</code> already exists.",
            parse_mode="HTML"
        )

        return

    # ========================================================
    # COPY TO STORAGE CHANNEL
    # ========================================================

    try:

        copied = await bot.copy_message(
            chat_id=STORAGE_CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.reply_to_message.message_id
        )

    except Exception as e:

        print(
            "Storage channel error:",
            repr(e)
        )

        await message.answer(
            "❌ Storage channel mein audio copy nahi hua.\n\n"
            "Check karo:\n"
            "• Bot channel mein admin hai\n"
            "• STORAGE_CHANNEL_ID correct hai"
        )

        return

    # ========================================================
    # SAVE MONGODB
    # ========================================================

    document = {

        "name": name,

        "sound_id": sound_id,

        "bot_file_id": file_data["file_id"],

        "file_unique_id":
            file_data["unique_id"],

        "file_type":
            file_data["type"],

        "file_name":
            file_data["name"],

        "duration":
            file_data["duration"],

        "storage_chat_id":
            STORAGE_CHANNEL_ID,

        "storage_message_id":
            copied.message_id,

        "created_by":
            OWNER_ID,

        "created_at":
            datetime.now(timezone.utc)
    }

    try:

        await save_sound(
            document
        )

    except Exception as e:

        print(
            "MongoDB error:",
            repr(e)
        )

        await message.answer(
            "❌ MongoDB mein save nahi hua."
        )

        return

    # ========================================================
    # SUCCESS
    # ========================================================

    await message.answer(

        "✅ <b>Sound Saved</b>\n\n"

        f"🎵 Name: "
        f"<code>{name}</code>\n"

        f"🔢 ID: "
        f"<code>{sound_id or 'N/A'}</code>\n"

        f"📦 Storage message: "
        f"<code>{copied.message_id}</code>",

        parse_mode="HTML"
    )


# ============================================================
# SOUNDS
# ============================================================

@dp.message(Command("sounds"))
async def sounds_command(message: Message):

    data = await get_all_sounds()

    if not data:

        await message.answer(
            "📭 No sounds saved."
        )

        return

    text = (
        "🎵 <b>Available Sounds</b>\n\n"
    )

    for item in data:

        name = item["name"]

        sound_id = item.get(
            "sound_id"
        )

        if sound_id is not None:

            text += (
                f"<code>{sound_id}</code>"
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

@dp.message(Command("get"))
async def get_command(message: Message):

    args = message.text.split(
        maxsplit=1
    )

    if len(args) < 2:

        await message.answer(
            "Usage:\n"
            "/get hello"
        )

        return

    name = args[1].strip().lower()

    sound = await get_sound(
        name
    )

    if not sound:

        await message.answer(
            "❌ Sound not found."
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

        print(
            "Get sound error:",
            repr(e)
        )

        await message.answer(
            "❌ Sound send failed."
        )


# ============================================================
# PLAY
# ============================================================

@dp.message(Command("play"))
async def play_command(message: Message):

    args = message.text.split(
        maxsplit=1
    )

    if len(args) < 2:

        await message.answer(
            "Usage:\n"
            "/play hello"
        )

        return

    name = args[1].strip().lower()

    sound = await get_sound(
        name
    )

    if not sound:

        await message.answer(
            "❌ Sound not found."
        )

        return

    # --------------------------------------------------------
    # Only owner can control VC
    # --------------------------------------------------------

    if not is_owner(message):

        await message.answer(
            "❌ Only owner can control playback."
        )

        return

    # --------------------------------------------------------
    # Cache
    # --------------------------------------------------------

    base_dir = os.path.dirname(
        os.path.abspath(__file__)
    )

    cache_dir = os.path.join(
        base_dir,
        "cache"
    )

    os.makedirs(
        cache_dir,
        mode=0o700,
        exist_ok=True
    )

    # Safe filename using Mongo ObjectId
    filename = str(
        sound["_id"]
    )

    if sound["file_type"] == "audio":

        extension = ".mp3"

    elif sound["file_type"] == "voice":

        extension = ".ogg"

    else:

        extension = ".bin"

    path = os.path.join(
        cache_dir,
        filename + extension
    )

    # --------------------------------------------------------
    # Download only if not cached
    # --------------------------------------------------------

    try:

        if not os.path.exists(path):

            print(
                f"Downloading {name}..."
            )

            await bot.download(
                sound["bot_file_id"],
                destination=path
            )

        else:

            print(
                f"Using cached file: {path}"
            )

        # ----------------------------------------------------
        # PLAY
        # ----------------------------------------------------

        await play_file(
            DEFAULT_VC_CHAT_ID,
            path
        )

        await message.answer(
            f"▶️ Playing "
            f"<b>{name}</b>",
            parse_mode="HTML"
        )

    except Exception as e:

        print(
            "Playback error:",
            repr(e)
        )

        await message.answer(
            f"❌ <b>Playback error:</b>\n"
            f"<code>{str(e)}</code>",
            parse_mode="HTML"
        )


# ============================================================
# STOP
# ============================================================

@dp.message(Command("stop"))
async def stop_command(message: Message):

    if not is_owner(message):
        return

    try:

        await stop(
            DEFAULT_VC_CHAT_ID
        )

        await message.answer(
            "⏹ Playback stopped."
        )

    except Exception as e:

        await message.answer(
            f"❌ Stop error:\n{e}"
        )


# ============================================================
# PAUSE
# ============================================================

@dp.message(Command("pause"))
async def pause_command(message: Message):

    if not is_owner(message):
        return

    try:

        await pause(
            DEFAULT_VC_CHAT_ID
        )

        await message.answer(
            "⏸ Playback paused."
        )

    except Exception as e:

        await message.answer(
            f"❌ Pause error:\n{e}"
        )


# ============================================================
# RESUME
# ============================================================

@dp.message(Command("resume"))
async def resume_command(message: Message):

    if not is_owner(message):
        return

    try:

        await resume(
            DEFAULT_VC_CHAT_ID
        )

        await message.answer(
            "▶️ Playback resumed."
        )

    except Exception as e:

        await message.answer(
            f"❌ Resume error:\n{e}"
        )


# ============================================================
# DELETE
# ============================================================

@dp.message(Command("delete"))
async def delete_command(message: Message):

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
            "/delete hello"
        )

        return

    name = args[1].strip().lower()

    result = await delete_sound(
        name
    )

    if result.deleted_count == 0:

        await message.answer(
            "❌ Sound not found."
        )

        return

    await message.answer(
        f"🗑 Deleted: "
        f"<code>{name}</code>",
        parse_mode="HTML"
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    print(
        "Initializing MongoDB..."
    )

    await init_db()

    print(
        "Initializing Telegram user..."
    )

    # IMPORTANT:
    # Telethon + PyTgCalls are initialized
    # inside THIS exact asyncio event loop.

    await start_player()

    print(
        "🎵 SoundBox started successfully."
    )

    try:

        await dp.start_polling(
            bot
        )

    finally:

        print(
            "Shutting down..."
        )

        await shutdown_player()

        await bot.session.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )