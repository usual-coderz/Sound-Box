import os
import asyncio

from dotenv import load_dotenv
from telethon import TelegramClient
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream

load_dotenv()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
PHONE_NUMBER = os.environ["PHONE_NUMBER"]

DEFAULT_VC_CHAT_ID = int(os.environ["DEFAULT_VC_CHAT_ID"])

session = "sessions/soundbox"

user = TelegramClient(
    session,
    API_ID,
    API_HASH
)

calls = PyTgCalls(user)

queue = []
current = None
playing_chat = None


async def start_player():
    await user.start(
        phone=PHONE_NUMBER
    )

    await calls.start()

    print("Telegram user connected.")
    print("PyTgCalls started.")


async def play_file(chat_id, file_path):
    global current
    global playing_chat

    playing_chat = chat_id
    current = file_path

    stream = MediaStream(
        file_path,
        video_flags=MediaStream.Flags.IGNORE
    )

    try:
        await calls.play(
            chat_id,
            stream
        )

    except Exception:
        # Depending on PyTgCalls version,
        # play may need a joined call first.
        await calls.join_group_call(
            chat_id,
            stream
        )


async def stop(chat_id):
    global current

    try:
        await calls.leave_group_call(chat_id)
    except Exception:
        pass

    current = None


async def pause(chat_id):
    try:
        await calls.pause(chat_id)
    except Exception:
        pass


async def resume(chat_id):
    try:
        await calls.resume(chat_id)
    except Exception:
        pass


async def add_queue(item):
    queue.append(item)


async def next_item():
    if not queue:
        return None

    return queue.pop(0)