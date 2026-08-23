import json
import os
import sys

from PySide6.QtCore import QObject, Qt, QUrl, Signal, Slot
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from mutagen import File as MutagenFile

AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".opus"}
WEB_DIR = os.path.dirname(os.path.abspath(__file__))

def format_duration(seconds):
    if not seconds or seconds <= 0:
        return "--:--"
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def read_track_info(filepath):
    title = os.path.splitext(os.path.basename(filepath))[0]
    artist = "Unknown Artist"
    album = "Unknown Album"
    duration = 0
    try:
        audio = MutagenFile(filepath, easy=True)
        if audio is not None:
            if audio.tags:
                title = (audio.tags.get("title") or [title])[0]
                artist = (audio.tags.get("artist") or [artist])[0]
                album = (audio.tags.get("album") or [album])[0]
            if audio.info and getattr(audio.info, "length", None):
                duration = audio.info.length
    except Exception:
        pass
    return title, artist, album, duration


class Bridge(QObject):

    tracksLoaded = Signal(str)          # JSON array of track dicts
    folderChanged = Signal(str)         # display text, e.g. "/media/usb (12 tracks)"
    positionChanged = Signal(int)       # ms
    durationChanged = Signal(int)       # ms
    playbackStateChanged = Signal(bool) # True = playing
    nowPlayingChanged = Signal(str)     # JSON {title, artist, album, index}
    errorOccurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.tracks = []
        self.current_index = -1

        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(0.8)
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)

        self.player.positionChanged.connect(self.positionChanged.emit)
        self.player.durationChanged.connect(self.durationChanged.emit)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.playbackStateChanged.connect(
            lambda state: self.playbackStateChanged.emit(state == QMediaPlayer.PlayingState)
        )

    # ---------------- folder scanning ----------------
    @Slot()
    def chooseFolder(self):
        folder = QFileDialog.getExistingDirectory(
            None, "Select Folder or Drive (USB / SD card mount point, etc.)"
        )
        if not folder:
            return
        self._scan_folder(folder)

    def _scan_folder(self, folder):
        found_paths = []
        for root, _dirs, files in os.walk(folder):
            for name in files:
                if os.path.splitext(name)[1].lower() in AUDIO_EXTENSIONS:
                    found_paths.append(os.path.join(root, name))
        found_paths.sort()

        self.tracks = []
        for path in found_paths:
            title, artist, album, duration = read_track_info(path)
            self.tracks.append({
                "path": path,
                "title": title,
                "artist": artist,
                "album": album,
                "duration": duration,
                "durationText": format_duration(duration),
            })

        self.current_index = -1
        self.tracksLoaded.emit(json.dumps(self.tracks))
        self.folderChanged.emit(f"{folder}  ·  {len(self.tracks)} track(s) found")

    # ---------------- playback controls ----------------
    @Slot(int)
    def playTrack(self, index):
        if index < 0 or index >= len(self.tracks):
            return
        self.current_index = index
        track = self.tracks[index]
        self.player.setSource(QUrl.fromLocalFile(track["path"]))
        self.player.play()
        self.nowPlayingChanged.emit(json.dumps({**track, "index": index}))

    @Slot()
    def togglePlayPause(self):
        if self.current_index == -1:
            if self.tracks:
                self.playTrack(0)
            return
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    @Slot()
    def stopPlayback(self):
        self.player.stop()

    @Slot()
    def nextTrack(self):
        if not self.tracks:
            return
        self.playTrack((self.current_index + 1) % len(self.tracks))

    @Slot()
    def previousTrack(self):
        if not self.tracks:
            return
        self.playTrack((self.current_index - 1) % len(self.tracks))

    @Slot(int)
    def seek(self, position_ms):
        self.player.setPosition(position_ms)

    @Slot(int)
    def setVolume(self, percent):
        self.audio_output.setVolume(max(0, min(100, percent)) / 100)

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.nextTrack()
        elif status == QMediaPlayer.InvalidMedia:
            self.errorOccurred.emit("Couldn't play that file — it may be missing or corrupted.")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Local Music Player")
        self.resize(1000, 680)

        self.view = QWebEngineView()
        self.setCentralWidget(self.view)

        self.bridge = Bridge()
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        index_path = os.path.join(WEB_DIR, "index.html")
        self.view.load(QUrl.fromLocalFile(index_path))


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()