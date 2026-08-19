const soundsContainer = document.getElementById("sounds");
const searchInput = document.getElementById("search");
const toast = document.getElementById("toast");

let sounds = [];
let playingId = null;


// ============================================================
// TOAST
// ============================================================

function showToast(message) {
    toast.textContent = message;
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 2000);
}


// ============================================================
// LOAD SOUNDS
// ============================================================

async function loadSounds() {

    soundsContainer.innerHTML = `
        <div class="loading">
            Loading sounds...
        </div>
    `;

    try {

        const response = await fetch(
            "/api/sounds",
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }

        sounds = await response.json();

        renderSounds(sounds);

    } catch (error) {

        console.error(
            "Sound loading error:",
            error
        );

        soundsContainer.innerHTML = `
            <div class="empty">
                <div class="empty-icon">⚠️</div>
                Unable to load sounds.
            </div>
        `;
    }
}


// ============================================================
// RENDER
// ============================================================

function renderSounds(list) {

    soundsContainer.innerHTML = "";

    if (!list || list.length === 0) {

        soundsContainer.innerHTML = `
            <div class="empty">
                <div class="empty-icon">📭</div>
                No sounds found.
            </div>
        `;

        return;
    }


    list.forEach(sound => {

        const button =
            document.createElement("button");

        button.className = "sound-button";

        button.dataset.id =
            sound.sound_id;

        button.innerHTML = `
            <div class="sound-id">
                ${escapeHTML(
                    String(sound.sound_id ?? "")
                )}
            </div>

            <div class="sound-info">

                <div class="sound-name">
                    ${escapeHTML(
                        sound.name
                    )}
                </div>

                <div class="sound-subtitle">
                    Tap to play
                </div>

            </div>

            <div class="play-button">
                ▶
            </div>
        `;


        button.addEventListener(
            "click",
            () => playSound(
                sound,
                button
            )
        );


        soundsContainer.appendChild(
            button
        );
    });
}


// ============================================================
// PLAY SOUND
// ============================================================

async function playSound(
    sound,
    button
) {

    if (playingId !== null) {

        document
            .querySelectorAll(
                ".sound-button.playing"
            )
            .forEach(element => {

                element.classList.remove(
                    "playing"
                );

                const icon =
                    element.querySelector(
                        ".play-button"
                    );

                if (icon) {
                    icon.textContent = "▶";
                }
            });
    }


    playingId = sound.sound_id;

    button.classList.add(
        "playing"
    );

    const icon =
        button.querySelector(
            ".play-button"
        );

    if (icon) {
        icon.textContent = "⏳";
    }


    try {

        const response =
            await fetch(
                `/api/play/${encodeURIComponent(
                    sound.sound_id
                )}`,
                {
                    method: "POST"
                }
            );


        const data =
            await response.json();


        if (!response.ok || data.ok === false) {

            throw new Error(
                data.error ||
                "Playback failed"
            );
        }


        if (icon) {
            icon.textContent = "🔊";
        }


        showToast(
            `▶ Playing ${sound.name}`
        );


    } catch (error) {

        console.error(
            "Playback error:",
            error
        );

        if (icon) {
            icon.textContent = "▶";
        }

        button.classList.remove(
            "playing"
        );

        showToast(
            `❌ ${error.message}`
        );

    } finally {

        setTimeout(() => {

            button.classList.remove(
                "playing"
            );

            if (icon) {
                icon.textContent = "▶";
            }

            playingId = null;

        }, 2500);
    }
}


// ============================================================
// SEARCH
// ============================================================

searchInput.addEventListener(
    "input",
    () => {

        const query =
            searchInput.value
                .trim()
                .toLowerCase();


        if (!query) {

            renderSounds(
                sounds
            );

            return;
        }


        const filtered =
            sounds.filter(sound => {

                const name =
                    String(
                        sound.name || ""
                    ).toLowerCase();

                const id =
                    String(
                        sound.sound_id ?? ""
                    ).toLowerCase();


                return (
                    name.includes(query) ||
                    id.includes(query)
                );
            });


        renderSounds(
            filtered
        );
    }
);


// ============================================================
// ESCAPE HTML
// ============================================================

function escapeHTML(value) {

    return value
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


// ============================================================
// AUTO REFRESH
// ============================================================

// New sound bot se add hone ke baad
// web list automatically update ho jayegi.

setInterval(
    loadSounds,
    10000
);


// ============================================================
// INITIAL LOAD
// ============================================================

loadSounds();