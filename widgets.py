"""Small reusable Tkinter widgets styled like Discord (dark, black or light theme)."""
import base64
import hashlib
import os
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor

import cleaner_core as core
import i18n

FONT = "Segoe UI"

# Colour themes. The theme is read from the settings before anything is built, so every
# widget uses the right colours. Changing theme needs a restart (the app does it for you).
_BASE = {
    "BLURPLE": "#5865f2", "BLURPLE_HI": "#4752c4", "GREEN": "#23a55a", "RED": "#da373c",
    "RED_HI": "#a12828", "MENTION_BAR": "#f0b232", "PKG_COLOR": "#248046",
}
THEMES = {
    "dark": dict(_BASE,
                 RAIL="#1e1f22", SIDEBAR="#2b2d31", CHAT="#313338", USERBAR="#232428",
                 INPUT="#1e1f22", TEXT="#dbdee1", WHITE="#f2f3f5", MUTED="#949ba4",
                 HOVER="#35373c", SELECTED="#404249", LINK="#00a8fc", DIVIDER="#3f4147",
                 BORDER="#26282c", MATCH_BG="#3e2a2e", KEEP_BG="#26352c",
                 MENTION_BG="#3d3a30", MSG_HOVER="#2e3035", CODE_BG="#2b2d31",
                 FIELD_BG="#383a40", TIP_BG="#111214", ERROR_FG="#fa777c",
                 GOOD_FG="#57f287", PLACEHOLDER="#6d6f78", CHECK_OUTLINE="#80848e",
                 CHECK_INHERIT="#4e5058", QUOTE_BAR="#4e5058", DISABLED_BG="#3a3c42",
                 DISABLED_FG="#6d6f78", THUMB="#1a1b1e", THUMB_HOVER="#111214",
                 THUMB_ALT="#3f4147", CODE_BORDER="#1e1f22", REACT_ME_BG="#373a54",
                 ICON_MUTED="#b5bac1", LOG_BG="#1e1f22"),
    "black": dict(_BASE,
                  RAIL="#000000", SIDEBAR="#0e0e10", CHAT="#000000", USERBAR="#0a0a0b",
                  INPUT="#16171a", TEXT="#dbdee1", WHITE="#f2f3f5", MUTED="#8e9297",
                  HOVER="#1a1b1e", SELECTED="#26272b", LINK="#00a8fc", DIVIDER="#26272b",
                  BORDER="#151517", MATCH_BG="#2a1316", KEEP_BG="#102118",
                  MENTION_BG="#2a2513", MSG_HOVER="#0c0c0e", CODE_BG="#111214",
                  FIELD_BG="#16171a", TIP_BG="#111214", ERROR_FG="#fa777c",
                  GOOD_FG="#57f287", PLACEHOLDER="#5c5f66", CHECK_OUTLINE="#6d7079",
                  CHECK_INHERIT="#3a3c42", QUOTE_BAR="#3a3c42", DISABLED_BG="#1e1f22",
                  DISABLED_FG="#5c5f66", THUMB="#1e1f22", THUMB_HOVER="#2b2d31",
                  THUMB_ALT="#2b2d31", CODE_BORDER="#1e1f22", REACT_ME_BG="#232541",
                  ICON_MUTED="#8e9297", LOG_BG="#0a0a0b"),
    "light": dict(_BASE,
                  RAIL="#e3e5e8", SIDEBAR="#f2f3f5", CHAT="#ffffff", USERBAR="#ebedef",
                  INPUT="#e3e5e8", TEXT="#313338", WHITE="#060607", MUTED="#5c5e66",
                  HOVER="#e0e1e5", SELECTED="#d7d9dc", LINK="#006ce7", DIVIDER="#d4d7dc",
                  BORDER="#e1e2e4", MATCH_BG="#fde4e6", KEEP_BG="#def5e6",
                  MENTION_BG="#fdf3dc", MSG_HOVER="#f6f6f7", CODE_BG="#f2f3f5",
                  FIELD_BG="#ebedef", TIP_BG="#ffffff", ERROR_FG="#d22d39",
                  GOOD_FG="#1a7f43", PLACEHOLDER="#80848e", CHECK_OUTLINE="#80848e",
                  CHECK_INHERIT="#a5a9b0", QUOTE_BAR="#c4c9ce", DISABLED_BG="#d7d9dc",
                  DISABLED_FG="#80848e", THUMB="#c4c9ce", THUMB_HOVER="#a5a9b0",
                  THUMB_ALT="#c4c9ce", CODE_BORDER="#e3e5e8", REACT_ME_BG="#e6e8fd",
                  ICON_MUTED="#5c5e66", LOG_BG="#ebedef"),
}
THEMES["midnight"] = dict(THEMES["dark"], RAIL="#0f1424", SIDEBAR="#161c30", CHAT="#1c2338",
                          USERBAR="#121829", INPUT="#121829", HOVER="#232b44", SELECTED="#2c3552",
                          DIVIDER="#2c3552", BORDER="#121829", MSG_HOVER="#20283f",
                          CODE_BG="#161c30", FIELD_BG="#252e48", LOG_BG="#121829",
                          THUMB="#0f1424", THUMB_ALT="#2c3552", MATCH_BG="#3a2433",
                          KEEP_BG="#1d3330", MENTION_BG="#363423")
THEMES["forest"] = dict(THEMES["dark"], RAIL="#121a15", SIDEBAR="#18231c", CHAT="#1e2b22",
                        USERBAR="#141d17", INPUT="#141d17", HOVER="#253428", SELECTED="#2e4033",
                        DIVIDER="#2e4033", BORDER="#141d17", MSG_HOVER="#223026",
                        CODE_BG="#18231c", FIELD_BG="#283a2d", LOG_BG="#141d17",
                        THUMB="#121a15", THUMB_ALT="#2e4033", MATCH_BG="#3b2528",
                        KEEP_BG="#1f3a26", MENTION_BG="#36351f")
THEMES["grape"] = dict(THEMES["dark"], RAIL="#1a1425", SIDEBAR="#221a31", CHAT="#2a2040",
                       USERBAR="#1d162a", INPUT="#1d162a", HOVER="#33284b", SELECTED="#3d3059",
                       DIVIDER="#3d3059", BORDER="#1d162a", MSG_HOVER="#30254a",
                       CODE_BG="#221a31", FIELD_BG="#372b51", LOG_BG="#1d162a",
                       THUMB="#1a1425", THUMB_ALT="#3d3059", MATCH_BG="#43243a",
                       KEEP_BG="#23343a", MENTION_BG="#3d3526")
THEME_NAMES = {"dark": "Dark", "black": "Black (OLED)", "light": "Light", "midnight": "Midnight",
               "forest": "Forest", "grape": "Grape"}
THEME_SWATCHES = {k: (v["CHAT"], v["WHITE"]) for k, v in THEMES.items()}
ACCENTS = {"blurple": ("#5865f2", "#4752c4"), "green": ("#23a55a", "#1a8048"),
           "red": ("#da373c", "#a12828"), "pink": ("#eb459f", "#c13584"),
           "orange": ("#f0883e", "#c96d2c"), "teal": ("#1abc9c", "#138d75"),
           "purple": ("#9b59b6", "#7d3c98"), "gold": ("#f0b232", "#c28f22")}


def _saved_look():
    """(theme, accent) from the settings file, read before any widget is built."""
    try:
        import json
        root = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
        with open(os.path.join(root, "DiscordMessageCleaner", "settings.json"),
                  encoding="utf-8") as f:
            st = json.load(f)
        name = st.get("theme", "dark")
        accent = st.get("accent", "blurple")
        return (name if name in THEMES else "dark"), (accent if accent in ACCENTS else "blurple")
    except Exception:
        return "dark", "blurple"


THEME, ACCENT = _saved_look()
globals().update(THEMES[THEME])
BLURPLE, BLURPLE_HI = ACCENTS[ACCENT]
AVATAR_COLORS = ["#5865f2", "#757e8a", "#3ba55c", "#faa61a", "#ed4245", "#eb459f"]


def color_for(some_id):
    try:
        return AVATAR_COLORS[int(some_id) % len(AVATAR_COLORS)]
    except (TypeError, ValueError):
        return AVATAR_COLORS[0]


def set_bg(widget, color, skip=()):
    """Recursively change the background of a widget and its children."""
    if widget in skip:
        return
    try:
        widget.configure(bg=color)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        set_bg(child, color, skip)


def is_inside(widget, ancestor):
    while widget is not None:
        if widget is ancestor:
            return True
        widget = getattr(widget, "master", None)
    return False


def bind_tree(widget, event, func):
    """Bind an event on a widget and all its children."""
    widget.bind(event, func, add="+")
    for child in widget.winfo_children():
        bind_tree(child, event, func)


class ThinScrollbar(tk.Canvas):
    """Thin rounded scrollbar like Discord's (the Windows one can't be coloured)."""

    def __init__(self, master, bg, command, width=10, thumb=None, thumb_hover=None):
        super().__init__(master, width=width, bg=bg, highlightthickness=0, bd=0)
        self.command = command
        self.colors = (thumb or THUMB, thumb_hover or THUMB_HOVER)
        self.first, self.last = 0.0, 1.0
        self.drag = None
        self.hover = False
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<ButtonPress-1>", self.press)
        self.bind("<B1-Motion>", self.motion)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag", None))
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))

    def _hover(self, on):
        self.hover = on
        self.redraw()

    def set(self, first, last):
        self.first, self.last = float(first), float(last)
        self.redraw()

    def thumb_coords(self):
        h = max(1, self.winfo_height())
        y1 = self.first * h
        y2 = max(y1 + 24, self.last * h)
        if y2 > h:
            y1, y2 = h - (y2 - y1), h
        return y1, y2

    def redraw(self):
        self.delete("all")
        if self.first <= 0 and self.last >= 1:
            return
        w = int(self.cget("width"))
        y1, y2 = self.thumb_coords()
        pad = 2
        self.create_line(w / 2, y1 + w / 2, w / 2, y2 - w / 2, width=w - 2 * pad,
                         capstyle="round", fill=self.colors[1 if self.hover or self.drag
                                                            is not None else 0])

    def press(self, e):
        y1, y2 = self.thumb_coords()
        h = max(1, self.winfo_height())
        if y1 <= e.y <= y2:
            self.drag = (e.y, self.first)
        else:
            self.command("scroll", 1 if e.y > y2 else -1, "pages")

    def motion(self, e):
        if self.drag is None:
            return
        h = max(1, self.winfo_height())
        y0, first0 = self.drag
        self.command("moveto", first0 + (e.y - y0) / h)


class ScrollFrame(tk.Frame):
    """Vertically scrollable frame with smooth scrolling. Put content in .inner.

    - mouse wheel: smooth, ~100px per notch (like Discord)
    - hold the wheel (middle button) and move the mouse: auto-scroll
    - drag the thin scrollbar
    """

    def __init__(self, master, bg, scrollbar=True, **kw):
        super().__init__(master, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, yscrollincrement=1)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.sb = ThinScrollbar(self, bg, self.canvas.yview,
                                thumb=THUMB_ALT if bg in (RAIL, INPUT) else THUMB)
        self.canvas.configure(yscrollcommand=self.sb.set)
        if scrollbar:
            self.sb.pack(side="right", fill="y", padx=(0, 2))
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", self._update_region)
        self.canvas.bind("<Configure>", self._resize)
        self._target = None
        self._anim = None
        self._auto = None

    # ---- geometry
    def _update_region(self, _=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize(self, e):
        self.canvas.itemconfigure(self.win, width=e.width)

    def _metrics(self):
        bbox = self.canvas.bbox("all") or (0, 0, 0, 0)
        total = max(1, bbox[3] - bbox[1])
        view = max(1, self.canvas.winfo_height())
        top = self.canvas.yview()[0] * total
        return total, view, top

    # ---- smooth scrolling
    def scroll_pixels(self, px, smooth=True):
        total, view, top = self._metrics()
        if total <= view:
            return
        base = self._target if self._target is not None else top
        self._target = min(max(0, base + px), total - view)
        if not smooth:
            self.canvas.yview_moveto(self._target / total)
            self._target = None
            return
        if self._anim is None:
            self._animate()

    def _animate(self):
        if self._target is None:
            self._anim = None
            return
        total, view, top = self._metrics()
        diff = self._target - top
        if abs(diff) < 1:
            self.canvas.yview_moveto(self._target / total)
            self._target = None
            self._anim = None
            return
        step = diff * 0.35 if abs(diff) > 3 else diff
        self.canvas.yview_moveto((top + step) / total)
        self._anim = self.after(12, self._animate)

    def wheel(self, delta):
        notches = delta / 120 if abs(delta) >= 120 else (1 if delta > 0 else -1)
        self.scroll_pixels(-notches * 110)

    # ---- hold-the-wheel auto-scroll
    def start_autoscroll(self, y_root):
        self.stop_autoscroll()
        self._auto = {"origin": y_root, "y": y_root}
        try:
            self.canvas.configure(cursor="sb_v_double_arrow")
        except tk.TclError:
            pass
        self._autoscroll_step()

    def move_autoscroll(self, y_root):
        if self._auto:
            self._auto["y"] = y_root

    def stop_autoscroll(self):
        if self._auto:
            self._auto = None
            try:
                self.canvas.configure(cursor="")
            except tk.TclError:
                pass

    def _autoscroll_step(self):
        if not self._auto:
            return
        d = self._auto["y"] - self._auto["origin"]
        if abs(d) > 8:
            speed = (abs(d) - 8) ** 1.25 / 5
            self.scroll_pixels(speed if d > 0 else -speed, smooth=False)
        self.after(16, self._autoscroll_step)

    # ---- helpers
    def clear(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self._target = None
        self.canvas.yview_moveto(0)

    def to_bottom(self):
        self.update_idletasks()
        self._update_region()
        self._target = None
        self.canvas.yview_moveto(1.0)

    def to_top(self):
        self.update_idletasks()
        self._update_region()
        self._target = None
        self.canvas.yview_moveto(0.0)

    def page(self, direction):
        self.scroll_pixels(direction * max(100, self.canvas.winfo_height() - 80))


class Avatar(tk.Canvas):
    """Round picture with a coloured placeholder (initials) until the image loads.
    shape: 'circle' or 'rounded' (Discord's rounded square for hovered/selected servers)."""

    def __init__(self, master, size, bg, text="?", color=BLURPLE, font_size=None):
        super().__init__(master, width=size, height=size, bg=bg, highlightthickness=0, bd=0)
        self.size = size
        self.text = text
        self.color = color
        self.font_size = font_size or max(8, int(size / (2.6 if len(text) <= 1 else 3.4)))
        self.shape = "circle"
        self.photos = {}
        self.badge = None
        self.ph_color = color
        self._draw()

    def _shape_coords(self, shape):
        s = self.size
        if shape == "circle":
            return None
        r = s * 0.32
        return [r, 0, s - r, 0, s, 0, s, r, s, s - r, s, s, s - r, s, r, s, 0, s, 0, s - r,
                0, r, 0, 0]

    def _draw(self):
        self.delete("all")
        s = self.size
        photo = self.photos.get(self.shape) or self.photos.get("circle")
        if photo is not None:
            self.create_image(s / 2, s / 2, image=photo, tags="img")
        else:
            if self.shape == "circle":
                self.create_oval(0, 0, s - 1, s - 1, fill=self.ph_color, outline=self.ph_color)
            else:
                self.create_polygon(self._shape_coords("rounded"), smooth=True,
                                    fill=self.ph_color, outline=self.ph_color)
            self.create_text(s / 2, s / 2, text=self.text, fill="white",
                             font=(FONT, self.font_size, "bold"))
        if self.badge:
            self._draw_badge(self.badge)

    def set_image(self, photo, shape="circle"):
        self.photos[shape] = photo
        self._draw()

    def set_shape(self, shape, hover_color=None):
        self.shape = shape
        self.ph_color = hover_color or self.color
        self._draw()

    def set_badge(self, on, color=GREEN):
        self.badge = color if on else None
        self._draw()

    def _draw_badge(self, color):
        s = self.size
        r = max(5, s // 7)
        bg = self.cget("bg")
        self.create_oval(s - 2 * r - 3, s - 2 * r - 3, s, s, fill=bg, outline=bg, tags="badge")
        self.create_oval(s - 2 * r - 1, s - 2 * r - 1, s - 2, s - 2, fill=color,
                         outline=color, tags="badge")


class ImageLoader:
    """Downloads avatars/server icons/thumbnails in the background, caches them in
    memory and on disk (so the next start is instant).
    mode 'circle' / 'rounded': square picture of `size`.  mode 'thumb': fits in (w, h)."""

    def __init__(self, root, cache_dir=None):
        self.root = root
        self.pool = ThreadPoolExecutor(max_workers=10)
        self.cache = {}
        self.pending = {}
        self.cache_dir = cache_dir
        if cache_dir:
            try:
                os.makedirs(cache_dir, exist_ok=True)
            except OSError:
                self.cache_dir = None

    def load(self, url, size, widget, mode="circle"):
        if not url:
            return
        key = (url.split("?")[0] + ("?fmt" if "format=" in url else ""),
               size if mode in ("circle", "rounded") else tuple(size), mode)
        if key in self.cache:
            self._apply(widget, self.cache[key], mode)
            return
        if key in self.pending:
            self.pending[key].append(widget)
            return
        self.pending[key] = [widget]
        self.pool.submit(self._work, key, url)

    def _disk_path(self, key):
        h = hashlib.sha1(repr(key).encode()).hexdigest()
        return os.path.join(self.cache_dir, h + ".png")

    def _work(self, key, url):
        _, size, mode = key
        b64 = None
        path = self._disk_path(key) if self.cache_dir and mode != "anim" else None
        try:
            if path and os.path.exists(path):
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
            elif mode == "anim":
                frames, durations = core.gif_frames_b64(core.fetch_image(url), size[0], size[1])
                b64 = (frames, durations)
                path = None
            else:
                data = core.fetch_image(url)
                if mode == "circle":
                    b64 = core.circle_png_b64(data, size)
                elif mode == "rounded":
                    b64 = core.rounded_png_b64(data, size)
                else:
                    b64 = core.thumb_png_b64(data, size[0], size[1])
                if path and b64:
                    try:
                        with open(path, "wb") as f:
                            f.write(base64.b64decode(b64))
                    except OSError:
                        pass
        except Exception:
            b64 = None
        try:
            self.root.after(0, lambda: self._done(key, b64))
        except Exception:
            pass

    def _apply(self, w, photo, mode):
        if mode == "rounded":
            w.set_image(photo, "rounded")
        elif mode == "anim":
            if hasattr(w, "set_frames"):
                w.set_frames(*photo)
            else:
                w.set_image(photo[0][0])
        else:
            w.set_image(photo)

    def _done(self, key, b64):
        widgets = self.pending.pop(key, [])
        if not b64:
            for w in widgets:
                if hasattr(w, "failed"):
                    try:
                        w.failed()
                    except tk.TclError:
                        pass
            return
        try:
            if key[2] == "anim":
                photo = ([tk.PhotoImage(data=f) for f in b64[0]], b64[1])
            else:
                photo = tk.PhotoImage(data=b64)
        except tk.TclError:
            return
        self.cache[key] = photo
        for w in widgets:
            try:
                if w.winfo_exists():
                    self._apply(w, photo, key[2])
            except tk.TclError:
                pass


class Thumb(tk.Label):
    """Picture preview. overlay: text drawn on top (e.g. '▶' for videos).
    Animated GIFs play when set_frames() is used. on_click opens the big viewer."""

    def __init__(self, master, bg, name, overlay=None, on_click=None):
        super().__init__(master, text=i18n.tr("Loading…") + f" {name}", bg=bg, fg=MUTED,
                         font=(FONT, 8), anchor="w", cursor="hand2" if on_click else "",
                         notr=True)
        self.photo = None
        self.frames = None
        self.name = name
        self.overlay = overlay
        if on_click:
            self.bind("<Button-1>", lambda e: on_click())

    def set_image(self, photo):
        self.photo = photo
        if self.overlay:
            self.configure(image=photo, text=self.overlay, compound="center", fg="white",
                           font=(FONT, 22, "bold"))
        else:
            self.configure(image=photo, text="")

    def set_frames(self, photos, durations):
        self.frames = (photos, durations)
        self.set_image(photos[0])
        if len(photos) > 1:
            self._play(0)

    def _play(self, i):
        try:
            if not self.winfo_exists():
                return
            photos, durations = self.frames
            self.configure(image=photos[i])
            self.after(durations[i], lambda: self._play((i + 1) % len(photos)))
        except tk.TclError:
            pass

    def failed(self):
        self.configure(text=f"▪ {self.name}", fg=LINK)


class EmojiLabel(Thumb):
    """Shows an emoji: the picture when it loads, the emoji character until then."""

    def __init__(self, master, bg, text="", font_size=10):
        super().__init__(master, bg, "")
        self.configure(text=text, font=("Segoe UI Emoji", font_size), fg=TEXT)

    def failed(self):
        pass


class Check(tk.Canvas):
    """Discord-style square checkbox. state: 'off' | 'on' | 'inherited'."""

    def __init__(self, master, bg, command=None, size=20):
        super().__init__(master, width=size, height=size, bg=bg, highlightthickness=0, bd=0,
                         cursor="hand2")
        self.s = size
        self.command = command
        self.state = None
        self.set("off")
        self.bind("<Button-1>", self._click)

    def _click(self, _):
        if self.command:
            self.command()
        return "break"

    def set(self, state):
        if state == self.state:
            return
        self.state = state
        self.delete("all")
        s = self.s
        if state == "off":
            self.create_rectangle(2, 2, s - 3, s - 3, outline=CHECK_OUTLINE, width=2)
        else:
            fill = BLURPLE if state == "on" else CHECK_INHERIT
            self.create_rectangle(1, 1, s - 2, s - 2, fill=fill, outline=fill)
            self.create_line(s * .25, s * .52, s * .43, s * .70, s * .76, s * .32,
                             fill="white", width=2, capstyle="round", joinstyle="round")


class OptionCheck(tk.Frame):
    """Checkbox + text bound to a BooleanVar."""

    def __init__(self, master, text, var, bg, command=None, fg=TEXT):
        super().__init__(master, bg=bg, cursor="hand2")
        self.var = var
        self.command = command
        self.check = Check(self, bg, command=self.toggle, size=18)
        self.check.pack(side="left")
        self.label = tk.Label(self, text=text, bg=bg, fg=fg, font=(FONT, 9))
        self.label.pack(side="left", padx=(7, 0))
        self.label.bind("<Button-1>", lambda e: self.toggle())
        self.bind("<Button-1>", lambda e: self.toggle())
        var.trace_add("write", lambda *a: self.refresh())
        self.refresh()

    def toggle(self):
        self.var.set(not self.var.get())
        if self.command:
            self.command()

    def refresh(self):
        self.check.set("on" if self.var.get() else "off")


class PlaceholderEntry(tk.Entry):
    """Flat entry that shows grey hint text while empty."""

    def __init__(self, master, placeholder, show=None, **kw):
        kw.setdefault("bg", INPUT)
        kw.setdefault("font", (FONT, 10))
        super().__init__(master, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                         highlightthickness=0, **kw)
        self.placeholder = i18n.tr(placeholder)
        self.real_show = show or ""
        self.showing = False
        self.bind("<FocusIn>", self._in, add="+")
        self.bind("<FocusOut>", self._out, add="+")
        self.bind("<Key>", self._in, add="+")
        self._out()

    def _in(self, _=None):
        if self.showing:
            self.delete(0, "end")
            self.configure(fg=TEXT, show=self.real_show)
            self.showing = False

    def _out(self, _=None):
        if not super().get():
            self.configure(fg=MUTED, show="")
            self.insert(0, self.placeholder)
            self.showing = True

    def get(self):
        return "" if self.showing else super().get()

    def set(self, text):
        self._in()
        self.delete(0, "end")
        self.insert(0, text)
        if not text and self.focus_get() is not self:
            self._out()

    def set_show(self, show):
        self.real_show = show or ""
        if not self.showing:
            self.configure(show=self.real_show)


def entry_box(master, placeholder, bg=INPUT, show=None, width=None, font_size=10):
    """An entry inside a padded rounded-looking box. Returns (box, entry)."""
    box = tk.Frame(master, bg=bg)
    kw = {"width": width} if width else {}
    e = PlaceholderEntry(box, placeholder, show=show, bg=bg, font=(FONT, font_size), **kw)
    e.pack(fill="x", expand=True, padx=10, pady=7)
    box.bind("<Button-1>", lambda ev: e.focus_set())
    return box, e


class FlatButton(tk.Label):
    """Clickable label that looks like a Discord button."""

    def __init__(self, master, text, command, bg=BLURPLE, hover=BLURPLE_HI, fg="white",
                 font_size=10, padx=16, pady=7, bold=True):
        super().__init__(master, text=text, bg=bg, fg=fg, cursor="hand2", padx=padx, pady=pady,
                         font=(FONT, font_size, "bold" if bold else "normal"))
        self.command = command
        self.colors = (bg, hover)
        self.enabled = True
        self.bind("<Enter>", lambda e: self.enabled and self.configure(bg=self.colors[1]))
        self.bind("<Leave>", lambda e: self.enabled and self.configure(bg=self.colors[0]))
        self.bind("<Button-1>", lambda e: self.enabled and self.command and self.command())

    def set_colors(self, bg, hover):
        self.colors = (bg, hover)
        if self.enabled:
            self.configure(bg=bg)

    def set_enabled(self, on):
        self.enabled = on
        self.configure(bg=self.colors[0] if on else DISABLED_BG,
                       fg="white" if on else DISABLED_FG,
                       cursor="hand2" if on else "arrow")


class LinkLabel(tk.Label):
    def __init__(self, master, text, command, bg, fg=LINK, font_size=9):
        super().__init__(master, text=text, bg=bg, fg=fg, cursor="hand2", font=(FONT, font_size))
        self.bind("<Button-1>", lambda e: command())
        self.bind("<Enter>", lambda e: self.configure(font=(FONT, font_size, "underline")))
        self.bind("<Leave>", lambda e: self.configure(font=(FONT, font_size)))


class Tooltip:
    """Dark tooltip shown to the right of a widget (like server names in Discord)."""

    def __init__(self, widget, text_func, notr=False):
        self.widget = widget
        self.text_func = text_func
        self.notr = notr
        self.tip = None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")

    def show(self, _=None):
        self.hide()
        try:
            x = self.widget.winfo_rootx() + self.widget.winfo_width() + 10
            y = self.widget.winfo_rooty() + self.widget.winfo_height() // 2 - 16
            self.tip = tk.Toplevel(self.widget)
            self.tip.overrideredirect(True)
            self.tip.attributes("-topmost", True)
            self.tip.configure(bg=TIP_BG)
            tk.Label(self.tip, text=self.text_func(), notr=self.notr, bg=TIP_BG, fg=WHITE,
                     font=(FONT, 10, "bold"), padx=10, pady=6).pack()
            self.tip.geometry(f"+{x}+{y}")
        except tk.TclError:
            self.tip = None

    def hide(self, _=None):
        if self.tip is not None:
            try:
                self.tip.destroy()
            except tk.TclError:
                pass
            self.tip = None
