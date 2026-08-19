import os

from dotenv import load_dotenv
from telethon import TelegramClient
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream

load_dotenv()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
PHONE_NUMBER = os.environ["PHONE_NUMBER"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SESSION_DIR = os.path.join(BASE_DIR, "sessions")
CACHE_DIR = os.path.join(BASE_DIR, "cache")

os.makedirs(SESSION_DIR, mode=0o700, exist_ok=True)
os.makedirs(CACHE_DIR, mode=0o700, exist_ok=True)

SESSION_PATH = os.path.join(
    SESSION_DIR,
    "soundbox"
)

# Do NOT initialize these at import time.
user = None
calls = None

current_chat = None
current_file = None


async def start_player():

    global user
    global calls

    print("Starting Telegram user...")

    user = TelegramClient(
        SESSION_PATH,
        API_ID,
        API_HASH
    )

    await user.start(
        phone=PHONE_NUMBER
    )

    print("Telegram user connected.")

    calls = PyTgCalls(user)

    await calls.start()

    print("PyTgCalls started.")


async def play_file(chat_id: int, file_path: str):

    global current_chat
    global current_file

    if calls is None:
        raise RuntimeError(
            "PyTgCalls is not initialized."
        )

    if not os.path.isfile(file_path):
        raise FileNotFoundError(
            f"Audio file not found: {file_path}"
        )

    current_chat = chat_id
    current_file = file_path

    print(
        f"Playing {file_path} "
        f"in {chat_id}"
    )

    stream = MediaStream(
        file_path,
        video_flags=MediaStream.Flags.IGNORE
    )

    await calls.play(
        chat_id,
        stream
    )


async def stop(chat_id: int):

    global current_chat
    global current_file

    if calls is None:
        return

    try:
        await calls.leave_call(
            chat_id
        )
    except Exception as e:
        print(
            f"leave_call error: {e}"
        )

    current_chat = None
    current_file = None


async def pause(chat_id: int):

    if calls is None:
        raise RuntimeError(
            "PyTgCalls is not initialized."
        )

    await calls.pause(
        chat_id
    )


async def resume(chat_id: int):

    if calls is None:
        raise RuntimeError(
            "PyTgCalls is not initialized."
        )

    await calls.resume(
        chat_id
    )


async def set_volume(
    chat_id: int,
    volume: int
):

    if calls is None:
        raise RuntimeError(
            "PyTgCalls is not initialized."
        )

    await calls.change_volume_call(
        chat_id,
        volume
    )


async def shutdown_player():

    global user
    global calls

    if calls is not None:

        try:
            await calls.stop()
        except Exception as e:
            print(
                f"PyTgCalls stop error: {e}"
            )

    if user is not None:

        try:
            await user.disconnect()
        except Exception as e:
            print(
                f"Telegram disconnect error: {e}"
            )

    calls = None
    user = None