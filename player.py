import os

from dotenv import load_dotenv
from telethon import TelegramClient
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream


# ============================================================
# ENV
# ============================================================

load_dotenv()

API_ID = int(
    os.environ["API_ID"]
)

API_HASH = os.environ[
    "API_HASH"
]

PHONE_NUMBER = os.environ[
    "PHONE_NUMBER"
]


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

SESSION_DIR = os.path.join(
    BASE_DIR,
    "sessions"
)

CACHE_DIR = os.path.join(
    BASE_DIR,
    "cache"
)

os.makedirs(
    SESSION_DIR,
    mode=0o700,
    exist_ok=True
)

os.makedirs(
    CACHE_DIR,
    mode=0o700,
    exist_ok=True
)

SESSION_PATH = os.path.join(
    SESSION_DIR,
    "soundbox"
)


# ============================================================
# GLOBAL CLIENTS
# ============================================================

# IMPORTANT:
# In objects ko module import ke time create nahi karna.
# start_player() ke andar create karna hai.
#
# Isse aiogram + Telethon + PyTgCalls
# same asyncio event loop use karenge.

user = None
calls = None

current_chat = None
current_file = None


# ============================================================
# START
# ============================================================

async def start_player():

    global user
    global calls

    if user is not None:
        return

    print("🎧 Starting Telegram user...")


    # --------------------------------------------------------
    # Telethon
    # --------------------------------------------------------

    user = TelegramClient(
        SESSION_PATH,
        API_ID,
        API_HASH
    )


    await user.start(
        phone=PHONE_NUMBER
    )


    print(
        "✅ Telegram user connected."
    )


    # --------------------------------------------------------
    # PyTgCalls
    # --------------------------------------------------------

    calls = PyTgCalls(
        user
    )


    await calls.start()


    print(
        "✅ PyTgCalls started."
    )


# ============================================================
# PLAY
# ============================================================

async def play_file(
    chat_id: int,
    file_path: str
):

    global current_chat
    global current_file


    if calls is None:

        raise RuntimeError(
            "PyTgCalls is not started."
        )


    if not os.path.isfile(
        file_path
    ):

        raise FileNotFoundError(
            f"Audio file not found: {file_path}"
        )


    current_chat = chat_id

    current_file = file_path


    print(
        f"▶ Playing: {file_path}"
    )

    print(
        f"📞 VC Chat: {chat_id}"
    )


    # --------------------------------------------------------
    # PyTgCalls 2.3.x
    # --------------------------------------------------------
    #
    # join_group_call() use nahi karna.
    #
    # play() automatically starts/joins
    # the group call.
    #

    stream = MediaStream(
        file_path,
        video_flags=MediaStream.Flags.IGNORE
    )


    await calls.play(
        chat_id,
        stream
    )


    print(
        "✅ Playback started."
    )


# ============================================================
# STOP
# ============================================================

async def stop(
    chat_id: int
):

    global current_chat
    global current_file


    if calls is None:
        return


    try:

        await calls.leave_call(
            chat_id
        )

        print(
            "⏹ Call stopped."
        )

    except Exception as e:

        print(
            f"❌ Stop error: {e}"
        )


    current_chat = None
    current_file = None


# ============================================================
# PAUSE
# ============================================================

async def pause(
    chat_id: int
):

    if calls is None:

        raise RuntimeError(
            "PyTgCalls is not started."
        )


    await calls.pause(
        chat_id
    )


    print(
        "⏸ Playback paused."
    )


# ============================================================
# RESUME
# ============================================================

async def resume(
    chat_id: int
):

    if calls is None:

        raise RuntimeError(
            "PyTgCalls is not started."
        )


    await calls.resume(
        chat_id
    )


    print(
        "▶ Playback resumed."
    )


# ============================================================
# VOLUME
# ============================================================

async def set_volume(
    chat_id: int,
    volume: int
):

    if calls is None:

        raise RuntimeError(
            "PyTgCalls is not started."
        )


    volume = max(
        0,
        min(
            int(volume),
            200
        )
    )


    await calls.change_volume_call(
        chat_id,
        volume
    )


# ============================================================
# STATUS
# ============================================================

def get_current():

    return {
        "chat_id": current_chat,
        "file": current_file
    }


# ============================================================
# SHUTDOWN
# ============================================================

async def shutdown_player():

    global user
    global calls

    print(
        "🛑 Shutting down player..."
    )


    if calls is not None:

        try:

            await calls.stop()

        except Exception as e:

            print(
                f"PyTgCalls shutdown error: {e}"
            )


    if user is not None:

        try:

            await user.disconnect()

        except Exception as e:

            print(
                f"Telegram shutdown error: {e}"
            )


    calls = None
    user = None


    print(
        "✅ Player stopped."
    )