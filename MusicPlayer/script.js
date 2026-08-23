/* global QWebChannel, qt */

let bridge = null;
let tracks = [];
let currentIndex = -1;
let isPlaying = false;
let durationMs = 0;
let isScrubbing = false;

const el = {
  deck: document.querySelector(".deck"),
  openBtn: document.getElementById("openBtn"),
  folderPath: document.getElementById("folderPath"),
  emptyState: document.getElementById("emptyState"),
  trackTable: document.getElementById("trackTable"),
  trackBody: document.getElementById("trackBody"),

  lcdTitleText: document.getElementById("lcdTitleText"),
  lcdArtist: document.getElementById("lcdArtist"),
  lcdAlbum: document.getElementById("lcdAlbum"),

  seekSlider: document.getElementById("seekSlider"),
  timeCurrent: document.getElementById("timeCurrent"),
  timeTotal: document.getElementById("timeTotal"),

  playBtn: document.getElementById("playBtn"),
  playIcon: document.getElementById("playIcon"),
  pauseIcon: document.getElementById("pauseIcon"),
  stopBtn: document.getElementById("stopBtn"),
  prevBtn: document.getElementById("prevBtn"),
  nextBtn: document.getElementById("nextBtn"),
  shuffleBtn: document.getElementById("shuffleBtn"),
  volumeSlider: document.getElementById("volumeSlider"),

  toast: document.getElementById("toast"),
};

function formatMs(ms) {
  if (!ms || ms <= 0) return "0:00";
  const totalSeconds = Math.floor(ms / 1000);
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  const mm = h ? String(m).padStart(2, "0") : m;
  const ss = String(s).padStart(2, "0");
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

function showToast(message) {
  el.toast.textContent = message;
  el.toast.classList.add("show");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => el.toast.classList.remove("show"), 3200);
}

function setRangeFill(input) {
  const pct = input.max > 0 ? (input.value / input.max) * 100 : 0;
  input.style.setProperty("--fill", `${pct}%`);
}

/* ---------------- rendering ---------------- */

function renderTracks() {
  if (!tracks.length) {
    el.emptyState.style.display = "flex";
    el.trackTable.style.display = "none";
    return;
  }
  el.emptyState.style.display = "none";
  el.trackTable.style.display = "block";

  el.trackBody.innerHTML = tracks
    .map(
      (t, i) => `
      <tr data-index="${i}" class="${i === currentIndex ? "active" : ""}">
        <td class="col-index">${String(i + 1).padStart(2, "0")}</td>
        <td class="col-title">${escapeHtml(t.title)}</td>
        <td class="col-artist">${escapeHtml(t.artist)}</td>
        <td class="col-album">${escapeHtml(t.album)}</td>
        <td class="col-duration">${t.durationText}</td>
      </tr>
    `,
    )
    .join("");

  el.trackBody.querySelectorAll("tr").forEach((row) => {
    row.addEventListener("click", () => {
      const index = Number(row.dataset.index);
      bridge.playTrack(index);
    });
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function highlightActiveRow() {
  el.trackBody.querySelectorAll("tr").forEach((row) => {
    row.classList.toggle("active", Number(row.dataset.index) === currentIndex);
  });
}

function updatePlayIcon() {
  el.playIcon.style.display = isPlaying ? "none" : "block";
  el.pauseIcon.style.display = isPlaying ? "block" : "none";
  el.deck.classList.toggle("is-playing", isPlaying);
}

/* ---------------- bridge wiring ---------------- */

new QWebChannel(qt.webChannelTransport, (channel) => {
  bridge = channel.objects.bridge;

  bridge.tracksLoaded.connect((json) => {
    tracks = JSON.parse(json);
    currentIndex = -1;
    renderTracks();
  });

  bridge.folderChanged.connect((text) => {
    el.folderPath.textContent = text;
  });

  bridge.nowPlayingChanged.connect((json) => {
    const track = JSON.parse(json);
    currentIndex = track.index;
    el.lcdTitleText.textContent = track.title.toUpperCase();
    el.lcdArtist.textContent = track.artist;
    el.lcdAlbum.textContent = track.album;
    highlightActiveRow();
  });

  bridge.positionChanged.connect((ms) => {
    if (isScrubbing) return;
    el.timeCurrent.textContent = formatMs(ms);
    if (durationMs > 0) {
      el.seekSlider.value = Math.round((ms / durationMs) * 1000);
      setRangeFill(el.seekSlider);
    }
  });

  bridge.durationChanged.connect((ms) => {
    durationMs = ms;
    el.timeTotal.textContent = formatMs(ms);
  });

  bridge.playbackStateChanged.connect((playing) => {
    isPlaying = playing;
    updatePlayIcon();
  });

  bridge.errorOccurred.connect((message) => showToast(message));
});

/* ---------------- UI event handlers ---------------- */

el.openBtn.addEventListener("click", () => bridge.chooseFolder());

el.playBtn.addEventListener("click", () => bridge.togglePlayPause());
el.stopBtn.addEventListener("click", () => bridge.stopPlayback());
el.prevBtn.addEventListener("click", () => bridge.previousTrack());
el.nextBtn.addEventListener("click", () => bridge.nextTrack());
el.shuffleBtn.addEventListener("click", () => bridge.shuffleTrack());

el.seekSlider.addEventListener("input", () => {
  isScrubbing = true;
  setRangeFill(el.seekSlider);
  const pct = el.seekSlider.value / el.seekSlider.max;
  el.timeCurrent.textContent = formatMs(pct * durationMs);
});
el.seekSlider.addEventListener("change", () => {
  const pct = el.seekSlider.value / el.seekSlider.max;
  bridge.seek(Math.round(pct * durationMs));
  isScrubbing = false;
});

el.volumeSlider.addEventListener("input", () => {
  setRangeFill(el.volumeSlider);
  bridge.setVolume(Number(el.volumeSlider.value));
});

/* init fill state for sliders on load */
setRangeFill(el.seekSlider);
setRangeFill(el.volumeSlider);
