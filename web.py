import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from aiogram import Bot

from database import (
    get_all_sounds,
    get_sound_by_id,
)

from player import play_file


# ============================================================
# ENV
# ============================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]

DEFAULT_VC_CHAT_ID = int(
    os.environ["DEFAULT_VC_CHAT_ID"]
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parent

WEB_DIR = BASE_DIR / "web"

CACHE_DIR = BASE_DIR / "cache"

CACHE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# BOT
# ============================================================

bot = Bot(
    token=BOT_TOKEN
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Sound Box",
    docs_url="/docs"
)


# ============================================================
# STATIC
# ============================================================

app.mount(
    "/static",
    StaticFiles(
        directory=str(WEB_DIR)
    ),
    name="static"
)


# ============================================================
# HOME
# ============================================================

@app.get("/")
async def home():

    return FileResponse(
        WEB_DIR / "index.html"
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
async def health():

    return {
        "ok": True,
        "service": "Sound Box"
    }


# ============================================================
# GET SOUNDS
# ============================================================

@app.get("/api/sounds")
async def api_sounds():

    sounds = await get_all_sounds()

    result = []

    for sound in sounds:

        sound_id = sound.get(
            "sound_id"
        )

        if sound_id is None:
            continue

        result.append({

            "sound_id": int(
                sound_id
            ),

            "name": sound.get(
                "name",
                "Unknown"
            ),

            "duration": sound.get(
                "duration"
            )
        })

    result.sort(
        key=lambda x: x["sound_id"]
    )

    return result


# ============================================================
# CACHE PATH
# ============================================================

def get_cache_path(sound):

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

    elif file_type == "document":

        extension = ".bin"

    else:

        extension = ".bin"

    return (
        CACHE_DIR /
        f"{mongo_id}{extension}"
    )


# ============================================================
# DOWNLOAD SOUND
# ============================================================

async def download_sound(
    sound,
    file_path: Path
):

    storage_chat_id = sound.get(
        "storage_chat_id"
    )

    storage_message_id = sound.get(
        "storage_message_id"
    )

    if not storage_chat_id:
        raise RuntimeError(
            "Storage channel ID missing."
        )

    if not storage_message_id:
        raise RuntimeError(
            "Storage message ID missing."
        )

    print(
        f"⬇️ Downloading: "
        f"{sound.get('name', 'Unknown')}"
    )

    print(
        f"📦 Channel: {storage_chat_id}"
    )

    print(
        f"📨 Message: {storage_message_id}"
    )

    # --------------------------------------------------------
    # Telegram Bot API
    # --------------------------------------------------------

    message = await bot.forward_message(
        chat_id=storage_chat_id,
        from_chat_id=storage_chat_id,
        message_id=storage_message_id
    )

    # --------------------------------------------------------
    # IMPORTANT
    # --------------------------------------------------------
    #
    # forward_message() creates a new message.
    # We don't need that.
    #
    # Better approach:
    # use Telegram file_id saved in MongoDB.
    #
    # The original bot_file_id is already available.
    #

    try:

        await bot.delete_message(
            chat_id=storage_chat_id,
            message_id=message.message_id
        )

    except Exception:
        pass

    file_id = sound.get(
        "bot_file_id"
    )

    if not file_id:

        raise RuntimeError(
            "bot_file_id missing from database."
        )

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    await bot.download(
        file_id,
        destination=str(file_path)
    )

    if not file_path.exists():

        raise RuntimeError(
            "Telegram download failed."
        )

    if file_path.stat().st_size == 0:

        try:
            file_path.unlink()
        except Exception:
            pass

        raise RuntimeError(
            "Downloaded audio file is empty."
        )

    print(
        f"✅ Cached: {file_path}"
    )


# ============================================================
# PLAY SOUND
# ============================================================

@app.post(
    "/api/play/{sound_id}"
)
async def api_play(
    sound_id: int
):

    sound = await get_sound_by_id(
        sound_id
    )

    if not sound:

        raise HTTPException(
            status_code=404,
            detail="Sound not found."
        )

    name = sound.get(
        "name",
        "Unknown"
    )

    file_path = get_cache_path(
        sound
    )

    # --------------------------------------------------------
    # Download if not cached
    # --------------------------------------------------------

    if not file_path.exists():

        try:

            await download_sound(
                sound,
                file_path
            )

        except Exception as e:

            print(
                "❌ Download error:",
                repr(e)
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    f"Audio download failed: {e}"
                )
            )

    # --------------------------------------------------------
    # Play
    # --------------------------------------------------------

    try:

        await play_file(
            DEFAULT_VC_CHAT_ID,
            str(file_path)
        )

    except Exception as e:

        print(
            "❌ Web playback error:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    return {

        "ok": True,

        "sound_id": sound_id,

        "name": name,

        "playing": True
    }


# ============================================================
# CLOSE BOT
# ============================================================

@app.on_event("shutdown")
async def shutdown_web():

    try:

        await bot.session.close()

    except Exception:
        pass