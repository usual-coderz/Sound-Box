import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database import get_all_sounds, get_sound_by_id
from player import play_file


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parent

WEB_DIR = BASE_DIR / "web"

CACHE_DIR = BASE_DIR / "cache"

CACHE_DIR.mkdir(
    exist_ok=True
)


# ============================================================
# ENV
# ============================================================

DEFAULT_VC_CHAT_ID = int(
    os.environ["DEFAULT_VC_CHAT_ID"]
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Sound Box",
    docs_url="/docs"
)


# Static files
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
# GET ALL SOUNDS
# ============================================================

@app.get("/api/sounds")
async def api_sounds():

    sounds = await get_all_sounds()

    result = []

    for sound in sounds:

        sound_id = sound.get(
            "sound_id"
        )

        # Web buttons ke liye ID required hai
        if sound_id is None:
            continue

        result.append({

            "sound_id": sound_id,

            "name": sound.get(
                "name",
                "Unknown"
            ),

            "duration": sound.get(
                "duration"
            )
        })

    # ID order
    result.sort(
        key=lambda x: x["sound_id"]
    )

    return result


# ============================================================
# PLAY SOUND
# ============================================================

@app.post("/api/play/{sound_id}")
async def api_play(
    sound_id: int
):

    sound = await get_sound_by_id(
        sound_id
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
    # Cache filename
    # --------------------------------------------------------

    mongo_id = str(
        sound["_id"]
    )


    if sound.get(
        "file_type"
    ) == "audio":

        extension = ".mp3"

    elif sound.get(
        "file_type"
    ) == "voice":

        extension = ".ogg"

    else:

        extension = ".bin"


    file_path = (
        CACHE_DIR /
        f"{mongo_id}{extension}"
    )


    # --------------------------------------------------------
    # Download audio
    # --------------------------------------------------------
    #
    # IMPORTANT:
    # Bot instance is intentionally NOT imported here.
    #
    # Web API should use the same playback/cache system
    # that is initialized by the main application.
    #
    # If file is not cached, we raise a useful error.
    #
    # For the final integrated version, the Telegram Bot
    # download should be handled by the shared application.
    # --------------------------------------------------------

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Audio is not cached yet. "
                "Play it once from the Telegram bot "
                "to create the cache."
            )
        )


    # --------------------------------------------------------
    # PLAY
    # --------------------------------------------------------

    try:

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