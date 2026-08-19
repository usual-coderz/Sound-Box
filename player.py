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
os.makedirs(SESSION_DIR, mode=0o700, exist_ok=True)

SESSION_PATH = os.path.join(
    SESSION_DIR,
    "soundbox"
)

user = TelegramClient(
    SESSION_PATH,
    API_ID,
    API_HASH
)

calls = PyTgCalls(user)

current_chat = None
current_file = None


async def start_player():

    print("Starting Telegram user...")

    await user.start(
        phone=PHONE_NUMBER
    )

    print("Telegram user connected.")

    await calls.start()

    print("PyTgCalls started.")


async def play_file(chat_id, file_path):

    global current_chat
    global current_file

    if not os.path.exists(file_path):
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


async def stop(chat_id):

    global current_file

    try:
        await calls.leave_call(
            chat_id
        )
    except Exception as e:
        print(
            f"Leave call error: {e}"
        )

    current_file = None


async def pause(chat_id):

    await calls.pause(
        chat_id
    )


async def resume(chat_id):

    await calls.resume(
        chat_id
    )


async def volume(chat_id, value):

    await calls.change_volume_call(
        chat_id,
        value
    )