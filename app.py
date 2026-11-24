"""Discord Message Cleaner - Discord-style window.

Connect with your token, browse your DMs and servers like in Discord, preview the
conversation (messages that will be deleted are highlighted in red), tick what to
clean and run. Deletes YOUR OWN messages only.

Free and open source (MIT). Not affiliated with or endorsed by Discord Inc.
"""
import json
import os
import sys
import threading
import threading as bg_threading     # long-lived background connections
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

import applog
import cleaner_core as core
import demo
import i18n
import logger_service
import msglog
import package
import rules
import securestore
import emojis
import media
import richtext
import social
import widgets
from richtext import MessageText
from widgets import (BLURPLE, BLURPLE_HI, BORDER, CHAT, CHECK_INHERIT, CODE_BG, CODE_BORDER,
                     DIVIDER, ERROR_FG, FIELD_BG, FONT, GOOD_FG, GREEN, HOVER, ICON_MUTED, INPUT,
                     KEEP_BG, LINK, LOG_BG, MATCH_BG, MENTION_BAR, MENTION_BG, MSG_HOVER, MUTED,
                     PKG_COLOR, PLACEHOLDER, QUOTE_BAR, RAIL, REACT_ME_BG, RED, RED_HI, SELECTED,
                     SIDEBAR, TEXT, TIP_BG, USERBAR, WHITE, Avatar, Check, EmojiLabel, FlatButton,
                     ImageLoader,
                     LinkLabel, OptionCheck, ScrollFrame, Thumb, Tooltip, bind_tree, color_for,
                     entry_box, is_inside, set_bg)

i18n.install()            # must run before any widget is created
core.LANG = i18n.LANG

APP_NAME = "Discord Message Cleaner"
VERSION = "7.5.0"
PREVIEW_PAGE = 50
LOCAL = ("pkg", "deleted")      # previews that come from a local list, not from Discord
EDIT_BAR = "#f0b232"
LIVE_EVENTS = {"MESSAGE_CREATE", "MESSAGE_UPDATE", "MESSAGE_DELETE", "MESSAGE_REACTION_ADD",
               "MESSAGE_REACTION_REMOVE", "TYPING_START"} | social.SOCIAL_EVENTS

PACKAGE_HELP = (
    "Your Discord data package lists EVERY chat you've ever sent a message in, including "
    "closed DMs and servers you left, together with the IDs of your messages.\n\n"
    "HOW TO GET IT\n"
    "1. Discord > User Settings > Data & Privacy.\n"
    "2. Scroll down to 'Request all of my Data', tick Messages, and request it.\n"
    "3. Discord emails you a download link (this can take a few days).\n"
    "4. Download the .zip and import it here (no need to unzip).\n\n"
    "Messages in servers you left can't be deleted (Discord doesn't allow it). "
    "The app skips those chats automatically.")

DISCLAIMER = (
    "Before you use this app:\n\n"
    "• It only deletes YOUR OWN messages. Deleted messages cannot be recovered.\n"
    "• Using scripts on a user account goes against Discord's Terms of Service. "
    "Your account could be limited or banned. You use this app at your own risk.\n"
    "• Your token stays on this PC. It is only sent to discord.com and is never saved.\n"
    "• Never give your token to anyone.\n\n"
    "Do you understand and want to continue?"
)

HELP_TEXT = (
    "1. Open discord.com/app in Chrome or Edge and log in.\n"
    "2. Press F12 and open the Network tab.\n"
    "3. Type 'api' in the filter box, then click on any chat.\n"
    "4. Click a request (e.g. 'messages') > Headers > Request Headers.\n"
    "5. Copy the value next to 'authorization' and paste it here.\n\n"
    "It's about 70 characters with two dots. Never share it with anyone.\n"
    "Changing your Discord password resets it."
)


def resource(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def settings_path():
    root = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    return os.path.join(root, "DiscordMessageCleaner", "settings.json")


def app_data_file(name):
    root = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    return os.path.join(root, "DiscordMessageCleaner", name)


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError:
        pass


def cache_dir():
    root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or \
        os.path.expanduser("~/.cache")
    return os.path.join(root, "DiscordMessageCleaner", "cache")


def set_window_icon(win):
    """Sharp icon in the title bar AND the taskbar: the .ico has every size drawn
    natively, and iconphoto gives Windows the big ones for the taskbar/Alt-Tab."""
    try:
        win.iconbitmap(default=resource("icon.ico"))
    except Exception:
        pass
    try:
        win._icon_photos = [tk.PhotoImage(file=resource(f"icon_{s}.png"))
                            for s in (256, 64, 32, 16)]
        win.iconphoto(True, *win._icon_photos)
    except Exception:
        pass


def windows_setup(settings):
    """Run once before the window opens: taskbar identity (so Windows shows OUR icon,
    not Python's) and optional sharp mode on scaled screens (125%, 150%...)."""
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "08Raph.DiscordMessageCleaner")
    except Exception:
        pass
    if settings.get("sharp_mode"):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def dark_title_bar(win):
    """Windows 10/11: dark title bar coloured like Discord's."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        dwm = ctypes.windll.dwmapi
        on = ctypes.c_int(1)
        for attr in (20, 19):   # DWMWA_USE_IMMERSIVE_DARK_MODE (new / old builds)
            if dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(on), 4) == 0:
                break
        color = ctypes.c_int(0x00221F1E)   # #1e1f22 as 0x00BBGGRR (Windows 11 only)
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), 4)
    except Exception:
        pass


def flash_window(win):
    """Flash the taskbar button until the window is focused."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        class FLASHWINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("hwnd", wintypes.HWND),
                        ("dwFlags", wintypes.DWORD), ("uCount", wintypes.UINT),
                        ("dwTimeout", wintypes.DWORD)]
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, 0x3 | 0xC, 0, 0)
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
    except Exception:
        pass


def default_backup_dir():
    return os.path.join(os.path.expanduser("~"), "Documents", "Discord Cleaner Backups")


def section_label(master, text, bg=SIDEBAR):
    return tk.Label(master, text=text.upper(), bg=bg, fg=MUTED, font=(FONT, 8, "bold"))


class DemoBound:
    """Demo data with the same stop/pause behaviour as the real API."""

    def __init__(self, data, should_stop, paused, sleep):
        self.data, self.should_stop, self.paused, self.sleep = data, should_stop, paused, sleep

    def request(self, method, path, body=None, files=None):
        while self.paused() and not self.should_stop():
            self.sleep(0.3)
        if self.should_stop():
            return None, None
        return self.data.request(method, path, body, files)


class App(social.SocialMixin, social.MoreSocialMixin, social.CustomizeMixin, tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("1420x880")
        self.minsize(1200, 740)
        self.configure(bg=RAIL)
        set_window_icon(self)

        self.images = ImageLoader(self, cache_dir())
        self.settings = self.load_settings()
        self.apply_ui_scale()
        core.CLOCK_24 = bool(self.settings.get("clock_24h"))
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.running = False
        self.token_value = None
        self.remember_choice = None
        self.package = None           # imported data package (list of chats)
        self.pkg_by_id = {}
        self.pacer = None
        self.job = None
        self.job_checked = False
        self.keep_ids = set(read_json(app_data_file("keep.json"), []))
        self._running_rule = None
        self._close_after = None
        self._close_after_all = []
        self._save_first_now = False
        self._rule_timer = None
        self._last_stats = None
        self._error_shown = False
        self.demo = None              # DemoApi when "Try the demo" is used
        self._tour = None
        self.logger_state = "off"
        self.logger_store = None
        self.tray = None
        self.live_stop = None
        self.really_quit = False
        self._seen_total = None
        self._seen_event = None
        self._backup_running = False
        self._poll_n = 0
        self._toolbar = None
        self._picker = None
        self._chat_spacer = None
        self._deleted_sig = None
        self._logger_poll = False
        self.reset_data()

        self.setup_style()
        dark_title_bar(self)
        self.bind_all("<MouseWheel>", self.on_wheel)
        self.bind_all("<ButtonPress-2>", self.on_mid_press)
        self.bind_all("<B2-Motion>", lambda e: self._auto_sf and self._auto_sf.move_autoscroll(
            e.y_root))
        self.bind_all("<ButtonRelease-2>", self.on_mid_release)
        for seq, fn in (("<Prior>", lambda: self.messages.page(-1)),
                        ("<Next>", lambda: self.messages.page(1)),
                        ("<Control-Home>", lambda: self.messages.to_top()),
                        ("<Control-End>", lambda: self.messages.to_bottom())):
            self.bind_all(seq, lambda e, fn=fn: self.chat_key(fn))
        self.bind_all("<Control-f>", lambda e: self.open_find())
        self.bind_all("<Control-F>", lambda e: self.open_find())
        self.bind_all("<Control-k>", lambda e: self.open_switcher())
        self.bind_all("<Control-K>", lambda e: self.open_switcher())
        self._auto_sf = None
        self.switcher = None
        self.login_frame = None
        self.main_frame = None
        self.show_login()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(200, self.first_run_check)
        if securestore.has_accounts():
            self.after(300, self.auto_login)

    def reset_data(self):
        self.me = None
        self.dms, self.guilds = [], []
        self.guild_by_id = {}
        self.guild_channels = {}      # gid -> list | "loading" | "error"
        self.channel_guild = {}       # cid -> gid
        self.checked = {}             # key -> target dict (insertion ordered)
        self.check_widgets = {}       # key -> [Check]
        self.row_frames = {}          # key -> sidebar row frame
        self.rail_items = {}          # "dms" | gid -> (holder, pill, avatar)
        self.view = "dms"
        self.thread_info = {}         # thread id -> (name, parent channel name)
        self.open_key = None
        self.preview = None
        self.msg_rows = []
        self.text_labels = []
        self.row_by_id = {}
        self.preview_req = 0
        self.unread = {}              # channel id -> number of new messages
        self.channel_names = {}       # channel id -> name (for #channel mentions)

    # ================================================================ style
    def setup_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Horizontal.TProgressbar", background=BLURPLE, troughcolor=INPUT,
                    bordercolor=INPUT, lightcolor=BLURPLE, darkcolor=BLURPLE, thickness=6)

    def scrollframe_at(self, x, y):
        try:
            w = self.winfo_containing(x, y)
        except (tk.TclError, KeyError):
            return None
        while w is not None:
            if isinstance(w, ScrollFrame):
                return w
            w = getattr(w, "master", None)
        return None

    def on_wheel(self, e):
        sf = self.scrollframe_at(e.x_root, e.y_root)
        if sf is not None:
            sf.wheel(e.delta)

    def on_mid_press(self, e):
        """Hold the mouse wheel and move the mouse to scroll (like in a browser)."""
        sf = self.scrollframe_at(e.x_root, e.y_root)
        if sf is not None:
            self._auto_sf = sf
            sf.start_autoscroll(e.y_root)

    def on_mid_release(self, _):
        if self._auto_sf is not None:
            self._auto_sf.stop_autoscroll()
            self._auto_sf = None

    def chat_key(self, fn):
        if self.main_frame is None or not hasattr(self, "messages"):
            return
        if isinstance(self.focus_get(), (tk.Entry, tk.Text, tk.Spinbox)):
            return
        fn()

    # ================================================================ login screen
    def show_login(self, error=None):
        if self.main_frame is not None:
            self.main_frame.destroy()
            self.main_frame = None
        if self.login_frame is not None:
            self.login_frame.destroy()
        f = self.login_frame = tk.Frame(self, bg=RAIL)
        f.pack(fill="both", expand=True)

        card = tk.Frame(f, bg=CHAT, padx=34, pady=30)
        card.place(relx=0.5, rely=0.5, anchor="center")
        try:
            self.logo = tk.PhotoImage(file=resource("icon.png"))
            tk.Label(card, image=self.logo, bg=CHAT).pack(pady=(0, 10))
        except tk.TclError:
            pass
        tk.Label(card, text=APP_NAME, bg=CHAT, fg=WHITE,
                 font=(FONT, 18, "bold")).pack()
        tk.Label(card, text="Delete your own messages from DMs and servers.", bg=CHAT,
                 fg=MUTED, font=(FONT, 10)).pack(pady=(2, 20))

        accounts = securestore.list_accounts()
        if accounts:
            section_label(card, "Saved accounts", CHAT).pack(anchor="w")
            acc_box = tk.Frame(card, bg=CHAT)
            acc_box.pack(fill="x", pady=(6, 16))
            for acc in accounts[:6]:
                self.account_row(acc_box, acc)
            section_label(card, "Or add another account", CHAT).pack(anchor="w")
        lab = tk.Frame(card, bg=CHAT)
        lab.pack(fill="x")
        section_label(lab, "Your token", CHAT).pack(side="left")
        tk.Label(lab, text="*", bg=CHAT, fg=RED, font=(FONT, 8, "bold")).pack(side="left")
        box, self.token = entry_box(card, "Paste your token here", show="•", width=46,
                                    font_size=11)
        box.pack(fill="x", pady=(6, 4))
        self.token.bind("<Return>", lambda e: self.connect())

        row = tk.Frame(card, bg=CHAT)
        row.pack(fill="x")
        self.show_token = tk.BooleanVar(value=False)
        OptionCheck(row, "Show token", self.show_token, CHAT,
                    command=lambda: self.token.set_show("" if self.show_token.get() else "•")
                    ).pack(side="left")
        LinkLabel(row, "Where do I find my token?",
                  lambda: messagebox.showinfo("Find your token", HELP_TEXT), CHAT).pack(
            side="right")

        self.remember = tk.BooleanVar(value=securestore.has_accounts())
        if securestore.available():
            OptionCheck(card, "Remember me on this PC (saved encrypted with your Windows "
                              "account)", self.remember, CHAT).pack(anchor="w", pady=(8, 0))

        self.login_error = tk.Label(card, text=error or "", bg=CHAT, fg=ERROR_FG,
                                    font=(FONT, 9), wraplength=420, justify="left")
        self.login_error.pack(fill="x", pady=(8, 0))

        self.connect_btn = FlatButton(card, "Connect", self.connect, font_size=11, pady=10)
        self.connect_btn.pack(fill="x", pady=(10, 6))
        FlatButton(card, "Try the demo (no account)", self.start_demo, bg=SELECTED,
                   hover=HOVER, font_size=9, pady=6).pack(fill="x", pady=(0, 14))
        tk.Label(card, text="Your token stays on this PC and is only sent to discord.com.\n"
                            "This app is not made by or affiliated with Discord.",
                 bg=CHAT, fg=MUTED, font=(FONT, 8), justify="center").pack()
        self.token.focus_set()

    def start_demo(self):
        """Pretend account with sample chats: try the app or record a video safely."""
        self.demo = demo.DemoApi()
        self.token_value = "demo"
        self.remember_choice = None
        api = self.make_api()
        me, _ = core.get_me(api)
        self.on_connected(me, core.list_dms(api), core.list_guilds(api))

    def account_row(self, parent, acc):
        row = tk.Frame(parent, bg=SIDEBAR, cursor="hand2")
        row.pack(fill="x", pady=2)
        av = Avatar(row, 32, SIDEBAR, core.initials(acc["name"])[:1], color_for(acc["id"]))
        av.pack(side="left", padx=10, pady=6)
        if acc.get("avatar"):
            self.images.load(acc["avatar"], 32, av)
        lbl = tk.Label(row, notr=True, text=acc["name"], bg=SIDEBAR, fg=WHITE, font=(FONT, 10, "bold"),
                       anchor="w")
        lbl.pack(side="left", fill="x", expand=True)
        x = tk.Label(row, text="✕", bg=SIDEBAR, fg=MUTED, font=(FONT, 9), cursor="hand2")
        x.pack(side="right", padx=10)
        Tooltip(x, lambda: "Remove this saved account from this PC")

        def remove(_):
            if messagebox.askyesno(APP_NAME, f"Remove {acc['name']} from this PC?"):
                securestore.remove_account(acc["id"])
                self.show_login()
            return "break"
        x.bind("<Button-1>", remove)
        for w in (row, av, lbl):
            w.bind("<Button-1>", lambda e: self.login_account(acc["id"]))
        bind_tree(row, "<Enter>", lambda e: set_bg(row, HOVER))
        bind_tree(row, "<Leave>", lambda e: set_bg(row, SIDEBAR))

    def login_account(self, account_id):
        token = securestore.get_account_token(account_id)
        if not token:
            self.login_error.configure(text="That saved account couldn't be read. "
                                            "Paste your token again.", fg=ERROR_FG)
            return
        self.token.set(token)
        self.remember.set(True)
        self.login_error.configure(text="Signing in…", fg=MUTED)
        self.connect()

    def auto_login(self):
        if self.login_frame is None or not self.settings.get("accepted_terms"):
            return
        if not self.settings.get("auto_login", True):
            return
        accounts = securestore.list_accounts()
        last = self.settings.get("last_account")
        acc = next((a for a in accounts if a["id"] == last), accounts[0] if accounts else None)
        if acc:
            self.login_account(acc["id"])

    def connect(self):
        if self.running:
            return
        self.remember_choice = self.remember.get()
        self.settings["auto_login"] = True
        token = core.clean_token(self.token.get())
        problem = core.token_problem(token)
        if problem:
            self.login_error.configure(text=problem)
            return
        self.token_value = token
        self.connect_btn.set_enabled(False)
        self.connect_btn.configure(text="Connecting…")
        self.login_error.configure(text="", fg=ERROR_FG)

        def work():
            try:
                me, dms, guilds = self.fetch_account()
                self.after(0, lambda: self.on_connected(me, dms, guilds))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self.on_connect_failed(msg))
        threading.Thread(target=work, daemon=True).start()

    def fetch_account(self):
        """Load your account, DMs and servers at the same time (faster start)."""
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(3) as ex:
            f_me = ex.submit(core.get_me, self.make_api())
            f_dms = ex.submit(core.list_dms, self.make_api())
            f_g = ex.submit(core.list_guilds, self.make_api())
            me, st = f_me.result()
            if not me:
                raise RuntimeError(core.friendly_error(st, "log in"))
            return me, f_dms.result(), f_g.result()

    def on_connect_failed(self, msg):
        self.token_value = None
        if self.login_frame is not None:
            self.connect_btn.set_enabled(True)
            self.connect_btn.configure(text="Connect")
            self.login_error.configure(text=msg, fg=ERROR_FG)

    def on_connected(self, me, dms, guilds):
        keep = dict(self.checked)
        keep_chans = {g: v for g, v in self.guild_channels.items() if isinstance(v, list)}
        keep_map = dict(self.channel_guild)
        self.reset_data()
        self.guild_channels.update(keep_chans)
        self.channel_guild.update(keep_map)
        self.me = me
        self.dms = dms
        self.guilds = guilds
        self.guild_by_id = {g["id"]: g for g in guilds}
        # keep ticks when refreshing
        for k, v in keep.items():
            if k[0] in ("dm", "link", "server", "channel"):
                self.checked[k] = v
        if self.remember_choice is not None:
            try:
                if self.remember_choice:
                    securestore.save_account(me, self.token_value,
                                             core.user_avatar_url(me) if me.get("id") else None)
                    self.settings["last_account"] = me.get("id")
                    self.save_settings()
            except OSError as e:
                self.log(f"Could not save your account: {e}", "bad")
            self.remember_choice = None
        if self.login_frame is not None:
            self.login_frame.destroy()
            self.login_frame = None
        self.build_main()
        self.start_live()
        self.start_tray()
        self.log(f"Connected as {self.my_name()}: {len(dms)} DMs and {len(guilds)} servers.",
                 "good")
        if self.demo is not None:
            self.set_status("Demo mode: nothing is really deleted.")
            self.log("Demo mode: nothing is really deleted.", "dim")
        elif not self.job_checked:
            self.job_checked = True
            self.after(400, self.check_unfinished_job)
        if not self.settings.get("tour_done"):
            self.after(900, self.start_tour)

    def my_name(self):
        return (self.me or {}).get("global_name") or (self.me or {}).get("username", "")

    def make_api(self, stoppable=False):
        if self.demo is not None:
            return DemoBound(self.demo, self.stop_event.is_set if stoppable else (lambda: False),
                             self.pause_event.is_set if stoppable else (lambda: False),
                             self.stop_event.wait if stoppable else time.sleep)
        if stoppable:
            return core.DiscordApi(self.token_value, self.log, self.stop_event.is_set,
                                   self.stop_event.wait, pacer=self.pacer,
                                   paused=self.pause_event.is_set)
        return core.DiscordApi(self.token_value, self.log, lambda: False, time.sleep)

    def logout(self):
        if self.running:
            messagebox.showinfo(APP_NAME, "Stop the cleaner first.")
            return
        me_id = (self.me or {}).get("id")
        saved = any(a["id"] in (me_id, "legacy") for a in securestore.list_accounts())
        if saved:
            ans = messagebox.askyesnocancel(
                APP_NAME, "Remove this account from this PC too?\n\nYes = log out and forget "
                          "it\nNo = log out but keep it saved (to switch accounts)")
            if ans is None:
                return
            if ans:
                securestore.remove_account(me_id)
                securestore.remove_account("legacy")
        self.stop_live()
        self.settings["auto_login"] = False
        self.save_settings()
        self.token_value = None
        self.demo = None
        self.save_settings()
        self.package = None
        self.pkg_by_id = {}
        self.job_checked = False
        self.reset_data()
        self.show_login()

    def switch_account(self):
        if self.running:
            messagebox.showinfo(APP_NAME, "Stop the cleaner first.")
            return
        self.stop_live()
        self.settings["auto_login"] = False
        self.save_settings()
        self.token_value = None
        self.demo = None
        self.package = None
        self.pkg_by_id = {}
        self.job_checked = False
        self.reset_data()
        self.show_login()

    def refresh(self):
        if self.running:
            return
        self.log("Refreshing your chats…", "dim")

        def work():
            try:
                me, dms, guilds = self.fetch_account()
                self.after(0, lambda: self.on_connected(me, dms, guilds))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self.log(msg, "bad"))
        threading.Thread(target=work, daemon=True).start()

    # ================================================================ main layout
    def build_main(self):
        if self.main_frame is not None:
            self.main_frame.destroy()
        m = self.main_frame = tk.Frame(self, bg=RAIL)
        m.pack(fill="both", expand=True)

        # server rail | sidebar | chat | cleaner
        self.rail = ScrollFrame(m, RAIL, scrollbar=False, width=72)
        self.rail.pack(side="left", fill="y")
        self.rail.canvas.configure(width=72)

        self.cleaner = tk.Frame(m, bg=SIDEBAR, width=370)
        self.cleaner.pack(side="right", fill="y")
        self.cleaner.pack_propagate(False)

        self.sidebar = tk.Frame(m, bg=SIDEBAR, width=250)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.chat = tk.Frame(m, bg=CHAT)
        self.chat.pack(side="left", fill="both", expand=True)

        self.build_rail()
        self.build_sidebar_shell()
        self.build_chat()
        self.build_cleaner()
        self._cleaner_packed = True
        if not self.clean_mode():
            self.cleaner.pack_forget()
            self._cleaner_packed = False
        if not self._logger_poll:
            self._logger_poll = True
            self.after(1500, self.poll_logger)
        if not self._rule_timer and self.demo is None:
            self._rule_timer = rules.RuleTimer(self, self.run_rule_now)
            self._rule_timer.start()
        self.open_view("dms")
        self.on_selection_changed()
        self.open_friends("online")
        self.bind_social_keys()
        self.after(300, self.reopen_last_chat)

    # ---------------------------------------------------------------- rail
    def build_rail(self):
        inner = self.rail.inner
        self.rail_item(inner, "dms", "Direct Messages", None, "@", BLURPLE, home=True)
        if self.clean_mode():
            self.rail_item(inner, "pkg", "Data package (every chat you ever used)", None, "▤",
                           PKG_COLOR)
        if self.settings.get("show_deleted_view", True) is not False:
            self.rail_item(inner, "deleted", "Deleted messages (people's deleted DMs)", None, "⊘",
                       RED)
        tk.Frame(inner, bg=DIVIDER, height=2, width=32).pack(pady=6)
        for g in self.guilds:
            self.rail_item(inner, g["id"], g["name"], g.get("icon"), core.initials(g["name"]),
                           CHAT)
        add = tk.Frame(inner, bg=RAIL)
        add.pack(pady=(4, 10))
        refresh = Avatar(add, 48, RAIL, "↻", CHAT, font_size=16)
        refresh.pack(padx=12)
        refresh.configure(cursor="hand2")
        refresh.bind("<Button-1>", lambda e: self.refresh())
        Tooltip(refresh, lambda: "Refresh DMs and servers")

    def rail_item(self, parent, key, name, icon_url, text, color, home=False):
        holder = tk.Frame(parent, bg=RAIL)
        holder.pack(pady=4, fill="x")
        pill = tk.Frame(holder, bg=WHITE, width=4)
        av = Avatar(holder, 48, RAIL, text, color)
        av.pack(padx=12)
        av.configure(cursor="hand2")
        if home:
            try:
                img = tk.PhotoImage(file=resource("icon_48.png"))
                av.set_image(img)
            except tk.TclError:
                pass
        elif icon_url:
            self.images.load(icon_url, 48, av)
        if icon_url:
            self.images.load(icon_url, 48, av, mode="rounded")
        hover_color = color if home or key in ("pkg", "deleted") else BLURPLE

        def enter(_):
            av.set_shape("rounded", hover_color if not icon_url else None)
            if self.view != key:
                pill.place(x=0, rely=0.5, anchor="w", height=20)

        def leave(_):
            if self.view != key:
                av.set_shape("circle")
                pill.place_forget()
        av.bind("<Button-1>", lambda e: self.open_view(key))
        if not home and key not in ("pkg", "deleted"):
            av.bind("<Button-3>", lambda e: self.mute_menu(e, key, name))
        av.bind("<Enter>", enter, add="+")
        av.bind("<Leave>", leave, add="+")
        Tooltip(av, lambda: name, notr=not home and key not in ("pkg", "deleted"))
        self.rail_items[key] = (holder, pill, av)

    def update_rail(self):
        for key, (holder, pill, av) in self.rail_items.items():
            if key == self.view:
                pill.place(x=0, rely=0.5, anchor="w", height=40)
                av.set_shape("rounded", None if key not in ("dms", "pkg", "deleted") and
                             self.guild_by_id.get(key, {}).get("icon") else
                             {"pkg": PKG_COLOR, "deleted": RED}.get(key, BLURPLE))
            else:
                pill.place_forget()
                av.set_shape("circle")
            if key == "dms":
                has = any(k[0] in ("dm", "link") for k in self.checked)
            elif key == "pkg":
                has = any(k[0] == "pkg" for k in self.checked)
            elif key == "deleted":
                has = self.logger_state.startswith("running")
            else:
                has = ("server", key) in self.checked or any(
                    k[0] == "channel" and self.channel_guild.get(k[1]) == key
                    for k in self.checked)
                mark = self.server_mark(key)
                if mark:
                    av.set_badge(True, mark)
                    continue
            av.set_badge(has)

    # ---------------------------------------------------------------- sidebar
    def build_sidebar_shell(self):
        self.view_frames = {}
        # user panel at the bottom, like Discord
        up = tk.Frame(self.sidebar, bg=USERBAR, height=54)
        up.pack(side="bottom", fill="x")
        up.pack_propagate(False)
        me = self.me or {}
        av = Avatar(up, 32, USERBAR, core.initials(self.my_name())[:1], color_for(me.get("id")))
        av.pack(side="left", padx=(8, 8))
        if me.get("id"):
            self.images.load(core.user_avatar_url(me), 32, av)
        av.set_badge(True)
        self.me_avatar = av
        txt = tk.Frame(up, bg=USERBAR, cursor="hand2")
        txt.pack(side="left", fill="x", expand=True)
        self.me_name_label = tk.Label(txt, notr=True, text=self.my_name(), bg=USERBAR, fg=WHITE,
                                      font=(FONT, 10, "bold"), anchor="w", cursor="hand2")
        self.me_name_label.pack(fill="x", pady=(8, 0))
        self.user_status = tk.Label(txt, notr=True, text=self.user_status_text(), bg=USERBAR,
                                    fg=MUTED, font=(FONT, 8), anchor="w", cursor="hand2")
        self.user_status.pack(fill="x")
        for w in (av, txt, self.me_name_label, self.user_status):
            w.bind("<Button-1>", self.open_status_menu)
        Tooltip(txt, lambda: "Set your status")
        self.update_user_panel()
        gear = tk.Label(up, text="⚙", bg=USERBAR, fg=MUTED, font=(FONT, 13), cursor="hand2")
        gear.pack(side="right", padx=(0, 10))
        gear.bind("<Button-1>", lambda e: self.open_settings())
        Tooltip(gear, lambda: "Settings, accounts, help")
        self.side_body = tk.Frame(self.sidebar, bg=SIDEBAR)
        self.side_body.pack(side="top", fill="both", expand=True)

    def user_status_text(self):
        n = int(self.settings.get("total_deleted", 0) or 0)
        return f"Connected  •  {n:,} cleaned" if n else "Connected"

    def open_view(self, view, rebuild=False):
        """Show a sidebar view. Views are built once and kept (switching is instant)."""
        self.view = view
        self.clear_server_unread(view)
        for v, f in self.view_frames.items():
            if v != view:
                f.pack_forget()
        if rebuild and view in self.view_frames:
            self.view_frames.pop(view).destroy()
            self.row_frames = {k: r for k, r in self.row_frames.items() if r.winfo_exists()}
            self.prune_checks()
        if view not in self.view_frames:
            self.vp = tk.Frame(self.side_body, bg=SIDEBAR)
            self.view_frames[view] = self.vp
            if view == "dms":
                self.build_dm_sidebar()
            elif view == "pkg":
                self.build_package_sidebar()
            elif view == "deleted":
                self.build_deleted_sidebar()
            else:
                self.build_server_sidebar(view)
        self.view_frames[view].pack(fill="both", expand=True)
        self.update_rail()
        self.update_checks()
        self.mark_open_row()

    def invalidate_view(self, view):
        """Rebuild a view next time (or now if it's showing)."""
        if view == self.view and self.main_frame is not None:
            self.open_view(view, rebuild=True)
        elif view in self.view_frames:
            self.view_frames.pop(view).destroy()
            self.row_frames = {k: r for k, r in self.row_frames.items() if r.winfo_exists()}
            self.prune_checks()

    def sidebar_header(self, text=None):
        head = tk.Frame(self.vp, bg=SIDEBAR, height=48)
        head.pack(fill="x")
        head.pack_propagate(False)
        tk.Frame(self.vp, bg=BORDER, height=1).pack(fill="x")
        if text:
            tk.Label(head, text=text, bg=SIDEBAR, fg=WHITE, font=(FONT, 11, "bold"),
                     anchor="w").pack(fill="both", expand=True, padx=16)
        return head

    def sidebar_row(self, parent, key, name, open_cmd, avatar=None, prefix=None,
                    indent=8, extra=None, before=None, checkable=True, on_expand=None):
        """One clickable row with avatar/#, name and a checkbox (like a Discord DM)."""
        row = tk.Frame(parent, bg=SIDEBAR, cursor="hand2")
        if before is not None:
            row.pack(fill="x", padx=(indent, 8), pady=1, before=before)
        else:
            row.pack(fill="x", padx=(indent, 8), pady=1)
        if avatar is not None:
            url, text, color, size = avatar
            av = Avatar(row, size, SIDEBAR, text, color)
            av.pack(side="left", padx=(8, 10), pady=5)
            if url:
                self.images.load(url, size, av)
        if prefix:
            tk.Label(row, text=prefix, bg=SIDEBAR, fg=MUTED, font=(FONT, 13)).pack(
                side="left", padx=(8, 4), pady=3)
        row.avatar = av if avatar is not None else None
        chk = Check(row, SIDEBAR, command=lambda: self.toggle(key))
        if checkable and self.clean_mode():
            chk.pack(side="right", padx=(4, 8))
        if on_expand is not None:
            ex = tk.Label(row, text="⋯", bg=SIDEBAR, fg=MUTED, font=(FONT, 11, "bold"),
                          cursor="hand2")
            ex.pack(side="right", padx=(2, 2 if checkable else 10))
            ex.bind("<Button-1>", lambda e: (on_expand(), "break")[1])
            Tooltip(ex, lambda: "Show threads / posts")
            row.expander = ex
        if extra:
            tk.Label(row, text=extra, bg=SIDEBAR, fg=MUTED, font=(FONT, 8)).pack(side="right")
        lbl = tk.Label(row, notr=True, text=name, bg=SIDEBAR, fg=MUTED, font=(FONT, 10), anchor="w")
        lbl.pack(side="left", fill="x", expand=True)
        if checkable:
            self.check_widgets.setdefault(key, []).append(chk)
        self.row_frames[key] = row
        if key[0] in ("dm", "channel", "link"):
            for w in [row] + list(row.winfo_children()):
                w.bind("<Button-3>", lambda e, k=key, n=name: self.mute_menu(e, k[1], n), add="+")

        def enter(_):
            if self.open_key != key:
                set_bg(row, HOVER)
            lbl.configure(fg=TEXT)

        def leave(_):
            w = self.winfo_containing(*self.winfo_pointerxy())
            if w is not None and is_inside(w, row):
                return
            set_bg(row, SELECTED if self.open_key == key else SIDEBAR)
            lbl.configure(fg=WHITE if self.open_key == key else MUTED)

        bind_tree(row, "<Enter>", enter)
        bind_tree(row, "<Leave>", leave)
        for w in [row] + [c for c in row.winfo_children()
                          if c is not chk and c is not getattr(row, "expander", None)]:
            w.bind("<Button-1>", lambda e: open_cmd(), add="+")
        row.name_label = lbl
        row.badge = None
        if key[0] in ("dm", "channel") and self.unread.get(key[1]):
            self.set_row_badge(row, self.unread[key[1]])
        return row

    def build_dm_sidebar(self):
        head = self.sidebar_header()
        box, self.dm_search = entry_box(head, "Find a conversation", bg=INPUT, font_size=9)
        box.pack(fill="x", padx=10, pady=10)
        self.dm_search.bind("<KeyRelease>", lambda e: self.filter_dms())

        self.friends_row(self.vp)
        top = tk.Frame(self.vp, bg=SIDEBAR)
        top.pack(fill="x", padx=16, pady=(14, 4))
        section_label(top, f"Direct messages  ({len(self.dms)})").pack(side="left")
        if self.clean_mode():
            LinkLabel(top, "Select all", self.select_all_dms, SIDEBAR, font_size=8).pack(side="right")

        self.dm_list = ScrollFrame(self.vp, SIDEBAR)
        self.dm_list.pack(fill="both", expand=True)
        self.dm_rows = []
        if not self.dms:
            tk.Label(self.dm_list.inner, text="No open DMs.\nUse 'Add by link' on the right\n"
                                              "for closed DMs.", bg=SIDEBAR, fg=MUTED,
                     font=(FONT, 9), justify="center").pack(pady=30)
        links = [(k, v) for k, v in self.checked.items() if k[0] == "link"]
        dm_list = self.dm_list

        def add_rows(start=0, chunk=30):
            """Build rows in small chunks so the window never freezes with many DMs."""
            if not dm_list.winfo_exists():
                return
            for d in self.dms[start:start + chunk]:
                key = ("dm", d["id"])
                row = self.sidebar_row(
                    dm_list.inner, key, d["name"],
                    lambda d=d: self.open_chat(("dm", d["id"]), d["id"], d["name"], "@",
                                               d.get("avatar"), d.get("user_id")),
                    avatar=(d.get("avatar"), core.initials(d["name"])[:1],
                            color_for(d.get("user_id")), 32),
                    before=self.dm_links_sec)
                self.dm_rows.append((d, row))
                if self.dm_search.get().strip() and \
                        self.dm_search.get().strip().lower() not in d["name"].lower():
                    row.pack_forget()
            self.update_checks()
            self.mark_open_row()
            self.update_presence_dots()
            if start + chunk < len(self.dms):
                self.after(1, lambda: add_rows(start + chunk, chunk))

        self.dm_links_sec = None
        if links:
            sec = self.dm_links_sec = tk.Frame(self.dm_list.inner, bg=SIDEBAR)
            sec.pack(fill="x", padx=16, pady=(14, 4))
            section_label(sec, "Added by link").pack(side="left")
            for k, v in links:
                self.sidebar_row(self.dm_list.inner, k, v["name"] or f"Chat {k[1]}",
                                 lambda k=k, v=v: self.open_chat(k, k[1], v["name"] or "Chat",
                                                                 "@", None, k[1]),
                                 prefix="↗")
        add_rows()

    def filter_dms(self):
        q = self.dm_search.get().strip().lower()
        for d, row in self.dm_rows:
            row.pack_forget()
        for d, row in self.dm_rows:
            if not q or q in d["name"].lower():
                if self.dm_links_sec is not None:
                    row.pack(fill="x", padx=(8, 8), pady=1, before=self.dm_links_sec)
                else:
                    row.pack(fill="x", padx=(8, 8), pady=1)
        self.dm_list.to_top()

    def select_all_dms(self):
        if self.running:
            return
        q = self.dm_search.get().strip().lower() if hasattr(self, "dm_search") else ""
        keys = [("dm", d["id"]) for d in self.dms if not q or q in d["name"].lower()]
        if keys and all(k in self.checked for k in keys):
            for k in keys:
                self.checked.pop(k, None)
        else:
            for k in keys:
                self.checked[k] = self.make_target(k)
        self.on_selection_changed()

    # ---------------------------------------------------------------- deleted messages logger
    def store(self):
        if self.logger_store is None:
            self.logger_store = msglog.Store()
            try:
                self.logger_store.prune_deleted(int(self.settings.get("deleted_keep_days", 0) or 0))
            except Exception:
                pass
        return self.logger_store

    def build_deleted_sidebar(self):
        self.sidebar_header("Deleted messages")
        body = tk.Frame(self.vp, bg=SIDEBAR)
        body.pack(fill="x", padx=14, pady=(10, 0))
        st = self.logger_state
        running = st.startswith("running") or st == "starting" or st == "reconnecting"
        card = tk.Frame(body, bg=INPUT, padx=10, pady=8)
        card.pack(fill="x")
        dot = GREEN if st.startswith("running") else (MENTION_BAR if running else (
            RED if st.startswith("error") else MUTED))
        top = tk.Frame(card, bg=INPUT)
        top.pack(fill="x")
        tk.Label(top, text="●", notr=True, bg=INPUT, fg=dot, font=(FONT, 11)).pack(side="left")
        tk.Label(top, text=self.logger_status_text(), bg=INPUT, fg=WHITE, font=(FONT, 9, "bold"),
                 anchor="w", wraplength=170, justify="left").pack(side="left", padx=(6, 0),
                                                                  fill="x")
        FlatButton(card, "Turn off" if running else "Turn on", self.toggle_logger,
                   bg=RED if running else GREEN, hover=RED_HI if running else "#1a7f43",
                   font_size=9, pady=5).pack(fill="x", pady=(8, 0))

        auto = tk.BooleanVar(value=logger_service.autostart_enabled())
        OptionCheck(body, "Start with Windows", auto, SIDEBAR,
                    command=lambda: self.set_logger_autostart(auto)).pack(anchor="w", pady=(8, 0))
        pics = tk.BooleanVar(value=bool(self.settings.get("logger_pictures")))
        OptionCheck(body, "Also save pictures (uses more disk)", pics, SIDEBAR,
                    command=lambda: self.set_setting("logger_pictures", pics.get(), True)
                    ).pack(anchor="w", pady=(4, 0))
        dr = tk.Frame(body, bg=SIDEBAR)
        dr.pack(fill="x", pady=(6, 0))
        tk.Label(dr, text="Remember messages for", bg=SIDEBAR, fg=TEXT, font=(FONT, 9)).pack(
            side="left")
        days = self.spin(dr, 1, 365, 1, 4)
        days.pack(side="left", padx=6)
        self.set_spin(days, self.settings.get("logger_days", 7))
        tk.Label(dr, text="days", bg=SIDEBAR, fg=TEXT, font=(FONT, 9)).pack(side="left")
        days.configure(command=lambda: self.set_setting("logger_days", spin_int(days) or 7, True))
        days.bind("<FocusOut>", lambda e: self.set_setting("logger_days", spin_int(days) or 7,
                                                           True))
        kr = tk.Frame(body, bg=SIDEBAR)
        kr.pack(fill="x", pady=(6, 0))
        tk.Label(kr, text="Keep deleted messages for", bg=SIDEBAR, fg=TEXT, font=(FONT, 9)).pack(
            side="left")
        kdays = self.spin(kr, 0, 3650, 1, 5)
        kdays.pack(side="left", padx=6)
        self.set_spin(kdays, self.settings.get("deleted_keep_days", 0))
        tk.Label(kr, text="days (0 = forever)", bg=SIDEBAR, fg=TEXT, font=(FONT, 9)).pack(
            side="left")

        def keep_changed(_e=None):
            n = spin_int(kdays) or 0
            self.set_setting("deleted_keep_days", n, True)
            if n:
                removed = self.store().prune_deleted(n)
                if removed:
                    self.log(i18n.tr(f"Removed {removed} saved deleted message(s) older than {n} days."))
        kdays.configure(command=keep_changed)
        kdays.bind("<FocusOut>", keep_changed)
        for key, label in (("logger_ghost", "Catch ghost pings in servers"),
                           ("logger_friends", "Tell me when I lose a friend"),
                           ("logger_catchup", "Check what changed while my PC was off")):
            var = tk.BooleanVar(value=self.settings.get(key, True) is not False)
            OptionCheck(body, label, var, SIDEBAR,
                        command=lambda k=key, v=var: self.set_setting(k, v.get(), True)
                        ).pack(anchor="w", pady=(4, 0))
        tk.Label(body, text="Saves messages people delete in your DMs, and pings that get "
                            "deleted in servers. Everything stays on this PC. Your own "
                            "messages are skipped.",
                 bg=SIDEBAR, fg=MUTED, font=(FONT, 8), wraplength=215, justify="left",
                 anchor="w").pack(fill="x", pady=(8, 0))
        links = tk.Frame(body, bg=SIDEBAR)
        links.pack(fill="x", pady=(6, 0))
        me_id = (self.me or {}).get("id")
        n_ev = self.store().event_count(me_id) if me_id else 0
        LinkLabel(links, f"Activity ({n_ev})" if n_ev else "Activity", self.open_activity,
                  SIDEBAR, font_size=8).pack(anchor="w")
        LinkLabel(links, "Saved messages 🔖", self.open_bookmarks, SIDEBAR,
                  font_size=8).pack(anchor="w")
        LinkLabel(links, "Keep it running when this PC is off…", self.other_device_help,
                  SIDEBAR, font_size=8).pack(anchor="w")
        LinkLabel(links, "Import from another device…", self.import_logger_db, SIDEBAR,
                  font_size=8).pack(anchor="w")
        LinkLabel(links, "Auto-import a synced file…", self.pick_import_folder, SIDEBAR,
                  font_size=8).pack(anchor="w")
        LinkLabel(links, "Muted chats…", self.open_ignore_list, SIDEBAR,
                  font_size=8).pack(anchor="w")
        LinkLabel(links, "Export all deleted messages…", self.export_all_deleted, SIDEBAR,
                  font_size=8).pack(anchor="w")
        LinkLabel(links, "Export edit history…", self.export_edit_history, SIDEBAR,
                  font_size=8).pack(anchor="w")
        LinkLabel(links, "📊 Dashboard", self.open_dashboard, SIDEBAR,
                  font_size=8).pack(anchor="w")
        sbox, self.deleted_search = entry_box(body, "Search deleted messages", bg=INPUT,
                                              font_size=9)
        sbox.pack(fill="x", pady=(10, 0))
        self.deleted_search.bind("<Return>", lambda e: self.search_deleted())

        me = (self.me or {}).get("id")
        chats = self.store().chats(me) if me else []
        head = tk.Frame(self.vp, bg=SIDEBAR)
        head.pack(fill="x", padx=16, pady=(14, 4))
        section_label(head, f"Deleted messages  ({sum(c[2] for c in chats)})").pack(side="left")
        if chats:
            LinkLabel(head, "Clear all", self.clear_deleted, SIDEBAR, font_size=8).pack(
                side="right")
        lst = ScrollFrame(self.vp, SIDEBAR)
        lst.pack(fill="both", expand=True)
        if not chats:
            tk.Label(lst.inner, text="Nothing yet.\nDeleted messages will show up here.",
                     bg=SIDEBAR, fg=MUTED, font=(FONT, 9), justify="center").pack(pady=30)
        for cid, name, count, _last in chats:
            self.sidebar_row(lst.inner, ("deleted", cid), name or "DM",
                             lambda cid=cid, name=name: self.open_deleted_chat(cid, name),
                             prefix="#" if (name or "").startswith("#") else None,
                             avatar=(None, core.initials(name or "?")[:1], color_for(cid), 28),
                             checkable=False, extra=f"{count:,}")

    def logger_status_text(self):
        st = self.logger_state
        if st.startswith("running"):
            n = (self.logger_info or {}).get("dms") or 0
            return i18n.tr(f"On: watching {n} DMs") if n else i18n.tr("On")
        if st in ("starting", "reconnecting"):
            return i18n.tr("Starting…")
        if st.startswith("error"):
            return i18n.tr(st.replace("error: ", ""))
        return i18n.tr("Off")

    logger_info = None

    def set_setting(self, key, value, restart_logger=False):
        self.settings[key] = value
        self.save_settings()
        if restart_logger and self.logger_state.startswith("running"):
            self.set_status("The change applies the next time the logger starts.")

    def set_logger_autostart(self, var):
        try:
            logger_service.set_autostart(var.get())
        except OSError as e:
            var.set(False)
            messagebox.showerror(APP_NAME, f"Windows didn't accept it: {e}")

    def toggle_logger(self):
        st = self.logger_state
        if st.startswith("running") or st in ("starting", "reconnecting"):
            logger_service.request_stop(self.store())
            self.logger_state = "off"
            self.log("Deleted-messages logger: stopping.", "dim")
            self.invalidate_view("deleted")
            return
        if self.demo is not None:
            messagebox.showinfo(APP_NAME, "The logger needs a real account (it's not "
                                          "available in the demo).")
            return
        if not securestore.available():
            messagebox.showinfo(APP_NAME, "The logger only works on Windows.")
            return
        me = self.me or {}
        if me.get("id") not in [a["id"] for a in securestore.list_accounts()]:
            if not messagebox.askyesno(
                    APP_NAME, "To run in the background, the logger needs this account saved "
                              "on this PC (encrypted, like 'Remember me').\n\nSave it now?"):
                return
            securestore.save_account(me, self.token_value, core.user_avatar_url(me))
        self.settings["logger_account"] = me.get("id")
        self.save_settings()
        store = self.store()
        store.set_meta("stop", False)
        store.set_meta("status", "starting")
        try:
            logger_service.start_process()
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Could not start the logger: {e}")
            return
        self.logger_state = "starting"
        self.log("Deleted-messages logger: starting in the background.", "good")
        self.invalidate_view("deleted")

    def poll_logger(self):
        """Every few seconds: logger status + new deleted messages (cheap local reads)."""
        if self.main_frame is None:
            self._logger_poll = False
            return
        try:
            st, info = logger_service.status(self.store())
            if info.get("account") not in (None, (self.me or {}).get("id")):
                st = "off"
            me = (self.me or {}).get("id")
            sig = (st, info.get("dms"), self.store().total(me) if me else 0,
                   self.store().event_count(me) if me else 0)
            self.watch_logger_events()
            self._poll_n = getattr(self, "_poll_n", 0) + 1
            if self._poll_n % 12 == 1:
                self.check_import_folder()
            self.logger_info = info
            changed = sig != self._deleted_sig
            self._deleted_sig = sig
            self.logger_state = st
            if changed:
                self.update_rail()
                if "deleted" in self.view_frames:
                    self.invalidate_view("deleted")
        except Exception as e:
            applog.write(f"logger poll: {e}")
        self.after(5000, self.poll_logger)

    def open_deleted_chat(self, cid, name):
        me = (self.me or {}).get("id")
        msgs = self.deleted_rows_to_msgs(self.store().messages(me, cid))
        for m in msgs:
            m["channel_id"] = cid
        self.open_key = ("deleted", cid)
        self.preview = {"key": ("deleted", cid), "channel_id": cid, "title": name or "DM",
                        "icon": "@", "avatar": None, "user_id": cid,
                        "server": i18n.tr("Deleted messages"), "msgs": [], "all": msgs,
                        "more": False, "source": "deleted", "count": len(msgs)}
        self.chat_icon.configure(text="@")
        self.chat_title.configure(text=name or "DM")
        self.set_input_hint("@", name or "DM")
        self.mark_open_row()
        self.update_chat_header_check()
        self.show_pkg_page()

    def forget_deleted(self, mid):
        me = (self.me or {}).get("id")
        self.store().forget(me, message_id=mid)
        p = self.preview
        if p:
            p["all"] = [m for m in p["all"] if m["id"] != mid]
            p["msgs"] = [m for m in p["msgs"] if m["id"] != mid]
            p["count"] = len(p["all"])
            self.update_count_label()
            self.render_preview(scroll="keep")

    def clear_deleted(self):
        if messagebox.askyesno(APP_NAME, "Remove all saved deleted messages from this PC?"):
            self.store().forget((self.me or {}).get("id"))
            if self.preview and self.preview.get("source") == "deleted":
                self.preview = None
                self.open_key = None
                self.chat_empty()
                self.update_chat_header_check()
            self.invalidate_view("deleted")

    # ---------------------------------------------------------------- data package
    def build_package_sidebar(self):
        self.sidebar_header("Data package")
        body = tk.Frame(self.vp, bg=SIDEBAR)
        body.pack(fill="x", padx=14, pady=(10, 0))
        if not self.package:
            tk.Label(body, text="Find EVERY chat you've ever sent a message in, including "
                                "closed DMs, using your Discord data package.",
                     bg=SIDEBAR, fg=TEXT, font=(FONT, 9), wraplength=215, justify="left",
                     anchor="w").pack(fill="x")
            FlatButton(body, "Import package (.zip)", self.import_package_zip, font_size=9,
                       pady=6).pack(fill="x", pady=(12, 6))
            LinkLabel(body, "I already unzipped it (pick folder)", self.import_package_folder,
                      SIDEBAR, font_size=8).pack(anchor="w")
            LinkLabel(body, "How do I get my data package?",
                      lambda: messagebox.showinfo("Data package", PACKAGE_HELP), SIDEBAR,
                      font_size=8).pack(anchor="w", pady=(6, 0))
            self.pkg_status = tk.Label(body, text="", bg=SIDEBAR, fg=MUTED, font=(FONT, 8),
                                       wraplength=215, justify="left", anchor="w")
            self.pkg_status.pack(fill="x", pady=(10, 0))
            return

        total = sum(len(c["messages"]) for c in self.package)
        tk.Label(body, text=f"{len(self.package)} chats  •  {total:,} of your messages",
                 bg=SIDEBAR, fg=TEXT, font=(FONT, 9, "bold"), anchor="w").pack(fill="x")
        links = tk.Frame(body, bg=SIDEBAR)
        links.pack(fill="x", pady=(2, 6))
        LinkLabel(links, "Select all", self.select_all_pkg, SIDEBAR, font_size=8).pack(
            side="left")
        LinkLabel(links, "Import another", self.import_package_zip, SIDEBAR,
                  font_size=8).pack(side="right")
        box, self.pkg_search = entry_box(body, "Search chats", bg=INPUT, font_size=9)
        box.pack(fill="x")
        self.pkg_search.bind("<KeyRelease>", lambda e: self.filter_pkg())

        self.pkg_list = ScrollFrame(self.vp, SIDEBAR)
        self.pkg_list.pack(fill="both", expand=True, pady=(6, 0))
        self.pkg_rows = []
        groups = (("dm", "Direct messages"), ("group", "Group DMs"), ("channel", "Servers"))
        items = []
        for kind, title in groups:
            chats = [c for c in self.package if c["kind"] == kind]
            if chats:
                items.append(("section", f"{title}  ({len(chats)})"))
                items.extend(("chat", c) for c in chats)
        pkg_list = self.pkg_list

        def add_items(start=0, chunk=40):
            if not pkg_list.winfo_exists():
                return
            for what, x in items[start:start + chunk]:
                if what == "section":
                    sec = tk.Frame(pkg_list.inner, bg=SIDEBAR)
                    sec.pack(fill="x", padx=16, pady=(12, 4))
                    section_label(sec, x).pack(side="left")
                    self.pkg_rows.append((None, sec))
                    continue
                c = x
                name = c["name"] + (f"  · {c['guild_name']}" if c["guild_name"] else "")
                row = self.sidebar_row(
                    pkg_list.inner, ("pkg", c["id"]), name,
                    lambda c=c: self.open_pkg_chat(c),
                    avatar=None if c["kind"] == "channel" else
                    (None, package_initial(c["name"]), color_for(c["id"]), 28),
                    prefix="#" if c["kind"] == "channel" else None,
                    extra=f"{len(c['messages']):,}")
                self.pkg_rows.append((c, row))
            self.update_checks()
            self.mark_open_row()
            if start + chunk < len(items):
                self.after(1, lambda: add_items(start + chunk, chunk))
            elif self.pkg_search.get().strip():
                self.filter_pkg()
        add_items()

    def filter_pkg(self):
        q = self.pkg_search.get().strip().lower()
        for c, row in self.pkg_rows:
            row.pack_forget()
        for c, row in self.pkg_rows:
            if c is None:
                if not q:
                    row.pack(fill="x", padx=16, pady=(12, 4))
            elif not q or q in c["name"].lower() or q in (c["guild_name"] or "").lower():
                row.pack(fill="x", padx=(8, 8), pady=1)
        self.pkg_list.to_top()

    def select_all_pkg(self):
        if self.running or not self.package:
            return
        q = self.pkg_search.get().strip().lower() if hasattr(self, "pkg_search") else ""
        keys = [("pkg", c["id"]) for c in self.package
                if not q or q in c["name"].lower() or q in (c["guild_name"] or "").lower()]
        if keys and all(k in self.checked for k in keys):
            for k in keys:
                self.checked.pop(k, None)
        else:
            for k in keys:
                self.checked[k] = self.make_target(k)
        self.on_selection_changed()

    def import_package_zip(self):
        path = filedialog.askopenfilename(title="Pick your Discord data package",
                                          filetypes=[("Zip file", "*.zip"), ("All files", "*.*")])
        if path:
            self.import_package(path)

    def import_package_folder(self):
        path = filedialog.askdirectory(title="Pick the extracted data package folder")
        if path:
            self.import_package(path)

    def import_package(self, path):
        self.set_status("Reading your data package…")
        self.log(f"Reading data package: {path}", "dim")

        def prog(i, total):
            self.after(0, lambda: self.set_status(f"Reading your data package… {i}/{total} chats"))

        def work():
            try:
                chats = package.load_package(path, prog)
                self.after(0, lambda: self.on_package(chats))
            except Exception as e:
                msg = str(e) or "Could not read that file."
                self.after(0, lambda: self.on_package(None, msg))
        threading.Thread(target=work, daemon=True).start()

    def on_package(self, chats, error=None):
        if error:
            self.set_status("Could not read the data package.")
            self.log(error, "bad")
            messagebox.showerror("Data package", error)
            return
        self.package = chats
        self.pkg_by_id = {c["id"]: c for c in chats}
        total = sum(len(c["messages"]) for c in chats)
        self.set_status(f"Data package loaded: {len(chats)} chats, {total:,} messages.")
        self.log(f"Data package loaded: {len(chats)} chats, {total:,} of your messages.", "good")
        if self.main_frame is not None:
            self.invalidate_view("pkg")
            self.open_view("pkg")

    def open_pkg_chat(self, c):
        icon = "#" if c["kind"] == "channel" else "@"
        self.open_key = ("pkg", c["id"])
        msgs = self.pkg_messages(c)
        self.preview = {"key": ("pkg", c["id"]), "channel_id": c["id"], "title": c["name"],
                        "icon": icon, "avatar": None, "user_id": c["id"],
                        "server": c["guild_name"] or "From your data package",
                        "msgs": [], "all": msgs, "more": False, "source": "pkg",
                        "count": len(msgs)}
        self.chat_icon.configure(text=icon)
        self.chat_title.configure(text=c["name"])
        self.set_input_hint(icon, c["name"])
        self.mark_open_row()
        self.update_chat_header_check()
        self.show_pkg_page()

    def pkg_messages(self, c):
        """Data package messages as normal message dicts (oldest first)."""
        msgs = []
        for m in reversed(c["messages"]):
            atts = [{"filename": u.rsplit("/", 1)[-1].split("?")[0], "url": u}
                    for u in (m.get("attachments") or "").split() if u.startswith("http")]
            msgs.append({"id": m["id"], "content": m.get("content", ""),
                         "timestamp": pkg_time(m.get("timestamp")), "author": dict(self.me),
                         "channel_id": c["id"], "type": 0, "attachments": atts})
        return msgs

    def messages_to_save(self, cid, api, should_stop=lambda: False, progress=None):
        """Everyone's messages from Discord; if the chat can't be read any more, fall back to
        your own messages from the data package."""
        msgs = core.fetch_all_messages(api, cid, progress, should_stop)
        if not msgs and cid in self.pkg_by_id:
            self.log("Chat can't be read live: saving your messages from the data package.",
                     "dim")
            msgs = self.pkg_messages(self.pkg_by_id[cid])
        return msgs

    def show_pkg_page(self, older=False):
        p = self.preview
        shown = len(p["msgs"]) + (PREVIEW_PAGE if older or not p["msgs"] else 0)
        p["msgs"] = p["all"][-shown:] if shown < len(p["all"]) else list(p["all"])
        p["more"] = len(p["msgs"]) < len(p["all"])
        self.update_count_label()
        self.render_preview(scroll="top" if older else "bottom")

    def build_server_sidebar(self, gid):
        g = self.guild_by_id.get(gid, {"name": "Server", "id": gid})
        self.sidebar_header(g["name"])

        whole = tk.Frame(self.vp, bg=SIDEBAR, cursor="hand2")
        whole.pack(fill="x", padx=8, pady=(10, 4))
        key = ("server", gid)
        chk = Check(whole, SIDEBAR, command=lambda: self.toggle(key))
        chk.pack(side="left", padx=(8, 10), pady=6)
        txt = tk.Frame(whole, bg=SIDEBAR)
        txt.pack(side="left", fill="x", expand=True)
        tk.Label(txt, text="Clean the whole server", bg=SIDEBAR, fg=WHITE,
                 font=(FONT, 10, "bold"), anchor="w").pack(fill="x")
        tk.Label(txt, text="All your messages in every channel (fastest)", bg=SIDEBAR,
                 fg=MUTED, font=(FONT, 8), anchor="w").pack(fill="x")
        for w in (whole, txt) + tuple(txt.winfo_children()):
            w.bind("<Button-1>", lambda e: self.toggle(key))
        self.check_widgets.setdefault(key, []).append(chk)
        tk.Frame(self.vp, bg=DIVIDER, height=1).pack(fill="x", padx=16, pady=(4, 0))

        self.chan_list = ScrollFrame(self.vp, SIDEBAR)
        self.chan_list.pack(fill="both", expand=True)
        state = self.guild_channels.get(gid)
        if state is None or state == "error":
            self.load_channels(gid)
            state = "loading"
        if state == "loading":
            tk.Label(self.chan_list.inner, text="Loading channels…", bg=SIDEBAR, fg=MUTED,
                     font=(FONT, 9)).pack(pady=30)
            return
        if not state:
            tk.Label(self.chan_list.inner, text="No text channels you can see.", bg=SIDEBAR,
                     fg=MUTED, font=(FONT, 9)).pack(pady=30)
            return
        current_cat = None
        for ch in state:
            if ch["category"] != current_cat:
                current_cat = ch["category"]
                if current_cat:
                    cat = tk.Frame(self.chan_list.inner, bg=SIDEBAR)
                    cat.pack(fill="x", padx=(12, 8), pady=(16, 2))
                    tk.Label(cat, notr=True, text="⌄ " + current_cat.upper(), bg=SIDEBAR, fg=MUTED,
                             font=(FONT, 8, "bold"), anchor="w").pack(fill="x")
            holder = {}
            if ch.get("forum"):
                row = self.sidebar_row(
                    self.chan_list.inner, ("forum", ch["id"]), ch["name"],
                    lambda ch=ch, g=g, h=holder: self.toggle_threads(g, ch, h),
                    prefix="▤", checkable=False,
                    on_expand=lambda ch=ch, g=g, h=holder: self.toggle_threads(g, ch, h))
            else:
                row = self.sidebar_row(
                    self.chan_list.inner, ("channel", ch["id"]), ch["name"],
                    lambda ch=ch, g=g: self.open_chat(("channel", ch["id"]), ch["id"],
                                                      ch["name"], "#", None, None,
                                                      server=g["name"]),
                    prefix="#",
                    on_expand=lambda ch=ch, g=g, h=holder: self.toggle_threads(g, ch, h))
            holder["row"] = row

    # ---------------------------------------------------------------- threads
    def toggle_threads(self, g, ch, holder):
        """Show/hide the threads (or forum posts) under a channel."""
        box = holder.get("box")
        if box is not None and box.winfo_exists():
            if box.winfo_ismapped():
                box.pack_forget()
            else:
                box.pack(fill="x", after=holder["row"])
            return
        box = holder["box"] = tk.Frame(holder["row"].master, bg=SIDEBAR)
        box.pack(fill="x", after=holder["row"])
        tk.Label(box, text="Loading threads…", bg=SIDEBAR, fg=MUTED, font=(FONT, 8),
                 anchor="w").pack(fill="x", padx=34, pady=2)

        def work():
            try:
                th = core.list_threads(self.make_api(), g["id"], ch["id"])
            except Exception:
                th = []
            self.after(0, lambda: self.show_threads(g, ch, box, th))
        threading.Thread(target=work, daemon=True).start()

    def show_threads(self, g, ch, box, threads):
        if not box.winfo_exists():
            return
        for w in box.winfo_children():
            w.destroy()
        if not threads:
            tk.Label(box, text="No threads found.", bg=SIDEBAR, fg=MUTED, font=(FONT, 8),
                     anchor="w").pack(fill="x", padx=34, pady=2)
            return
        for th in threads:
            self.channel_guild[th["id"]] = g["id"]
            self.thread_info[th["id"]] = (th["name"], ch["name"])
            self.sidebar_row(
                box, ("channel", th["id"]),
                th["name"] + (i18n.tr("  (archived)") if th["archived"] else ""),
                lambda th=th: self.open_chat(("channel", th["id"]), th["id"], th["name"], "#",
                                             None, None, server=f"{g['name']} › {ch['name']}"),
                prefix="↳", indent=22)
        self.update_checks()
        self.mark_open_row()

    def load_channels(self, gid):
        self.guild_channels[gid] = "loading"

        def work():
            try:
                api = self.make_api()
                chans = core.list_guild_channels(api, gid)
                richtext.ROLES.update(core.list_guild_roles(api, gid))
                self.after(0, lambda: self.on_channels(gid, chans))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self.on_channels(gid, "error", msg))
        threading.Thread(target=work, daemon=True).start()

    def on_channels(self, gid, chans, error=None):
        self.guild_channels[gid] = chans
        if chans != "error":
            for ch in chans:
                self.channel_guild[ch["id"]] = gid
        else:
            self.log(error, "bad")
        if self.main_frame is not None:
            self.invalidate_view(gid)

    # ---------------------------------------------------------------- selection
    def make_target(self, key):
        kind, i = key
        if kind == "dm":
            d = next((d for d in self.dms if d["id"] == i), {"name": f"Chat {i}"})
            return {"kind": "channel", "id": i, "name": d["name"], "type": "dm",
                    "avatar": d.get("avatar"), "user_id": d.get("user_id"), "is_dm": True}
        if kind == "server":
            g = self.guild_by_id.get(i, {"name": "Server"})
            return {"kind": "server", "id": i, "name": g["name"], "type": "server",
                    "avatar": g.get("icon")}
        if kind == "channel":
            gid = self.channel_guild.get(i)
            g = self.guild_by_id.get(gid, {"name": "Server"})
            chs = self.guild_channels.get(gid) or []
            ch = next((c for c in chs if isinstance(c, dict) and c["id"] == i), None)
            if ch is None:
                tname, parent = self.thread_info.get(i, (i, ""))
                ch = {"name": f"{parent} › {tname}" if parent else tname}
            return {"kind": "channel", "id": i, "name": f"#{ch['name']} ({g['name']})",
                    "type": "channel", "avatar": g.get("icon"), "server": g["name"],
                    "short": ch["name"], "guild_id": gid}
        if kind == "pkg":
            c = self.pkg_by_id.get(i, {"name": f"Chat {i}", "messages": [], "guild_name": ""})
            name = c["name"] + (f" ({c['guild_name']})" if c.get("guild_name") else "")
            return {"kind": "ids", "id": i, "name": name, "type": "pkg",
                    "count": len(c["messages"])}
        return {"kind": "channel", "id": i, "name": None, "type": "link"}

    def toggle(self, key):
        if key[0] in ("deleted", "forum"):
            return
        if self.running:
            self.set_status("You can't change the selection while the cleaner is running.")
            return
        if key[0] == "channel":
            gid = self.channel_guild.get(key[1])
            if ("server", gid) in self.checked:
                self.set_status("The whole server is ticked. Untick it to pick single channels.")
                return
        if key in self.checked:
            del self.checked[key]
        else:
            self.checked[key] = self.make_target(key)
            if key[0] == "server":
                for k in [k for k in self.checked
                          if k[0] == "channel" and self.channel_guild.get(k[1]) == key[1]]:
                    del self.checked[k]
        self.on_selection_changed()

    def check_state(self, key):
        if key in self.checked:
            return "on"
        if key[0] == "channel" and ("server", self.channel_guild.get(key[1])) in self.checked:
            return "inherited"
        return "off"

    def prune_checks(self):
        for key in list(self.check_widgets):
            alive = []
            for w in self.check_widgets[key]:
                try:
                    if w.winfo_exists():
                        alive.append(w)
                except tk.TclError:
                    pass
            self.check_widgets[key] = alive

    def update_checks(self):
        for key, widgets in self.check_widgets.items():
            st = self.check_state(key)
            for w in widgets:
                try:
                    w.set(st)
                except tk.TclError:
                    pass

    def on_selection_changed(self):
        if self.main_frame is None:
            return
        self.prune_checks()
        self.update_checks()
        self.update_rail()
        self.build_chips()
        self.update_chat_header_check()

    def build_chips(self):
        self.chips.clear()
        n = len(self.checked)
        self.sel_title.configure(text=f"SELECTED  ({n})")
        if not n:
            tk.Label(self.chips.inner, text="Nothing yet. Tick DMs, channels or a whole\n"
                                            "server on the left.", bg=INPUT, fg=MUTED,
                     font=(FONT, 9), justify="left").pack(anchor="w", padx=10, pady=10)
            return
        for key, t in list(self.checked.items()):
            row = tk.Frame(self.chips.inner, bg=INPUT)
            row.pack(fill="x", padx=6, pady=2)
            if t["type"] == "server":
                av = Avatar(row, 22, INPUT, core.initials(t["name"])[:2], CHAT)
                if t.get("avatar"):
                    self.images.load(t["avatar"], 22, av)
            elif t["type"] == "dm":
                av = Avatar(row, 22, INPUT, core.initials(t["name"])[:1],
                            color_for(t.get("user_id")))
                if t.get("avatar"):
                    self.images.load(t["avatar"], 22, av)
            elif t["type"] == "pkg":
                av = Avatar(row, 22, INPUT, "▤", PKG_COLOR)
            else:
                av = Avatar(row, 22, INPUT, "#" if t["type"] == "channel" else "↗", CHAT)
            av.pack(side="left", padx=(4, 8), pady=3)
            name = t["name"] or f"Chat {t['id']}"
            if t["type"] == "server":
                name += "  · whole server"
            elif t["type"] == "pkg":
                name += f"  · {t['count']:,} msgs"
            lbl = tk.Label(row, notr=True, text=name, bg=INPUT, fg=TEXT, font=(FONT, 9), anchor="w",
                           cursor="hand2")
            lbl.pack(side="left", fill="x", expand=True)
            lbl.bind("<Button-1>", lambda e, k=key: self.reveal(k))
            x = tk.Label(row, text="✕", bg=INPUT, fg=MUTED, font=(FONT, 9), cursor="hand2")
            x.pack(side="right", padx=6)
            x.bind("<Button-1>", lambda e, k=key: self.toggle(k))
            x.bind("<Enter>", lambda e, x=x: x.configure(fg=RED))
            x.bind("<Leave>", lambda e, x=x: x.configure(fg=MUTED))

    def reveal(self, key):
        """Jump to a selected item in the sidebar and open it."""
        t = self.checked.get(key)
        if not t:
            return
        if key[0] == "server":
            self.open_view(key[1])
        elif key[0] == "deleted":
            self.open_view("deleted")
        elif key[0] == "pkg":
            self.open_view("pkg")
            if key[1] in self.pkg_by_id:
                self.open_pkg_chat(self.pkg_by_id[key[1]])
        elif key[0] == "channel":
            gid = self.channel_guild.get(key[1])
            if gid:
                self.open_view(gid)
            self.open_chat(key, key[1], t.get("short", t["name"]), "#", None, None,
                           server=t.get("server"))
        else:
            self.open_view("dms")
            self.open_chat(key, key[1], t["name"] or f"Chat {key[1]}", "@", t.get("avatar"),
                           t.get("user_id"))

    def add_by_link(self):
        if self.running:
            return
        ids, bad = core.parse_channel_list(self.link_entry.get())
        if bad or not ids:
            messagebox.showerror("Add by link", "Paste a chat link like "
                                 "https://discord.com/channels/@me/123… or a Channel ID.")
            return
        for cid in ids:
            dm_key = ("dm", cid)
            if any(d["id"] == cid for d in self.dms):
                self.checked[dm_key] = self.make_target(dm_key)
                continue
            if cid in self.channel_guild:
                k = ("channel", cid)
                if ("server", self.channel_guild[cid]) not in self.checked:
                    self.checked[k] = self.make_target(k)
                continue
            key = ("link", cid)
            self.checked[key] = self.make_target(key)
            self.resolve_link_name(cid)
        self.link_entry.set("")
        self.invalidate_view("dms")
        self.on_selection_changed()

    def resolve_link_name(self, cid):
        def work():
            try:
                ch = core.get_channel(self.make_api(), cid)
            except Exception:
                ch = None
            name = core.channel_display_name(ch) if ch else None
            if name:
                self.after(0, lambda: self.on_link_name(cid, name))
        threading.Thread(target=work, daemon=True).start()

    def on_link_name(self, cid, name):
        t = self.checked.get(("link", cid))
        if t:
            t["name"] = name
            self.invalidate_view("dms")
            self.on_selection_changed()

    # ================================================================ quick switcher
    def switcher_items(self):
        items = []
        for d in self.dms:
            items.append((d["name"], "@", i18n.tr("Direct message"),
                          lambda d=d: (self.open_view("dms"), self.open_chat(
                              ("dm", d["id"]), d["id"], d["name"], "@", d.get("avatar"),
                              d.get("user_id")))))
        for g in self.guilds:
            items.append((g["name"], "▣", i18n.tr("Server"), lambda g=g: self.open_view(g["id"])))
            chans = self.guild_channels.get(g["id"])
            if isinstance(chans, list):
                for ch in chans:
                    items.append((ch["name"], "#", g["name"],
                                  lambda ch=ch, g=g: (self.open_view(g["id"]), self.open_chat(
                                      ("channel", ch["id"]), ch["id"], ch["name"], "#", None,
                                      None, server=g["name"]))))
        for c in self.package or []:
            items.append((c["name"].lstrip("#"), "▤", i18n.tr("Data package") + (
                f" · {c['guild_name']}" if c["guild_name"] else ""),
                lambda c=c: (self.open_view("pkg"), self.open_pkg_chat(c))))
        return items

    def open_switcher(self):
        """Ctrl+K: jump to any DM, server, channel or package chat (like Discord)."""
        if self.main_frame is None:
            return
        if self.switcher is not None:
            try:
                self.switcher.destroy()
            except tk.TclError:
                pass
        top = self.switcher = tk.Toplevel(self)
        top.overrideredirect(True)
        top.configure(bg=SIDEBAR, highlightthickness=1, highlightbackground=BORDER)
        w, h = 570, 430
        x = self.winfo_rootx() + max(0, (self.winfo_width() - w) // 2)
        y = self.winfo_rooty() + 110
        top.geometry(f"{w}x{h}+{x}+{y}")
        top.transient(self)
        body = tk.Frame(top, bg=SIDEBAR, padx=22, pady=20)
        body.pack(fill="both", expand=True)
        tk.Label(body, text="Search for servers, channels or DMs", bg=SIDEBAR, fg=WHITE,
                 font=(FONT, 12, "bold"), anchor="w").pack(fill="x", pady=(0, 12))
        box, entry = entry_box(body, "Where would you like to go?", bg=RAIL, font_size=13)
        box.pack(fill="x")
        results = tk.Frame(body, bg=SIDEBAR)
        results.pack(fill="both", expand=True, pady=(12, 0))
        tk.Label(body, text="↑ ↓ to choose   •   Enter to open   •   Esc to close", bg=SIDEBAR,
                 fg=MUTED, font=(FONT, 8)).pack(anchor="w", pady=(8, 0))
        all_items = self.switcher_items()
        state = {"shown": [], "sel": 0}

        def close(_=None):
            try:
                top.destroy()
            except tk.TclError:
                pass
            self.switcher = None

        def activate(i=None):
            i = state["sel"] if i is None else i
            if 0 <= i < len(state["shown"]):
                fn = state["shown"][i][3]
                close()
                fn()

        def render():
            for wdg in results.winfo_children():
                wdg.destroy()
            q = entry.get().strip().lower()
            if q:
                found = [it for it in all_items if q in it[0].lower()]
                found.sort(key=lambda it: (not it[0].lower().startswith(q), len(it[0])))
            else:
                found = all_items
            state["shown"] = found[:9]
            state["sel"] = min(state["sel"], max(0, len(state["shown"]) - 1))
            if not state["shown"]:
                tk.Label(results, text="No matches.", bg=SIDEBAR, fg=MUTED,
                         font=(FONT, 10)).pack(pady=20)
            for i, (name, icon, sub, _fn) in enumerate(state["shown"]):
                bg = SELECTED if i == state["sel"] else SIDEBAR
                row = tk.Frame(results, bg=bg, cursor="hand2")
                row.pack(fill="x", pady=1)
                tk.Label(row, text=icon, bg=bg, fg=MUTED, font=(FONT, 12), width=2).pack(
                    side="left", padx=(8, 6), pady=5)
                tk.Label(row, notr=True, text=name, bg=bg, fg=WHITE, font=(FONT, 10, "bold"),
                         anchor="w").pack(side="left")
                tk.Label(row, notr=True, text=sub, bg=bg, fg=MUTED, font=(FONT, 8)).pack(
                    side="right", padx=10)
                for wdg in (row,) + tuple(row.winfo_children()):
                    wdg.bind("<Button-1>", lambda e, i=i: activate(i))

        def move(d):
            if state["shown"]:
                state["sel"] = (state["sel"] + d) % len(state["shown"])
                render()

        def typed(e):
            if e.keysym not in ("Up", "Down", "Return", "Escape"):
                state["sel"] = 0
                render()

        entry.bind("<KeyRelease>", typed)
        entry.bind("<Up>", lambda e: move(-1))
        entry.bind("<Down>", lambda e: move(1))
        entry.bind("<Return>", lambda e: activate())
        entry.bind("<Escape>", close)
        top.bind("<Escape>", close)
        entry.bind("<FocusOut>", lambda e: self.after(150, lambda: (
            self.switcher is top and self.focus_get() is None and close())))
        render()
        entry.focus_force()

    # ================================================================ chat preview
    def build_chat(self):
        head = tk.Frame(self.chat, bg=CHAT, height=48)
        head.pack(fill="x")
        head.pack_propagate(False)
        tk.Frame(self.chat, bg=BORDER, height=1).pack(fill="x")
        self.chat_icon = tk.Label(head, text="", bg=CHAT, fg=MUTED, font=(FONT, 16))
        self.chat_icon.pack(side="left", padx=(16, 6))
        self.chat_title = tk.Label(head, notr=True, text="Preview", bg=CHAT, fg=WHITE,
                                   font=(FONT, 11, "bold"))
        self.chat_title.pack(side="left")
        self.chat_sub = tk.Label(head, notr=True, text="", bg=CHAT, fg=MUTED, font=(FONT, 9))
        self.chat_sub.pack(side="left", padx=(12, 0))
        self.marks_btn = tk.Label(head, text="🔖", bg=CHAT, fg=MUTED, font=("Segoe UI Emoji", 12),
                                  cursor="hand2")
        self.clean_btn = tk.Label(head, text="🧹", bg=CHAT, fg=RED if self.clean_mode() else MUTED,
                                  font=("Segoe UI Emoji", 13), cursor="hand2")
        self.clean_btn.pack(side="right", padx=(0, 14))
        self.clean_btn.bind("<Button-1>", lambda e: self.toggle_clean_mode())
        Tooltip(self.clean_btn, lambda: "Show or hide the cleaning tools")
        self.marks_btn.pack(side="right", padx=(0, 12))
        self.pins_btn = tk.Label(head, text="📌", bg=CHAT, fg=MUTED, font=("Segoe UI Emoji", 12),
                                 cursor="hand2")
        self.pins_btn.bind("<Button-1>", lambda e: self.open_pins())
        Tooltip(self.pins_btn, lambda: "Pinned messages")
        self.call_btn = tk.Label(head, text="📞", bg=CHAT, fg=MUTED, font=("Segoe UI Emoji", 12),
                                 cursor="hand2")
        self.call_btn.bind("<Button-1>", lambda e: self.call_open_chat())
        Tooltip(self.call_btn, lambda: "Start a call (opens Discord)")
        self.members_btn = tk.Label(head, text="👥", bg=CHAT, fg=MUTED, font=("Segoe UI Emoji", 12),
                                    cursor="hand2")
        self.members_btn.bind("<Button-1>", lambda e: self.open_members())
        Tooltip(self.members_btn, lambda: "Members")
        self.marks_btn.bind("<Button-1>", lambda e: self.open_bookmarks())
        Tooltip(self.marks_btn, lambda: "Saved messages")
        self.export_btn = FlatButton(head, "Chat ▾", self.export_chat, bg=SELECTED,
                                     hover=HOVER, font_size=9, padx=10, pady=3)
        self.count_label = tk.Label(head, text="", bg=CHAT, fg=TEXT, font=(FONT, 9, "bold"))

        self.head_check_frame = tk.Frame(head, bg=CHAT, cursor="hand2")
        self.head_check = Check(self.head_check_frame, CHAT, command=self.toggle_open_chat)
        self.head_check.pack(side="left")
        self.head_check_label = tk.Label(self.head_check_frame, text="Clean this chat",
                                         bg=CHAT, fg=TEXT, font=(FONT, 10, "bold"),
                                         cursor="hand2")
        self.head_check_label.pack(side="left", padx=(8, 0))
        self.head_check_label.bind("<Button-1>", lambda e: self.toggle_open_chat())

        bar = tk.Frame(self.chat, bg=CHAT)
        bar.pack(side="bottom", fill="x", padx=16, pady=(0, 20))
        self.typing_lbl = tk.Label(bar, notr=True, text="", bg=CHAT, fg=TEXT, font=(FONT, 8),
                                   anchor="w")
        self.typing_lbl.pack(side="bottom", fill="x")
        self.reply_bar = tk.Frame(bar, bg=SIDEBAR, padx=14, pady=6)
        self.reply_lbl = tk.Label(self.reply_bar, notr=True, text="", bg=SIDEBAR, fg=MUTED,
                                  font=(FONT, 9), anchor="w")
        self.reply_lbl.pack(side="left", fill="x", expand=True)
        rx = tk.Label(self.reply_bar, text="✕", notr=True, bg=SIDEBAR, fg=MUTED,
                      cursor="hand2", font=(FONT, 10))
        rx.pack(side="right")
        rx.bind("<Button-1>", lambda e: self.cancel_reply())
        self.files_bar = tk.Frame(bar, bg=SIDEBAR, padx=10, pady=6)
        box = tk.Frame(bar, bg=FIELD_BG)
        box.pack(fill="x")
        self.input_box = box
        plus = Avatar(box, 24, FIELD_BG, "+", ICON_MUTED, font_size=13)
        plus.pack(side="left", padx=(14, 12), pady=10, anchor="n")
        plus.configure(cursor="hand2")
        plus.bind("<Button-1>", lambda e: self.attach_files())
        Tooltip(plus, lambda: "Upload a file")
        self.plus_btn = plus
        emo = EmojiLabel(box, FIELD_BG, "☺", font_size=14)
        emo.configure(fg=ICON_MUTED, cursor="hand2", padx=8)
        emo.pack(side="right", padx=(0, 8), pady=8, anchor="n")
        self.images.load(core.twemoji_url("😀"), (22, 22), emo, mode="thumb")
        emo.bind("<Button-1>", lambda e: self.can_chat() and self.open_emoji_picker(
            self.insert_emoji, emo))
        self.emoji_btn = emo
        self.input_hint = tk.Label(box, notr=True, text=i18n.tr("Pick a chat to preview it"),
                                   bg=FIELD_BG, fg=PLACEHOLDER, font=(FONT, 10), anchor="w")
        self.input_hint.pack(side="left", fill="x", expand=True, pady=12)
        self.composer = tk.Text(box, bg=FIELD_BG, fg=TEXT, insertbackground=TEXT,
                                font=(FONT, 10), wrap="word", bd=0, highlightthickness=0,
                                height=1, width=1, padx=0, pady=12, undo=True)
        self.composer.bind("<Return>", self.on_composer_enter)
        self.composer.bind("<KP_Enter>", self.on_composer_enter)
        self.composer.bind("<KeyRelease>", self.on_composer_key)
        self.composer.bind("<Escape>", lambda e: self.cancel_reply())
        self.composer.bind("<Up>", self.on_composer_up)
        self.composer.bind("<Control-v>", self.on_composer_paste)
        self.composer_files = []
        self.reply_to = None
        self.editing = None
        self._typing_sent = 0
        self._typing_users = {}
        self.setup_composer_extras(box, emo)
        self.hint_shortcut = tk.Label(box, text="Ctrl+K  find a chat", bg=FIELD_BG,
                                      fg=PLACEHOLDER, font=(FONT, 8))
        self.hint_shortcut.pack(side="right", padx=14)

        self.find_bar = tk.Frame(self.chat, bg=SIDEBAR, padx=10, pady=6)
        fbox, self.find_entry = entry_box(self.find_bar, "Find in this chat", font_size=9,
                                          width=28)
        fbox.pack(side="left")
        self.find_entry.bind("<KeyRelease>", self.on_find_key)
        self.find_entry.bind("<Escape>", lambda e: self.close_find())
        self.find_count = tk.Label(self.find_bar, text="", notr=True, bg=SIDEBAR, fg=MUTED,
                                   font=(FONT, 9))
        self.find_count.pack(side="left", padx=8)
        for txt, d in (("▲", -1), ("▼", 1)):
            bt = tk.Label(self.find_bar, text=txt, notr=True, bg=SIDEBAR, fg=TEXT,
                          font=(FONT, 10), cursor="hand2", padx=4)
            bt.pack(side="left")
            bt.bind("<Button-1>", lambda e, d=d: self.find_step(d))
        FlatButton(self.find_bar, "Search the whole chat", self.find_everywhere, bg=SELECTED,
                   hover=HOVER, font_size=8, padx=8, pady=3).pack(side="left", padx=(10, 0))
        x = tk.Label(self.find_bar, text="✕", notr=True, bg=SIDEBAR, fg=MUTED, font=(FONT, 10),
                     cursor="hand2")
        x.pack(side="right")
        x.bind("<Button-1>", lambda e: self.close_find())
        self.find_hits, self.find_pos = [], -1
        self.find_anchor = tk.Frame(self.chat, bg=CHAT, height=0)
        self.find_anchor.pack(fill="x")

        self.messages = ScrollFrame(self.chat, CHAT)
        self.messages.pack(fill="both", expand=True)
        self.messages.canvas.bind("<Configure>", self.on_chat_resize, add="+")
        self.chat_empty()

    def chat_empty(self, text=None):
        self.messages.clear()
        self.msg_rows, self.text_labels, self.row_by_id = [], [], {}
        box = tk.Frame(self.messages.inner, bg=CHAT)
        box.pack(expand=True, pady=150)
        tk.Label(box, text="◉", bg=CHAT, fg=DIVIDER,
                 font=(FONT, 46)).pack()
        tk.Label(box, text=text or "Click a DM or channel on the left to preview it here.",
                 bg=CHAT, fg=MUTED, font=(FONT, 11)).pack(pady=(8, 2))
        if self.clean_mode():
            tk.Label(box, text="Your messages that match the filters are highlighted in red.",
                     bg=CHAT, fg=MUTED, font=(FONT, 9)).pack()

    def toggle_open_chat(self):
        if self.open_key:
            self.toggle(self.open_key)

    def set_input_hint(self, icon, title):
        self.update_composer(icon, title)

    # ================================================================ chatting
    def update_composer(self, icon=None, title=None):
        """Real message box for live chats, a hint for previews (data package, deleted)."""
        p = self.preview or {}
        icon = icon if icon is not None else p.get("icon", "")
        title = title if title is not None else p.get("title", "")
        chat = self.can_chat()
        self.cancel_reply(quiet=True)
        try:
            if chat:
                self.input_hint.pack_forget()
                self.hint_shortcut.pack_forget()
                self.composer.pack(side="left", fill="x", expand=True)
                self.input_hint.configure(text=i18n.tr("Message ") + (
                    icon if icon == "@" else "#" if icon == "#" else "") + title.lstrip("#"))
                self.plus_btn.configure(cursor="hand2")
                self.composer.configure(state="normal")
                self.show_placeholder()
            else:
                self.composer.pack_forget()
                self.input_hint.place_forget()
                self.input_hint.pack(side="left", fill="x", expand=True, pady=12)
                self.hint_shortcut.pack(side="right", padx=14)
                why = ("   ·   " + i18n.tr("preview only")) if p.get("source") in LOCAL else (
                    "   ·   " + i18n.tr("chatting is turned off in Settings")
                    if p and self.settings.get("chat_enabled", True) is False else "")
                self.input_hint.configure(
                    text=(i18n.tr("Message ") + (icon if icon == "@" else "") + title + why)
                    if p else i18n.tr("Pick a chat to preview it"))
        except tk.TclError:
            pass

    def show_placeholder(self):
        try:
            if self.composer.winfo_ismapped() or self.can_chat():
                if not self.composer.get("1.0", "end-1c"):
                    self.input_hint.place(in_=self.composer, x=0, rely=0.5, anchor="w")
                    self.input_hint.bind("<Button-1>", lambda e: self.composer.focus_set())
                else:
                    self.input_hint.place_forget()
        except tk.TclError:
            pass

    def on_composer_key(self, e=None):
        self.show_placeholder()
        try:
            lines = int(self.composer.index("end-1c").split(".")[0])
        except (tk.TclError, ValueError):
            lines = 1
        try:
            dl = self.composer.count("1.0", "end", "displaylines")
            lines = max(lines, dl[0] if isinstance(dl, (tuple, list)) else int(dl or 1))
        except (tk.TclError, TypeError, ValueError):
            pass
        self.composer.configure(height=min(10, max(1, lines)))
        if e is None or e.keysym not in ("Up", "Down", "Return", "Tab", "Escape"):
            self.mention_check()
        text = self.composer.get("1.0", "end-1c")
        if text and e is not None and e.keysym not in ("Return", "Escape", "Up", "Down") \
                and time.time() - self._typing_sent > 8 and self.demo is None:
            self._typing_sent = time.time()
            cid = self.preview["channel_id"]
            threading.Thread(target=lambda: core.typing(self.make_api(), cid),
                             daemon=True).start()

    def on_composer_enter(self, e):
        if self.mention_visible():
            self.mention_pick()
            return "break"
        if e.state & 0x0001:            # Shift+Enter = new line
            return None
        self.send_composer()
        return "break"

    def on_composer_up(self, e):
        """Up arrow in an empty box edits your last message (like Discord)."""
        if self.mention_visible():
            self.mention_move(-1)
            return "break"
        if self.composer.get("1.0", "end-1c"):
            return None
        mine = [r["msg"] for r in self.msg_rows
                if self.me and (r["msg"].get("author") or {}).get("id") == self.me["id"]
                and not r["msg"].get("_deleted")]
        if mine:
            self.start_edit(mine[-1])
            return "break"
        return None

    def on_composer_paste(self, e):
        """Ctrl+V a picture (screenshot) -> attach it, like in Discord."""
        try:
            from PIL import ImageGrab
            img = ImageGrab.grabclipboard()
        except Exception:
            img = None
        if img is not None and hasattr(img, "save"):
            import io
            buf = io.BytesIO()
            img.save(buf, "PNG")
            self.add_file("image.png", buf.getvalue())
            return "break"
        return None

    def insert_emoji(self, em):
        if em.get("id"):
            text = f"<{'a' if em.get('animated') else ''}:{em['name']}:{em['id']}>"
        else:
            text = em["name"]
            recent = [x for x in self.settings.get("recent_emojis", []) if x != text]
            self.settings["recent_emojis"] = ([text] + recent)[:16]
        self.composer.insert("insert", text)
        self.composer.focus_set()
        self.on_composer_key()

    def attach_files(self):
        if not self.can_chat():
            return
        paths = filedialog.askopenfilenames(title="Upload files")
        for path in paths or []:
            try:
                if os.path.getsize(path) > 10 * 1024 * 1024:
                    messagebox.showwarning(APP_NAME, f"{os.path.basename(path)} is bigger than "
                                                     "10 MB (Discord's limit without Nitro).")
                    continue
                with open(path, "rb") as f:
                    self.add_file(os.path.basename(path), f.read())
            except OSError as ex:
                messagebox.showerror(APP_NAME, str(ex))

    def add_file(self, name, data):
        self.composer_files.append((name, data))
        self.render_files_bar()

    def render_files_bar(self):
        for w in self.files_bar.winfo_children():
            w.destroy()
        if not self.composer_files:
            self.files_bar.pack_forget()
            return
        for i, (name, data) in enumerate(self.composer_files):
            chip = tk.Frame(self.files_bar, bg=CODE_BG, padx=8, pady=4)
            chip.pack(side="left", padx=(0, 6))
            tk.Label(chip, notr=True, text=f"📎 {name}  ({core.human_size(len(data))})",
                     bg=CODE_BG, fg=TEXT, font=(FONT, 9)).pack(side="left")
            x = tk.Label(chip, text="✕", bg=CODE_BG, fg=MUTED, cursor="hand2")
            x.pack(side="left", padx=(6, 0))
            x.bind("<Button-1>", lambda e, i=i: (self.composer_files.pop(i),
                                                  self.render_files_bar()))
        self.files_bar.pack(fill="x", before=self.input_box)

    def start_reply(self, m):
        if not self.can_chat():
            return
        self.editing = None
        self.reply_to = m
        name = (m.get("author") or {}).get("global_name") or (m.get("author") or {}).get(
            "username", "?")
        self.reply_lbl.configure(text=i18n.tr("Replying to ") + name)
        self.reply_bar.pack(fill="x", before=self.input_box)
        self.composer.focus_set()

    def start_edit(self, m):
        if not self.can_chat():
            return
        self.reply_to = None
        self.editing = m
        self.reply_lbl.configure(text=i18n.tr("Editing message  ·  Enter to save, Esc to cancel"))
        self.reply_bar.pack(fill="x", before=self.input_box)
        self.composer.delete("1.0", "end")
        self.composer.insert("1.0", m.get("content") or "")
        self.composer.focus_set()
        self.on_composer_key()

    def cancel_reply(self, quiet=False):
        was_edit = self.editing is not None
        self.reply_to = None
        self.editing = None
        try:
            self.reply_bar.pack_forget()
            if was_edit and not quiet:
                self.composer.delete("1.0", "end")
                self.on_composer_key()
        except (tk.TclError, AttributeError):
            pass

    def send_composer(self):
        if not self.can_chat():
            return
        text = self.mention_convert(self.composer.get("1.0", "end-1c").strip())
        files = list(self.composer_files)
        p = self.preview
        cid = p["channel_id"]
        if self.editing is not None:
            m = self.editing
            if not text:
                self.cancel_reply()
                return
            self.cancel_reply(quiet=True)
            self.composer.delete("1.0", "end")
            self.on_composer_key()

            old_text = m.get("content") or ""

            def work_edit():
                st, data = core.edit_message(self.make_api(), cid, m["id"], text)
                if st in (200, 201) and old_text != text:
                    self.after(0, lambda: self.remember_edit(dict(m, content=old_text),
                                                             {"content": text}, target=m))
                self.after(0, lambda: self.on_sent(cid, st, data, edited=True))
            threading.Thread(target=work_edit, daemon=True).start()
            return
        if not text and not files:
            return
        if len(text) > 2000:
            messagebox.showwarning(APP_NAME, f"Discord messages can be 2000 characters max "
                                             f"(this one has {len(text)}).")
            return
        reply = (self.reply_to or {}).get("id")
        self.composer.delete("1.0", "end")
        self.composer_files = []
        self.render_files_bar()
        self.cancel_reply(quiet=True)
        self.on_composer_key()
        self._typing_sent = 0

        def work():
            st, data = core.send_message(self.make_api(), cid, text, reply, files or None)
            self.after(0, lambda: self.on_sent(cid, st, data, failed_text=text))
        threading.Thread(target=work, daemon=True).start()

    def on_sent(self, cid, st, data, edited=False, failed_text=None):
        if st not in (200, 201):
            msg = core.friendly_error(st, "send this message") if st else "No connection."
            if isinstance(data, dict) and data.get("message"):
                msg += f"\n\nDiscord says: {data['message']}"
            messagebox.showerror(APP_NAME, msg)
            if failed_text and not self.composer.get("1.0", "end-1c"):
                self.composer.insert("1.0", failed_text)     # don't lose what you wrote
                self.on_composer_key()
            return
        if isinstance(data, dict) and data.get("id"):
            self.live_message(data, edited=edited, mine=True)

    # ================================================================ live updates
    def start_live(self):
        """One real-time connection while the app is open: new messages appear by
        themselves, reactions/edits/deletions update, unread DMs get a badge."""
        self.stop_live()
        if self.demo is not None or not self.token_value or \
                self.settings.get("live_updates", True) is False:
            return
        import gateway
        stop = threading.Event()
        self.live_stop = stop
        token = self.token_value

        def on_event(t, d):
            if t in LIVE_EVENTS and not stop.is_set():
                try:
                    self.after(0, lambda: self.on_live_event(t, d))
                except Exception:
                    pass

        def run():
            sess = gateway.GatewaySession(token, on_event, stop.is_set, log=applog.write)
            sess.presence = self.presence_payload()
            self.live_session = sess
            sess.run_forever()
        bg_threading.Thread(target=run, daemon=True).start()

    def stop_live(self):
        ev = getattr(self, "live_stop", None)
        if ev is not None:
            ev.set()
        self.live_stop = None

    def on_live_event(self, t, d):
        if self.main_frame is None:
            return
        if t in social.SOCIAL_EVENTS:
            self.on_social_event(t, d)
            return
        p = self.preview
        open_live = bool(p and p.get("source") == "live" and not p.get("jumped"))
        cid = d.get("channel_id")
        here = open_live and cid == p.get("channel_id")
        if t == "MESSAGE_CREATE":
            mine = self.me and (d.get("author") or {}).get("id") == self.me.get("id")
            self._typing_users.pop((d.get("author") or {}).get("id"), None)
            if here:
                self.live_message(d)
                self.update_typing()
            elif not mine:
                self.mark_unread(d)
        elif t == "MESSAGE_UPDATE" and here and d.get("id") in self.row_by_id:
            m = self.row_by_id[d["id"]]["msg"]
            self.remember_edit(m, d)
            m.update({k: v for k, v in d.items() if k != "reactions"})
            self.render_preview(scroll="keep")
        elif t == "MESSAGE_DELETE" and here and d.get("id") in self.row_by_id:
            m = self.row_by_id[d["id"]]["msg"]
            if self.settings.get("show_deleted", True) is not False and not (
                    self.me and (m.get("author") or {}).get("id") == self.me.get("id")):
                m["_deleted"] = True              # keep it visible, in red
                m["_deleted_at"] = core.format_time(core.datetime.now().astimezone().isoformat())
                self.row_by_id[d["id"]]["matched"] = "unset"
                self.refresh_highlights()
            else:
                p["msgs"] = [x for x in p["msgs"] if x.get("id") != d["id"]]
                self.render_preview(scroll="keep")
        elif t in ("MESSAGE_REACTION_ADD", "MESSAGE_REACTION_REMOVE") and here:
            info = self.row_by_id.get(d.get("message_id"))
            if info:
                me = bool(self.me and d.get("user_id") == self.me.get("id"))
                core.apply_reaction(info["msg"], d.get("emoji") or {},
                                    t == "MESSAGE_REACTION_ADD", me=me)
                self.redraw_reactions(info["msg"])
        elif t == "TYPING_START" and here and d.get("user_id") != (self.me or {}).get("id"):
            member = (d.get("member") or {}).get("user") or {}
            name = member.get("global_name") or member.get("username") or self.dm_user_name(
                cid, d.get("user_id"))
            self._typing_users[d.get("user_id")] = (name, time.time() + 10)
            self.update_typing()
            self.after(10500, self.update_typing)

    def remember_edit(self, old_msg, new, target=None):
        """Keep the text a message had before an edit, so you can still read it."""
        if "content" not in new or new.get("content") == old_msg.get("content"):
            return
        old = old_msg.get("content") or ""
        target = target if target is not None else old_msg
        if (target.get("_edits") or [None])[-1] != old:
            target["_edits"] = (target.get("_edits") or []) + [old]
        try:
            self.store().add_edit((self.me or {}).get("id"), old_msg.get("channel_id")
                                  or new.get("channel_id"), old_msg.get("id"), old)
        except Exception:
            pass

    def dm_user_name(self, cid, uid):
        for dm in self.dms:
            if dm.get("id") == cid:
                for r in dm.get("recipients") or []:
                    if r.get("id") == uid:
                        return r.get("global_name") or r.get("username")
        return "Someone"

    def update_typing(self):
        now = time.time()
        self._typing_users = {k: v for k, v in self._typing_users.items() if v[1] > now}
        names = [v[0] for v in self._typing_users.values()]
        try:
            self.typing_lbl.configure(
                text="" if not names else (", ".join(names[:3]) + i18n.tr(
                    " is typing…" if len(names) == 1 else " are typing…")))
        except tk.TclError:
            pass

    def live_message(self, m, edited=False, mine=False):
        """Add (or update) one message at the bottom of the open chat."""
        p = self.preview
        if not p or p.get("channel_id") != m.get("channel_id"):
            return
        ids = [x.get("id") for x in p["msgs"]]
        if m.get("id") in ids:
            i = ids.index(m["id"])
            self.remember_edit(p["msgs"][i], m)
            p["msgs"][i].update(m)
            self.render_preview(scroll="keep")
            return
        if edited:
            return
        at_bottom = self.messages.canvas.yview()[1] > 0.97 or mine
        prev = p["msgs"][-1] if p["msgs"] else None
        p["msgs"].append(m)
        if p.get("count") is not None and self.me and (m.get("author") or {}).get(
                "id") == self.me.get("id"):
            p["count"] += 1
            self.update_count_label()
        if not self.msg_rows or p.get("only_mine"):
            self.render_preview(scroll="bottom" if at_bottom else "keep")
            return
        width = max(300, self.messages.canvas.winfo_width() - 230)
        spacer = getattr(self, "_chat_spacer", None)
        day = local_day(m)
        new_day = prev is not None and day and day != local_day(prev)
        if new_day:
            self.date_divider(self.messages.inner, day, before=spacer)
        head = (prev is None or new_day or prev["author"]["id"] != m["author"]["id"]
                or core.is_system(prev) or abs(core_ts(m) - core_ts(prev)) > 7 * 60
                or m.get("message_reference"))
        self.render_message(self.messages.inner, m, head, width, before=spacer)
        self.refresh_highlights()
        if at_bottom:
            self.messages.to_bottom()

    def mark_unread(self, m):
        cid = m.get("channel_id")
        if m.get("guild_id") and cid not in self.row_frames:
            self.server_unread(m)
            return
        self.unread[cid] = self.unread.get(cid, 0) + 1
        self.update_title()
        row = self.row_frames.get(("dm", cid)) or self.row_frames.get(("channel", cid))
        if row is not None and self.mute_of(cid, m.get("guild_id")) != "all":
            self.set_row_badge(row, self.unread[cid])
        is_dm = not m.get("guild_id")
        if is_dm:
            n = sum(v for k, v in self.unread.items() if k not in self.channel_guild)
            item = self.rail_items.get("dms")
            if item:
                try:
                    item[2].set_badge(n > 0, RED)
                except (tk.TclError, AttributeError, TypeError):
                    pass
            author = m.get("author") or {}
            name = author.get("global_name") or author.get("username", "?")
            if self.should_notify(m):
                self.notify(name, (m.get("content") or i18n.tr("sent an attachment"))[:120],
                            flash=True)
        else:
            self.server_unread(m)

    def set_row_badge(self, row, n):
        try:
            badge = getattr(row, "badge", None)
            if n <= 0:
                if badge is not None:
                    badge.destroy()
                    row.badge = None
                row.name_label.configure(font=(FONT, 10))
                return
            if badge is None:
                badge = tk.Label(row, text="", bg=RED, fg="white", font=(FONT, 8, "bold"),
                                 padx=5)
                badge.pack(side="right", padx=(2, 4), before=row.name_label)
                row.badge = badge
            badge.configure(text=str(n) if n < 100 else "99+")
            row.name_label.configure(font=(FONT, 10, "bold"), fg=WHITE)
        except tk.TclError:
            pass

    def clear_unread(self, cid):
        if self.unread.pop(cid, None):
            self.update_title()
            row = self.row_frames.get(("dm", cid)) or self.row_frames.get(("channel", cid))
            if row is not None:
                self.set_row_badge(row, 0)
            n = sum(v for k, v in self.unread.items() if k not in self.channel_guild)
            item = self.rail_items.get("dms")
            if item and n == 0:
                try:
                    item[2].set_badge(False)
                except (tk.TclError, AttributeError, TypeError):
                    pass

    # ================================================================ background / tray
    def notify(self, title, text, flash=False):
        """Windows notification when the window is hidden or not in front."""
        if self.settings.get("notifications", True) is False:
            return
        try:
            focused = self.focus_displayof() is not None and self.state() == "normal"
        except tk.TclError:
            focused = False
        if focused:
            return
        if self.tray is not None:
            self.tray.notify(title, text)
        elif flash:
            flash_window(self)

    def start_tray(self):
        if self.tray is not None or self.settings.get("close_to_tray", True) is False:
            return
        try:
            import tray
            self.tray = tray.Tray(self, resource("icon_64.png"))
            self.tray.start()
        except Exception as e:
            applog.write(f"Tray not available: {e}")
            self.tray = None

    def apply_tray_setting(self):
        if self.settings.get("close_to_tray", True) is False:
            if self.tray is not None:
                self.tray.stop()
                self.tray = None
        elif self.main_frame is not None:
            self.start_tray()

    def hide_to_tray(self):
        self.withdraw()
        if not self.settings.get("tray_tip_shown"):
            self.settings["tray_tip_shown"] = True
            self.save_settings()
            self.tray.notify(APP_NAME, i18n.tr("Still running here. Right-click this icon to "
                                               "open or quit. You can change this in Settings."))

    def show_from_tray(self, view=None):
        self.deiconify()
        self.lift()
        try:
            self.focus_force()
        except tk.TclError:
            pass
        if view and self.main_frame is not None:
            self.open_view(view)

    def quit_app(self):
        self.really_quit = True
        self.on_close()

    def watch_logger_events(self):
        """Pop a notification when the logger saves something (window hidden too)."""
        me = (self.me or {}).get("id")
        if not me or self.logger_store is None and self.logger_state == "off":
            return
        try:
            total = self.store().total(me)
            evs = self.store().events(me, 1)
        except Exception:
            return
        last_total = getattr(self, "_seen_total", None)
        last_ev = getattr(self, "_seen_event", None)
        if last_total is not None and total > last_total:
            self.notify(i18n.tr("Deleted message saved"),
                        i18n.tr(f"{total - last_total} new in Deleted messages"))
        if evs and last_ev is not None and evs[0]["id"] != last_ev:
            e = evs[0]
            self.notify(*self.event_text(e))
        self._seen_total = total
        self._seen_event = evs[0]["id"] if evs else 0

    def event_text(self, e):
        name = e.get("name") or "?"
        info = e.get("info") or {}
        if e["kind"] == "friend_removed":
            return (i18n.tr("Friend list"),
                    i18n.tr(f"You're no longer friends with {name}")
                    + (i18n.tr(" (while your PC was off)") if info.get("offline") else ""))
        if e["kind"] == "ghost_ping":
            return (i18n.tr("Ghost ping"),
                    i18n.tr(f"{name} pinged you in {info.get('where', 'a server')} "
                            f"and deleted it"))
        return (e["kind"], name)

    def open_activity(self):
        me = (self.me or {}).get("id")
        top, b = self.dialog("Activity", 600, 600)
        tk.Label(b, text="Activity", bg=CHAT, fg=WHITE, font=(FONT, 14, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(b, text="Things Discord doesn't tell you: ghost pings (someone pinged you, "
                         "then deleted it) and friends you lost. Needs the logger to be on.",
                 bg=CHAT, fg=MUTED, font=(FONT, 9), anchor="w", justify="left",
                 wraplength=540).pack(fill="x", pady=(2, 10))
        sf = ScrollFrame(b, CHAT)
        sf.pack(fill="both", expand=True)

        def render():
            sf.clear()
            evs = self.store().events(me) if me else []
            if not evs:
                tk.Label(sf.inner, text="Nothing yet.", bg=CHAT, fg=MUTED,
                         font=(FONT, 10)).pack(pady=40)
            for e in evs:
                row = tk.Frame(sf.inner, bg=CODE_BG, padx=10, pady=8)
                row.pack(fill="x", pady=3, padx=(0, 10))
                av = Avatar(row, 32, CODE_BG, core.initials(e.get("name") or "?")[:1],
                            color_for(e.get("user_id")))
                av.pack(side="left", anchor="n")
                if e.get("user_id"):
                    self.images.load(core.user_avatar_url(
                        {"id": e["user_id"], "avatar": e.get("avatar")}), 32, av)
                col = tk.Frame(row, bg=CODE_BG)
                col.pack(side="left", fill="x", expand=True, padx=10)
                title, text = self.event_text(e)
                tk.Label(col, notr=True, text=text, bg=CODE_BG, fg=WHITE,
                         font=(FONT, 10, "bold"), anchor="w", wraplength=420,
                         justify="left").pack(fill="x")
                when = core.format_time(core.datetime.fromtimestamp(e["at"]).astimezone()
                                        .isoformat())
                tk.Label(col, notr=True, text=f"{title}  ·  {when}", bg=CODE_BG, fg=MUTED,
                         font=(FONT, 8), anchor="w").pack(fill="x")
                if (e.get("info") or {}).get("content"):
                    MessageText(col, richtext.parse(e["info"]["content"]), self.images,
                                CODE_BG).pack(fill="x", pady=(4, 0))
                x = tk.Label(row, text="✕", bg=CODE_BG, fg=MUTED, cursor="hand2")
                x.pack(side="right", anchor="n")
                x.bind("<Button-1>", lambda ev, i=e["id"]: (
                    self.store().forget_events(me, i), render()))
        render()

    def other_device_help(self):
        top, b = self.dialog("Keep it running when this PC is off", 600, 560)
        tk.Label(b, text="When your PC is off", bg=CHAT, fg=WHITE, font=(FONT, 14, "bold"),
                 anchor="w").pack(fill="x")
        txt = (
            "Discord really erases deleted messages, so something has to be online when a "
            "message arrives to keep a copy. When this PC is off, nothing on it can do that.\n\n"
            "WHAT ALREADY WORKS\n"
            "When your PC turns back on, the logger checks your DMs: messages it had seen "
            "that got deleted or edited while the PC was off are found and saved "
            "(marked 'while your PC was off'). Friends you lost meanwhile are listed in "
            "Activity.\n\n"
            "TO CATCH EVERYTHING, 24/7\n"
            "Run the logger on a device that stays on: an old laptop, a Raspberry Pi, or an "
            "Android phone with Termux. Free, Python only:\n"
            "1. Copy the app's source folder to that device (it's on GitHub).\n"
            "2. Run server/install_linux.sh (Raspberry Pi, Linux) or server/install_termux.sh "
            "(Android). It asks for your token once and starts by itself after a reboot.\n"
            "3. Sync the file it writes to this PC (Syncthing is free) and use 'Auto-import a "
            "synced file'. The app then imports it by itself.\n\n"
            "Your token gives full access to your account: only put it on a device you own, "
            "never on a shared or public server.")
        tk.Label(b, text=txt, bg=CHAT, fg=TEXT, font=(FONT, 9), anchor="w", justify="left",
                 wraplength=550).pack(fill="x", pady=(8, 0))

    def import_logger_db(self):
        path = filedialog.askopenfilename(title="Pick deleted_messages.db from the other device",
                                          filetypes=[("Database", "*.db"), ("All files", "*.*")])
        if not path:
            return
        try:
            n, ev = self.store().merge_from(path)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Could not read that file: {e}")
            return
        self._deleted_sig = None
        self.invalidate_view("deleted")
        if self.view == "deleted":
            self.open_view("deleted", rebuild=True)
        messagebox.showinfo(APP_NAME, f"Imported {n} deleted messages and {ev} events.")

    def update_count_label(self):
        p = self.preview
        if not p or p.get("count") is None:
            self.count_label.configure(text="")
            return
        self.count_label.configure(
            text=f"{p['count']:,} deleted messages saved" if p.get("source") == "deleted" else
            f"{p['count']:,} of your messages" if p.get("source") == "pkg"
            else f"≈ {p['count']:,} of your messages")

    def update_chat_header_check(self):
        live = bool(self.preview and self.preview.get("source") == "live")
        for w in (self.pins_btn, self.call_btn, self.members_btn):
            w.pack_forget()
        if not self.open_key:
            self.head_check_frame.pack_forget()
            self.export_btn.pack_forget()
            self.count_label.pack_forget()
            return
        clean = self.clean_mode()
        if self.open_key[0] == "deleted" or not clean:
            self.head_check_frame.pack_forget()
        else:
            self.head_check_frame.pack(side="right", padx=16)
        self.export_btn.pack(side="right", padx=(0, 4))
        if live:
            if self.open_key[0] == "channel":
                self.members_btn.pack(side="right", padx=(0, 10))
            self.pins_btn.pack(side="right", padx=(0, 10))
            if self.open_key[0] in ("dm", "link"):
                self.call_btn.pack(side="right", padx=(0, 10))
        if clean:
            self.count_label.pack(side="right", padx=(0, 14))
        else:
            self.count_label.pack_forget()
        st = self.check_state(self.open_key)
        self.head_check.set(st)
        self.head_check_label.configure(
            text="Whole server ticked" if st == "inherited" else
            ("Will be cleaned" if st == "on" else "Clean this chat"),
            fg=GREEN if st != "off" else TEXT)

    def mark_open_row(self):
        for key, row in self.row_frames.items():
            try:
                on = key == self.open_key
                set_bg(row, SELECTED if on else SIDEBAR)
                row.name_label.configure(fg=WHITE if on else MUTED)
            except tk.TclError:
                pass

    def open_chat(self, key, channel_id, title, icon, avatar_url, user_id, server=None):
        self.open_key = key
        self.after_idle(self.mark_friends_row)
        self.remember_last_chat(key, channel_id, title, icon, avatar_url, user_id, server)
        self.clear_unread(channel_id)
        if self.find_bar.winfo_ismapped():
            self.close_find()
        self.preview = {"key": key, "channel_id": channel_id, "title": title, "icon": icon,
                        "avatar": avatar_url, "user_id": user_id, "server": server,
                        "msgs": [], "more": False, "source": "live", "count": None}
        self.chat_icon.configure(text=icon)
        self.chat_title.configure(text=title)
        self.chat_sub.configure(text=server or "")
        self.set_input_hint(icon, title)
        self.mark_open_row()
        self.update_chat_header_check()
        self.after_idle(self.update_chat_header_check)
        self.messages.clear()
        tk.Label(self.messages.inner, text="Loading messages…", bg=CHAT, fg=MUTED,
                 font=(FONT, 10)).pack(pady=40)
        self.update_count_label()
        self.fetch_preview()
        self.fetch_count()

    def fetch_count(self):
        """Ask Discord search how many of your messages are in the open chat."""
        p = self.preview
        req = self.preview_req
        kind, cid = p["key"]
        gid = self.channel_guild.get(cid) if kind == "channel" else None
        my_id = (self.me or {}).get("id")
        if not my_id:
            return

        def work():
            try:
                n = core.search_count(self.make_api(), "channel", cid, my_id, gid)
            except Exception:
                n = None
            if n is not None:
                self.after(0, lambda: self.on_count(req, n))
        threading.Thread(target=work, daemon=True).start()

    def on_count(self, req, n):
        if self.preview and req == self.preview_req and self.preview.get("source") == "live":
            self.preview["count"] = n
            self.update_count_label()

    def fetch_preview(self, before=None):
        self.preview_req += 1
        req = self.preview_req
        cid = self.preview["channel_id"]

        def work():
            try:
                st, msgs = core.fetch_messages(self.make_api(), cid, before, PREVIEW_PAGE)
            except Exception:
                st, msgs = 0, []
            self.after(0, lambda: self.on_preview(req, st, msgs, before))
        threading.Thread(target=work, daemon=True).start()

    def on_preview(self, req, status, msgs, before):
        if req != self.preview_req or not self.preview or self.main_frame is None:
            return
        if status != 200:
            self.chat_empty(core.friendly_error(status, "load this chat"))
            return
        older = list(reversed(msgs))
        if self.preview.pop("jump_pending", False):
            self.preview["msgs"] = older
            self.preview["more"] = len(msgs) >= PREVIEW_PAGE
            self.render_preview(scroll="bottom")
            return
        self.preview["msgs"] = older + (self.preview["msgs"] if before else [])
        self.preview["more"] = len(msgs) >= PREVIEW_PAGE
        self.render_preview(scroll="top" if before else "bottom")

    def render_preview(self, scroll="bottom"):
        p = self.preview
        keep_pos = self.messages.canvas.yview()[0] if scroll == "keep" else None
        self.messages.clear()
        self.msg_rows, self.text_labels, self.row_by_id = [], [], {}
        inner = self.messages.inner
        width = max(300, self.messages.canvas.winfo_width() - 230)

        if p["more"]:
            top = tk.Frame(inner, bg=CHAT)
            top.pack(fill="x", pady=12)
            older = ((lambda: self.show_pkg_page(older=True)) if p.get("source") in LOCAL else
                     (lambda: self.fetch_preview(p["msgs"][0]["id"]) if p["msgs"] else None))
            FlatButton(top, "Load older messages", older,
                       bg=SELECTED, hover=HOVER, font_size=9, pady=5).pack()
        else:
            start = tk.Frame(inner, bg=CHAT)
            start.pack(fill="x", padx=16, pady=(30, 10))
            big = Avatar(start, 80, CHAT, p["icon"] if p["icon"] == "#" else
                         core.initials(p["title"])[:1],
                         CHAT if p["icon"] == "#" else color_for(p["user_id"]),
                         font_size=30)
            big.pack(anchor="w")
            if p.get("avatar"):
                self.images.load(p["avatar"], 80, big)
            tk.Label(start, notr=True, text=(i18n.tr("Welcome to #") if p["icon"] == "#" else "")
                     + p["title"].lstrip("#"),
                     bg=CHAT, fg=WHITE, font=(FONT, 20, "bold"), anchor="w").pack(
                fill="x", pady=(8, 0))
            tk.Label(start, text={"pkg": "These are your messages from your data package.",
                                  "deleted": "Messages people deleted after sending them to you."
                                  }.get(p.get("source"), "This is the beginning of this chat."),
                     bg=CHAT, fg=MUTED,
                     font=(FONT, 10), anchor="w").pack(fill="x")
            tk.Frame(inner, bg=DIVIDER, height=1).pack(fill="x", padx=16, pady=(10, 4))

        if not p["msgs"]:
            tk.Label(inner, text="No messages here yet.", bg=CHAT, fg=MUTED,
                     font=(FONT, 10)).pack(pady=20)
        if p.get("source") == "live" and p["msgs"] and self.me:
            try:
                hist = self.store().edit_history([m.get("id") for m in p["msgs"]
                                                  if m.get("edited_timestamp")])
                for m in p["msgs"]:
                    if m.get("id") in hist:
                        m["_edits"] = hist[m["id"]]
            except Exception:
                pass
        prev = None
        prev_day = None
        shown = p["msgs"]
        if p.get("only_mine") and self.me:
            shown = [m for m in shown if (m.get("author") or {}).get("id") == self.me["id"]]
            if not shown:
                tk.Label(inner, text="None of your messages in this part of the chat. "
                                     "Load older messages to see more.", bg=CHAT, fg=MUTED,
                         font=(FONT, 10)).pack(pady=20)
        for m in shown:
            day = local_day(m)
            new_day = day and day != prev_day
            if new_day:
                self.date_divider(inner, day)
                prev_day = day
            head = (prev is None or new_day or prev["author"]["id"] != m["author"]["id"]
                    or core.is_system(prev) or abs(core_ts(m) - core_ts(prev)) > 7 * 60
                    or m.get("message_reference"))
            self.render_message(inner, m, head, width)
            prev = m
        if p.get("jumped"):
            jp = tk.Frame(inner, bg=CHAT)
            jp.pack(fill="x", pady=(16, 0))
            FlatButton(jp, "You're viewing older messages   •   Jump to present",
                       self.jump_to_present, font_size=9, pady=6).pack()
        self._chat_spacer = tk.Frame(inner, bg=CHAT, height=24)
        self._chat_spacer.pack(fill="x")
        self.refresh_highlights()
        if scroll == "bottom":
            self.messages.to_bottom()
        elif scroll == "top":
            self.messages.to_top()
        elif keep_pos is not None:
            self.messages.update_idletasks()
            self.messages.canvas.yview_moveto(keep_pos)

    def date_divider(self, parent, day, before=None):
        f = tk.Frame(parent, bg=CHAT)
        f.pack(fill="x", padx=16, pady=(18, 0), **({"before": before} if before else {}))
        tk.Frame(f, bg=DIVIDER, height=1).pack(side="left", fill="x", expand=True, pady=(1, 0))
        tk.Label(f, notr=True, text=i18n.long_date(day), bg=CHAT, fg=MUTED,
                 font=(FONT, 8, "bold"), padx=6).pack(side="left")
        tk.Frame(f, bg=DIVIDER, height=1).pack(side="left", fill="x", expand=True, pady=(1, 0))

    def render_system(self, parent, m, before=None):
        """Calls, pins, people joining… shown as one grey line, like Discord."""
        icon, text = core.system_text(m, (self.me or {}).get("id"))
        row = tk.Frame(parent, bg=CHAT)
        row.pack(fill="x", pady=(8, 0), **({"before": before} if before else {}))
        bar = tk.Frame(row, bg=CHAT, width=3)
        bar.pack(side="left", fill="y")
        left = tk.Frame(row, bg=CHAT, width=68)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        colour = GREEN if icon in ("➜", "📞") and "missed" not in text.lower() else (
            RED if icon == "📞" else MUTED)
        tk.Label(left, text=icon, notr=True, bg=CHAT, fg=colour,
                 font=("Segoe UI Emoji", 11)).pack(pady=(2, 0))
        tag = tk.Label(row, text="", bg=CHAT, fg=RED, font=(FONT, 7, "bold"))
        content = tk.Frame(row, bg=CHAT)
        content.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=3)
        line = tk.Frame(content, bg=CHAT)
        line.pack(fill="x")
        tk.Label(line, text=text, notr=True, bg=CHAT, fg=MUTED, font=(FONT, 10), anchor="w",
                 justify="left", wraplength=700).pack(side="left")
        tk.Label(line, text="  " + core.format_time(m.get("timestamp")), notr=True, bg=CHAT,
                 fg=MUTED, font=(FONT, 8)).pack(side="left", pady=(2, 0))
        react_row = tk.Frame(content, bg=CHAT)
        info = {"msg": m, "row": row, "bar": bar, "tag": tag, "content": content,
                "react_row": react_row, "matched": "unset", "fixed": [bar], "time": None,
                "mention": False, "bg": CHAT, "hover": False, "system": True}
        self.msg_rows.append(info)
        self.row_by_id[m.get("id")] = info
        bind_tree(row, "<Button-3>", lambda e, info=info: self.message_menu(e, info))

    def render_message(self, parent, m, head, width, before=None):
        if core.is_system(m) and m.get("type") != 21:
            return self.render_system(parent, m, before)
        author = m.get("author", {})
        row = tk.Frame(parent, bg=CHAT)
        row.pack(fill="x", pady=((4 if self.settings.get("compact") else 14) if head else 0, 0),
                 **({"before": before} if before else {}))
        bar = tk.Frame(row, bg=CHAT, width=3)
        bar.pack(side="left", fill="y")
        left = tk.Frame(row, bg=CHAT, width=68)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tag = tk.Label(row, text="WILL BE DELETED", bg=CHAT, fg=RED, font=(FONT, 7, "bold"))
        content = tk.Frame(row, bg=CHAT)
        content.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=1)

        if head:
            name = author.get("global_name") or author.get("username", "?")
            av = Avatar(left, 40, CHAT, core.initials(name)[:1], color_for(author.get("id")))
            av.pack(pady=(3, 0))
            av.configure(cursor="hand2")
            av.bind("<Button-1>", lambda e, a=author: self.open_profile(a))
            if author.get("id"):
                self.images.load(core.user_avatar_url(author), 40, av)
            ref = m.get("referenced_message")
            if ref:
                rname = (ref.get("author", {}).get("global_name")
                         or ref.get("author", {}).get("username", ""))
                rtext = core.render_content(ref).replace("\n", " ")[:80]
                tk.Label(content, notr=True, text=f"╭─ @{rname}  {rtext}", bg=CHAT, fg=MUTED,
                         font=(FONT, 8), anchor="w").pack(fill="x")
            line = tk.Frame(content, bg=CHAT)
            line.pack(fill="x")
            is_me = self.me and author.get("id") == self.me.get("id")
            nl = tk.Label(line, notr=True, text=name, bg=CHAT, fg=WHITE, font=(FONT, 10, "bold"),
                          cursor="hand2")
            nl.pack(side="left")
            nl.bind("<Button-1>", lambda e, a=author: self.open_profile(a))
            if author.get("bot"):
                tk.Label(line, text=" APP ", bg=BLURPLE, fg="white",
                         font=(FONT, 7, "bold")).pack(side="left", padx=(5, 0))
            if is_me and self.clean_mode():
                tk.Label(line, text="  you", bg=CHAT, fg=GREEN, font=(FONT, 8, "bold")).pack(
                    side="left")
            tk.Label(line, text="  " + core.format_time(m.get("timestamp")), bg=CHAT,
                     fg=MUTED, font=(FONT, 8)).pack(side="left", pady=(2, 0))

        raw = m.get("content") or ""
        if m.get("type") not in core.DELETABLE_TYPES and not raw:
            raw = core.system_text(m, (self.me or {}).get("id"))[1]
        fixed = []      # widgets that keep their own colour on hover/highlight
        jumbo = emojis.only_emojis(raw)
        mentions = m.get("mentions", [])
        for kind, part in core.split_blocks(raw) if raw.strip() else []:
            if kind == "code":
                lbl = tk.Label(content, notr=True, text=part, bg=CODE_BG, fg=TEXT,
                               font=("Consolas", 9), justify="left", anchor="w", padx=10,
                               pady=8, wraplength=width, highlightthickness=1,
                               highlightbackground=CODE_BORDER)
                lbl.pack(fill="x", anchor="w", pady=(2, 2))
                fixed.append(lbl)
            elif kind == "quote":
                q = tk.Frame(content, bg=CHAT)
                q.pack(fill="x", anchor="w", pady=1)
                qb = tk.Frame(q, bg=QUOTE_BAR, width=4)
                qb.pack(side="left", fill="y")
                fixed.append(qb)
                MessageText(q, richtext.parse(part, mentions, self.channel_name), self.images,
                            CHAT).pack(side="left", fill="x", expand=True, padx=(10, 0))
            else:
                MessageText(content, richtext.parse(part, mentions, self.channel_name),
                            self.images, CHAT, jumbo=jumbo).pack(fill="x", anchor="w")
        if m.get("edited_timestamp"):
            tk.Label(content, text="(edited)", bg=CHAT, fg=MUTED, font=(FONT, 7),
                     anchor="w").pack(fill="x")
        if m.get("_edits") and self.settings.get("show_edits", True) is not False:
            for old in m["_edits"][-5:]:
                ef = tk.Frame(content, bg=CHAT)
                ef.pack(fill="x", anchor="w", pady=(1, 0))
                eb = tk.Frame(ef, bg=EDIT_BAR, width=3)
                eb.pack(side="left", fill="y")
                fixed.append(eb)
                tk.Label(ef, text="before edit:", bg=CHAT, fg=EDIT_BAR,
                         font=(FONT, 8, "bold")).pack(side="left", anchor="n", padx=(6, 4))
                tk.Label(ef, notr=True, text=old or "(empty)", bg=CHAT, fg=MUTED,
                         font=(FONT, 9, "italic"), anchor="w", justify="left",
                         wraplength=max(200, width - 120)).pack(side="left", fill="x")
        for a in m.get("attachments", []):
            self.render_attachment(content, a)
        for e in m.get("embeds", [])[:4]:
            card = self.render_embed(content, e, width)
            if card is not None:
                fixed.append(card)
        for st in m.get("sticker_items") or []:
            url = core.sticker_url(st)
            if url:
                th = Thumb(content, CHAT, st.get("name", "sticker"))
                th.pack(anchor="w", pady=(4, 2))
                self.images.load(url, (160, 160), th,
                                 mode="anim" if url.split("?")[0].endswith(".gif") else "thumb")
            else:
                tk.Label(content, notr=True, text=f"[sticker] {st.get('name', '')}", bg=CHAT,
                         fg=MUTED, font=(FONT, 9), anchor="w").pack(fill="x")
        react_row = tk.Frame(content, bg=CHAT)
        react_row.pack(anchor="w", pady=(4, 0) if m.get("reactions") else 0)
        self.render_reactions(react_row, m, fixed)
        if m.get("pinned"):
            tk.Label(content, text="pinned", bg=CHAT, fg=MUTED, font=(FONT, 8),
                     anchor="w").pack(fill="x")

        time_lbl = None
        if not head:   # Discord shows the time on hover for grouped messages
            time_lbl = tk.Label(left, text=short_time(m.get("timestamp")), bg=CHAT, fg=CHAT,
                                font=(FONT, 7))
            time_lbl.pack(pady=(4, 0))
        me_id = (self.me or {}).get("id")
        mention = bool(m.get("mention_everyone")) or any(
            u.get("id") == me_id for u in m.get("mentions", []))
        info = {"msg": m, "row": row, "bar": bar, "tag": tag, "content": content,
                "react_row": react_row,
                "matched": "unset", "fixed": [bar] + fixed, "time": time_lbl,
                "mention": mention, "bg": CHAT, "hover": False}
        self.msg_rows.append(info)
        self.row_by_id[m.get("id")] = info
        bind_tree(row, "<Button-3>", lambda e, info=info: self.message_menu(e, info))
        bind_tree(row, "<Enter>", lambda e, info=info: self.msg_hover(info, True))
        bind_tree(row, "<Leave>", lambda e, info=info: self.msg_hover(info, False))

    def render_attachment(self, parent, a):
        """Pictures, animated GIFs, videos (play right here) and file links."""
        url = a.get("proxy_url") or a.get("url")
        name = a.get("filename", "file")
        spoiler = name.startswith("SPOILER_")
        if url and core.is_video(a):
            w, h = media.fit(a.get("width") or 400, a.get("height") or 300, 400, 300)
            player = media.VideoPlayer(parent, a.get("url") or url, core.video_thumb_url(a),
                                       self.images, CHAT, (w, h), name=name,
                                       duration=a.get("duration_secs"))
            player.pack(anchor="w", pady=(4, 2))
        elif url and core.is_image(a):
            th = Thumb(parent, CHAT, name, overlay="SPOILER" if spoiler else None,
                       on_click=lambda: self.open_image(a))
            th.pack(anchor="w", pady=(4, 2))
            self.images.load(url, (400, 300), th,
                             mode="anim" if core.is_animated(a) else "thumb")
        else:
            box = tk.Frame(parent, bg=CODE_BG, padx=10, pady=8, highlightthickness=1,
                           highlightbackground=CODE_BORDER)
            box.pack(anchor="w", pady=(4, 2))
            tk.Label(box, text="📄", bg=CODE_BG, fg=TEXT, font=(FONT, 18)).pack(side="left")
            col = tk.Frame(box, bg=CODE_BG)
            col.pack(side="left", padx=(8, 0))
            lbl = tk.Label(col, notr=True, text=name, bg=CODE_BG, fg=LINK, font=(FONT, 10),
                           anchor="w", cursor="hand2" if a.get("url") else "")
            lbl.pack(fill="x")
            tk.Label(col, notr=True, text=core.human_size(a.get("size")), bg=CODE_BG, fg=MUTED,
                     font=(FONT, 8), anchor="w").pack(fill="x")
            if a.get("url"):
                lbl.bind("<Button-1>", lambda e: webbrowser.open(a["url"]))

    def open_image(self, a):
        """Big picture viewer with Save and Open in browser."""
        url = a.get("proxy_url") or a.get("url")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = int(sw * 0.8), int(sh * 0.8)
        top, b = self.dialog(a.get("filename", "Picture"), w, h)
        b.configure(bg=RAIL)
        top.configure(bg=RAIL)
        bar = tk.Frame(b, bg=RAIL)
        bar.pack(side="bottom", fill="x", pady=(10, 0))
        th = Thumb(b, RAIL, a.get("filename", "picture"))
        th.pack(expand=True)
        self.images.load(url, (w - 60, h - 110), th,
                         mode="anim" if core.is_animated(a) else "thumb")
        FlatButton(bar, "Save picture…", lambda: self.save_attachment(a), font_size=9,
                   pady=6).pack(side="left")
        FlatButton(bar, "Open in browser", lambda: webbrowser.open(a.get("url") or url),
                   bg=SELECTED, hover=HOVER, font_size=9, pady=6).pack(side="left", padx=8)
        FlatButton(bar, "Close", top.destroy, bg=SELECTED, hover=HOVER, font_size=9,
                   pady=6).pack(side="right")

    def save_attachment(self, a):
        name = a.get("filename", "picture")
        path = filedialog.asksaveasfilename(title="Save picture", initialfile=name)
        if not path:
            return

        def work():
            try:
                data = core.download(a.get("url") or a.get("proxy_url"))
                with open(path, "wb") as f:
                    f.write(data)
                self.after(0, lambda: self.set_status(f"Saved {name}"))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: messagebox.showerror(APP_NAME, f"Could not save: {msg}"))
        threading.Thread(target=work, daemon=True).start()

    def render_embed(self, parent, e, width):
        """Link previews / bot embeds as Discord-style cards."""
        etype = e.get("type")
        thumb = (e.get("thumbnail") or {}).get("proxy_url") or (e.get("thumbnail") or {}).get(
            "url")
        image = (e.get("image") or {}).get("proxy_url") or (e.get("image") or {}).get("url")
        video = media.gifv_video_url(e)
        if etype == "gifv" and video:
            tw, th_ = ((e.get("video") or {}).get("width") or 300,
                       (e.get("video") or {}).get("height") or 200)
            w, h = media.fit(tw, th_, 400, 300)
            media.VideoPlayer(parent, video, thumb, self.images, CHAT, (w, h), gif=True,
                              name="GIF").pack(anchor="w", pady=(4, 2))
            return None
        if etype in ("image", "gifv") and thumb:
            src = (e.get("url") or "") if (e.get("url") or "").split("?")[0].lower().endswith(
                (".gif", ".webp")) else thumb
            big = {"url": e.get("url") or thumb, "proxy_url": thumb, "filename": "picture"}
            th = Thumb(parent, CHAT, "image", on_click=lambda: self.open_image(big))
            th.pack(anchor="w", pady=(4, 2))
            self.images.load(src or thumb, (400, 300), th,
                             mode="anim" if src != thumb else "thumb")
            return None
        if etype == "video" and video and "youtube" not in (
                (e.get("provider") or {}).get("name") or "").lower() and video.split(
                "?")[0].lower().endswith((".mp4", ".mov", ".webm")):
            w, h = media.fit((e.get("video") or {}).get("width") or 400,
                             (e.get("video") or {}).get("height") or 300, 400, 300)
            media.VideoPlayer(parent, video, thumb, self.images, CHAT, (w, h),
                              name="video").pack(anchor="w", pady=(4, 2))
            return None
        title, desc = e.get("title"), e.get("description")
        if not (title or desc or image or e.get("fields")):
            return None
        color = "#%06x" % e["color"] if isinstance(e.get("color"), int) else CODE_BORDER
        card = tk.Frame(parent, bg=CODE_BG)
        card.pack(anchor="w", pady=(4, 2), fill="x", padx=(0, 80))
        tk.Frame(card, bg=color, width=4).pack(side="left", fill="y")
        body = tk.Frame(card, bg=CODE_BG, padx=12, pady=8)
        body.pack(side="left", fill="both", expand=True)
        wrap = max(200, width - 160)
        for txt, fg, f in (((e.get("provider") or {}).get("name"), MUTED, (FONT, 8)),
                           ((e.get("author") or {}).get("name"), WHITE, (FONT, 9, "bold")),
                           (title, LINK if e.get("url") else WHITE, (FONT, 10, "bold")),
                           (core.render_content({"content": desc or ""})[:600] if desc
                            else None, TEXT, (FONT, 9))):
            if txt:
                tk.Label(body, notr=True, text=txt, bg=CODE_BG, fg=fg, font=f, justify="left",
                         anchor="w", wraplength=wrap).pack(fill="x", anchor="w", pady=(0, 2))
        for fl in (e.get("fields") or [])[:6]:
            tk.Label(body, notr=True, text=fl.get("name", ""), bg=CODE_BG, fg=WHITE,
                     font=(FONT, 9, "bold"), anchor="w", wraplength=wrap,
                     justify="left").pack(fill="x")
            tk.Label(body, notr=True, text=core.render_content({"content": fl.get("value", "")})[:300],
                     bg=CODE_BG, fg=TEXT, font=(FONT, 9), anchor="w", wraplength=wrap,
                     justify="left").pack(fill="x", pady=(0, 3))
        if image or thumb:
            big = {"url": image or thumb, "proxy_url": image or thumb, "filename": "picture"}
            th = Thumb(body, CODE_BG, "image", on_click=lambda: self.open_image(big))
            th.pack(anchor="w", pady=(4, 0))
            self.images.load(image or thumb, (300, 200) if image else (80, 80), th,
                             mode="thumb")
        return card

    # ================================================================ reactions & emojis
    def channel_name(self, cid):
        if cid in self.channel_names:
            return self.channel_names[cid]
        for chans in self.guild_channels.values():
            if isinstance(chans, list):
                for c in chans:
                    self.channel_names[c["id"]] = c.get("name")
        return self.channel_names.get(cid)

    def render_reactions(self, holder, m, fixed=None):
        """Reaction pills like Discord: emoji picture + count, blue when you reacted.
        Click to add/remove your reaction, hover to see who reacted."""
        for w in holder.winfo_children():
            w.destroy()
        for r in (m.get("reactions") or [])[:20]:
            em = r.get("emoji") or {}
            mine = bool(r.get("me"))
            bg = REACT_ME_BG if mine else CODE_BG
            pill = tk.Frame(holder, bg=bg, highlightthickness=1, cursor="hand2",
                            highlightbackground=BLURPLE if mine else CODE_BG)
            pill.pack(side="left", padx=(0, 4), pady=(0, 2))
            img = EmojiLabel(pill, bg)
            img.configure(text=(em.get("name") or "?") if not em.get("id") else
                          f":{em.get('name')}:", font=("Segoe UI Emoji", 10), fg=TEXT)
            img.pack(side="left", padx=(6, 3), pady=2)
            url = core.emoji_image_url(em, 48)
            if url:
                self.images.load(url, (18, 18), img,
                                 mode="anim" if em.get("animated") else "thumb")
            tk.Label(pill, notr=True, text=str(r.get("count", 1)), bg=bg,
                     fg=WHITE if mine else TEXT, font=(FONT, 9, "bold")).pack(
                side="left", padx=(0, 7))
            if fixed is not None:
                fixed.append(pill)
            bind_tree(pill, "<Button-1>", lambda e, em=em, mine=mine: self.toggle_reaction(
                m, em, not mine))
            Tooltip(pill, lambda em=em: self.reaction_tip(m, em), notr=True)
        if m.get("reactions") and self.can_chat():
            add = tk.Label(holder, text="☺+", bg=CODE_BG, fg=MUTED, font=(FONT, 9),
                           padx=6, pady=2, cursor="hand2")
            add.pack(side="left")
            add.bind("<Button-1>", lambda e: self.open_emoji_picker(
                lambda em: self.toggle_reaction(m, em, True), e.widget))
            if fixed is not None:
                fixed.append(add)

    def reaction_tip(self, m, em):
        """Names of who reacted (loaded once in the background, like Discord's tooltip)."""
        key = (m.get("id"), em.get("id") or em.get("name"))
        cache = self.__dict__.setdefault("_react_names", {})
        if key in cache:
            names = cache[key]
            label = f":{em['name']}:" if em.get("id") else em.get("name", "")
            return f"{label} " + (", ".join(names[:12]) + (" …" if len(names) > 12 else "")
                                  if names else i18n.tr("reacted"))
        cache[key] = []
        cid = (self.preview or {}).get("channel_id")
        if cid and self.preview.get("source") == "live":
            def work():
                try:
                    users = core.reaction_users(self.make_api(), cid, m["id"], em)
                except Exception:
                    users = []
                cache[key] = [u.get("global_name") or u.get("username", "?") for u in users]
            threading.Thread(target=work, daemon=True).start()
        return i18n.tr("Loading…")

    def can_chat(self):
        return bool(self.preview and self.preview.get("source") == "live"
                    and self.settings.get("chat_enabled", True))

    def toggle_reaction(self, m, em, add):
        p = self.preview
        if not self.can_chat():
            return
        cid = p["channel_id"]
        core.apply_reaction(m, em, add)        # show it right away
        self.redraw_reactions(m)
        if add and not em.get("id"):
            recent = [x for x in self.settings.get("recent_emojis", []) if x != em["name"]]
            self.settings["recent_emojis"] = ([em["name"]] + recent)[:16]

        def work():
            ok = core.react(self.make_api(), cid, m["id"], em, add)
            if not ok:
                def undo():
                    core.apply_reaction(m, em, not add)
                    self.redraw_reactions(m)
                    self.set_status("Discord refused that reaction.")
                self.after(0, undo)
        threading.Thread(target=work, daemon=True).start()

    def redraw_reactions(self, m):
        info = self.row_by_id.get(m.get("id"))
        if not info:
            return
        try:
            holder = info["react_row"]
            self.render_reactions(holder, info["msg"], info["fixed"])
            holder.pack_configure(pady=(4, 0) if info["msg"].get("reactions") else 0)
            if info["bg"] != CHAT:
                set_bg(holder, info["bg"], skip=info["fixed"])
        except tk.TclError:
            pass

    def open_emoji_picker(self, on_pick, anchor=None):
        """Emoji picker: search box, recent emojis, popular emojis, this server's emojis."""
        if getattr(self, "_picker", None) is not None:
            try:
                self._picker.destroy()
            except tk.TclError:
                pass
        top = tk.Toplevel(self)
        self._picker = top
        top.overrideredirect(True)
        top.configure(bg=SIDEBAR, highlightthickness=1, highlightbackground=BORDER)
        x = (anchor.winfo_rootx() if anchor else self.winfo_pointerx()) - 160
        y = (anchor.winfo_rooty() if anchor else self.winfo_pointery()) - 330
        top.geometry(f"352x320+{max(0, x)}+{max(0, y)}")
        head = tk.Frame(top, bg=SIDEBAR)
        head.pack(fill="x", padx=8, pady=8)
        box, search = entry_box(head, "Find the perfect emoji", font_size=9)
        box.pack(fill="x")
        grid = ScrollFrame(top, SIDEBAR)
        grid.pack(fill="both", expand=True, padx=4, pady=(0, 6))
        gid = self.channel_guild.get((self.preview or {}).get("channel_id"))
        server_emojis = self.__dict__.setdefault("_server_emojis", {})

        def pick(em):
            try:
                top.destroy()
            except tk.TclError:
                pass
            self._picker = None
            on_pick(em)

        def cell(parent, em, url, col, row_):
            th = EmojiLabel(parent, SIDEBAR)
            th.configure(text=em.get("name") if not em.get("id") else f":{em['name']}:",
                         font=("Segoe UI Emoji", 14), width=2, padx=4, pady=3)
            th.grid(row=row_, column=col, padx=1, pady=1)
            if url:
                self.images.load(url, (28, 28), th,
                                 mode="anim" if em.get("animated") else "thumb")
            th.bind("<Button-1>", lambda e: pick(em))
            th.bind("<Enter>", lambda e: th.configure(bg=HOVER))
            th.bind("<Leave>", lambda e: th.configure(bg=SIDEBAR))
            Tooltip(th, lambda: f":{em['name']}:" if em.get("id")
                    else ":" + emojis.name_of(em["name"]) + ":", notr=True)

        def section(title, items):
            if not items:
                return
            tk.Label(grid.inner, notr=True, text=i18n.tr(title).upper(), bg=SIDEBAR, fg=MUTED,
                     font=(FONT, 8, "bold"), anchor="w").pack(fill="x", padx=6, pady=(6, 2))
            f = tk.Frame(grid.inner, bg=SIDEBAR)
            f.pack(fill="x", padx=4)
            for i, em in enumerate(items):
                cell(f, em, core.emoji_image_url(em, 48), i % 9, i // 9)

        def render(*_):
            grid.clear()
            q = search.get().strip().lower()
            mine = [e for e in server_emojis.get(gid, [])
                    if not q or q in (e.get("name") or "").lower()]
            if not q:
                section("Recent", [{"name": c, "id": None}
                                   for c in self.settings.get("recent_emojis", [])])
            section("This server", [{"name": e["name"], "id": e["id"],
                                     "animated": e.get("animated", False)} for e in mine])
            section("Emojis" if not q else "Results",
                    [{"name": c, "id": None} for c in emojis.search(q)])
        search.bind("<KeyRelease>", render)
        top.bind("<Escape>", lambda e: pick_close())

        def pick_close():
            try:
                top.destroy()
            except tk.TclError:
                pass
            self._picker = None
        top.bind("<FocusOut>", lambda e: self.after(150, lambda: (
            pick_close() if self.focus_get() is None or not is_inside(self.focus_get(), top)
            else None)))
        render()
        search.focus_set()
        if gid and gid not in server_emojis and self.demo is None:
            def work():
                try:
                    server_emojis[gid] = core.guild_emojis(self.make_api(), gid)
                except Exception:
                    server_emojis[gid] = []
                self.after(0, lambda: top.winfo_exists() and render())
            threading.Thread(target=work, daemon=True).start()

    # ================================================================ message toolbar
    def hover_toolbar(self, info, on):
        """Small toolbar at the top-right of a message on hover (react, reply, edit...)."""
        bar = getattr(self, "_toolbar", None)
        if not on:
            if bar is not None and getattr(bar, "owner", None) is info:
                bar.place_forget()
            return
        if not self.can_chat() and (self.preview or {}).get("source") != "live":
            return
        try:
            if bar is None or not bar.winfo_exists() or bar.master is not self.messages.inner:
                bar = tk.Frame(self.messages.inner, bg=SIDEBAR, highlightthickness=1,
                               highlightbackground=BORDER)
                self._toolbar = bar
            for w in bar.winfo_children():
                w.destroy()
            bar.owner = info
            m = info["msg"]
            mine = self.me and (m.get("author") or {}).get("id") == self.me.get("id")
            buttons = []
            if self.can_chat():
                for ch in emojis.QUICK[:3]:
                    buttons.append((ch, lambda c=ch: self.toggle_reaction(m, {"name": c, "id": None},
                                                                          True), None, True))
                buttons.append(("☺+", lambda: self.open_emoji_picker(
                    lambda em: self.toggle_reaction(m, em, True), bar), "Add reaction", False))
                buttons.append(("↩", lambda: self.start_reply(m), "Reply", False))
                if mine and m.get("type") in core.DELETABLE_TYPES:
                    buttons.append(("✎", lambda: self.start_edit(m), "Edit", False))
            buttons.append(("🔖", lambda: self.toggle_bookmark(m),
                            "Save for later", False))
            buttons.append(("⋯", lambda: self.message_menu(types_ns(bar), info), "More",
                            False))
            for text, cmd, tip, is_emoji in buttons:
                b = EmojiLabel(bar, SIDEBAR)
                b.configure(text=text, font=("Segoe UI Emoji", 11) if is_emoji else (FONT, 11),
                            fg=TEXT, padx=6, pady=2, cursor="hand2")
                b.pack(side="left")
                if is_emoji:
                    self.images.load(core.twemoji_url(text), (20, 20), b, mode="thumb")
                b.bind("<Button-1>", lambda e, cmd=cmd: cmd())
                b.bind("<Enter>", lambda e, b=b: b.configure(bg=HOVER))
                b.bind("<Leave>", lambda e, b=b: b.configure(bg=SIDEBAR))
                if tip:
                    Tooltip(b, lambda tip=tip: tip)
            bind_tree(bar, "<Leave>", lambda e: self.msg_hover(bar.owner, False))
            bar.place(in_=info["row"], relx=1.0, x=-14, y=-14, anchor="ne")
            bar.lift()
        except tk.TclError:
            pass

    # ================================================================ bookmarks
    def bookmarks(self):
        return read_json(app_data_file("bookmarks.json"), [])

    def toggle_bookmark(self, m):
        marks = self.bookmarks()
        if any(b.get("id") == m.get("id") for b in marks):
            marks = [b for b in marks if b.get("id") != m.get("id")]
            self.set_status("Removed from saved messages.")
        else:
            p = self.preview or {}
            marks.insert(0, {"id": m.get("id"), "channel_id": m.get("channel_id")
                             or p.get("channel_id"), "chat": p.get("title", ""),
                             "server": p.get("server"),
                             "author": (m.get("author") or {}).get("global_name")
                             or (m.get("author") or {}).get("username", "?"),
                             "content": m.get("content", ""),
                             "attachments": [a.get("url") for a in m.get("attachments", [])],
                             "timestamp": m.get("timestamp"), "saved": time.time()})
            self.set_status("Saved. Find it in Saved messages (🔖 at the top).")
        write_json(app_data_file("bookmarks.json"), marks[:2000])

    def open_bookmarks(self):
        top, b = self.dialog("Saved messages", 640, 620)
        tk.Label(b, text="Saved messages", bg=CHAT, fg=WHITE, font=(FONT, 14, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(b, text="Messages you saved with 🔖. They stay on this PC even if the "
                         "message gets deleted on Discord.", bg=CHAT, fg=MUTED,
                 font=(FONT, 9), anchor="w", wraplength=580, justify="left").pack(
            fill="x", pady=(2, 10))
        sf = ScrollFrame(b, CHAT)
        sf.pack(fill="both", expand=True)

        def render():
            sf.clear()
            marks = self.bookmarks()
            if not marks:
                tk.Label(sf.inner, text="Nothing saved yet. Hover a message and click 🔖.",
                         bg=CHAT, fg=MUTED, font=(FONT, 10)).pack(pady=40)
            for bm in marks:
                card = tk.Frame(sf.inner, bg=CODE_BG, padx=12, pady=8)
                card.pack(fill="x", pady=4, padx=(0, 10))
                head = tk.Frame(card, bg=CODE_BG)
                head.pack(fill="x")
                where = bm.get("chat", "") + (f"  ·  {bm['server']}" if bm.get("server") else "")
                tk.Label(head, notr=True, text=f"{bm.get('author')}  ", bg=CODE_BG, fg=WHITE,
                         font=(FONT, 10, "bold")).pack(side="left")
                tk.Label(head, notr=True, text=f"{where}  ·  {core.format_time(bm.get('timestamp'))}",
                         bg=CODE_BG, fg=MUTED, font=(FONT, 8)).pack(side="left")
                x = tk.Label(head, text="✕", bg=CODE_BG, fg=MUTED, cursor="hand2")
                x.pack(side="right")
                x.bind("<Button-1>", lambda e, bm=bm: (self.toggle_bookmark(bm), render()))
                MessageText(card, richtext.parse(bm.get("content", "")), self.images,
                            CODE_BG).pack(fill="x")
                for url in bm.get("attachments") or []:
                    LinkLabel(card, url.split("/")[-1].split("?")[0],
                              lambda u=url: webbrowser.open(u), CODE_BG).pack(anchor="w")
                if bm.get("channel_id") and self.demo is None:
                    LinkLabel(card, "Jump to message", lambda bm=bm: (top.destroy(),
                              self.jump_to_bookmark(bm)), CODE_BG, font_size=8).pack(anchor="e")
        render()

    def jump_to_bookmark(self, bm):
        webbrowser.open(f"https://discord.com/channels/"
                        f"{self.channel_guild.get(bm['channel_id'], '@me')}/"
                        f"{bm['channel_id']}/{bm['id']}")

    # ================================================================ logger: muted, search, export
    def open_ignore_list(self):
        """Chats and people the logger should not watch."""
        top, outer = self.dialog("Muted for the logger", 520, 620)
        tk.Label(outer, text="Muted for the logger", bg=CHAT, fg=WHITE,
                 font=(FONT, 14, "bold"), anchor="w").pack(fill="x")
        tk.Label(outer, text="Ticked chats are not saved by the logger (noisy group chats, "
                             "bots...). Changes apply right away.", bg=CHAT, fg=MUTED,
                 font=(FONT, 9), anchor="w", wraplength=470, justify="left").pack(
            fill="x", pady=(2, 8))
        sf = ScrollFrame(outer, CHAT)
        sf.pack(fill="both", expand=True)
        ignored = set(self.settings.get("logger_ignore") or [])

        def changed(i, var):
            if var.get():
                ignored.add(i)
            else:
                ignored.discard(i)
            self.set_setting("logger_ignore", sorted(ignored), True)
        items = [(d["id"], d["name"], "DM") for d in self.dms] + [
            (g["id"], g["name"], "Server (ghost pings)") for g in self.guilds]
        for i, name, kind in items:
            var = tk.BooleanVar(value=i in ignored)
            row = tk.Frame(sf.inner, bg=CHAT)
            row.pack(fill="x", pady=1)
            OptionCheck(row, "", var, CHAT, command=lambda i=i, v=var: changed(i, v)).pack(
                side="left")
            tk.Label(row, notr=True, text=name, bg=CHAT, fg=TEXT, font=(FONT, 10)).pack(
                side="left", padx=(4, 6))
            tk.Label(row, text=kind, bg=CHAT, fg=MUTED, font=(FONT, 8)).pack(side="left")

    def deleted_rows_to_msgs(self, rows, with_chat=False):
        msgs = []
        for r in rows:
            created = core.datetime.fromtimestamp(r["created"] or 0).astimezone()
            deleted = core.datetime.fromtimestamp(r["deleted_at"] or 0).astimezone()
            content = r["content"] or ""
            if with_chat and r.get("channel_name"):
                content = f"-# {r['channel_name']}\n" + content
            for old in r["edits"]:
                content += f"\n> {i18n.tr('before edit:')} {old}"
            atts = []
            for a in r["attachments"]:
                a = dict(a)
                if a.get("local"):
                    a["url"] = "file:///" + os.path.join(msglog.files_dir(),
                                                         a["local"]).replace("\\", "/")
                atts.append(a)
            msgs.append({"id": r["id"], "content": content, "timestamp": created.isoformat(),
                         "author": {"id": r["author_id"], "username": r["author_name"],
                                    "avatar": r["avatar"]},
                         "channel_id": r.get("channel_id"), "type": 0, "attachments": atts,
                         "_deleted": True,
                         "_deleted_at": core.format_time(deleted.isoformat()) + {
                             "offline": "  ·  " + i18n.tr("while your PC was off"),
                             "ghost": "  ·  " + i18n.tr("GHOST PING")}.get(r.get("note"), "")})
        return msgs

    def search_deleted(self, text=None):
        q = (text if text is not None else self.deleted_search.get()).strip()
        if not q:
            return
        me = (self.me or {}).get("id")
        rows = self.store().search_deleted(me, q)
        msgs = self.deleted_rows_to_msgs(sorted(rows, key=lambda r: int(r["id"])),
                                         with_chat=True)
        key = ("deleted", "search")
        self.open_key = key
        self.preview = {"key": key, "channel_id": "search", "title": f"“{q}”", "icon": "⌕",
                        "avatar": None, "user_id": "search",
                        "server": i18n.tr("Search in deleted messages"), "msgs": [],
                        "all": msgs, "more": False, "source": "deleted", "count": len(msgs)}
        self.chat_icon.configure(text="⌕")
        self.chat_title.configure(text=f"“{q}”")
        self.set_input_hint("⌕", q)
        self.mark_open_row()
        self.update_chat_header_check()
        self.show_pkg_page()

    def export_all_deleted(self):
        me = (self.me or {}).get("id")
        rows = self.store().all_deleted(me) if me else []
        if not rows:
            messagebox.showinfo(APP_NAME, "There are no deleted messages to export yet.")
            return
        base = filedialog.askdirectory(title="Where to save the export")
        if not base:
            return
        folder = os.path.join(base, "Deleted messages " + time.strftime("%Y-%m-%d_%H-%M"))
        os.makedirs(folder, exist_ok=True)
        msgs = self.deleted_rows_to_msgs(rows, with_chat=True)
        core.export_html(msgs, "Deleted messages", os.path.join(folder, "deleted_messages.html"))
        core.export_txt(msgs, "Deleted messages", os.path.join(folder, "deleted_messages.txt"))
        with open(os.path.join(folder, "deleted_messages.json"), "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
        self.set_status(f"Exported {len(rows)} deleted messages.")
        open_path(folder)

    def check_import_folder(self):
        """Auto-import the logger file synced from another device (Syncthing, OneDrive...)."""
        path = self.settings.get("logger_import_path")
        if not path or not os.path.isfile(path) or not self.me:
            return
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return
        if mtime == self.settings.get("logger_import_mtime"):
            return
        try:
            n, ev = self.store().merge_from(path)
        except Exception as e:
            applog.write(f"auto-import failed: {e}")
            return
        self.settings["logger_import_mtime"] = mtime
        self.save_settings()
        if n or ev:
            self.log(f"Imported {n} deleted messages and {ev} events from the other device.",
                     "good")
            self._deleted_sig = None

    def pick_import_folder(self):
        path = filedialog.askopenfilename(
            title="Pick the synced deleted_messages_export.db",
            filetypes=[("Database", "*.db"), ("All files", "*.*")])
        if not path:
            return
        self.settings["logger_import_path"] = path
        self.settings.pop("logger_import_mtime", None)
        self.save_settings()
        self.check_import_folder()
        messagebox.showinfo(APP_NAME, "Done. The app now imports this file by itself every "
                                      "time it changes.")

    # ================================================================ media gallery
    def open_gallery(self):
        """Every picture, video, file and link of the open chat (Discord search)."""
        p = self.preview
        if not p or p.get("source") != "live":
            messagebox.showinfo(APP_NAME, "Open a DM or channel first.")
            return
        cid = p["channel_id"]
        gid = self.channel_guild.get(cid)
        top, b = self.dialog(f"Media · {p['title']}", 820, 700)
        tabs = tk.Frame(b, bg=CHAT)
        tabs.pack(fill="x")
        sf = ScrollFrame(b, CHAT)
        sf.pack(fill="both", expand=True, pady=(10, 0))
        state = {"kind": "image", "offset": 0, "total": None, "col": 0, "row": None}
        buttons = {}

        def tile(m, a=None, link=None):
            if state["row"] is None or state["col"] >= 4:
                state["row"] = tk.Frame(sf.inner, bg=CHAT)
                state["row"].pack(fill="x", pady=4)
                state["col"] = 0
            cell = tk.Frame(state["row"], bg=CODE_BG, width=185, height=165)
            cell.pack(side="left", padx=4)
            cell.pack_propagate(False)
            state["col"] += 1
            author = (m.get("author") or {}).get("global_name") or (m.get("author") or {}).get(
                "username", "?")
            if a is not None and (core.is_image(a) or core.is_video(a)):
                url = core.video_thumb_url(a) if core.is_video(a) else (
                    a.get("proxy_url") or a.get("url"))
                th = Thumb(cell, CODE_BG, a.get("filename", ""), overlay="▶" if core.is_video(a)
                           else None, on_click=lambda: (media.open_external(a.get("url"))
                                                        if core.is_video(a) else
                                                        self.open_image(a)))
                th.pack(expand=True)
                self.images.load(url, (175, 125), th, mode="thumb")
            else:
                name = a.get("filename") if a else link
                lbl = tk.Label(cell, notr=True, text=("📄 " if a else "🔗 ") + (name or ""),
                               bg=CODE_BG, fg=LINK, font=(FONT, 9), wraplength=170,
                               justify="left", cursor="hand2")
                lbl.pack(expand=True, padx=6)
                lbl.bind("<Button-1>", lambda e: webbrowser.open((a or {}).get("url") or link))
            tk.Label(cell, notr=True, text=f"{author} · {core.format_time(m.get('timestamp'))}",
                     bg=CODE_BG, fg=MUTED, font=(FONT, 7)).pack(side="bottom", pady=2)

        def show(total, msgs, more_btn):
            if more_btn is not None:
                more_btn.destroy()
            state["total"] = total
            if total is None:
                tk.Label(sf.inner, text="Discord search isn't available for this chat.",
                         bg=CHAT, fg=MUTED, font=(FONT, 10)).pack(pady=30)
                return
            kind = state["kind"]
            for m in msgs:
                for a in m.get("attachments") or []:
                    if (kind == "image" and core.is_image(a)) or (
                            kind == "video" and core.is_video(a)) or (
                            kind == "file" and not core.is_image(a) and not core.is_video(a)):
                        tile(m, a=a)
                if kind == "link":
                    import re as _re
                    for url in _re.findall(r"https?://\S+", m.get("content") or "")[:3]:
                        tile(m, link=url)
            state["offset"] += 25
            if not state["offset"] or total == 0:
                pass
            if state["offset"] < total:
                btn = FlatButton(sf.inner, f"Load more ({state['offset']:,} / {total:,})",
                                 lambda: load(btn), bg=SELECTED, hover=HOVER, font_size=9)
                btn.pack(pady=10)
            elif total == 0:
                tk.Label(sf.inner, text="Nothing here.", bg=CHAT, fg=MUTED,
                         font=(FONT, 10)).pack(pady=30)

        def load(more_btn=None):
            kind, off = state["kind"], state["offset"]

            def work():
                try:
                    total, msgs = core.search_has(self.make_api(), cid, kind, gid, off)
                except Exception:
                    total, msgs = None, []
                self.after(0, lambda: top.winfo_exists() and show(total, msgs, more_btn))
            threading.Thread(target=work, daemon=True).start()

        def pick(kind):
            state.update(kind=kind, offset=0, col=0, row=None)
            sf.clear()
            for k, bt in buttons.items():
                bt.configure(bg=BLURPLE if k == kind else INPUT, fg="white" if k == kind
                             else TEXT)
            load()
        for kind, label in (("image", "Pictures"), ("video", "Videos"), ("file", "Files"),
                            ("link", "Links")):
            bt = tk.Label(tabs, text=label, bg=INPUT, fg=TEXT, font=(FONT, 9, "bold"),
                          padx=14, pady=6, cursor="hand2")
            bt.pack(side="left", padx=(0, 6))
            bt.bind("<Button-1>", lambda e, k=kind: pick(k))
            buttons[kind] = bt
        pick("image")

    # ================================================================ diagnostics
    def run_diagnostics(self):
        """'Check my setup': quick tests, with a report you can copy and send."""
        top, b = self.dialog("Check my setup", 620, 600)
        tk.Label(b, text="Check my setup", bg=CHAT, fg=WHITE, font=(FONT, 14, "bold"),
                 anchor="w").pack(fill="x")
        box = tk.Text(b, bg=LOG_BG, fg=TEXT, font=("Consolas", 9), bd=0, height=24,
                      highlightthickness=0, wrap="word")
        box.pack(fill="both", expand=True, pady=10)
        lines = []

        def add(ok, text):
            mark = {True: "✔", False: "✘", None: "•"}[ok]
            lines.append(f"{mark} {text}")
            try:
                box.insert("end", f"{mark} {text}\n")
                box.see("end")
            except tk.TclError:
                pass

        def work():
            import platform
            self.after(0, lambda: add(None, f"{APP_NAME} {VERSION} · Windows "
                                            f"{platform.release()} · Python "
                                            f"{platform.python_version()}"))
            if self.demo is not None:
                self.after(0, lambda: add(None, "Demo mode: Discord checks skipped"))
            elif self.token_value:
                try:
                    me, st = core.get_me(self.make_api())
                    self.after(0, lambda: add(me is not None, "Discord answers and your token "
                                              "works" if me else f"Discord said {st}"))
                except Exception as e:
                    err = str(e)
                    self.after(0, lambda: add(False, f"Can't reach Discord: {err}"))
            for name, mod, why in (("Pillow", "PIL", "pictures"),
                                   ("OpenCV", "cv2", "videos and GIFs in the app"),
                                   ("pystray", "pystray", "icon next to the clock")):
                try:
                    __import__(mod)
                    ok = True
                except Exception:
                    ok = False
                self.after(0, lambda n=name, w=why, ok=ok: add(
                    ok, f"{n} ({w})" + ("" if ok else " is missing - rebuild with the script")))
            try:
                core.fetch_image(core.twemoji_url("👍"))
                emo = True
            except Exception:
                emo = False
            self.after(0, lambda: add(emo, "Emoji pictures load" if emo else
                                      "Emoji pictures can't load (offline or blocked)"))
            st, _info = logger_service.status(self.store())
            self.after(0, lambda: add(st.startswith("running") or None,
                                      f"Deleted-messages logger: {st}"))
            self.after(0, lambda: add(None, f"Live updates: "
                                            f"{'on' if self.live_stop else 'off'} · tray: "
                                            f"{'on' if self.tray else 'off'}"))
            try:
                import shutil
                free = shutil.disk_usage(msglog.data_dir()).free // (1024 ** 3)
                self.after(0, lambda: add(free > 1, f"Free disk space: {free} GB"))
            except OSError:
                pass
            self.after(0, lambda: add(None, "Done. Copy this report if you need help."))
        bar = tk.Frame(b, bg=CHAT)
        bar.pack(fill="x")

        def copy():
            self.clipboard_clear()
            self.clipboard_append("\n".join(lines))
            self.set_status("Report copied.")
        FlatButton(bar, "Copy report", copy, font_size=9, pady=6).pack(side="left")
        FlatButton(bar, "Close", top.destroy, bg=SELECTED, hover=HOVER, font_size=9,
                   pady=6).pack(side="right")
        threading.Thread(target=work, daemon=True).start()

    def msg_hover(self, info, on):
        if not on:
            w = self.winfo_containing(*self.winfo_pointerxy())
            if w is not None and (is_inside(w, info["row"]) or (
                    getattr(self, "_toolbar", None) is not None
                    and is_inside(w, self._toolbar))):
                return
        if info["hover"] == on:
            return
        info["hover"] = on
        self.hover_toolbar(info, on)
        bg = MSG_HOVER if on and info["matched"] is None and not info["mention"] else info["bg"]
        try:
            set_bg(info["row"], bg, skip=info["fixed"])
            if info["time"] is not None:
                info["time"].configure(fg=MUTED if on else bg)
        except tk.TclError:
            pass

    def on_chat_resize(self, e):
        if getattr(self, "_resize_job", None):
            self.after_cancel(self._resize_job)

        def apply():
            width = max(300, e.width - 230)
            for lbl in self.text_labels:
                try:
                    lbl.configure(wraplength=width)
                except tk.TclError:
                    pass
        self._resize_job = self.after(150, apply)

    def current_filter(self):
        """Filter from the current settings, ignoring invalid fields (for the preview)."""
        try:
            from_d = core.parse_date(self.from_date.get())
        except ValueError:
            from_d = None
        try:
            to_d = core.parse_date(self.to_date.get())
        except ValueError:
            to_d = None
        opts = core.Options(channel_id="", keywords=core.parse_keywords(self.keywords.get()),
                            case_sensitive=self.case_sensitive.get(),
                            match_mode=self.match_mode.get(), from_date=from_d, to_date=to_d,
                            skip_pinned=self.skip_pinned.get(), keep_ids=set(self.keep_ids),
                            has_files=self.has_files.get(), has_images=self.has_images.get(),
                            has_links=self.has_links.get(),
                            only_replies=self.only_replies.get(),
                            min_len=spin_int(self.min_len), max_len=spin_int(self.max_len),
                            older_than_days=spin_int(self.older_than))
        return core.MessageFilter(opts)

    # ---------------------------------------------------------------- right-click menu
    def message_menu(self, event, info):
        m = info["msg"]
        mine = self.me and m.get("author", {}).get("id") == self.me["id"] and \
            not (self.preview and self.preview.get("source") == "deleted")
        menu = tk.Menu(self, tearoff=0, bg=TIP_BG, fg=TEXT, activebackground=BLURPLE,
                       activeforeground="white", bd=0, font=(FONT, 9))
        if mine:
            menu.add_command(label="Delete this message", foreground=ERROR_FG,
                             command=lambda: self.delete_single(info))
            if m["id"] in self.keep_ids:
                menu.add_command(label="Remove from keep list",
                                 command=lambda: self.set_keep(m["id"], False))
            else:
                menu.add_command(label="Keep (never delete this one)",
                                 command=lambda: self.set_keep(m["id"], True))
            menu.add_separator()
        if self.preview and self.preview.get("source") == "deleted":
            mine = False
            menu.add_command(label="Remove from this list",
                             command=lambda: self.forget_deleted(m["id"]))
            menu.add_separator()
        menu.add_command(label="Copy text", command=lambda: self.copy_text(m))
        menu.add_command(label="Copy message ID", command=lambda: self.copy_text(m, True))
        if m.get("channel_id") and not str(m.get("id", "")).startswith("pkg"):
            menu.add_command(label="Copy message link", command=lambda: self.copy_link(m))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def copy_link(self, m):
        self.clipboard_clear()
        self.clipboard_append(core.message_link(m, self.channel_guild.get(m.get("channel_id"))))
        self.set_status(i18n.tr("Message link copied."))

    def update_title(self):
        n = sum(self.unread.values()) if getattr(self, "unread", None) else 0
        try:
            self.title((f"({n}) " if n else "") + f"{APP_NAME} v{VERSION}")
        except tk.TclError:
            pass

    def copy_text(self, m, msg_id=False):
        self.clipboard_clear()
        self.clipboard_append(m["id"] if msg_id else core.render_content(m))

    def set_keep(self, mid, keep):
        if keep:
            self.keep_ids.add(mid)
        else:
            self.keep_ids.discard(mid)
        write_json(app_data_file("keep.json"), sorted(self.keep_ids))
        self.refresh_highlights()
        self.set_status(f"{len(self.keep_ids)} message(s) in your keep list.")

    def delete_single(self, info):
        m = info["msg"]
        if self.running:
            messagebox.showinfo(APP_NAME, "Wait for the cleaner to finish first.")
            return
        if self.settings.get("undo_delete", True) is not False:
            self.delete_with_undo(info)
            return
        preview = core.render_content(m)[:120] or "[attachment]"
        if not messagebox.askyesno("Delete message?", f"Delete this message?\n\n{preview}\n\n"
                                   "This cannot be undone.", icon="warning"):
            return

        def work():
            try:
                st = core.delete_message(self.make_api(), m["channel_id"], m["id"])
            except Exception:
                st = 0
            self.after(0, lambda: self.on_single_deleted(info, st))
        threading.Thread(target=work, daemon=True).start()

    def on_single_deleted(self, info, st):
        if st in (200, 204, 404):
            self.log(f"Deleted 1 message: {core.render_content(info['msg'])[:60]}", "good")
            p = self.preview
            if p:
                p["msgs"] = [x for x in p["msgs"] if x["id"] != info["msg"]["id"]]
                if p.get("all"):
                    p["all"] = [x for x in p["all"] if x["id"] != info["msg"]["id"]]
                if p.get("count"):
                    p["count"] -= 1
                self.update_count_label()
                self.render_preview(scroll="keep")
        else:
            self.log(core.friendly_error(st, "delete that message"), "bad")
            messagebox.showerror(APP_NAME, core.friendly_error(st, "delete that message"))

    # ---------------------------------------------------------------- export
    def export_chat(self):
        """Export button: menu with the save options."""
        if not self.preview:
            return
        menu = tk.Menu(self, tearoff=0, bg=TIP_BG, fg=TEXT, activebackground=BLURPLE,
                       activeforeground="white", bd=0, font=(FONT, 9))
        only = tk.BooleanVar(value=bool(self.preview.get("only_mine")))
        menu.add_checkbutton(label="Show only my messages", variable=only,
                             command=lambda: self.set_only_mine(only.get()))
        menu.add_command(label="Find in this chat…   Ctrl+F", command=self.open_find)
        menu.add_command(label="Jump to a date…", command=self.jump_to_date)
        if self.preview.get("jumped"):
            menu.add_command(label="Jump to present", command=self.jump_to_present)
        menu.add_command(label="Statistics…", command=self.open_stats)
        if self.preview.get("source") == "live":
            menu.add_command(label="Media, files and links…", command=self.open_gallery)
        menu.add_separator()
        menu.add_command(label="Save whole conversation (offline, with pictures and files)",
                         command=self.save_open_chat)
        menu.add_separator()
        menu.add_command(label="Quick export as web page (.html)",
                         command=lambda: self.quick_export("html"))
        menu.add_command(label="Quick export as text (.txt)",
                         command=lambda: self.quick_export("txt"))
        try:
            x = self.export_btn.winfo_rootx()
            y = self.export_btn.winfo_rooty() + self.export_btn.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    # ---------------------------------------------------------------- find in chat
    def open_find(self):
        if self.main_frame is None or not self.preview:
            return
        if not self.find_bar.winfo_ismapped():
            self.find_bar.pack(fill="x", before=self.find_anchor)
        self.find_entry.focus_set()
        self.run_find()

    def close_find(self):
        self.find_bar.pack_forget()
        self.find_entry.set("")
        self.clear_find_marks()
        self.find_hits, self.find_pos = [], -1
        self.find_count.configure(text="")

    def on_find_key(self, e):
        if e.keysym == "Return":
            self.find_step(-1 if e.state & 0x1 else 1)
            return
        self.run_find()

    def clear_find_marks(self):
        for r in self.msg_rows:
            if r.get("found"):
                r["found"] = False
                r["matched"] = "unset"
        self.refresh_highlights()

    def run_find(self):
        q = self.find_entry.get().strip().lower()
        self.clear_find_marks()
        self.find_hits = [r for r in self.msg_rows
                          if q and q in (r["msg"].get("content") or "").lower()]
        self.find_pos = len(self.find_hits) - 1 if self.find_hits else -1
        for r in self.find_hits:
            r["found"] = True
            try:
                r["bar"].configure(bg=MENTION_BAR)
            except tk.TclError:
                pass
        self.show_find_pos()

    def find_step(self, d):
        if not self.find_hits:
            return
        self.find_pos = (self.find_pos + d) % len(self.find_hits)
        self.show_find_pos()

    def show_find_pos(self):
        q = self.find_entry.get().strip()
        if not q:
            self.find_count.configure(text="")
            return
        if not self.find_hits:
            self.find_count.configure(
                text=i18n.tr("No matches here. Try 'Search the whole chat'."))
            return
        self.find_count.configure(text=f"{self.find_pos + 1}/{len(self.find_hits)}")
        for i, r in enumerate(self.find_hits):
            try:
                set_bg(r["row"], SELECTED if i == self.find_pos else r["bg"], skip=r["fixed"])
            except tk.TclError:
                pass
        self.scroll_to_row(self.find_hits[self.find_pos]["row"])

    def scroll_to_row(self, row):
        try:
            self.messages.update_idletasks()
            total = max(1, self.messages.inner.winfo_height())
            y = max(0, row.winfo_y() - 120)
            self.messages.canvas.yview_moveto(y / total)
        except (tk.TclError, TypeError):
            pass

    def find_everywhere(self):
        """Search the whole chat with Discord search (or the data package) and list results."""
        p = self.preview
        q = self.find_entry.get().strip()
        if not p or not q:
            return
        top, b = self.dialog(f"Search: {q}", 620, 560)
        status = tk.Label(b, text="Loading…", bg=CHAT, fg=MUTED, font=(FONT, 10))
        status.pack(anchor="w")
        res = ScrollFrame(b, CHAT)
        res.pack(fill="both", expand=True, pady=(8, 0))

        def work():
            if p.get("source") in LOCAL:
                words = core.parse_search(q, self.chat_people(), (self.me or {}).get("id"))[0]
                hits = [m for m in reversed(p["all"])
                        if words.lower() in (m["content"] or "").lower()]
                total = len(hits)
            else:
                gid = self.channel_guild.get(p["channel_id"]) if p["key"][0] == "channel" \
                    else None
                total, hits = core.search_text(self.make_api(), p["channel_id"], q, gid,
                                               people=self.chat_people(),
                                               me_id=(self.me or {}).get("id"))
            self.after(0, lambda: show(total, hits))

        def show(total, hits):
            if not top.winfo_exists():
                return
            if total is None:
                status.configure(text="Discord search isn't available in this chat.")
                return
            status.configure(text=i18n.tr(f"{total:,} result(s)"))
            for m in hits[:100]:
                row = tk.Frame(res.inner, bg=SIDEBAR, padx=10, pady=6, cursor="hand2")
                row.pack(fill="x", pady=2)
                a = m.get("author") or {}
                tk.Label(row, notr=True, text=f"{a.get('global_name') or a.get('username', '?')}"
                         f"   {core.format_time(m.get('timestamp'))}", bg=SIDEBAR, fg=MUTED,
                         font=(FONT, 8), anchor="w").pack(fill="x")
                tk.Label(row, notr=True, text=core.render_content(m)[:200], bg=SIDEBAR, fg=TEXT,
                         font=(FONT, 9), anchor="w", justify="left", wraplength=540).pack(
                    fill="x")
                for w in (row,) + tuple(row.winfo_children()):
                    w.bind("<Button-1>", lambda e, m=m: (top.destroy(), self.jump_to_message(m)))
        threading.Thread(target=work, daemon=True).start()

    def jump_to_message(self, m):
        p = self.preview
        if not p:
            return
        p["jumped"] = True
        if p.get("source") in LOCAL:
            ids = [x["id"] for x in p["all"]]
            i = ids.index(m["id"]) if m["id"] in ids else len(ids) - 1
            p["msgs"] = p["all"][max(0, i - 25):i + 25]
            p["more"] = i - 25 > 0
            self.render_preview(scroll="bottom")
            self.mark_jump_target(m["id"])
            return

        def work():
            st, msgs = core.fetch_around(self.make_api(), p["channel_id"], m["id"])
            self.after(0, lambda: done(st, msgs))

        def done(st, msgs):
            if st != 200 or not msgs:
                self.set_status(core.friendly_error(st, "load this chat"))
                return
            p["msgs"] = list(reversed(msgs))
            p["more"] = True
            self.render_preview(scroll="bottom")
            self.mark_jump_target(m["id"])
        threading.Thread(target=work, daemon=True).start()

    def mark_jump_target(self, mid):
        for r in self.msg_rows:
            if r["msg"]["id"] == mid:
                try:
                    r["bar"].configure(bg=MENTION_BAR)
                    set_bg(r["row"], SELECTED, skip=r["fixed"])
                except tk.TclError:
                    pass
                self.after(50, lambda r=r: self.scroll_to_row(r["row"]))
                break

    # ---------------------------------------------------------------- preview tools
    def set_only_mine(self, on):
        if self.preview:
            self.preview["only_mine"] = on
            self.render_preview(scroll="bottom")

    def jump_to_date(self):
        from tkinter import simpledialog
        p = self.preview
        if not p:
            return
        text = simpledialog.askstring("Jump to a date", "Show messages from which day?\n"
                                      "(YYYY-MM-DD, e.g. 2025-06-15)", parent=self)
        if not text:
            return
        try:
            day = core.parse_date(text)
        except ValueError:
            messagebox.showerror(APP_NAME, "Dates must look like 2025-06-15")
            return
        if not day:
            return
        cut = core.date_to_snowflake(day + core.timedelta(days=1))
        p["jumped"] = True
        if p.get("source") in LOCAL:
            older = [m for m in p["all"] if int(m["id"]) < cut]
            p["msgs"] = older[-PREVIEW_PAGE:]
            p["more"] = len(older) > PREVIEW_PAGE
            self.render_preview(scroll="bottom")
            return
        p["jump_pending"] = True
        self.messages.clear()
        tk.Label(self.messages.inner, text="Loading…", bg=CHAT, fg=MUTED,
                 font=(FONT, 10)).pack(pady=40)
        self.fetch_preview(str(cut))

    def jump_to_present(self):
        p = self.preview
        if not p:
            return
        p["jumped"] = False
        if p.get("source") in LOCAL:
            p["msgs"] = []
            self.show_pkg_page()
        else:
            self.open_chat(p["key"], p["channel_id"], p["title"], p["icon"], p["avatar"],
                           p["user_id"], p["server"])

    # ---------------------------------------------------------------- statistics
    def open_stats(self):
        p = self.preview
        if not p:
            return
        top, b = self.dialog(f"Statistics · {p['title']}", 720, 640)
        status = tk.Label(b, text="Loading every message of this chat…", bg=CHAT, fg=MUTED,
                          font=(FONT, 10))
        status.pack(pady=40)

        def work():
            try:
                if p.get("source") in LOCAL:
                    msgs = list(p["all"])
                else:
                    msgs = self.messages_to_save(
                        p["channel_id"], self.make_api(),
                        progress=lambda n: self.after(0, lambda: status.winfo_exists() and
                                                      status.configure(
                                                          text=f"Loading… {n:,} messages")))
                st = core.chat_stats(msgs, self.me["id"])
                self.after(0, lambda: self.show_stats(top, b, p["title"], st))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: status.winfo_exists() and status.configure(
                    text=f"Could not load: {msg}"))
        threading.Thread(target=work, daemon=True).start()

    def show_stats(self, top, b, title, st):
        if not top.winfo_exists():
            return
        for w in b.winfo_children():
            w.destroy()
        tk.Label(b, notr=True, text=title, bg=CHAT, fg=WHITE, font=(FONT, 15, "bold"),
                 anchor="w").pack(fill="x")
        span = (f"{st['first']:%b %d, %Y} → {st['last']:%b %d, %Y}" if st["first"] else "")
        tk.Label(b, text=span, bg=CHAT, fg=MUTED, font=(FONT, 9), anchor="w").pack(fill="x")
        cards = tk.Frame(b, bg=CHAT)
        cards.pack(fill="x", pady=(12, 4))
        for label, value in (("Messages", st["total"]), ("Yours", st["mine"]),
                             ("Yours with files", st["with_files"]),
                             ("Characters you typed", st["chars"])):
            c = tk.Frame(cards, bg=SIDEBAR, padx=14, pady=10)
            c.pack(side="left", padx=(0, 8), fill="x", expand=True)
            tk.Label(c, text=f"{value:,}", bg=SIDEBAR, fg=WHITE, font=(FONT, 16, "bold")).pack(
                anchor="w")
            tk.Label(c, text=label, bg=SIDEBAR, fg=MUTED, font=(FONT, 8)).pack(anchor="w")
        if st["months"]:
            section_label(b, "Messages per month (yours in blue)", CHAT).pack(
                anchor="w", pady=(14, 4))
            self.bar_chart(b, [(k[2:].replace("-", "/"), all_, mine)
                               for k, mine, all_ in st["months"][-24:]], 170)
        low = tk.Frame(b, bg=CHAT)
        low.pack(fill="both", expand=True, pady=(12, 0))
        left = tk.Frame(low, bg=CHAT)
        left.pack(side="left", fill="both", expand=True)
        section_label(left, "Your most used words", CHAT).pack(anchor="w", pady=(0, 4))
        words = st["top_words"][:12]
        if words:
            for w, n in words:
                r = tk.Frame(left, bg=CHAT)
                r.pack(fill="x")
                tk.Label(r, notr=True, text=w, bg=CHAT, fg=TEXT, font=(FONT, 9), anchor="w").pack(
                    side="left")
                tk.Label(r, text=f"{n:,}", bg=CHAT, fg=MUTED, font=(FONT, 9)).pack(side="right",
                                                                                padx=20)
        else:
            tk.Label(left, text="Not enough text.", bg=CHAT, fg=MUTED, font=(FONT, 9)).pack(
                anchor="w")
        right = tk.Frame(low, bg=CHAT)
        right.pack(side="left", fill="both", expand=True)
        section_label(right, "When you write (hour of day)", CHAT).pack(anchor="w",
                                                                        pady=(0, 4))
        self.bar_chart(right, [(str(h) if h % 6 == 0 else "", 0, n)
                               for h, n in enumerate(st["hours"])], 110, width=330)
        if st["weekdays"]:
            tk.Label(right, text=f"Busiest day: {i18n.day_name(st['weekdays'][0][0])}", bg=CHAT,
                     fg=TEXT,
                     font=(FONT, 9)).pack(anchor="w", pady=(6, 0))

    def bar_chart(self, parent, bars, height, width=660):
        """bars: [(label, background_value, value)] drawn as Discord-coloured bars."""
        c = tk.Canvas(parent, width=width, height=height + 18, bg=CHAT, highlightthickness=0)
        c.pack(anchor="w")
        top = max([max(a, v) for _, a, v in bars] + [1])
        n = max(1, len(bars))
        bw = width / n
        for i, (label, back, val) in enumerate(bars):
            x0, x1 = i * bw + 2, (i + 1) * bw - 2
            if back:
                c.create_rectangle(x0, height - back / top * height, x1, height, fill=SELECTED,
                                   outline="")
            if val:
                c.create_rectangle(x0, height - val / top * height, x1, height, fill=BLURPLE,
                                   outline="")
            if label:
                c.create_text((x0 + x1) / 2, height + 9, text=label, fill=MUTED,
                              font=(FONT, 7))

    def conversations_dir(self):
        return os.path.join(default_backup_dir(), "Conversations")

    def preview_messages_for_save(self, p):
        if p.get("source") == "deleted":
            return list(p["all"])
        return None   # always try the full live chat first (falls back to the package)

    def save_open_chat(self):
        p = self.preview
        base = filedialog.askdirectory(title="Where should the conversation be saved?",
                                       initialdir=self.conversations_dir()
                                       if os.path.isdir(self.conversations_dir()) else None)
        if not base:
            return
        self.save_conversations([(p["channel_id"], self.preview_title(p),
                                  self.preview_messages_for_save(p))], base)

    def preview_title(self, p):
        t = p["title"]
        if p.get("icon") == "#" and not t.startswith("#"):
            t = "#" + t
        return t + (f" ({p['server']})" if p.get("server") and p.get("source") != "pkg"
                    else "")

    def save_selected(self):
        """Save every ticked chat (not whole servers) to a folder."""
        items, skipped = [], 0
        for t in self.checked.values():
            if t["kind"] == "server":
                skipped += 1
                continue
            items.append((t["id"], t["name"] or f"Chat {t['id']}", None))
        if not items:
            messagebox.showinfo(APP_NAME, "Tick some DMs or channels first. "
                                          "(Whole servers are too big to save as one chat.)")
            return
        base = filedialog.askdirectory(title="Where should the conversations be saved?")
        if not base:
            return
        if skipped:
            self.log(f"Skipped {skipped} whole server(s): save their channels one by one.",
                     "dim")
        self.save_conversations(items, base)

    def save_conversations(self, items, base, then=None):
        """items: [(channel_id, title, messages or None)]. Runs in the background."""
        self.set_status(f"Saving {len(items)} conversation(s)…")

        def work():
            done, last = 0, None
            for cid, title, msgs in items:
                try:
                    if msgs is None:
                        msgs = self.messages_to_save(
                            cid, self.make_api(), progress=lambda n, title=title: self.after(
                                0, lambda: self.set_status(f"Saving {title}: loading {n:,}")))
                    folder, n, files = core.save_conversation(
                        self.make_api(), cid, title, base, log=self.log,
                        progress=lambda t, title=title: self.after(
                            0, lambda: self.set_status(f"Saving {title}: {t}")),
                        messages=msgs)
                    if n == 0:
                        self.log(f"{title}: no messages could be read (no access or empty).",
                                 "dim")
                    else:
                        self.log(f"Saved {title}: {n:,} messages, {files} files → {folder}",
                                 "good")
                        done += 1
                        last = folder
                except Exception as e:
                    self.log(f"Could not save {title}: {e}", "bad")
            self.after(0, lambda: self.on_saved(done, len(items), last, then))
        threading.Thread(target=work, daemon=True).start()

    def on_saved(self, done, total, last, then):
        self.set_status(f"Saved {done} of {total} conversation(s).")
        if then:
            then()
            return
        if last and messagebox.askyesno(
                APP_NAME, f"Saved {done} of {total} conversation(s).\n\nOpen the folder?"):
            open_path(last if total == 1 else os.path.dirname(last))

    def quick_export(self, kind):
        p = self.preview
        if not p:
            return
        safe = core.safe_name(p["title"])
        path = filedialog.asksaveasfilename(
            title="Export chat", initialfile=f"{safe}.{kind}", defaultextension="." + kind,
            filetypes=[("Web page (looks like Discord)", "*.html")] if kind == "html"
            else [("Text file", "*.txt")])
        if not path:
            return
        title = self.preview_title(p)
        self.set_status("Exporting…")

        def work():
            try:
                if p.get("source") in LOCAL:
                    msgs = list(p["all"])
                else:
                    msgs = core.fetch_all_messages(
                        self.make_api(), p["channel_id"],
                        lambda n: self.after(0, lambda: self.set_status(
                            f"Exporting… {n:,} messages loaded")))
                if path.lower().endswith(".txt"):
                    core.export_txt(msgs, title, path)
                else:
                    core.export_html(msgs, title, path)
                self.after(0, lambda: self.on_exported(path, len(msgs)))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self.log(f"Export failed: {msg}", "bad"))
        threading.Thread(target=work, daemon=True).start()

    def on_exported(self, path, n):
        self.set_status(f"Exported {n:,} messages.")
        self.log(f"Exported {n:,} messages to {path}", "good")
        if messagebox.askyesno(APP_NAME, f"Exported {n:,} messages.\n\nOpen the file now?"):
            webbrowser.open("file:///" + os.path.abspath(path).replace("\\", "/"))

    def refresh_highlights(self, *_):
        if not self.msg_rows or not self.me:
            if self.preview:
                self.chat_sub.configure(text=self.preview.get("server") or "")
            return
        flt = self.current_filter()
        my_id = self.me["id"]
        clean = self.clean_mode()
        count = mine = 0
        for r in self.msg_rows:
            m = r["msg"]
            is_mine = m.get("author", {}).get("id") == my_id
            mine += is_mine
            if m.get("_deleted"):
                state = "removed"
            elif not clean:
                state = None
            elif is_mine and m.get("id") in self.keep_ids:
                state = "keep"
            elif flt.matches(m, my_id) and flt.in_dates(m):
                state = "match"
            else:
                state = None
            count += state == "match"
            if state == r["matched"]:
                continue
            r["matched"] = state
            look = state or ("mention" if r.get("mention") else None)
            bg = {"match": MATCH_BG, "keep": KEEP_BG, "mention": MENTION_BG,
                  "removed": MATCH_BG}.get(look, CHAT)
            r["bg"] = bg
            r["hover"] = False
            try:
                set_bg(r["row"], bg, skip=r.get("fixed", (r["bar"],)))
                if r.get("time") is not None:
                    r["time"].configure(fg=bg)
                r["bar"].configure(bg={"match": RED, "keep": GREEN, "mention": MENTION_BAR,
                                       "removed": RED}.get(look, CHAT))
                if state:
                    r["tag"].configure(
                        text={"match": "WILL BE DELETED", "keep": "KEPT"}.get(
                            state, i18n.tr("DELETED") + " " + m.get("_deleted_at", "")),
                        fg=GREEN if state == "keep" else RED)
                    r["tag"].pack(side="right", anchor="n", padx=12, pady=4,
                                  before=r["content"])
                else:
                    r["tag"].pack_forget()
            except tk.TclError:
                pass
        server = self.preview.get("server") if self.preview else None
        self.chat_sub.configure(
            text=(f"{server}   •   " if server else "")
            + i18n.tr(f"{len(self.msg_rows)} shown  •  {mine} yours  •  "
                      f"{count} match your filters"))

    def schedule_highlight(self, *_):
        if getattr(self, "_hl_job", None):
            self.after_cancel(self._hl_job)
        self._hl_job = self.after(250, self.refresh_highlights)

    # ================================================================ cleaner panel
    def build_cleaner(self):
        c = self.cleaner
        head = tk.Frame(c, bg=SIDEBAR, height=48)
        head.pack(fill="x")
        head.pack_propagate(False)
        tk.Frame(c, bg=BORDER, height=1).pack(fill="x")
        tk.Label(head, text="Cleaner", bg=SIDEBAR, fg=WHITE, font=(FONT, 11, "bold")).pack(
            side="left", padx=16)
        LinkLabel(head, "Help", lambda: messagebox.showinfo("Help", HELP_TEXT), SIDEBAR,
                  fg=MUTED).pack(side="right", padx=16)

        self.cleaner_scroll = ScrollFrame(c, SIDEBAR)
        self.cleaner_scroll.pack(fill="both", expand=True)
        body = tk.Frame(self.cleaner_scroll.inner, bg=SIDEBAR)
        body.pack(fill="both", expand=True, padx=14, pady=10)

        # selected
        top = tk.Frame(body, bg=SIDEBAR)
        top.pack(fill="x")
        self.sel_title = section_label(top, "Selected (0)")
        self.sel_title.pack(side="left")
        LinkLabel(top, "Clear", self.clear_selection, SIDEBAR, font_size=8).pack(side="right")
        LinkLabel(top, "Save chats", self.save_selected, SIDEBAR, font_size=8).pack(
            side="right", padx=(0, 10))
        self.chips = ScrollFrame(body, INPUT, height=112)
        self.chips.pack(fill="x", pady=(6, 6))
        self.chips.canvas.configure(height=112)
        lrow = tk.Frame(body, bg=SIDEBAR)
        lrow.pack(fill="x")
        box, self.link_entry = entry_box(lrow, "Add by link (closed DMs)", font_size=9)
        box.pack(side="left", fill="x", expand=True)
        self.link_entry.bind("<Return>", lambda e: self.add_by_link())
        FlatButton(lrow, "Add", self.add_by_link, bg=SELECTED, hover=HOVER, font_size=9,
                   padx=12, pady=6).pack(side="left", padx=(6, 0))

        # which messages
        section_label(body, "Which messages").pack(anchor="w", pady=(16, 6))
        box, self.keywords = entry_box(body, "Keywords, e.g. hello, hi  (empty = all)",
                                       font_size=9)
        box.pack(fill="x")
        self.keywords_box = box
        self.keywords.bind("<KeyRelease>", self.schedule_highlight)
        self.case_sensitive = tk.BooleanVar(value=False)
        self.match_mode = tk.StringVar(value="whole")
        self.skip_pinned = tk.BooleanVar(value=True)
        seg = tk.Frame(body, bg=SIDEBAR)
        seg.pack(fill="x", pady=(6, 0))
        tk.Label(seg, text="Match", bg=SIDEBAR, fg=TEXT, font=(FONT, 9)).pack(side="left",
                                                                               padx=(0, 8))
        self.mode_buttons = {}
        for mode, label in core.MATCH_MODES.items():
            b = tk.Label(seg, text=label, bg=INPUT, fg=TEXT, font=(FONT, 8, "bold"), padx=9,
                         pady=4, cursor="hand2")
            b.pack(side="left", padx=(0, 2))
            b.bind("<Button-1>", lambda e, m=mode: self.set_match_mode(m))
            self.mode_buttons[mode] = b
        self.mode_hint = tk.Label(body, text="", bg=SIDEBAR, fg=MUTED, font=(FONT, 8),
                                  anchor="w")
        self.mode_hint.pack(fill="x", pady=(3, 0))
        r = tk.Frame(body, bg=SIDEBAR)
        r.pack(fill="x", pady=(4, 0))
        OptionCheck(r, "Caps matter", self.case_sensitive, SIDEBAR,
                    command=self.schedule_highlight).pack(side="left")
        OptionCheck(r, "Keep pinned messages", self.skip_pinned, SIDEBAR,
                    command=self.schedule_highlight).pack(side="left", padx=(14, 0))
        self.keywords.bind("<KeyRelease>", lambda e: self.update_mode_buttons(), add="+")

        d = tk.Frame(body, bg=SIDEBAR)
        d.pack(fill="x", pady=(8, 0))
        box, self.from_date = entry_box(d, "From YYYY-MM-DD", font_size=9, width=14)
        box.pack(side="left", fill="x", expand=True)
        tk.Label(d, text="→", bg=SIDEBAR, fg=MUTED).pack(side="left", padx=6)
        box, self.to_date = entry_box(d, "To YYYY-MM-DD", font_size=9, width=14)
        box.pack(side="left", fill="x", expand=True)
        self.from_date.bind("<KeyRelease>", self.schedule_highlight)
        self.to_date.bind("<KeyRelease>", self.schedule_highlight)

        n = tk.Frame(body, bg=SIDEBAR)
        n.pack(fill="x", pady=(8, 0))
        self.max_delete = self.spin(n, 0, 1000000, 1, 8)
        tk.Label(n, text="Max per chat", bg=SIDEBAR, fg=TEXT, font=(FONT, 9)).pack(side="left")
        self.max_delete.pack(side="left", padx=(8, 6))
        tk.Label(n, text="0 = all", bg=SIDEBAR, fg=MUTED, font=(FONT, 8)).pack(side="left")

        self.has_files = tk.BooleanVar(value=False)
        self.has_images = tk.BooleanVar(value=False)
        self.has_links = tk.BooleanVar(value=False)
        self.only_replies = tk.BooleanVar(value=False)
        more_link = LinkLabel(body, "More filters ▸", lambda: self.toggle_more_filters(),
                              SIDEBAR, font_size=8)
        more_link.pack(anchor="w", pady=(8, 0))
        self.more_link = more_link
        mf = self.more_filters = tk.Frame(body, bg=SIDEBAR)
        r1 = tk.Frame(mf, bg=SIDEBAR)
        r1.pack(fill="x", pady=(4, 0))
        OptionCheck(r1, "With files", self.has_files, SIDEBAR,
                    command=self.schedule_highlight).pack(side="left")
        OptionCheck(r1, "With pictures", self.has_images, SIDEBAR,
                    command=self.schedule_highlight).pack(side="left", padx=(12, 0))
        r2 = tk.Frame(mf, bg=SIDEBAR)
        r2.pack(fill="x", pady=(4, 0))
        OptionCheck(r2, "With links", self.has_links, SIDEBAR,
                    command=self.schedule_highlight).pack(side="left")
        OptionCheck(r2, "Only replies", self.only_replies, SIDEBAR,
                    command=self.schedule_highlight).pack(side="left", padx=(12, 0))
        r3 = tk.Frame(mf, bg=SIDEBAR)
        r3.pack(fill="x", pady=(6, 0))
        tk.Label(r3, text="Length", bg=SIDEBAR, fg=TEXT, font=(FONT, 9)).pack(side="left")
        self.min_len = self.spin(r3, 0, 4000, 1, 5)
        self.min_len.pack(side="left", padx=(8, 4))
        tk.Label(r3, text="to", bg=SIDEBAR, fg=MUTED, font=(FONT, 8)).pack(side="left")
        self.max_len = self.spin(r3, 0, 4000, 1, 5)
        self.max_len.pack(side="left", padx=4)
        tk.Label(r3, text="characters (0 = any)", bg=SIDEBAR, fg=MUTED, font=(FONT, 8)).pack(
            side="left")
        r4 = tk.Frame(mf, bg=SIDEBAR)
        r4.pack(fill="x", pady=(6, 0))
        tk.Label(r4, text="Older than", bg=SIDEBAR, fg=TEXT, font=(FONT, 9)).pack(side="left")
        self.older_than = self.spin(r4, 0, 36500, 1, 6)
        self.older_than.pack(side="left", padx=(8, 4))
        tk.Label(r4, text="days (0 = any)", bg=SIDEBAR, fg=MUTED, font=(FONT, 8)).pack(
            side="left")
        for sp in (self.min_len, self.max_len, self.older_than):
            sp.bind("<KeyRelease>", self.schedule_highlight)
            sp.configure(command=self.schedule_highlight)

        # options
        section_label(body, "Options").pack(anchor="w", pady=(16, 6))
        o = tk.Frame(body, bg=SIDEBAR)
        o.pack(fill="x")
        tk.Label(o, text="Delay", bg=SIDEBAR, fg=TEXT, font=(FONT, 9)).pack(side="left")
        self.delay = self.spin(o, 0.5, 30, 0.5, 5)
        self.delay.pack(side="left", padx=(6, 4))
        tk.Label(o, text="sec", bg=SIDEBAR, fg=MUTED, font=(FONT, 8)).pack(side="left")
        self.parallel = self.spin(o, 1, 5, 1, 3)
        tk.Label(o, text="chats at once", bg=SIDEBAR, fg=MUTED, font=(FONT, 8)).pack(
            side="right")
        self.parallel.pack(side="right", padx=(6, 4))
        tk.Label(o, text="Run", bg=SIDEBAR, fg=TEXT, font=(FONT, 9)).pack(side="right")
        self.dry_run = tk.BooleanVar(value=True)
        self.backup = tk.BooleanVar(value=True)
        OptionCheck(body, "Preview only (delete nothing)", self.dry_run, SIDEBAR,
                    command=self.update_start_button).pack(anchor="w", pady=(8, 0))
        self.save_first = tk.BooleanVar(value=False)
        sf = OptionCheck(body, "Save whole conversations before deleting", self.save_first,
                         SIDEBAR)
        sf.pack(anchor="w", pady=(4, 0))
        Tooltip(sf, lambda: "Saves everyone's messages + pictures/files to "
                            "Documents\\Discord Cleaner Backups\\Conversations first")
        OptionCheck(body, "Back up deleted messages", self.backup, SIDEBAR).pack(
            anchor="w", pady=(4, 0))
        self.remove_reactions = tk.BooleanVar(value=False)
        self.close_dms = tk.BooleanVar(value=False)
        rr = OptionCheck(body, "Also remove my reactions", self.remove_reactions, SIDEBAR)
        rr.pack(anchor="w", pady=(4, 0))
        Tooltip(rr, lambda: "Takes your reactions off everyone's messages (reads the whole chat)")
        OptionCheck(body, "Close DMs / leave group DMs when done", self.close_dms,
                    SIDEBAR).pack(anchor="w", pady=(4, 0))
        self.auto_speed = tk.BooleanVar(value=True)
        self.use_search = tk.BooleanVar(value=True)
        r2 = tk.Frame(body, bg=SIDEBAR)
        r2.pack(fill="x", pady=(4, 0))
        a = OptionCheck(r2, "Auto speed", self.auto_speed, SIDEBAR)
        a.pack(side="left")
        Tooltip(a, lambda: "Slows down when Discord limits you, speeds up again after")
        b = OptionCheck(r2, "Use search (faster)", self.use_search, SIDEBAR)
        b.pack(side="left", padx=(14, 0))
        Tooltip(b, lambda: "Find only your messages with Discord search instead of reading "
                           "the whole chat")

        FlatButton(body, "Auto-clean rules…", self.open_rules, bg=SELECTED, hover=HOVER,
                   font_size=9, pady=5).pack(anchor="w", pady=(10, 0))

        # run
        btns = tk.Frame(body, bg=SIDEBAR)
        btns.pack(fill="x", pady=(14, 8))
        self.start_btn = FlatButton(btns, "Preview", self.start, font_size=11, pady=9)
        self.start_btn.pack(side="left", fill="x", expand=True)
        self.pause_btn = FlatButton(btns, "Pause", self.toggle_pause, bg=SELECTED, hover=HOVER,
                                    font_size=11, pady=9)
        self.pause_btn.pack(side="left", padx=(8, 0))
        self.pause_btn.set_enabled(False)
        self.stop_btn = FlatButton(btns, "Stop", self.stop, bg=RED, hover=RED_HI,
                                   font_size=11, pady=9)
        self.stop_btn.pack(side="left", padx=(8, 0))
        self.stop_btn.set_enabled(False)

        self.status = tk.Label(body, text="Ready.", bg=SIDEBAR, fg=TEXT,
                               font=(FONT, 9, "bold"), anchor="w", justify="left",
                               wraplength=330)
        self.status.pack(fill="x")
        self.progress = ttk.Progressbar(body, mode="determinate")
        self.progress.pack(fill="x", pady=(6, 8))

        lg = tk.Frame(body, bg=SIDEBAR)
        lg.pack(fill="x")
        section_label(lg, "Log").pack(side="left")
        for txt, cmd in (("Save", self.save_log), ("Clear", self.clear_log),
                         ("Backups", self.open_backups)):
            LinkLabel(lg, txt, cmd, SIDEBAR, font_size=8).pack(side="right", padx=(8, 0))
        self.out = tk.Text(body, height=10, state="disabled", bg=LOG_BG, fg=TEXT,
                           insertbackground=TEXT, relief="flat", font=("Consolas", 8),
                           bd=8, highlightthickness=0, wrap="word")
        self.out.pack(fill="both", expand=True, pady=(4, 0))
        self.out.tag_configure("good", foreground=GOOD_FG)
        self.out.tag_configure("bad", foreground=ERROR_FG)
        self.out.tag_configure("dim", foreground=MUTED)
        for line, tag in self.pending_log:
            self._write_log(line, tag)
        self.pending_log = []

        self.apply_settings()
        self.update_start_button()

    pending_log = []

    def toggle_more_filters(self):
        if self.more_filters.winfo_ismapped():
            self.more_filters.pack_forget()
            self.more_link.configure(text="More filters ▸")
        else:
            self.more_filters.pack(fill="x", after=self.more_link)
            self.more_link.configure(text="More filters ▾")

    def set_match_mode(self, mode):
        self.match_mode.set(mode)
        self.update_mode_buttons()
        self.schedule_highlight()

    def update_mode_buttons(self):
        cur = self.match_mode.get()
        for mode, b in self.mode_buttons.items():
            b.configure(bg=BLURPLE if mode == cur else INPUT,
                        fg="white" if mode == cur else TEXT)
        k = (core.parse_keywords(self.keywords.get()) or ["hello"])[0]
        examples = {"whole": f'"{k}" finds  {k}, {k}!   but not  {k}s',
                    "starts": f'"{k}" finds  {k}, {k}s, {k}oo   but not  x{k}',
                    "anywhere": f'"{k}" finds  {k}, {k}s, x{k}   (anywhere in a word)'}
        self.mode_hint.configure(text=examples[cur])

    def spin(self, master, lo, hi, inc, width):
        return tk.Spinbox(master, from_=lo, to=hi, increment=inc, width=width, bg=INPUT,
                          fg=TEXT, insertbackground=TEXT, relief="flat", bd=4,
                          buttonbackground=SELECTED, highlightthickness=0,
                          font=(FONT, 9))

    def set_spin(self, sp, value):
        sp.delete(0, "end")
        sp.insert(0, str(value))

    def clear_selection(self):
        if self.running:
            return
        self.checked.clear()
        self.on_selection_changed()

    def update_start_button(self):
        if self.dry_run.get():
            self.start_btn.configure(text="Preview")
            self.start_btn.set_colors(BLURPLE, BLURPLE_HI)
        else:
            self.start_btn.configure(text="Delete messages")
            self.start_btn.set_colors(RED, RED_HI)

    def set_status(self, text):
        try:
            self.status.configure(text=text)
        except (tk.TclError, AttributeError):
            pass

    # ================================================================ settings
    def load_settings(self):
        try:
            with open(settings_path(), encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_settings(self):
        # The token is deliberately NOT saved.
        # Start from everything already saved (theme, language, logger, accounts…), then
        # overwrite with what's currently in the window.
        data = {k: v for k, v in self.settings.items() if v is not None}
        if self.main_frame is not None:
            try:
                data.update({
                    "keywords": self.keywords.get(), "case_sensitive": self.case_sensitive.get(),
                    "match_mode": self.match_mode.get(), "max_delete": self.max_delete.get(),
                    "save_first": self.save_first.get(),
                    "remove_reactions": self.remove_reactions.get(),
                    "close_dms": self.close_dms.get(), "has_files": self.has_files.get(),
                    "has_images": self.has_images.get(), "has_links": self.has_links.get(),
                    "only_replies": self.only_replies.get(), "min_len": self.min_len.get(),
                    "max_len": self.max_len.get(), "older_than_days": self.older_than.get(),
                    "delay": self.delay.get(), "parallel": self.parallel.get(),
                    "skip_pinned": self.skip_pinned.get(), "backup": self.backup.get(),
                    "auto_speed": self.auto_speed.get(), "use_search": self.use_search.get()})
            except tk.TclError:
                pass
        else:
            data.update({k: v for k, v in self.settings.items() if k not in data})
        self.settings = data
        try:
            os.makedirs(os.path.dirname(settings_path()), exist_ok=True)
            with open(settings_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass

    def apply_settings(self):
        s = self.settings
        self.keywords.set(s.get("keywords", ""))
        self.case_sensitive.set(s.get("case_sensitive", False))
        mode = s.get("match_mode") or ("whole" if s.get("whole_word", True) else "anywhere")
        self.match_mode.set(mode if mode in core.MATCH_MODES else "whole")
        self.update_mode_buttons()
        self.save_first.set(s.get("save_first", False))
        self.remove_reactions.set(s.get("remove_reactions", False))
        self.close_dms.set(s.get("close_dms", False))
        for var, key in ((self.has_files, "has_files"), (self.has_images, "has_images"),
                         (self.has_links, "has_links"), (self.only_replies, "only_replies")):
            var.set(s.get(key, False))
        self.set_spin(self.min_len, s.get("min_len", "0"))
        self.set_spin(self.max_len, s.get("max_len", "0"))
        self.set_spin(self.older_than, s.get("older_than_days", "0"))
        if any(s.get(k) for k in ("has_files", "has_images", "has_links", "only_replies")) or \
                spin_int(self.min_len) or spin_int(self.max_len) or spin_int(self.older_than):
            self.toggle_more_filters()
        self.set_spin(self.max_delete, s.get("max_delete", "0"))
        self.set_spin(self.delay, s.get("delay", "1.5"))
        self.set_spin(self.parallel, s.get("parallel", "2"))
        self.skip_pinned.set(s.get("skip_pinned", True))
        self.backup.set(s.get("backup", True))
        self.auto_speed.set(s.get("auto_speed", True))
        self.use_search.set(s.get("use_search", True))

    def first_run_check(self):
        if not self.settings.get("accepted_terms"):
            if messagebox.askyesno(APP_NAME, DISCLAIMER, icon="warning"):
                self.settings["accepted_terms"] = True
                self.save_settings()
            else:
                self.destroy()

    # ================================================================ first-time tour
    TOUR = [
        ("rail", "Your DMs and servers",
         "Click a server to see its channels. The top icon is your DMs, the green one is your "
         "Discord data package (every chat you ever used)."),
        ("side_body", "Tick what to clean",
         "Use the boxes next to the names. Click a name to read the chat in the middle. "
         "Tick 'Clean the whole server' at the top of a server to clean all of it."),
        ("chat", "Preview the chat",
         "Your messages that would be deleted are red. Right-click a message to delete or keep "
         "just that one. The Chat menu has only-my-messages, jump to a date, statistics and "
         "saving. Ctrl+F searches, Ctrl+K jumps to any chat."),
        ("keywords_box", "Choose which messages",
         "Leave it empty for all your messages, or type words like hello, hi. Pick Whole word, "
         "Starts with or Anywhere, and open More filters for files, links, dates and more."),
        ("start_btn", "Preview first, then delete",
         "Press Preview to see what would be deleted. When it looks right, untick 'Preview "
         "only' and press Delete messages. You can pause, stop and continue later."),
    ]

    def start_tour(self, step=0):
        if self.main_frame is None:
            return
        if self._tour is not None:
            try:
                self._tour.destroy()
            except tk.TclError:
                pass
            self._tour = None
        if step >= len(self.TOUR):
            self.settings["tour_done"] = True
            self.save_settings()
            return
        attr, title, text = self.TOUR[step]
        target = getattr(self, attr, None)
        if target is None:
            return self.start_tour(step + 1)
        self.update_idletasks()
        top = self._tour = tk.Toplevel(self)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.configure(bg=BLURPLE)
        box = tk.Frame(top, bg=TIP_BG, padx=16, pady=14)
        box.pack(padx=2, pady=2)
        tk.Label(box, text=f"{step + 1}/{len(self.TOUR)}", notr=True, bg=TIP_BG, fg=MUTED,
                 font=(FONT, 8, "bold")).pack(anchor="w")
        tk.Label(box, text=title, bg=TIP_BG, fg=WHITE, font=(FONT, 12, "bold"),
                 anchor="w").pack(fill="x", pady=(2, 4))
        tk.Label(box, text=text, bg=TIP_BG, fg=TEXT, font=(FONT, 9), wraplength=300,
                 justify="left", anchor="w").pack(fill="x")
        btns = tk.Frame(box, bg=TIP_BG)
        btns.pack(fill="x", pady=(12, 0))
        last = step == len(self.TOUR) - 1
        FlatButton(btns, "Done" if last else "Next", lambda: self.start_tour(step + 1),
                   font_size=9, padx=14, pady=5).pack(side="right")
        if not last:
            LinkLabel(btns, "Skip", lambda: self.start_tour(len(self.TOUR)), TIP_BG,
                      fg=MUTED).pack(side="left")
        top.update_idletasks()
        try:
            tx, ty = target.winfo_rootx(), target.winfo_rooty()
            tw, th = target.winfo_width(), target.winfo_height()
            w, h = top.winfo_reqwidth(), top.winfo_reqheight()
            sw = self.winfo_rootx() + self.winfo_width()
            x = tx + tw + 12 if tx + tw + 12 + w < sw else max(self.winfo_rootx(), tx - w - 12)
            y = min(max(self.winfo_rooty(), ty + min(th, 400) // 3),
                    self.winfo_rooty() + self.winfo_height() - h - 10)
            if attr == "chat":
                x, y = tx + (tw - w) // 2, ty + 80
            top.geometry(f"+{int(x)}+{int(y)}")
        except (tk.TclError, TypeError):
            pass

    # ================================================================ errors, settings, help
    def report_callback_exception(self, exc, val, tb):
        """Any error inside the window: log it and show a friendly message."""
        text = applog.crash_text(exc, val, tb)
        applog.write("ERROR\n" + text)
        if getattr(self, "_error_shown", False):
            return
        self._error_shown = True
        try:
            if messagebox.askyesno(APP_NAME, "Something went wrong, sorry!\n\n"
                                   f"{applog.mask(val)}\n\nThe app keeps working. Open the "
                                   "problem report so you can send it to the developer?",
                                   icon="error"):
                self.open_report()
        finally:
            self.after(3000, lambda: setattr(self, "_error_shown", False))

    def dialog(self, title, w=520, h=560):
        top = tk.Toplevel(self)
        top.title(title)
        top.configure(bg=CHAT)
        top.transient(self)
        x = self.winfo_rootx() + max(0, (self.winfo_width() - w) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - h) // 3)
        top.geometry(f"{w}x{h}+{x}+{y}")
        dark_title_bar(top)
        try:
            set_window_icon(top)
        except Exception:
            pass
        top.bind("<Escape>", lambda e: top.destroy())
        body = tk.Frame(top, bg=CHAT, padx=24, pady=20)
        body.pack(fill="both", expand=True)
        return top, body

    def open_settings(self):
        top, outer = self.dialog("Settings", 560, 760)
        sf = ScrollFrame(outer, CHAT)
        sf.pack(fill="both", expand=True)
        b = sf.inner
        tk.Label(b, text="Settings", bg=CHAT, fg=WHITE, font=(FONT, 16, "bold")).pack(anchor="w")

        section_label(b, "My account", CHAT).pack(anchor="w", pady=(18, 6))
        acc = tk.Frame(b, bg=SIDEBAR, padx=12, pady=10)
        acc.pack(fill="x")
        av = Avatar(acc, 40, SIDEBAR, core.initials(self.my_name())[:1],
                    color_for((self.me or {}).get("id")))
        av.pack(side="left")
        if (self.me or {}).get("id"):
            self.images.load(core.user_avatar_url(self.me), 40, av)
        tk.Label(acc, notr=True, text=self.my_name(), bg=SIDEBAR, fg=WHITE, font=(FONT, 11, "bold")).pack(
            side="left", padx=10)
        FlatButton(acc, "Log out", lambda: (top.destroy(), self.logout()), bg=RED, hover=RED_HI,
                   font_size=9, padx=10, pady=5).pack(side="right")
        FlatButton(acc, "Switch account", lambda: (top.destroy(), self.switch_account()),
                   bg=SELECTED, hover=HOVER, font_size=9, padx=10, pady=5).pack(
            side="right", padx=6)
        auto = tk.BooleanVar(value=self.settings.get("auto_login", True))
        OptionCheck(b, "Sign in automatically when the app starts (saved accounts)", auto, CHAT,
                    command=lambda: (self.settings.__setitem__("auto_login", auto.get()),
                                     self.save_settings())).pack(anchor="w", pady=(8, 0))

        section_label(b, "Appearance", CHAT).pack(anchor="w", pady=(18, 6))
        th = tk.Frame(b, bg=CHAT)
        th.pack(fill="x")
        current = self.settings.get("theme", "dark")
        for i, (name, label) in enumerate(widgets.THEME_NAMES.items()):
            if i == 3:
                th = tk.Frame(b, bg=CHAT)
                th.pack(fill="x", pady=(8, 0))
            bgc, fgc = widgets.THEME_SWATCHES[name]
            cell = tk.Frame(th, bg=BLURPLE if name == current else SIDEBAR, padx=3, pady=3)
            cell.pack(side="left", padx=(0, 10))
            sw = tk.Label(cell, text=label, bg=bgc, fg=fgc, font=(FONT, 9, "bold"), width=12,
                          height=3, cursor="hand2")
            sw.pack()
            sw.bind("<Button-1>", lambda e, n=name: self.set_theme(n, top))
        self.build_customize(b, top)

        FlatButton(b, "Edit my profile (display name, About me, status)…",
                   lambda: (top.destroy(), self.open_profile_editor()), bg=SELECTED, hover=HOVER,
                   font_size=9, padx=10, pady=5).pack(anchor="w", pady=(8, 0))
        section_label(b, "App behaviour", CHAT).pack(anchor="w", pady=(18, 6))
        for key, label, default, after in (
                ("show_cleaner", "Show the cleaning tools (delete panel, checkboxes, red "
                                 "highlights)", True, self.apply_clean_mode),
                ("show_deleted_view", "Show Deleted messages (⊘) in the server bar", True,
                 self.apply_clean_mode),
                ("reopen_last", "Open the last chat when the app starts", True, None),
                ("undo_delete", "Give me 10 seconds to undo when I delete one message", True,
                 None),
                ("close_to_tray", "Keep running next to the clock when I close the window",
                 True, self.apply_tray_setting),
                ("notifications", "Show notifications (new DMs, deleted messages, ghost pings)",
                 True, None),
                ("chat_enabled", "Let me chat, react and reply from the app", True,
                 lambda: self.update_composer()),
                ("live_updates", "Live updates (new messages appear by themselves)", True,
                 self.start_live),
                ("show_deleted", "Keep messages people delete visible (in red) in open chats",
                 True, None),
                ("show_edits", "Show the original text of edited messages", True,
                 lambda: self.preview and self.render_preview(scroll="keep")),
                ("sharp_mode", "Sharp mode for scaled screens (125%, 150%…) - needs a restart",
                 False, None)):
            var = tk.BooleanVar(value=self.settings.get(key, default) is not False
                                if default else bool(self.settings.get(key)))

            def changed(k=key, v=var, fn=after):
                self.settings[k] = v.get()
                self.save_settings()
                if fn:
                    fn()
            OptionCheck(b, label, var, CHAT, command=changed).pack(anchor="w", pady=(2, 0))
        if not media.HAVE_VIDEO:
            tk.Label(b, text="Videos open in your browser because OpenCV isn't installed "
                             "(the build script adds it).", bg=CHAT, fg=MUTED, font=(FONT, 8),
                     anchor="w", wraplength=500, justify="left").pack(fill="x", pady=(4, 0))

        section_label(b, "Language", CHAT).pack(anchor="w", pady=(18, 6))
        lr = tk.Frame(b, bg=CHAT)
        lr.pack(fill="x")
        for code, label in i18n.LANGUAGES.items():
            on = code == i18n.LANG
            bt = tk.Label(lr, text=label, notr=True, bg=BLURPLE if on else INPUT,
                          fg="white" if on else TEXT, font=(FONT, 9, "bold"), padx=14, pady=6,
                          cursor="hand2")
            bt.pack(side="left", padx=(0, 6))
            bt.bind("<Button-1>", lambda e, c=code: self.set_language(c, top))

        section_label(b, "Auto-clean", CHAT).pack(anchor="w", pady=(18, 6))
        FlatButton(b, "Auto-clean rules…", lambda: (top.destroy(), self.open_rules()),
                   bg=SELECTED, hover=HOVER, font_size=9, pady=6).pack(anchor="w")

        section_label(b, "Help", CHAT).pack(anchor="w", pady=(18, 6))
        hb = tk.Frame(b, bg=CHAT)
        hb.pack(fill="x")
        for i, (text, cmd) in enumerate((("Check my setup", lambda: (top.destroy(), self.run_diagnostics())),
                          ("Report a problem", lambda: (top.destroy(), self.open_report())),
                          ("Open log folder", lambda: open_path(applog.log_dir())),
                          ("Show the tour again", lambda: (top.destroy(), self.start_tour())),
                          ("Find my token", lambda: messagebox.showinfo("Find your token",
                                                                       HELP_TEXT)))):
            if i % 3 == 0:
                hrow = tk.Frame(hb, bg=CHAT)
                hrow.pack(fill="x", pady=(0, 6))
            FlatButton(hrow, text, cmd, bg=SELECTED, hover=HOVER, font_size=9, padx=10,
                       pady=5).pack(side="left", padx=(0, 6))
        tk.Label(b, text=f"{APP_NAME} {VERSION}  •  MIT license  •  not affiliated with Discord",
                 bg=CHAT, fg=MUTED, font=(FONT, 8)).pack(side="bottom", anchor="w")

    def set_language(self, code, top=None):
        if code == i18n.LANG:
            return
        self.settings["language"] = code
        self.save_settings()
        if self.running:
            messagebox.showinfo(APP_NAME, "The new language will be used next time you open "
                                          "the app.")
            return
        if messagebox.askyesno(APP_NAME, "Restart the app now to use the new language?"):
            if top is not None:
                top.destroy()
            self.restart()

    def set_theme(self, name, top=None):
        if name == self.settings.get("theme", "dark"):
            return
        self.settings["theme"] = name
        self.save_settings()
        if self.running:
            messagebox.showinfo(APP_NAME, "The new theme will be used next time you open "
                                          "the app.")
            return
        if messagebox.askyesno(APP_NAME, "Restart the app now to use the new theme?"):
            if top is not None:
                top.destroy()
            self.restart()

    def restart(self):
        import subprocess
        self.save_settings()
        if self.job:
            self.save_job(force=True)
        args = [sys.executable] if getattr(sys, "frozen", False) else \
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")]
        try:
            subprocess.Popen(args)
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Could not restart: {e}")
            return
        self.images.pool.shutdown(wait=False, cancel_futures=True)
        self.destroy()

    def open_report(self):
        top, b = self.dialog("Report a problem", 640, 560)
        tk.Label(b, text="Report a problem", bg=CHAT, fg=WHITE, font=(FONT, 16, "bold")).pack(
            anchor="w")
        tk.Label(b, text="Copy this and send it to the developer, with what you were doing when "
                         "it happened. Your token is never included.", bg=CHAT, fg=MUTED,
                 font=(FONT, 9), wraplength=580, justify="left").pack(anchor="w", pady=(4, 10))
        report = applog.system_info(VERSION) + "\n--- recent log ---\n" + applog.recent_lines()
        txt = tk.Text(b, bg=LOG_BG, fg=TEXT, font=("Consolas", 8), relief="flat", bd=8,
                      highlightthickness=0, wrap="word")
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", report)
        btns = tk.Frame(b, bg=CHAT)
        btns.pack(fill="x", pady=(10, 0))

        def copy():
            self.clipboard_clear()
            self.clipboard_append(applog.mask(txt.get("1.0", "end")))
            self.set_status("Problem report copied.")
        FlatButton(btns, "Copy report", copy, font_size=9, pady=6).pack(side="left")
        FlatButton(btns, "Open log folder", lambda: open_path(applog.log_dir()), bg=SELECTED,
                   hover=HOVER, font_size=9, pady=6).pack(side="left", padx=8)
        FlatButton(btns, "Close", top.destroy, bg=SELECTED, hover=HOVER, font_size=9,
                   pady=6).pack(side="right")

    # ================================================================ log
    def log(self, text, tag=None):
        applog.write(text)
        if tag is None:
            low = text.lower()
            if "deleted #" in low:
                tag = "good"
            elif "failed" in low or "could not" in low or "error" in low:
                tag = "bad"

        def add():
            if self.main_frame is None or not hasattr(self, "out"):
                self.pending_log.append((text, tag))
                return
            self._write_log(text, tag)
        self.after(0, add)

    def _write_log(self, text, tag):
        try:
            self.out.configure(state="normal")
            self.out.insert("end", time.strftime("%H:%M:%S "), ("dim",))
            self.out.insert("end", i18n.tr_log(text) + "\n", (tag,) if tag else ())
            self.out.see("end")
            self.out.configure(state="disabled")
        except tk.TclError:
            self.pending_log.append((text, tag))

    def clear_log(self):
        self.out.configure(state="normal")
        self.out.delete("1.0", "end")
        self.out.configure(state="disabled")

    def save_log(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                            initialfile="cleaner_log.txt",
                                            filetypes=[("Text", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.out.get("1.0", "end"))

    def open_backups(self):
        d = default_backup_dir()
        os.makedirs(d, exist_ok=True)
        open_path(d)

    # ================================================================ run
    def collect_options(self):
        try:
            delay = max(0.5, float(self.delay.get()))
        except ValueError:
            raise ValueError("Delay must be a number, like 1.5")
        try:
            max_delete = max(0, int(float(self.max_delete.get() or 0)))
        except ValueError:
            raise ValueError("Max per chat must be a whole number (0 = all).")
        try:
            parallel = min(5, max(1, int(float(self.parallel.get() or 1))))
        except ValueError:
            raise ValueError("'Chats at once' must be 1 to 5.")
        try:
            core.parse_date(self.from_date.get())
            core.parse_date(self.to_date.get())
        except ValueError:
            raise ValueError("Dates must look like 2026-11-21")
        d = {"delay": delay, "dry_run": self.dry_run.get(), "max_delete": max_delete,
             "keywords": self.keywords.get(), "case_sensitive": self.case_sensitive.get(),
             "match_mode": self.match_mode.get(), "from_date": self.from_date.get(),
             "save_first": self.save_first.get(),
             "to_date": self.to_date.get(), "skip_pinned": self.skip_pinned.get(),
             "backup": self.backup.get(), "use_search": self.use_search.get(),
             "auto_speed": self.auto_speed.get(), "parallel": parallel,
             "remove_reactions": self.remove_reactions.get(),
             "close_dms": self.close_dms.get(), "has_files": self.has_files.get(),
             "has_images": self.has_images.get(), "has_links": self.has_links.get(),
             "only_replies": self.only_replies.get(), "min_len": spin_int(self.min_len),
             "max_len": spin_int(self.max_len), "older_than_days": spin_int(self.older_than)}
        if d["min_len"] and d["max_len"] and d["min_len"] > d["max_len"]:
            raise ValueError("The minimum length is bigger than the maximum length.")
        opts = self.options_from_dict(d)
        if opts.from_date and opts.to_date and opts.from_date > opts.to_date:
            raise ValueError("The 'From' date is after the 'To' date.")
        return opts, d

    def options_from_dict(self, d):
        return core.options_from_dict(d, self.keep_ids, default_backup_dir())

    def targets(self):
        out = []
        for key, t in self.checked.items():
            d = {"kind": t["kind"], "id": t["id"], "name": t["name"]}
            if t.get("guild_id"):
                d["guild_id"] = t["guild_id"]
            if t.get("is_dm"):
                d["is_dm"] = True
            if t["kind"] == "ids":
                c = self.pkg_by_id.get(t["id"])
                if not c:
                    continue
                d["messages"] = c["messages"]
            out.append(d)
        return out

    def start(self):
        if self.running:
            return
        targets = self.targets()
        if not targets:
            messagebox.showinfo(APP_NAME, "Tick at least one DM, channel or server first.\n\n"
                                          "Use the boxes next to the names on the left.")
            return
        try:
            opts, d = self.collect_options()
        except ValueError as e:
            messagebox.showerror("Check your settings", str(e))
            return
        if not opts.dry_run:
            what = (f"your messages containing: {', '.join(opts.keywords)}"
                    if opts.keywords else "ALL your messages")
            names = "\n".join("  • " + (t["name"] or f"Chat {t['id']}")
                              + ("  (whole server)" if t["kind"] == "server" else "")
                              for t in targets[:12])
            if len(targets) > 12:
                names += f"\n  … and {len(targets) - 12} more"
            limit = f"\nLimit: {opts.max_delete} per chat." if opts.max_delete else ""
            kept = (f"\n{len(self.keep_ids)} message(s) in your keep list will be skipped."
                    if self.keep_ids else "")
            if self.save_first.get():
                kept += "\nThe whole conversations are saved first."
            if self.remove_reactions.get():
                kept += "\nYour reactions are removed too."
            if self.close_dms.get():
                kept += "\nCleaned DMs are closed and group DMs are left."
            if not messagebox.askyesno(
                    "Delete messages?",
                    f"This will permanently delete {what} in:\n\n{names}\n{limit}{kept}\n"
                    "This cannot be undone. Continue?", icon="warning"):
                return
        self.save_settings()
        self.launch(opts, d, targets)

    def launch(self, opts, d, targets, resumed=False):
        """Start a run. Real (non-preview) runs are saved as a job so they can be resumed."""
        self._save_first_now = bool(d.get("save_first")) and not resumed
        self._close_after = ([t for t in targets if t.get("is_dm")]
                             if d.get("close_dms") and not opts.dry_run else None)
        self.pacer = core.Pacer(opts.delay, auto=d.get("auto_speed", True))
        opts.pacer = self.pacer
        if not opts.dry_run:
            self.job = {"version": 1, "created": time.time(), "options": d,
                        "targets": [dict(t, state="waiting") for t in targets],
                        "user_id": (self.me or {}).get("id")}
            self.save_job(force=True)
        else:
            self.job = None
        self.stop_event.clear()
        self.pause_event.clear()
        self.running = True
        self.current_dry = opts.dry_run
        self.current_max = opts.max_delete
        self.start_time = time.time()
        self._last_stats = None
        self.start_btn.set_enabled(False)
        self.stop_btn.set_enabled(True)
        self.pause_btn.set_enabled(True)
        self.pause_btn.configure(text="Pause")
        self.progress.configure(mode="indeterminate", value=0)
        self.progress.start(12)
        self.log("─" * 40, "dim")
        self.log(f"{'Resuming' if resumed else 'Preview of' if opts.dry_run else 'Cleaning'} "
                 f"{len(targets)} target(s), {min(d['parallel'], len(targets))} at a time.")
        self._close_after_all = list(targets)
        threading.Thread(target=self.worker, args=(opts, targets, d["parallel"]),
                         daemon=True).start()
        self.tick()

    # ---------------------------------------------------------------- jobs (resume)
    def save_job(self, force=False):
        if not self.job or self.demo is not None:
            return
        now = time.time()
        if not force and now - getattr(self, "_job_saved", 0) < 3:
            return
        self._job_saved = now
        write_json(app_data_file("job.json"), self.job)

    def update_job(self, snap):
        if not self.job:
            return
        for t, st in zip(self.job["targets"], snap):
            t["state"] = st.get("state", t.get("state"))
            t["deleted"] = st.get("deleted", 0) + t.get("deleted_before", 0)
            if st.get("cursor") is not None:
                t["cursor"] = st["cursor"]
        self.save_job()

    def check_unfinished_job(self):
        job = read_json(app_data_file("job.json"), None)
        if not job or not isinstance(job, dict) or not job.get("targets"):
            return
        if job.get("user_id") and self.me and job["user_id"] != self.me.get("id"):
            return   # belongs to another account
        left = [t for t in job["targets"] if t.get("state") != "done"]
        if not left:
            self.clear_job()
            return
        deleted = sum(t.get("deleted", 0) for t in job["targets"])
        names = "\n".join("  • " + (t.get("name") or t["id"]) for t in left[:8])
        if len(left) > 8:
            names += f"\n  … and {len(left) - 8} more"
        if messagebox.askyesno(
                "Continue where you left off?",
                f"Your last cleanup didn't finish.\n\n{deleted:,} messages were deleted, "
                f"{len(left)} of {len(job['targets'])} chats are left:\n\n{names}\n\n"
                "Continue now?"):
            for t in left:
                t["deleted_before"] = t.get("deleted", 0)
                t.pop("state", None)
            try:
                opts = self.options_from_dict(job["options"])
            except (KeyError, ValueError):
                self.clear_job()
                return
            self.launch(opts, job["options"], left, resumed=True)
        else:
            self.clear_job()

    def clear_job(self):
        self.job = None
        try:
            os.remove(app_data_file("job.json"))
        except OSError:
            pass

    # ---------------------------------------------------------------- progress
    def tick(self):
        if self.running:
            if getattr(self, "_last_stats", None):
                self.on_progress(self._last_stats)
            self.after(1000, self.tick)

    def on_progress(self, all_stats):
        snap = [dict(s) for s in all_stats]
        self._last_stats = snap

        def upd():
            self.update_job(snap)
            elapsed = int(time.time() - self.start_time)
            key = "matched" if self.current_dry else "deleted"
            done = sum(s[key] for s in snap)
            scanned = sum(s["scanned"] for s in snap)
            failed = sum(s["failed"] for s in snap)
            finished = sum(s.get("state") in ("done", "stopped") for s in snap)
            label = "Found" if self.current_dry else "Deleted"
            speed = (f"  •  {self.pacer.delay:.1f}s each" if self.pacer and not self.current_dry
                     and self.running else "")
            paused = "PAUSED  •  " if self.pause_event.is_set() and self.running else ""
            reacts = sum(s.get("reactions", 0) for s in snap)
            self.set_status(f"{paused}{label} {done:,}  •  Checked {scanned:,}  •  "
                            f"Chats {finished}/{len(snap)}"
                            + (f"  •  Reactions {reacts:,}" if reacts else "")
                            + (f"  •  Failed {failed}" if failed else "")
                            + f"  •  {elapsed // 60}:{elapsed % 60:02d}{speed}")
            if self.current_max:
                total = self.current_max * len(snap)
                value = sum(min(s[key], self.current_max) for s in snap)
            elif len(snap) > 1:
                total, value = len(snap), finished
            elif snap and snap[0].get("total"):
                total, value = snap[0]["total"], min(done, snap[0]["total"])
            else:
                return
            try:
                self.progress.stop()
                self.progress.configure(mode="determinate", maximum=max(total, 1), value=value)
            except tk.TclError:
                pass
        self.after(0, upd)

    def worker(self, opts, targets, parallel):
        results = None
        if not opts.dry_run and getattr(self, "_save_first_now", False):
            self.save_before_delete(targets)
        try:
            results = core.run_many(lambda: self.make_api(stoppable=True), opts, targets,
                                    parallel, self.log, self.on_progress,
                                    self.stop_event.is_set, self.stop_event.wait)
            key = "matched" if opts.dry_run else "deleted"
            verb = "would be deleted" if opts.dry_run else "deleted"
            self.log("═" * 40, "dim")
            for i, r in enumerate(results, 1):
                self.log(f"{i}. {r['chat']}: {r[key]:,} {verb}"
                         + (f", {r['failed']} failed" if r["failed"] else ""))
            self.log(f"TOTAL: {sum(r[key] for r in results):,} {verb}", "good")
        except Exception as e:
            self.log(f"Unexpected error: {e}", "bad")
        finally:
            self.after(0, lambda: self.finished(opts.dry_run, results))

    def finished(self, dry_run, results=None):
        self.running = False
        self.pause_event.clear()
        rule = getattr(self, "_running_rule", None)
        self._running_rule = None
        if rule is not None:
            self.finish_rule(rule, results)
        if not dry_run and results and getattr(self, "_close_after", None):
            self.close_finished_dms(results)
        if not dry_run and results:
            n = sum(r.get("deleted", 0) for r in results)
            self.settings["total_deleted"] = int(self.settings.get("total_deleted", 0) or 0) + n
            self.save_settings()
            try:
                self.update_user_panel()
            except (tk.TclError, AttributeError):
                pass
        if results is not None:
            try:
                self.bell()
                if self.focus_displayof() is None:
                    flash_window(self)
            except tk.TclError:
                pass
        if results is not None:
            self.update_job(results)
        if self.job:
            if results is not None and all(r.get("state") == "done" for r in results):
                self.clear_job()
            else:
                self.save_job(force=True)
                self.log("Not finished. The app will offer to continue next time you open it.",
                         "dim")
        if self.main_frame is None:
            return
        self.progress.stop()
        if str(self.progress["mode"]) == "indeterminate":
            self.progress.configure(mode="determinate", value=0)
        self.start_btn.set_enabled(True)
        self.update_start_button()
        self.stop_btn.set_enabled(False)
        self.pause_btn.set_enabled(False)
        self.pause_btn.configure(text="Pause")
        if getattr(self, "_last_stats", None):
            self.on_progress(self._last_stats)
            self._last_stats = None
        if not dry_run and self.preview and self.preview.get("source") == "live":
            p = self.preview   # show the chat after cleaning
            self.open_chat(p["key"], p["channel_id"], p["title"], p["icon"], p["avatar"],
                           p["user_id"], p["server"])

    def save_before_delete(self, targets):
        """Save each chat fully before it gets cleaned (runs in the worker thread)."""
        base = self.conversations_dir()
        os.makedirs(base, exist_ok=True)
        self.log("Saving whole conversations before deleting…", "dim")
        for t in targets:
            if self.stop_event.is_set():
                return
            if t["kind"] == "server":
                self.log(f"Not saving {t['name']} (whole server is too big). Tick its channels "
                         "to save them.", "dim")
                continue
            title = t.get("name") or f"Chat {t['id']}"
            try:
                api = self.make_api(stoppable=True)
                msgs = self.messages_to_save(t["id"], api, self.stop_event.is_set)
                folder, n, files = core.save_conversation(
                    api, t["id"], title, base, log=self.log, messages=msgs,
                    progress=lambda txt, title=title: self.after(
                        0, lambda: self.set_status(f"Saving {title}: {txt}")),
                    should_stop=self.stop_event.is_set)
                self.log(f"Saved {title}: {n:,} messages, {files} files → {folder}", "good")
            except Exception as e:
                self.log(f"Could not save {title}: {e}", "bad")

    def close_finished_dms(self, results):
        """Close DMs / leave group DMs that were fully cleaned."""
        done_ids = {t["id"] for t, r in zip(self._close_after_all, results)
                    if r.get("state") == "done"} if hasattr(self, "_close_after_all") else set()
        todo = [t for t in self._close_after if t["id"] in done_ids]
        self._close_after = None
        if not todo:
            return

        def work():
            closed = 0
            for t in todo:
                try:
                    if core.close_channel(self.make_api(), t["id"]):
                        closed += 1
                        self.log(f"Closed {t['name']}.", "dim")
                except Exception as e:
                    self.log(f"Could not close {t['name']}: {e}", "bad")
            self.after(0, lambda: (self.log(f"Closed {closed} DM(s)."), self.refresh()))
        threading.Thread(target=work, daemon=True).start()

    # ---------------------------------------------------------------- auto-clean rules
    def run_rule_now(self, rule, manual=False):
        """Start a rule in the app. Returns True if it started."""
        if self.running or not self.token_value or self.main_frame is None:
            if manual:
                messagebox.showinfo(APP_NAME, "Wait for the cleaner to finish first.")
            return False
        if rule.get("account_id") != (self.me or {}).get("id"):
            if manual:
                messagebox.showinfo(APP_NAME, "This rule belongs to another account. "
                                              "Switch to that account to run it.")
            return False
        if rule.get("kind") == "backup":
            return self.run_backup_rule(rule)
        d = dict(rule["options"], dry_run=False)
        d.setdefault("parallel", 2)
        try:
            opts = self.options_from_dict(d)
        except (KeyError, ValueError) as e:
            self.log(f"Rule '{rule['name']}' has bad settings: {e}", "bad")
            return False
        self._running_rule = rule
        self.log(f"Auto-clean: running rule '{rule['name']}' ({rules.describe(rule)})", "dim")
        self.launch(opts, d, rule["targets"])
        return True

    def run_backup_rule(self, rule):
        """Backups run beside the cleaner (they only read), in the background."""
        if getattr(self, "_backup_running", False):
            return False
        self._backup_running = True
        self.log(f"Backup: {rules.describe(rule)}", "dim")
        self.set_status(f"Backing up {len(rule['targets'])} chat(s)…")

        def work():
            try:
                n = rules.run_backup(rule, self.make_api,
                                     log=lambda t: self.after(0, lambda: self.log(t, "dim")))
                result = f"{n} chat(s) saved"
            except Exception as e:
                result = f"Error: {e}"

            def done():
                self._backup_running = False
                all_rules = rules.load_rules()
                for r in all_rules:
                    if r["id"] == rule["id"]:
                        r["last_run"] = time.time()
                        r["last_result"] = result
                rules.save_rules(all_rules)
                self.log(f"Backup '{rule['name']}' done: {result}.", "good")
                self.set_status(f"Backup done: {result}")
            self.after(0, done)
        threading.Thread(target=work, daemon=True).start()
        return True

    def finish_rule(self, rule, results):
        deleted = sum(r.get("deleted", 0) for r in results or [])
        all_rules = rules.load_rules()
        for r in all_rules:
            if r["id"] == rule["id"]:
                r["last_run"] = time.time()
                r["last_result"] = f"{deleted} deleted"
        rules.save_rules(all_rules)
        self.log(f"Auto-clean rule '{rule['name']}' done: {deleted} deleted.", "good")

    def open_rules(self):
        top, outer = self.dialog("Auto-clean rules", 660, 760)
        sfr = ScrollFrame(outer, CHAT)
        sfr.pack(fill="both", expand=True)
        b = sfr.inner
        tk.Label(b, text="Auto-clean rules", bg=CHAT, fg=WHITE, font=(FONT, 16, "bold")).pack(
            anchor="w")
        tk.Label(b, text="Rules clean chats again and again on their own, for example: every "
                         "day, delete my messages older than 30 days in these chats. They run "
                         "while the app is open, and if you turn it on below, once a day even "
                         "when it's closed.", bg=CHAT, fg=MUTED, font=(FONT, 9),
                 wraplength=580, justify="left").pack(anchor="w", pady=(4, 12))
        lst = tk.Frame(b, bg=CHAT)
        lst.pack(fill="x")

        def render():
            for w in lst.winfo_children():
                w.destroy()
            all_rules = rules.load_rules()
            if not all_rules:
                tk.Label(lst, text="No rules yet.", bg=CHAT, fg=MUTED, font=(FONT, 9)).pack(
                    anchor="w", pady=6)
            for r in all_rules:
                row = tk.Frame(lst, bg=SIDEBAR, padx=10, pady=8)
                row.pack(fill="x", pady=2)
                en = tk.BooleanVar(value=r.get("enabled", True))

                def toggle(r=r, en=en):
                    rs = rules.load_rules()
                    for x in rs:
                        if x["id"] == r["id"]:
                            x["enabled"] = en.get()
                    rules.save_rules(rs)
                OptionCheck(row, "", en, SIDEBAR, command=toggle).pack(side="left")
                info = tk.Frame(row, bg=SIDEBAR)
                info.pack(side="left", fill="x", expand=True, padx=(6, 0))
                tk.Label(info, notr=True, text=r["name"], bg=SIDEBAR, fg=WHITE, font=(FONT, 10, "bold"),
                         anchor="w").pack(fill="x")
                last = (time.strftime("%b %d %H:%M", time.localtime(r["last_run"]))
                        + f" ({r.get('last_result', '')})") if r.get("last_run") else "never"
                tk.Label(info, text=f"{rules.describe(r)}  •  last run: {last}", bg=SIDEBAR,
                         fg=MUTED, font=(FONT, 8), anchor="w", wraplength=380,
                         justify="left").pack(fill="x")

                def delete(r=r):
                    if messagebox.askyesno(APP_NAME, f"Delete the rule '{r['name']}'?"):
                        rules.save_rules([x for x in rules.load_rules() if x["id"] != r["id"]])
                        render()
                FlatButton(row, "Delete", delete, bg=RED, hover=RED_HI, font_size=8, padx=8,
                           pady=3).pack(side="right")
                FlatButton(row, "Run now", lambda r=r: (top.destroy(),
                                                        self.run_rule_now(r, manual=True)),
                           bg=SELECTED, hover=HOVER, font_size=8, padx=8, pady=3).pack(
                    side="right", padx=6)
        render()

        section_label(b, "New rule from what you've ticked", CHAT).pack(anchor="w",
                                                                         pady=(18, 6))
        targets = [t for t in self.targets() if t["kind"] != "ids"]
        names = ", ".join((t["name"] or t["id"]) for t in targets[:4]) + (
            f" + {len(targets) - 4} more" if len(targets) > 4 else "")
        tk.Label(b, text=f"Chats: {names}" if targets else
                 "Tick some DMs, channels or servers first (data package chats can't be used).",
                 bg=CHAT, fg=TEXT if targets else ERROR_FG, font=(FONT, 9), wraplength=580,
                 justify="left", anchor="w").pack(fill="x")
        form = tk.Frame(b, bg=CHAT)
        form.pack(fill="x", pady=(8, 0))
        box, name_e = entry_box(form, "Rule name, e.g. Clean old DMs", font_size=9)
        box.pack(fill="x")
        r2 = tk.Frame(form, bg=CHAT)
        r2.pack(fill="x", pady=(8, 0))
        tk.Label(r2, text="Delete my messages older than", bg=CHAT, fg=TEXT,
                 font=(FONT, 9)).pack(side="left")
        days = self.spin(r2, 0, 36500, 1, 6)
        days.pack(side="left", padx=6)
        self.set_spin(days, spin_int(self.older_than) or 30)
        tk.Label(r2, text="days", bg=CHAT, fg=TEXT, font=(FONT, 9)).pack(side="left")
        every = tk.StringVar(value="day")
        r3 = tk.Frame(form, bg=CHAT)
        r3.pack(fill="x", pady=(8, 0))
        btns = {}

        def pick(v):
            every.set(v)
            for k, bt in btns.items():
                bt.configure(bg=BLURPLE if k == v else INPUT, fg="white" if k == v else TEXT)
        for k, label in rules.INTERVAL_NAMES.items():
            bt = tk.Label(r3, text=label, bg=INPUT, fg=TEXT, font=(FONT, 8, "bold"), padx=10,
                          pady=4, cursor="hand2")
            bt.pack(side="left", padx=(0, 4))
            bt.bind("<Button-1>", lambda e, k=k: pick(k))
            btns[k] = bt
        pick("day")
        tk.Label(form, text="Uses your current keywords and filters from the cleaner panel.",
                 bg=CHAT, fg=MUTED, font=(FONT, 8)).pack(anchor="w", pady=(6, 0))

        def create():
            if not targets:
                messagebox.showinfo(APP_NAME, "Tick some chats first.")
                return
            try:
                _, d = self.collect_options()
            except ValueError as e:
                messagebox.showerror(APP_NAME, str(e))
                return
            n = spin_int(days)
            if not messagebox.askyesno(
                    APP_NAME, f"Create a rule that deletes your messages older than {n} days "
                              f"in {len(targets)} chat(s), {rules.INTERVAL_NAMES[every.get()].lower()}?"
                              "\n\nIt deletes for real (no preview)."):
                return
            r = rules.new_rule(name_e.get().strip() or f"Rule {time.strftime('%b %d')}",
                               targets, d, (self.me or {}).get("id"), every.get(), n)
            rules.save_rules(rules.load_rules() + [r])
            render()
        brow = tk.Frame(form, bg=CHAT)
        brow.pack(anchor="w", pady=(10, 0))
        FlatButton(brow, "Create rule", create, font_size=9, pady=6).pack(side="left")

        def create_backup():
            chans = [t for t in targets if t["kind"] == "channel"]
            if not chans:
                messagebox.showinfo(APP_NAME, "Tick some DMs or channels first (whole servers "
                                              "can't be backed up as one chat).")
                return
            when = rules.INTERVAL_NAMES[every.get()].lower()
            if not messagebox.askyesno(
                    APP_NAME, f"Save a full copy of {len(chans)} chat(s) {when}?\n\n"
                              f"Everyone's messages, pictures and files go to:\n"
                              f"{rules.default_backup_folder()}\n\nThe 4 newest copies of "
                              f"each chat are kept."):
                return
            r = rules.new_backup_rule(name_e.get().strip() or f"Backup {time.strftime('%b %d')}",
                                      chans, (self.me or {}).get("id"), every.get())
            rules.save_rules(rules.load_rules() + [r])
            render()
        FlatButton(brow, "Back up these chats on a schedule", create_backup, bg=GREEN,
                   hover="#1a7f43", font_size=9, pady=6).pack(side="left", padx=8)

        section_label(b, "When the app is closed", CHAT).pack(anchor="w", pady=(18, 6))
        on = tk.BooleanVar(value=rules.task_installed())

        def set_task():
            try:
                if on.get():
                    if not securestore.has_accounts():
                        messagebox.showinfo(APP_NAME, "Log in with 'Remember me' ticked first, "
                                                      "so rules can sign in without you.")
                        on.set(False)
                        return
                    rules.install_task("03:00")
                    self.log("Auto-clean will also run every day at 3:00 AM.", "good")
                else:
                    rules.remove_task()
            except OSError as e:
                on.set(False)
                messagebox.showerror(APP_NAME, f"Windows didn't accept the task: {e}")
        OptionCheck(b, "Run due rules every day at 3:00 AM, even when the app is closed "
                       "(Windows Task Scheduler)", on, CHAT, command=set_task).pack(anchor="w")

    def toggle_pause(self):
        if not self.running:
            return
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_btn.configure(text="Pause")
            self.log("Resumed.")
        else:
            self.pause_event.set()
            self.pause_btn.configure(text="Resume")
            self.log("Paused. Press Resume to continue.")
        if getattr(self, "_last_stats", None):
            self.on_progress(self._last_stats)

    def stop(self):
        self.pause_event.clear()
        self.stop_event.set()
        self.log("Stopping…")

    def on_close(self):
        if (not self.really_quit and self.tray is not None and self.main_frame is not None
                and self.settings.get("close_to_tray", True) is not False):
            self.hide_to_tray()          # keeps running next to the clock
            return
        self.really_quit = False
        if self.running and not messagebox.askyesno(
                APP_NAME, "Still running. Stop and quit?\n\nYou can continue where you left "
                          "off next time you open the app."):
            return
        self.stop_event.set()
        self.pause_event.clear()
        if self.job:
            self.save_job(force=True)
        self.save_settings()
        self.stop_live()
        if self.tray is not None:
            self.tray.stop()
            self.tray = None
        self.images.pool.shutdown(wait=False, cancel_futures=True)
        self.destroy()


def types_ns(widget):
    """A fake mouse event at a widget (to open the right-click menu from a button)."""
    import types
    return types.SimpleNamespace(x_root=widget.winfo_rootx(),
                                 y_root=widget.winfo_rooty() + widget.winfo_height())


def open_path(path):
    try:
        os.startfile(path)  # Windows
    except (AttributeError, OSError):
        webbrowser.open("file:///" + os.path.abspath(path).replace("\\", "/"))


def spin_int(sp):
    try:
        return max(0, int(float(sp.get() or 0)))
    except (ValueError, tk.TclError):
        return 0


def local_day(m):
    try:
        ts = m.get("timestamp") or ""
        return core.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().date()
    except (ValueError, AttributeError):
        return None


def short_time(ts):
    try:
        dt = core.datetime.fromisoformat((ts or "").replace("Z", "+00:00")).astimezone()
        return dt.strftime("%H:%M") if i18n.LANG == "fr" else dt.strftime("%I:%M %p").lstrip("0")
    except (ValueError, AttributeError):
        return ""


def package_initial(name):
    return (core.initials(name) or "?")[:1]


def pkg_time(ts):
    """Data package time '2023-01-02 10:11:12.123000+00:00' -> ISO for format_time."""
    ts = (ts or "").strip()
    if ts and "T" not in ts:
        ts = ts.replace(" ", "T", 1)
    if ts and "+" not in ts[10:] and not ts.endswith("Z"):
        ts += "+00:00"
    return ts


def core_ts(m):
    """Seconds since Discord epoch from a message id (cheap, no date parsing)."""
    try:
        return (int(m["id"]) >> 22) / 1000
    except (KeyError, ValueError):
        return 0


def main():
    i18n.install()
    core.LANG = i18n.LANG
    if "--run-rules" in sys.argv:          # started by Windows Task Scheduler
        rules.run_headless()
        return
    applog.cleanup()
    applog.write(f"--- {APP_NAME} {VERSION} started ---")
    sys.excepthook = lambda t, e, tb: applog.write("CRASH\n" + applog.crash_text(t, e, tb))
    threading.excepthook = lambda a: applog.write(
        "THREAD CRASH\n" + applog.crash_text(a.exc_type, a.exc_value, a.exc_traceback))
    windows_setup(read_json(settings_path(), {}))
    App().mainloop()


if __name__ == "__main__":
    main()
