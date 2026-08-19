import os
from pathlib import Path

from dotenv import load_dotenv

from telethon import TelegramClient
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream


# ============================================================
# ENV
# ============================================================

load_dotenv()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
PHONE_NUMBER = os.environ["PHONE_NUMBER"]


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

SESSION_DIR = BASE_DIR / "sessions"
CACHE_DIR = BASE_DIR / "cache"

SESSION_DIR.mkdir(
    mode=0o700,
    parents=True,
    exist_ok=True
)

CACHE_DIR.mkdir(
    mode=0o700,
    parents=True,
    exist_ok=True
)

SESSION_PATH = str(
    SESSION_DIR / "soundbox"
)


# ============================================================
# GLOBALS
# ============================================================

user: TelegramClient | None = None
calls: PyTgCalls | None = None

current_chat: int | str | None = None
current_file: str | None = None


# ============================================================
# START PLAYER
# ============================================================

async def start_player():

    global user
    global calls

    if calls is not None:
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

    print("✅ Telegram user connected.")

    # --------------------------------------------------------
    # PyTgCalls
    # --------------------------------------------------------

    calls = PyTgCalls(
        user
    )

    await calls.start()

    print("✅ PyTgCalls started.")
    print("🎧 Player ready.")


# ============================================================
# CHECK PLAYER
# ============================================================

def _check_player():

    if user is None:
        raise RuntimeError(
            "Telegram user is not started."
        )

    if calls is None:
        raise RuntimeError(
            "PyTgCalls is not started."
        )


# ============================================================
# PLAY FILE
# ============================================================

async def play_file(
    chat_id: int | str,
    file_path: str
):

    global current_chat
    global current_file

    _check_player()

    file_path = str(
        Path(file_path).resolve()
    )

    if not os.path.isfile(file_path):

        raise FileNotFoundError(
            f"Audio file not found: {file_path}"
        )

    if os.path.getsize(file_path) == 0:

        raise RuntimeError(
            "Audio file is empty."
        )

    print(
        f"▶️ Playing: {file_path}"
    )

    print(
        f"📞 VC Chat: {chat_id}"
    )

    # --------------------------------------------------------
    # PyTgCalls 2.3.x
    # --------------------------------------------------------
    #
    # join_group_call() nahi hai.
    #
    # calls.play() hi stream ko VC mein start karta hai.
    #

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

        # Agar previous call state stuck ho to
        # ek baar leave karke retry.
        try:

            await calls.leave_call(
                chat_id
            )

        except Exception:
            pass

        await calls.play(
            chat_id,
            stream
        )

    current_chat = chat_id
    current_file = file_path

    print("✅ Playback started.")


# ============================================================
# STOP
# ============================================================

async def stop(
    chat_id: int | str
):

    global current_chat
    global current_file

    if calls is None:
        return

    try:

        await calls.leave_call(
            chat_id
        )

        print("⏹ Playback stopped.")

    except Exception as e:

        print(
            f"⚠️ Stop warning: {e}"
        )

    current_chat = None
    current_file = None


# ============================================================
# PAUSE
# ============================================================

async def pause(
    chat_id: int | str
):

    _check_player()

    await calls.pause(
        chat_id
    )

    print("⏸ Playback paused.")


# ============================================================
# RESUME
# ============================================================

async def resume(
    chat_id: int | str
):

    _check_player()

    await calls.resume(
        chat_id
    )

    print("▶️ Playback resumed.")


# ============================================================
# VOLUME
# ============================================================

async def set_volume(
    chat_id: int | str,
    volume: int
):

    _check_player()

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

    print(
        f"🔊 Volume: {volume}"
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
# IS RUNNING
# ============================================================

def is_running():

    return (
        user is not None
        and calls is not None
    )


# ============================================================
# SHUTDOWN
# ============================================================

async def shutdown_player():

    global user
    global calls
    global current_chat
    global current_file

    print(
        "🛑 Shutting down player..."
    )

    # --------------------------------------------------------
    # Leave current VC
    # --------------------------------------------------------

    if calls is not None and current_chat is not None:

        try:

            await calls.leave_call(
                current_chat
            )

        except Exception as e:

            print(
                f"⚠️ Leave call error: {e}"
            )

    # --------------------------------------------------------
    # Stop PyTgCalls
    # --------------------------------------------------------

    if calls is not None:

        try:

            await calls.stop()

        except Exception as e:

            print(
                f"⚠️ PyTgCalls stop error: {e}"
            )

    # --------------------------------------------------------
    # Disconnect Telethon
    # --------------------------------------------------------

    if user is not None:

        try:

            await user.disconnect()

        except Exception as e:

            print(
                f"⚠️ Telegram disconnect error: {e}"
            )

    calls = None
    user = None

    current_chat = None
    current_file = None

    print(
        "✅ Player stopped."
    )