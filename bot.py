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
    resume
)


load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]

OWNER_ID = int(os.environ["OWNER_ID"])

STORAGE_CHANNEL_ID = int(
    os.environ["STORAGE_CHANNEL_ID"]
)

DEFAULT_VC_CHAT_ID = int(
    os.environ["DEFAULT_VC_CHAT_ID"]
)


bot = Bot(BOT_TOKEN)
dp = Dispatcher()


def owner(message: Message):
    return (
        message.from_user
        and message.from_user.id == OWNER_ID
    )


def private(message: Message):
    return message.chat.type == "private"


def extract_file(message):

    if message.audio:
        return {
            "file_id": message.audio.file_id,
            "unique_id": message.audio.file_unique_id,
            "type": "audio",
            "name": message.audio.file_name,
            "duration": message.audio.duration
        }

    if message.voice:
        return {
            "file_id": message.voice.file_id,
            "unique_id": message.voice.file_unique_id,
            "type": "voice",
            "name": None,
            "duration": message.voice.duration
        }

    if message.document:
        return {
            "file_id": message.document.file_id,
            "unique_id": message.document.file_unique_id,
            "type": "document",
            "name": message.document.file_name,
            "duration": None
        }

    return None


@dp.message(Command("start"))
async def start(message: Message):

    await message.answer(
        "🎵 Sound Box\n\n"
        "/sounds - sounds list\n"
        "/get <name> - get sound\n"
        "/play <name> - play in VC\n"
        "/stop - stop playback\n"
        "/pause - pause\n"
        "/resume - resume"
    )


@dp.message(Command("add"))
async def add(message: Message):

    if not owner(message):
        return

    if not private(message):
        await message.answer(
            "❌ /add sirf owner DM mein use karo."
        )
        return

    if not message.reply_to_message:
        await message.answer(
            "❌ Audio ko reply karke:\n"
            "/add hello 1"
        )
        return

    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "Example:\n/add hello 1"
        )
        return

    name = args[1].lower()

    sound_id = None

    if len(args) >= 3:
        try:
            sound_id = int(args[2])
        except ValueError:
            await message.answer(
                "❌ Sound ID number hona chahiye."
            )
            return

    file = extract_file(
        message.reply_to_message
    )

    if not file:
        await message.answer(
            "❌ Audio/voice/document nahi mila."
        )
        return

    old = await get_sound(name)

    if old:
        await message.answer(
            "❌ Ye sound already exist karta hai."
        )
        return

    # Automatically copy to storage channel
    try:

        sent = await bot.copy_message(
            chat_id=STORAGE_CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.reply_to_message.message_id
        )

    except Exception as e:

        await message.answer(
            "❌ Storage channel mein copy nahi hua.\n\n"
            "Check karo bot channel mein admin hai."
        )

        print(e)
        return

    data = {
        "name": name,
        "sound_id": sound_id,

        "bot_file_id": file["file_id"],
        "file_unique_id": file["unique_id"],
        "file_type": file["type"],

        "storage_chat_id": STORAGE_CHANNEL_ID,
        "storage_message_id": sent.message_id,

        "file_name": file["name"],
        "duration": file["duration"],

        "created_by": OWNER_ID,
        "created_at": datetime.now(timezone.utc)
    }

    try:

        await save_sound(data)

    except Exception as e:

        await message.answer(
            f"❌ MongoDB error:\n{e}"
        )
        return

    await message.answer(
        "✅ <b>Sound saved!</b>\n\n"
        f"🎵 Name: <code>{name}</code>\n"
        f"🔢 ID: <code>{sound_id}</code>\n"
        f"📦 Storage message: <code>{sent.message_id}</code>",
        parse_mode="HTML"
    )


@dp.message(Command("sounds"))
async def sounds(message: Message):

    data = await get_all_sounds()

    if not data:
        await message.answer(
            "📭 No sounds."
        )
        return

    text = "🎵 <b>Sounds</b>\n\n"

    for x in data:

        sid = x.get("sound_id")

        if sid:
            text += (
                f"<code>{sid}</code> "
                f"— <code>{x['name']}</code>\n"
            )
        else:
            text += (
                f"• <code>{x['name']}</code>\n"
            )

    await message.answer(
        text,
        parse_mode="HTML"
    )


@dp.message(Command("get"))
async def get(message: Message):

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "/get hello"
        )
        return

    name = args[1].lower()

    sound = await get_sound(name)

    if not sound:
        await message.answer(
            "❌ Sound nahi mila."
        )
        return

    file_id = sound["bot_file_id"]

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
            f"❌ Send error: {e}"
        )


@dp.message(Command("play"))
async def play(message: Message):

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "/play hello"
        )
        return

    name = args[1].lower()

    sound = await get_sound(name)

    if not sound:
        await message.answer(
            "❌ Sound nahi mila."
        )
        return

    # Bot file ID ko local file mein download
    temp_dir = "cache"
    os.makedirs(temp_dir, exist_ok=True)

    extension = "ogg"

    if sound["file_type"] == "audio":
        extension = "mp3"

    path = (
        f"{temp_dir}/"
        f"{sound['_id']}.{extension}"
    )

    try:

        await bot.download(
            sound["bot_file_id"],
            destination=path
        )

        await play_file(
            DEFAULT_VC_CHAT_ID,
            path
        )

        await message.answer(
            f"▶️ Playing: <b>{name}</b>",
            parse_mode="HTML"
        )

    except Exception as e:

        await message.answer(
            f"❌ Playback error:\n{e}"
        )


@dp.message(Command("stop"))
async def stop_cmd(message: Message):

    if not owner(message):
        return

    await stop(
        DEFAULT_VC_CHAT_ID
    )

    await message.answer(
        "⏹ Stopped."
    )


@dp.message(Command("pause"))
async def pause_cmd(message: Message):

    if not owner(message):
        return

    await pause(
        DEFAULT_VC_CHAT_ID
    )

    await message.answer(
        "⏸ Paused."
    )


@dp.message(Command("resume"))
async def resume_cmd(message: Message):

    if not owner(message):
        return

    await resume(
        DEFAULT_VC_CHAT_ID
    )

    await message.answer(
        "▶️ Resumed."
    )


@dp.message(Command("delete"))
async def delete_cmd(message: Message):

    if not owner(message):
        return

    if not private(message):
        return

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "/delete hello"
        )
        return

    name = args[1].lower()

    result = await delete_sound(name)

    if result.deleted_count == 0:
        await message.answer(
            "❌ Sound not found."
        )
        return

    await message.answer(
        f"🗑 Deleted: {name}"
    )


async def main():

    await init_db()

    await start_player()

    print("🎵 SoundBox started")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())