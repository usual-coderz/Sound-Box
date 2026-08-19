import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from database import (
    get_all_sounds,
    get_sound_by_id,
)

from player import play_file, user


# ============================================================
# ENV
# ============================================================

load_dotenv()

DEFAULT_VC_CHAT_ID = int(
    os.environ["DEFAULT_VC_CHAT_ID"]
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

WEB_DIR = BASE_DIR / "web"

CACHE_DIR = BASE_DIR / "cache"

CACHE_DIR.mkdir(
    mode=0o700,
    exist_ok=True
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
# SOUNDS API
# ============================================================

@app.get("/api/sounds")
async def api_sounds():

    try:

        sounds = await get_all_sounds()

    except Exception as e:

        print(
            "MongoDB sounds error:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Database error"
        )


    result = []


    for sound in sounds:

        sound_id = sound.get(
            "sound_id"
        )


        # Web buttons ke liye ID required
        if sound_id is None:
            continue


        result.append({

            "sound_id":
                sound_id,

            "name":
                sound.get(
                    "name",
                    "Unknown"
                ),

            "duration":
                sound.get(
                    "duration"
                )
        })


    result.sort(
        key=lambda x: x["sound_id"]
    )


    return result


# ============================================================
# FILE EXTENSION
# ============================================================

def get_extension(sound):

    file_type = sound.get(
        "file_type"
    )


    if file_type == "audio":
        return ".mp3"


    if file_type == "voice":
        return ".ogg"


    return ".bin"


# ============================================================
# CACHE FILE
# ============================================================

def get_cache_path(sound):

    mongo_id = str(
        sound["_id"]
    )

    extension = get_extension(
        sound
    )

    return CACHE_DIR / (
        mongo_id + extension
    )


# ============================================================
# DOWNLOAD SOUND
# ============================================================

async def ensure_cached(sound):

    file_path = get_cache_path(
        sound
    )


    # Already cached
    if (
        file_path.exists()
        and
        file_path.stat().st_size > 0
    ):

        return file_path


    # Telegram user client check
    #
    # player.py mein user global
    # start_player() ke baad available hota hai.

    import player

    telegram_user = (
        player.user
    )


    if telegram_user is None:

        raise RuntimeError(
            "Telegram user is not connected."
        )


    file_id = sound.get(
        "bot_file_id"
    )


    if not file_id:

        raise RuntimeError(
            "Sound does not have Telegram file_id."
        )


    print(
        f"⬇️ Web downloading: "
        f"{sound.get('name', 'Unknown')}"
    )


    try:

        downloaded = await telegram_user.download_media(
            file_id,
            file=str(file_path)
        )

    except Exception as e:

        print(
            "Telegram download error:",
            repr(e)
        )

        raise RuntimeError(
            f"Telegram download failed: {e}"
        )


    if not downloaded:

        raise RuntimeError(
            "Telegram returned no file."
        )


    if not file_path.exists():

        raise RuntimeError(
            "Downloaded file was not created."
        )


    if file_path.stat().st_size <= 0:

        try:
            file_path.unlink()
        except Exception:
            pass

        raise RuntimeError(
            "Downloaded file is empty."
        )


    print(
        f"✅ Cached: {file_path}"
    )


    return file_path


# ============================================================
# PLAY SOUND
# ============================================================

@app.post("/api/play/{sound_id}")
async def api_play(
    sound_id: int
):

    # --------------------------------------------------------
    # Find sound
    # --------------------------------------------------------

    try:

        sound = await get_sound_by_id(
            sound_id
        )

    except Exception as e:

        print(
            "Database error:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Database error"
        )


    if not sound:

        raise HTTPException(
            status_code=404,
            detail="Sound not found"
        )


    name = sound.get(
        "name",
        "Unknown"
    )


    # --------------------------------------------------------
    # Cache / Download
    # --------------------------------------------------------

    try:

        file_path = await ensure_cached(
            sound
        )

    except Exception as e:

        print(
            "Cache error:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


    # --------------------------------------------------------
    # Play
    # --------------------------------------------------------

    try:

        print(
            f"🌐 Web play: "
            f"{name}"
        )

        await play_file(
            DEFAULT_VC_CHAT_ID,
            str(file_path)
        )

    except Exception as e:

        print(
            "Web playback error:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


    return {

        "ok": True,

        "sound_id":
            sound_id,

        "name":
            name
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
async def health():

    import player

    return {

        "ok": True,

        "telegram":
            player.user is not None,

        "player":
            player.calls is not None,

        "vc_chat_id":
            DEFAULT_VC_CHAT_ID
    }