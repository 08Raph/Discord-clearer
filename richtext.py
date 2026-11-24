"""Discord-style message text: emojis as pictures inside the text, @mentions, links,
**bold**, *italic*, __underline__, ~~strike~~, `code`, ||spoilers||, # headers, lists.

MessageText is a read-only tk.Text that sizes itself to its content (like a Label),
but can show pictures in the middle of a line and lets you select / copy text.
"""
import re
import tkinter as tk
import webbrowser
from datetime import datetime

import cleaner_core as core
import emojis
from widgets import CODE_BG, FONT, LINK, MUTED, TEXT, WHITE

MENTION_BG = "#3c4270"
MENTION_FG = "#c9cdfb"
SPOILER_BG = "#1e1f22"
INLINE = 22
JUMBO = 48

TOKEN_RE = re.compile(
    r"(?P<custom><a?:\w+:\d+>)"
    r"|(?P<user><@!?\d+>)|(?P<role><@&\d+>)|(?P<chan><#\d+>)|(?P<every>@everyone|@here)"
    r"|(?P<time><t:-?\d+(?::[tTdDfFR])?>)"
    r"|(?P<mlink>\[(?P<mtext>[^\]\n]+)\]\((?P<murl>https?://[^)\s]+)\))"
    r"|(?P<link><?https?://[^\s<>]+[^\s<>.,:;\"')\]]>?)"
    r"|(?P<code>`[^`\n]+`)"
    r"|(?P<bold>\*\*(?=\S)(?:.+?)(?<=\S)\*\*)"
    r"|(?P<under>__(?=\S)(?:.+?)(?<=\S)__)"
    r"|(?P<strike>~~(?=\S)(?:.+?)(?<=\S)~~)"
    r"|(?P<spoil>\|\|(?:.+?)\|\|)"
    r"|(?P<ital>(?<![\w*])\*(?=\S)(?:[^*\n]+?)(?<=\S)\*(?!\*)|(?<!\w)_(?=\S)(?:[^_\n]+?)(?<=\S)_(?!\w))",
    re.S)


ROLES = {}   # role id -> (name, colour int); filled when a server's channels load


def parse(text, mentions=None, resolve_channel=None):
    """Turn message text into segments: (kind, value, styles, extra)."""
    names = {u["id"]: (u.get("global_name") or u.get("username", "user"))
             for u in mentions or []}
    out = []
    for line_no, line in enumerate((text or "").split("\n")):
        if line_no:
            out.append(("text", "\n", frozenset(), None))
        styles = set()
        m = re.match(r"^(#{1,3}) (.+)$", line)
        if m:
            styles.add("h" + str(len(m.group(1))))
            line = m.group(2)
        elif line.startswith("-# "):
            styles.add("sub")
            line = line[3:]
        else:
            lm = re.match(r"^(\s*)[-*] (.+)$", line)
            if lm:
                out.append(("text", lm.group(1) + "  •  ", frozenset(), None))
                line = lm.group(2)
        _inline(line, frozenset(styles), out, names, resolve_channel)
    return out


def _inline(text, styles, out, names, resolve_channel):
    pos = 0
    for m in TOKEN_RE.finditer(text):
        if m.start() > pos:
            _plain(text[pos:m.start()], styles, out)
        kind = m.lastgroup if m.lastgroup not in ("mtext", "murl") else "mlink"
        g = m.group()
        if kind == "custom":
            anim, name, eid = core.EMOJI_RE.match(g).groups()
            out.append(("emoji", f":{name}:", styles,
                        core.emoji_url(eid, anim == "a", 48)))
        elif kind == "user":
            uid = re.sub(r"\D", "", g)
            out.append(("text", "@" + names.get(uid, "user"), styles | {"mention"}, None))
        elif kind == "role":
            name, _colour = ROLES.get(re.sub(r"\D", "", g), ("role", 0))
            out.append(("text", "@" + name, styles | {"mention"}, None))
        elif kind == "chan":
            cid = re.sub(r"\D", "", g)
            name = resolve_channel(cid) if resolve_channel else None
            out.append(("text", "#" + (name or "channel"), styles | {"mention"}, None))
        elif kind == "every":
            out.append(("text", g, styles | {"mention"}, None))
        elif kind == "time":
            out.append(("text", _timestamp(g), styles | {"code"}, None))
        elif kind == "mlink":
            out.append(("text", m.group("mtext"), styles | {"link"}, m.group("murl")))
        elif kind == "link":
            url = g.strip("<>")
            out.append(("text", url, styles | {"link"}, url))
        elif kind == "code":
            out.append(("text", g[1:-1], styles | {"code"}, None))
        else:
            n = {"bold": 2, "under": 2, "strike": 2, "spoil": 2, "ital": 1}[kind]
            _inline(g[n:-n], styles | {kind}, out, names, resolve_channel)
        pos = m.end()
    if pos < len(text):
        _plain(text[pos:], styles, out)


def _plain(text, styles, out):
    pos = 0
    for start, end, chars in emojis.find(text):
        if start > pos:
            out.append(("text", text[pos:start], styles, None))
        out.append(("emoji", chars, styles, core.twemoji_url(chars)))
        pos = end
    if pos < len(text):
        out.append(("text", text[pos:], styles, None))


def _timestamp(tag):
    m = re.match(r"<t:(-?\d+)(?::(\w))?>", tag)
    try:
        dt = datetime.fromtimestamp(int(m.group(1)))
    except (ValueError, OSError, OverflowError):
        return tag
    style = m.group(2) or "f"
    if style == "R":
        secs = (dt - datetime.now()).total_seconds()
        a = abs(secs)
        for unit, n in (("day", 86400), ("hour", 3600), ("minute", 60)):
            if a >= n:
                v = int(a // n)
                txt = f"{v} {unit}{'s' if v > 1 else ''}"
                return f"in {txt}" if secs > 0 else f"{txt} ago"
        return "just now"
    return dt.strftime({"t": "%H:%M", "T": "%H:%M:%S", "d": "%Y-%m-%d", "D": "%B %d, %Y",
                        "F": "%A, %B %d, %Y %H:%M"}.get(style, "%B %d, %Y %H:%M"))


class _Slot:
    """Where a picture goes inside the text (ImageLoader calls set_image on it)."""

    def __init__(self, owner, mark, fallback):
        self.owner, self.mark, self.fallback = owner, mark, fallback
        self.name = None
        self.frames = None

    def winfo_exists(self):
        try:
            return self.owner.winfo_exists()
        except tk.TclError:
            return False

    def set_image(self, photo):
        try:
            self.owner.configure(state="normal")
            if self.name is None:
                self.name = self.owner.image_create(self.mark, image=photo, padx=1)
            else:
                self.owner.image_configure(self.name, image=photo)
            self.owner.configure(state="disabled")
            self.owner.photos.append(photo)
            self.owner.fit()
        except tk.TclError:
            pass

    def set_frames(self, photos, durations):
        self.set_image(photos[0])
        if len(photos) > 1:
            self.frames = (photos, durations)
            self._play(0)

    def _play(self, i):
        try:
            if not self.owner.winfo_exists() or self.name is None:
                return
            photos, durations = self.frames
            self.owner.image_configure(self.name, image=photos[i])
            self.owner.after(durations[i], lambda: self._play((i + 1) % len(photos)))
        except tk.TclError:
            pass

    def failed(self):
        try:
            self.owner.configure(state="normal")
            self.owner.insert(self.mark, self.fallback, ("emojitext",))
            self.owner.configure(state="disabled")
            self.owner.fit()
        except tk.TclError:
            pass


class MessageText(tk.Frame):
    """Read-only rich text that grows to fit its content. .text is the tk.Text."""

    def __init__(self, master, segments, images, bg, fg=TEXT, size=10, jumbo=False,
                 on_click=None):
        super().__init__(master, bg=bg, height=20)
        self.pack_propagate(False)
        self.segs = segments
        self.t = t = tk.Text(self, bg=bg, fg=fg, font=(FONT, size), wrap="word", bd=0,
                             highlightthickness=0, padx=0, pady=1, width=1, height=1,
                             cursor="xterm", insertwidth=0, spacing1=1, spacing3=1,
                             selectbackground="#4752c4", inactiveselectbackground="#4752c4",
                             exportselection=True, takefocus=0)
        t.pack(fill="both", expand=True)
        t.photos = []
        t.fit = self.fit
        self.size = size
        t.tag_configure("bold", font=(FONT, size, "bold"))
        t.tag_configure("ital", font=(FONT, size, "italic"))
        t.tag_configure("under", underline=True)
        t.tag_configure("strike", overstrike=True)
        t.tag_configure("code", font=("Consolas", size - 1), background=CODE_BG)
        t.tag_configure("mention", background=MENTION_BG, foreground=MENTION_FG)
        t.tag_configure("link", foreground=LINK, underline=False)
        t.tag_configure("h1", font=(FONT, size + 8, "bold"), foreground=WHITE)
        t.tag_configure("h2", font=(FONT, size + 5, "bold"), foreground=WHITE)
        t.tag_configure("h3", font=(FONT, size + 2, "bold"), foreground=WHITE)
        t.tag_configure("sub", font=(FONT, size - 2), foreground=MUTED)
        t.tag_configure("spoil", background=SPOILER_BG, foreground=SPOILER_BG)
        t.tag_configure("boldital", font=(FONT, size, "bold italic"))
        t.tag_configure("emojitext", font=("Segoe UI Emoji", size + (14 if jumbo else 2)))
        t.tag_bind("spoil", "<Button-1>",
                   lambda e: t.tag_configure("spoil", background=CODE_BG, foreground=TEXT))
        t.tag_bind("link", "<Enter>", lambda e: t.configure(cursor="hand2"))
        t.tag_bind("link", "<Leave>", lambda e: t.configure(cursor="xterm"))
        n_links = 0
        esize = JUMBO if jumbo else INLINE
        for kind, value, styles, extra in segments:
            tags = tuple(sorted(styles))
            if "bold" in styles and "ital" in styles:
                tags += ("boldital",)
            if kind == "emoji":
                mark = f"e{len(t.photos)}_{t.index('end-1c')}"
                t.mark_set(mark, "end-1c")
                t.mark_gravity(mark, "left")
                slot = _Slot(t, mark, value)
                if extra:
                    images.load(extra, (esize, esize), slot,
                                mode="anim" if extra.split("?")[0].endswith(".gif")
                                else "thumb")
                else:
                    slot.failed()
            else:
                if extra and "link" in styles:
                    n_links += 1
                    lt = f"link{n_links}"
                    t.tag_bind(lt, "<Button-1>", lambda e, u=extra: webbrowser.open(u))
                    tags = tags + (lt,)
                t.insert("end", value, tags)
        t.configure(state="disabled")
        if on_click:
            t.bind("<Button-1>", lambda e: on_click(), add="+")
        t.bind("<Configure>", lambda e: self.fit(), add="+")
        t.bind("<Control-c>", lambda e: self._copy())
        self.fit()

    def _copy(self):
        try:
            txt = self.t.get("sel.first", "sel.last")
            self.clipboard_clear()
            self.clipboard_append(txt)
        except tk.TclError:
            pass
        return "break"

    def fit(self):
        """Resize the frame to the real height of the text (it changes with the width
        and when emoji pictures arrive)."""
        try:
            self.t.tk.call(self.t._w, "sync")
            n = self.t.count("1.0", "end", "ypixels")
            if isinstance(n, (tuple, list)):
                n = n[0]
            if n:
                h = int(n) + 2
                if h != getattr(self, "_h", None):
                    self._h = h
                    self.configure(height=h)
        except (tk.TclError, TypeError, ValueError):
            pass

    def configure(self, cnf=None, **kw):     # background changes reach the text too
        if "bg" in kw:
            try:
                self.t.configure(bg=kw["bg"])
            except (tk.TclError, AttributeError):
                pass
        return super().configure(cnf, **kw)

    config = configure
