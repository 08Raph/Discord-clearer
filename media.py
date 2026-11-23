"""Videos and GIFs inside the app.

- Videos (.mp4 / .mov / .webm) play right in the chat, like in Discord.
- Tenor / Giphy "GIFs" are really small looping videos: they play on a loop, muted,
  exactly like Discord shows them.
- Videos play without sound inside the app (Tkinter can't play audio); the
  "Sound" button opens the video in your normal video player.

Uses OpenCV (opencv-python-headless) to read the video frames. If it isn't
installed the app falls back to a picture + "open in browser".
"""
import hashlib
import os
import queue
import sys
import threading
import time
import tkinter as tk
import webbrowser

import cleaner_core as core
from widgets import FONT, MUTED, WHITE

try:
    import cv2                       # noqa: F401
    HAVE_VIDEO = True
except Exception:                    # not installed / failed to load
    cv2 = None
    HAVE_VIDEO = False

MAX_VIDEO = 150 * 1024 * 1024
BAR_BG = "#111214"


def video_cache_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "DiscordMessageCleaner", "video_cache")
    os.makedirs(d, exist_ok=True)
    return d


def cached_file(url):
    """Download a video once and keep it in the cache folder (cleaned when too big)."""
    name = hashlib.sha1(url.split("?")[0].encode()).hexdigest()[:20]
    ext = os.path.splitext(url.split("?")[0])[1][:6] or ".mp4"
    path = os.path.join(video_cache_dir(), name + ext)
    if not os.path.exists(path):
        data = core.download(url, limit=MAX_VIDEO, timeout=60)
        tmp = path + ".part"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        trim_cache()
    return path


def trim_cache(max_bytes=500 * 1024 * 1024):
    try:
        d = video_cache_dir()
        files = sorted((os.path.join(d, f) for f in os.listdir(d)), key=os.path.getmtime)
        total = sum(os.path.getsize(f) for f in files)
        while files and total > max_bytes:
            f = files.pop(0)
            total -= os.path.getsize(f)
            os.remove(f)
    except OSError:
        pass


def fit(w, h, max_w, max_h):
    if not w or not h:
        return max_w, max_h
    r = min(max_w / w, max_h / h, 1.0)
    return max(1, int(w * r)), max(1, int(h * r))


def tenor_gif_url(url):
    """Tenor mp4 link -> the same animation as a .gif (used when OpenCV is missing)."""
    if "media.tenor.com/" not in (url or ""):
        return None
    try:
        head, name = url.split("?")[0].rsplit("/", 1)
        base, code = head.rsplit("/", 1)
        return f"{base}/{code[:-5]}AAAAC/{name.rsplit('.', 1)[0]}.gif"
    except ValueError:
        return None


def gifv_video_url(embed):
    v = embed.get("video") or {}
    return v.get("proxy_url") or v.get("url")


def open_external(path_or_url):
    """Open in the normal Windows program (video player / browser) - with sound."""
    try:
        if os.path.exists(path_or_url) and sys.platform == "win32":
            os.startfile(path_or_url)          # noqa
        else:
            webbrowser.open(path_or_url)
    except Exception:
        webbrowser.open(path_or_url)


class Decoder(threading.Thread):
    """Reads frames in the background and hands them over as small PIL pictures."""

    def __init__(self, path, max_w, max_h, loop):
        super().__init__(daemon=True)
        self.path, self.max_w, self.max_h, self.loop = path, max_w, max_h, loop
        self.frames = queue.Queue(maxsize=8)
        self.stop_flag = threading.Event()
        self.paused = threading.Event()
        self.seek_to = None
        self.fps = 30.0
        self.total = 0
        self.size = (max_w, max_h)
        self.ready = threading.Event()
        self.error = None

    def run(self):
        from PIL import Image
        cap = cv2.VideoCapture(self.path)
        if not cap.isOpened():
            self.error = "This video format can't be played here."
            self.ready.set()
            return
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        if not 1 <= self.fps <= 120:
            self.fps = 30.0
        self.total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.size = fit(int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), self.max_w, self.max_h)
        self.ready.set()
        idx = 0
        while not self.stop_flag.is_set():
            if self.seek_to is not None:
                cap.set(cv2.CAP_PROP_POS_FRAMES, self.seek_to)
                idx = self.seek_to
                self.seek_to = None
                self._drain()
            if self.paused.is_set():
                time.sleep(0.05)
                continue
            ok, frame = cap.read()
            if not ok:
                if self.loop:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    idx = 0
                    continue
                self._put((None, idx))
                self.paused.set()
                continue
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if (frame.shape[1], frame.shape[0]) != self.size:
                frame = cv2.resize(frame, self.size, interpolation=cv2.INTER_AREA)
            self._put((Image.fromarray(frame), idx))
            idx += 1
        cap.release()

    def _put(self, item):
        while not self.stop_flag.is_set():
            try:
                self.frames.put(item, timeout=0.2)
                return
            except queue.Full:
                if self.seek_to is not None:
                    return

    def _drain(self):
        try:
            while True:
                self.frames.get_nowait()
        except queue.Empty:
            pass


class VideoPlayer(tk.Frame):
    """Inline player. gif=True: plays by itself on a loop, no controls (like Discord GIFs)."""

    def __init__(self, master, url, poster_url, images, bg, max_size=(400, 300), gif=False,
                 name="video", duration=None):
        super().__init__(master, bg=bg)
        self.url, self.images, self.gif, self.name = url, images, gif, name
        self.max_w, self.max_h = max_size
        self.decoder = None
        self.photo = None
        self.path = None
        self.playing = False
        self.pos = 0
        self.screen = tk.Label(self, bg="#000000" if not gif else bg, fg=WHITE,
                               text="GIF" if gif else "▶", font=(FONT, 24, "bold"),
                               compound="center", cursor="hand2", notr=True,
                               width=0 if poster_url else 20, height=0 if poster_url else 6)
        self.screen.pack(anchor="w")
        self.screen.bind("<Button-1>", lambda e: self.toggle())
        self.poster = None
        if poster_url:
            images.load(poster_url, (self.max_w, self.max_h), self, mode="thumb")
        if not gif:
            bar = tk.Frame(self, bg=BAR_BG)
            bar.pack(fill="x")
            self.play_btn = self._btn(bar, "▶", self.toggle)
            self.time_lbl = tk.Label(bar, text="0:00" + (f" / {_mmss(duration)}" if duration
                                                         else ""), bg=BAR_BG, fg=MUTED,
                                     font=(FONT, 8), notr=True)
            self.time_lbl.pack(side="left", padx=4)
            self._btn(bar, "🔊 Sound", self.with_sound, side="right")
            self.track = tk.Canvas(bar, height=6, bg="#3f4147", highlightthickness=0,
                                   cursor="hand2")
            self.track.pack(side="left", fill="x", expand=True, padx=8, pady=8)
            self.track.bind("<Button-1>", self.seek_click)
        if gif:
            self.after(50, self.play)

    def _btn(self, bar, text, cmd, side="left"):
        b = tk.Label(bar, text=text, bg=BAR_BG, fg=WHITE, font=(FONT, 9), padx=8, pady=3,
                     cursor="hand2", notr=True)
        b.pack(side=side)
        b.bind("<Button-1>", lambda e: cmd())
        return b

    # ImageLoader calls this with the poster picture
    def set_image(self, photo):
        self.poster = photo
        if not self.playing and not self.photo:
            self.screen.configure(image=photo, width=0, height=0)

    def failed(self):
        pass

    def toggle(self):
        if self.playing:
            self.pause()
        else:
            self.play()

    def play(self):
        if not HAVE_VIDEO:
            self.fallback()
            return
        self.playing = True
        if not self.gif:
            self.play_btn.configure(text="⏸")
            self.screen.configure(text="")
        if self.decoder is None:
            if not self.gif:
                self.screen.configure(text="…")
            threading.Thread(target=self._start, daemon=True).start()
        else:
            if self.decoder.paused.is_set() and self.pos >= max(0, self.decoder.total - 2):
                self.decoder.seek_to = 0
            self.decoder.paused.clear()
            self._tick()

    def _start(self):
        try:
            self.path = cached_file(self.url)
        except Exception as e:
            msg = str(e)
            self.after(0, lambda: self._error(msg))
            return
        dec = Decoder(self.path, self.max_w, self.max_h, loop=self.gif)
        dec.start()
        dec.ready.wait(15)
        self.after(0, lambda: self._started(dec))

    def _started(self, dec):
        if dec.error:
            self._error(dec.error)
            return
        self.decoder = dec
        if not self.playing:
            dec.paused.set()
        self._tick()

    def _error(self, msg):
        self.playing = False
        try:
            self.screen.configure(text="▶", fg=WHITE)
            if not self.gif:
                self.play_btn.configure(text="▶")
                self.time_lbl.configure(text="Can't play here - use Sound to open it")
            else:
                self.fallback()
        except tk.TclError:
            pass

    def fallback(self):
        """No OpenCV: GIFs from Tenor still animate as real .gif, videos open outside."""
        if self.gif:
            gif = tenor_gif_url(self.url)
            if gif:
                self.images.load(gif, (self.max_w, self.max_h), self.screen_target(),
                                 mode="anim")
            return
        open_external(self.url)

    def screen_target(self):
        player = self

        class T:
            def winfo_exists(self):
                return player.winfo_exists()

            def set_frames(self, photos, durations):
                lbl = player.screen
                lbl.configure(text="")

                def step(i):
                    try:
                        if lbl.winfo_exists():
                            lbl.configure(image=photos[i])
                            lbl.photos = photos
                            lbl.after(durations[i], lambda: step((i + 1) % len(photos)))
                    except tk.TclError:
                        pass
                step(0)

            def set_image(self, photo):
                player.set_image(photo)

            def failed(self):
                pass
        return T()

    def pause(self):
        self.playing = False
        if self.decoder:
            self.decoder.paused.set()
        if not self.gif:
            self.play_btn.configure(text="▶")

    def visible(self):
        """Only decode while the player is on screen (saves CPU in long chats)."""
        try:
            if not self.winfo_viewable():
                return False
            top = self.winfo_toplevel()
            y = self.winfo_rooty()
            ty = top.winfo_rooty()
            return y + self.winfo_height() > ty and y < ty + top.winfo_height()
        except tk.TclError:
            return False

    def _tick(self):
        if not self.playing or self.decoder is None:
            return
        try:
            if not self.winfo_exists():
                self.destroy_decoder()
                return
        except tk.TclError:
            return
        delay = int(1000 / self.decoder.fps)
        if self.gif and not self.visible():
            self.after(400, self._tick)
            return
        try:
            img, idx = self.decoder.frames.get_nowait()
        except queue.Empty:
            self.after(max(5, delay // 2), self._tick)
            return
        if img is None:                         # end of the video
            self.playing = False
            self.play_btn.configure(text="↻")
            return
        from PIL import ImageTk
        self.photo = ImageTk.PhotoImage(img)
        self.pos = idx
        self.screen.configure(image=self.photo, text="", width=0, height=0)
        if not self.gif:
            self._draw_progress()
        self.after(delay, self._tick)

    def _draw_progress(self):
        d = self.decoder
        if not d or not d.total:
            return
        w = self.track.winfo_width()
        self.track.delete("all")
        x = int(w * self.pos / max(1, d.total))
        self.track.create_rectangle(0, 0, x, 6, fill="#5865f2", outline="")
        self.time_lbl.configure(text=f"{_mmss(self.pos / d.fps)} / {_mmss(d.total / d.fps)}")

    def seek_click(self, e):
        d = self.decoder
        if not d or not d.total:
            return
        frac = min(1.0, max(0.0, e.x / max(1, self.track.winfo_width())))
        d.seek_to = int(d.total * frac)
        self.pos = d.seek_to
        if not self.playing:
            self.play()

    def with_sound(self):
        self.pause()
        if self.path:
            open_external(self.path)
        else:
            def work():
                try:
                    p = cached_file(self.url)
                except Exception:
                    p = self.url
                self.after(0, lambda: open_external(p))
            threading.Thread(target=work, daemon=True).start()

    def destroy_decoder(self):
        if self.decoder:
            self.decoder.stop_flag.set()
            self.decoder = None

    def destroy(self):
        self.destroy_decoder()
        super().destroy()


def _mmss(sec):
    try:
        sec = int(sec)
    except (TypeError, ValueError):
        return "0:00"
    return f"{sec // 60}:{sec % 60:02d}"
