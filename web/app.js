"use strict";

const soundsContainer = document.getElementById("sounds");
const searchInput = document.getElementById("search");
const toast = document.getElementById("toast");

let sounds = [];
let loading = false;
let playingId = null;


// ============================================================
// TOAST
// ============================================================

let toastTimer = null;

function showToast(message) {
    if (!toast) return;

    toast.textContent = message;
    toast.classList.add("show");

    clearTimeout(toastTimer);

    toastTimer = setTimeout(() => {
        toast.classList.remove("show");
    }, 2500);
}


// ============================================================
// HTML ESCAPE
// ============================================================

function escapeHTML(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


// ============================================================
// FORMAT DURATION
// ============================================================

function formatDuration(seconds) {
    if (
        seconds === null ||
        seconds === undefined ||
        isNaN(Number(seconds))
    ) {
        return "";
    }

    seconds = Number(seconds);

    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;

    return `${minutes}:${String(secs).padStart(2, "0")}`;
}


// ============================================================
// LOAD SOUNDS
// ============================================================

async function loadSounds(silent = false) {

    if (loading) {
        return;
    }

    loading = true;

    if (!silent) {
        soundsContainer.innerHTML = `
            <div class="loading">
                <div>🎵</div>
                <span>Loading sounds...</span>
            </div>
        `;
    }

    try {

        const response = await fetch(
            "/api/sounds",
            {
                method: "GET",
                cache: "no-store",
                headers: {
                    "Accept": "application/json"
                }
            }
        );

        let data = null;

        try {
            data = await response.json();
        } catch {
            data = null;
        }

        if (!response.ok) {

            const message =
                data?.detail ||
                data?.error ||
                `HTTP ${response.status}`;

            throw new Error(message);
        }

        if (!Array.isArray(data)) {
            throw new Error(
                "Invalid response from server."
            );
        }

        sounds = data;

        renderSounds(
            getFilteredSounds()
        );

    } catch (error) {

        console.error(
            "Loading sounds failed:",
            error
        );

        if (!silent) {

            soundsContainer.innerHTML = `
                <div class="empty">
                    <div class="empty-icon">⚠️</div>

                    <div>
                        Unable to load sounds.
                    </div>

                    <small>
                        ${escapeHTML(
                            error.message
                        )}
                    </small>

                    <button
                        class="retry-button"
                        id="retryButton"
                    >
                        🔄 Retry
                    </button>
                </div>
            `;

            const retryButton =
                document.getElementById(
                    "retryButton"
                );

            if (retryButton) {
                retryButton.addEventListener(
                    "click",
                    () => loadSounds(false)
                );
            }
        }

    } finally {

        loading = false;
    }
}


// ============================================================
// FILTER
// ============================================================

function getFilteredSounds() {

    const query =
        searchInput
            ? searchInput.value
                .trim()
                .toLowerCase()
            : "";

    if (!query) {
        return sounds;
    }

    return sounds.filter(sound => {

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
}


// ============================================================
// RENDER SOUNDS
// ============================================================

function renderSounds(list) {

    soundsContainer.innerHTML = "";

    if (!list || list.length === 0) {

        soundsContainer.innerHTML = `
            <div class="empty">
                <div class="empty-icon">📭</div>

                <div>
                    ${
                        sounds.length === 0
                            ? "No sounds available."
                            : "No matching sounds."
                    }
                </div>
            </div>
        `;

        return;
    }


    const fragment =
        document.createDocumentFragment();


    list.forEach(sound => {

        const button =
            document.createElement("button");

        button.type = "button";

        button.className =
            "sound-button";

        button.dataset.id =
            String(sound.sound_id);


        const duration =
            formatDuration(
                sound.duration
            );


        button.innerHTML = `

            <div class="sound-id">
                ${escapeHTML(
                    sound.sound_id
                )}
            </div>

            <div class="sound-info">

                <div class="sound-name">
                    ${escapeHTML(
                        sound.name ||
                        "Unknown"
                    )}
                </div>

                <div class="sound-subtitle">

                    ${
                        duration
                            ? `⏱ ${duration}`
                            : "Tap to play"
                    }

                </div>

            </div>

            <div
                class="play-button"
                aria-hidden="true"
            >
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


        fragment.appendChild(
            button
        );
    });


    soundsContainer.appendChild(
        fragment
    );
}


// ============================================================
// RESET BUTTON
// ============================================================

function resetPlayingButtons() {

    document
        .querySelectorAll(
            ".sound-button.playing"
        )
        .forEach(button => {

            button.classList.remove(
                "playing"
            );

            button.disabled = false;

            const icon =
                button.querySelector(
                    ".play-button"
                );

            if (icon) {
                icon.textContent = "▶";
            }
        });

    playingId = null;
}


// ============================================================
// PLAY SOUND
// ============================================================

async function playSound(
    sound,
    button
) {

    if (!sound || !button) {
        return;
    }


    // Prevent double click
    if (
        button.classList.contains(
            "playing"
        )
    ) {
        return;
    }


    // Reset previous button
    resetPlayingButtons();


    playingId =
        sound.sound_id;


    button.classList.add(
        "playing"
    );

    button.disabled = true;


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
                    method: "POST",

                    headers: {
                        "Accept":
                            "application/json"
                    }
                }
            );


        let data = null;


        try {

            data =
                await response.json();

        } catch {

            data = null;
        }


        if (!response.ok) {

            const message =
                data?.detail ||
                data?.error ||
                `Playback failed (${response.status})`;

            throw new Error(
                message
            );
        }


        if (
            !data ||
            data.ok !== true
        ) {

            throw new Error(
                data?.detail ||
                data?.error ||
                "Playback failed."
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

        button.disabled = false;


        showToast(
            `❌ ${error.message}`
        );


        playingId = null;


        return;
    }


    // Keep visual state briefly
    setTimeout(() => {

        if (
            playingId ===
            sound.sound_id
        ) {

            button.classList.remove(
                "playing"
            );

            button.disabled = false;

            if (icon) {
                icon.textContent = "▶";
            }

            playingId = null;
        }

    }, 2500);
}


// ============================================================
// SEARCH
// ============================================================

if (searchInput) {

    searchInput.addEventListener(
        "input",
        () => {

            renderSounds(
                getFilteredSounds()
            );
        }
    );
}


// ============================================================
// KEYBOARD SEARCH
// ============================================================

document.addEventListener(
    "keydown",
    event => {

        if (
            event.key === "/" &&
            document.activeElement !==
            searchInput
        ) {

            event.preventDefault();

            if (searchInput) {
                searchInput.focus();
            }
        }
    }
);


// ============================================================
// AUTO REFRESH
// ============================================================
//
// Bot se naya sound add hone ke baad
// maximum 10 seconds mein web par aa jayega.
//

setInterval(
    () => loadSounds(true),
    10000
);


// ============================================================
// INITIAL LOAD
// ============================================================

loadSounds(false);