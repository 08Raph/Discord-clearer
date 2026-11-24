"""Everyday tools that make the app worth keeping open (7.6):

  * Archive + offline search of your chats, and "Your year" (recap) made from it
  * Reminders on messages, messages to send later, saved replies (;name + Tab)
  * Keyword alerts with an inbox
  * Privacy sweeper: leave servers, close old DMs, find friends you never talk to
  * Safe mode (slow, small, random) for everything automatic
  * Quick account switching, starting with Windows in the tray

Mixed into App (app.py). Widgets come from the app module at run time (no import cycle)."""
import os
import sys
import time
import tkinter as tk
from datetime import datetime, timedelta

import archive
import cleaner_core as core
import i18n
import planner
import safety

RUN_NAME = "DiscordMessageCleanerApp"
AUTO_SYNC_S = 6 * 3600
TICK_MS = 20 * 1000


def _t(template, **kw):
    """Translated template with {placeholders}."""
    try:
        return i18n.tr(template).format(**kw)
    except (KeyError, IndexError, ValueError):
        return template.format(**kw)


def _fmt_ts(ts):
    return core.format_time(datetime.fromtimestamp(ts).astimezone().isoformat()) if ts else ""


class EverydayMixin:
    _arch = None
    _plan_started = False
    _sync_stop = None
    _sync_busy = False
    _alert_cfg = None
    _toast = None
    _sweep_stop = None
    _missed_told = None
    sync_lbl = None
    sync_btn = None
    _arch_render = None

    # ------------------------------------------------------------------ basics
    def archive(self):
        if self._arch is None:
            self._arch = archive.Archive()
        return self._arch

    def me_id(self):
        return (self.me or {}).get("id")

    def start_everyday(self):
        """Called once the main window is built."""
        if self._plan_started:
            return
        self._plan_started = True
        self._missed_told = set()
        self.after(4000, self.planner_tick)
        if self.demo is None:
            self.after(2 * 60 * 1000, self.archive_auto_tick)
            self.after(1500, self.first_launch_warning)

    def chat_name_of(self, cid, gid=None):
        for d in self.dms or []:
            if d["id"] == cid:
                return d["name"]
        name = (self.channel_names or {}).get(cid)
        g = self.guild_by_id.get(gid or self.channel_guild.get(cid), {}).get("name")
        if name:
            return f"#{name}" + (f" · {g}" if g else "")
        return g or i18n.tr("a chat")

    def window_focused(self):
        try:
            return self.focus_displayof() is not None and self.state() == "normal"
        except tk.TclError:
            return False

    def notify_always(self, title, text, action=None):
        """Toast inside the window when you're looking at it, Windows notification otherwise."""
        if self.window_focused():
            self.toast(title, text, action)
        else:
            self.notify(title, text, flash=True)

    def toast(self, title, text, action=None, ms=7000):
        A = self._A
        if self.main_frame is None:
            return
        try:
            if self._toast is not None:
                self._toast.destroy()
        except tk.TclError:
            pass
        t = self._toast = tk.Frame(self.main_frame, bg=A.TIP_BG, padx=14, pady=10, cursor="hand2")
        tk.Label(t, notr=True, text=title, bg=A.TIP_BG, fg=A.WHITE, font=(A.FONT, 10, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(t, notr=True, text=text[:160], bg=A.TIP_BG, fg=A.TEXT, font=(A.FONT, 9),
                 anchor="w", justify="left", wraplength=300).pack(fill="x")
        t.place(relx=1.0, rely=1.0, x=-24, y=-90, anchor="se")

        def click(_e=None):
            try:
                t.destroy()
            except tk.TclError:
                pass
            if action:
                action()
        A.bind_tree(t, "<Button-1>", click)
        self.after(ms, lambda: t.winfo_exists() and t.destroy())

    def on_safety_limit(self):
        self.log(i18n.tr("Safe mode: today's limit for automatic deletes is reached. "
                         "The rule continues tomorrow."), "dim")
        self.stop_event.set()

    # ================================================================ planner timer
    def planner_tick(self):
        try:
            self._planner_tick()
        finally:
            self.after(TICK_MS, self.planner_tick)

    def _planner_tick(self):
        me = self.me_id()
        if not me or self.main_frame is None:
            return
        for r in planner.due_reminders(me):
            planner.finish_reminder(r["id"])
            what = r.get("note") or r.get("text") or i18n.tr("Reminder")
            where = (r.get("author") + " · " if r.get("author") else "") + (r.get("chat") or "")
            self.notify_always("⏰ " + i18n.tr("Reminder"), f"{what}\n{where}".strip(),
                               action=lambda r=r: self.open_reminder_target(r))
        send, missed = planner.due_sends(me)
        for x in missed:
            if x["id"] not in self._missed_told:
                self._missed_told.add(x["id"])
                self.notify_always(i18n.tr("A scheduled message was not sent"),
                                   _t("The app was closed when it was due ({chat}). Open "
                                      "Scheduled messages to send it or delete it.",
                                      chat=x.get("chat") or ""),
                                   action=self.open_scheduled)
        for x in send:
            self.send_scheduled(x)

    def send_scheduled(self, x, manual=False):
        if not safety.risk_on("send"):
            planner.update_send(x["id"], status="missed",
                                error=i18n.tr("Scheduled messages are a risky feature and are off"))
            if manual:
                self.risk_gate("send")
            return
        if safety.left("send") <= 0:
            planner.update_send(x["id"], status="missed",
                                error=i18n.tr("Safe mode: daily limit for scheduled messages"))
            return
        planner.update_send(x["id"], status="sending")

        def work():
            try:
                st, data = core.send_message(self.make_api(), x["channel_id"], x["content"],
                                             x.get("reply_to"))
            except Exception as e:
                st, data = 0, {"message": str(e)}

            def done():
                if st in (200, 201):
                    safety.use("send")
                    planner.set_send_status(x["id"], "sent")
                    self.log(_t("Scheduled message sent to {chat}.", chat=x.get("chat", "")),
                             "good")
                    if isinstance(data, dict) and data.get("id"):
                        self.live_message(data, mine=True)
                else:
                    err = (data or {}).get("message") if isinstance(data, dict) else ""
                    planner.set_send_status(x["id"], "failed",
                                            err or core.friendly_error(st, "send this message"))
                    self.notify_always(i18n.tr("A scheduled message was not sent"),
                                       err or core.friendly_error(st, "send this message"),
                                       action=self.open_scheduled)
            self.after(0, done)
        self._bg(work)

    # ================================================================ tools hub
    def open_tools(self):
        A = self._A
        top, outer = self.dialog(i18n.tr("Everyday tools"), 720, 720)
        sf = A.ScrollFrame(outer, A.CHAT)
        sf.pack(fill="both", expand=True)
        b = sf.inner
        tk.Label(b, text="Everyday tools", bg=A.CHAT, fg=A.WHITE, font=(A.FONT, 15, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(b, text="Things that work every day, not just for cleaning. Everything stays "
                         "on this PC.", bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9), anchor="w",
                 wraplength=640, justify="left").pack(fill="x", pady=(2, 12))
        me = self.me_id()
        try:
            n_arch = self.archive().total(me)
        except Exception:
            n_arch = 0
        upcoming = sum(1 for r in planner.reminders(me) if not r.get("done"))
        pend = planner.pending_count(me)
        unseen = sum(1 for x in planner.alert_inbox(me) if not x.get("seen"))
        tiles = [
            ("🗄", "Archive and search", _t("{n} messages saved on this PC", n=f"{n_arch:,}"),
             self.open_archive),
            ("📊", "Your year", "Who you talk to, when, your words and emojis", self.open_recap),
            ("⏰", "Reminders", _t("{n} coming up", n=upcoming), self.open_reminders),
            ("🕓", "Scheduled messages", _t("{n} waiting", n=pend), self.open_scheduled),
            ("📝", "Saved replies", _t("{n} saved · type ;name then Tab",
                                       n=len(planner.snippets())), self.open_snippets),
            ("🔔", "Keyword alerts", _t("{n} new", n=unseen), self.open_alerts),
            ("🧽", "Privacy sweeper", "Leave servers, close old DMs, find inactive friends",
             self.open_sweeper),
            ("🛡", "Safe mode", "On" if safety.enabled() else "Off", self.open_safety),
            ("⚠", "Risk tab", _t("{n} of {m} risky features on", n=safety.risk_count(),
                                 m=len(safety.RISK_FEATURES)), self.open_risk),
            ("🚀", "Start with Windows", "Open in the tray when your PC starts",
             self.open_startup),
        ]
        grid = tk.Frame(b, bg=A.CHAT)
        grid.pack(fill="x")
        for i, (icon, title, sub, fn) in enumerate(tiles):
            c = tk.Frame(grid, bg=A.SIDEBAR, padx=14, pady=12, cursor="hand2")
            c.grid(row=i // 3, column=i % 3, sticky="nsew", padx=4, pady=4)
            tk.Label(c, notr=True, text=icon, bg=A.SIDEBAR, fg=A.WHITE,
                     font=(A.FONT, 18)).pack(anchor="w")
            tk.Label(c, text=title, bg=A.SIDEBAR, fg=A.WHITE, font=(A.FONT, 10, "bold"),
                     anchor="w").pack(fill="x", pady=(4, 0))
            tk.Label(c, notr=True, text=i18n.tr(sub), bg=A.SIDEBAR, fg=A.MUTED,
                     font=(A.FONT, 8), anchor="w", justify="left", wraplength=180).pack(fill="x")
            A.bind_tree(c, "<Button-1>", lambda e, fn=fn: (top.destroy(), fn()))
        for col in range(3):
            grid.grid_columnconfigure(col, weight=1, uniform="t")
        tk.Label(b, text="Shortcuts: Ctrl+Shift+F search the archive · Ctrl+Shift+R reminders",
                 bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 8), anchor="w").pack(fill="x", pady=(12, 0))

    def bind_everyday_keys(self):
        self.bind_all("<Control-Shift-F>", lambda e: self.open_archive())
        self.bind_all("<Control-Shift-R>", lambda e: self.open_reminders())

    # ================================================================ archive
    def open_archive(self, query=""):
        A = self._A
        top, b = self.dialog(i18n.tr("Archive and search"), 820, 720)
        me = self.me_id()
        ar = self.archive()
        head = tk.Frame(b, bg=A.CHAT)
        head.pack(fill="x")
        tk.Label(head, text="Archive and search", bg=A.CHAT, fg=A.WHITE,
                 font=(A.FONT, 14, "bold")).pack(side="left")
        A.FlatButton(head, "Chats in the archive", lambda: self.open_archive_chats(top),
                     bg=A.SELECTED, hover=A.HOVER, font_size=9, padx=10, pady=4).pack(side="right")
        info = tk.Label(b, notr=True, text="", bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9), anchor="w")
        info.pack(fill="x", pady=(2, 8))

        row = tk.Frame(b, bg=A.CHAT)
        row.pack(fill="x")
        qbox, qe = A.entry_box(row, "Search words (\"exact phrase\" works)", width=34)
        qbox.pack(side="left")
        pbox, pe = A.entry_box(row, "Person", width=14)
        pbox.pack(side="left", padx=6)
        if query:
            qe.insert(0, query)
        chips = tk.Frame(b, bg=A.CHAT)
        chips.pack(fill="x", pady=(6, 4))
        state = {"when": "any", "chat": None, "mine": False}
        spans = [("any", "Any time"), ("week", "Past week"), ("month", "Past month"),
                 ("year", "Past year")]
        chip_w = {}

        def chip(parent, key, label, group):
            w = tk.Label(parent, text=label, bg=A.SIDEBAR, fg=A.TEXT, font=(A.FONT, 9),
                         padx=9, pady=3, cursor="hand2")
            w.pack(side="left", padx=(0, 4))
            w.bind("<Button-1>", lambda e: pick(group, key))
            chip_w[(group, key)] = w
            return w

        def paint():
            for (g, k), w in chip_w.items():
                on = state.get(g) == k if g != "mine" else state["mine"]
                w.configure(bg=A.BLURPLE if on else A.SIDEBAR, fg="white" if on else A.TEXT)

        def pick(group, key):
            if group == "mine":
                state["mine"] = not state["mine"]
            else:
                state[group] = key
            paint()
            run()
        for k, lb in spans:
            chip(chips, k, lb, "when")
        chip(chips, True, "Only my messages", "mine")
        if self.preview and ar.has_chat(me, self.preview.get("channel_id")):
            chip(chips, self.preview["channel_id"], "Only this chat", "chat")
        paint()
        res = A.ScrollFrame(b, A.CHAT)
        res.pack(fill="both", expand=True, pady=(6, 0))

        def run(_e=None):
            res.clear()
            now = time.time()
            since = {"week": now - 7 * 86400, "month": now - 31 * 86400,
                     "year": now - 366 * 86400}.get(state["when"])
            try:
                rows = ar.search(me, qe.get().strip(), channel_id=state.get("chat"),
                                 author=pe.get().strip() or None, since=since,
                                 only_author_id=me if state["mine"] else None)
            except Exception as e:
                rows = []
                info.configure(text=str(e))
            total = ar.total(me)
            info.configure(text=_t("{n} results · {t} messages from {c} chats on this PC",
                                   n=len(rows), t=f"{total:,}", c=len(ar.chats(me))))
            if not total:
                box = tk.Frame(res.inner, bg=A.CHAT)
                box.pack(pady=50)
                tk.Label(box, text="Your archive is empty.", bg=A.CHAT, fg=A.WHITE,
                         font=(A.FONT, 11, "bold")).pack()
                tk.Label(box, text="Add chats and the app keeps a copy on this PC that you can "
                                   "search, even offline or after messages are deleted.",
                         bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9), wraplength=440).pack(pady=6)
                A.FlatButton(box, "Add chats", lambda: self.pick_archive_chats(top)).pack()
                return
            for r in rows[:300]:
                self.archive_card(res.inner, r, top)
        qe.bind("<Return>", run)
        pe.bind("<Return>", run)
        qe.bind("<KeyRelease>", lambda e: self.after_idle(run) if e is None or len(qe.get()) != 1
                else None)
        run()
        qe.focus_set()

    def archive_card(self, parent, r, top):
        A = self._A
        card = tk.Frame(parent, bg=A.CODE_BG, padx=12, pady=7)
        card.pack(fill="x", pady=3, padx=(0, 10))
        h = tk.Frame(card, bg=A.CODE_BG)
        h.pack(fill="x")
        tk.Label(h, notr=True, text=r.get("author") or "?", bg=A.CODE_BG, fg=A.WHITE,
                 font=(A.FONT, 10, "bold")).pack(side="left")
        tk.Label(h, notr=True, text=f"  {r.get('chat') or ''}  ·  {_fmt_ts(r['ts'])}",
                 bg=A.CODE_BG, fg=A.MUTED, font=(A.FONT, 8)).pack(side="left")
        A.LinkLabel(h, "Open", lambda: (top.destroy(), self.goto_message(
            r["channel_id"], r["id"], r.get("guild"))), A.CODE_BG, font_size=8).pack(side="right")
        A.LinkLabel(h, "Around it", lambda: self.archive_context(r), A.CODE_BG,
                    font_size=8).pack(side="right", padx=8)
        text = r.get("content") or ""
        if r.get("files"):
            text += ("\n" if text else "") + "📎 " + ", ".join(__import__("json").loads(r["files"]))
        tk.Label(card, notr=True, text=text[:600] or "…", bg=A.CODE_BG, fg=A.TEXT,
                 font=(A.FONT, 9), anchor="w", justify="left", wraplength=700).pack(fill="x")

    def archive_context(self, r):
        A = self._A
        top, b = self.dialog(r.get("chat") or i18n.tr("Archive"), 640, 560)
        sf = A.ScrollFrame(b, A.CHAT)
        sf.pack(fill="both", expand=True)
        for m in self.archive().context(self.me_id(), r["channel_id"], r["ts"]):
            hit = m["id"] == r["id"]
            bg = A.MATCH_BG if hit else A.CHAT
            f = tk.Frame(sf.inner, bg=bg, padx=8, pady=4)
            f.pack(fill="x")
            tk.Label(f, notr=True, text=f"{m['author']}  ·  {_fmt_ts(m['ts'])}", bg=bg,
                     fg=A.WHITE, font=(A.FONT, 9, "bold"), anchor="w").pack(fill="x")
            tk.Label(f, notr=True, text=m.get("content") or "…", bg=bg, fg=A.TEXT,
                     font=(A.FONT, 9), anchor="w", justify="left", wraplength=560).pack(fill="x")

    def goto_message(self, cid, mid=None, gid=None):
        """Open a chat in the app and jump to a message."""
        d = next((x for x in self.dms or [] if x["id"] == cid), None)
        gid = gid or self.channel_guild.get(cid)
        try:
            if d is not None:
                if self.view != "dms":
                    self.open_view("dms")
                self.open_chat(("dm", cid), cid, d["name"], "@", d.get("avatar"), d.get("user_id"))
            elif gid and gid in self.guild_by_id:
                self.channel_guild[cid] = gid
                self.open_view(gid)
                self.open_chat(("channel", cid), cid, self.chat_name_of(cid, gid).split(" · ")[0],
                               "#", None, None, self.guild_by_id[gid].get("name"))
            else:
                self.open_in_discord(f"/channels/{gid or '@me'}/{cid}" + (f"/{mid}" if mid else ""))
                return
        except (tk.TclError, KeyError):
            return
        if mid:
            self.after(900, lambda: self.preview and self.preview.get("channel_id") == cid and
                       self.jump_to_message({"id": mid}))

    def open_archive_chats(self, parent_top=None):
        A = self._A
        top, b = self.dialog(i18n.tr("Chats in the archive"), 640, 640)
        me = self.me_id()
        ar = self.archive()
        tk.Label(b, text="Chats in the archive", bg=A.CHAT, fg=A.WHITE,
                 font=(A.FONT, 14, "bold"), anchor="w").pack(fill="x")
        tk.Label(b, text="Only reads messages, never changes anything on Discord. It goes "
                         "slowly on purpose (about 100 messages every 2 seconds).",
                 bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9), anchor="w", wraplength=580,
                 justify="left").pack(fill="x", pady=(2, 8))
        bar = tk.Frame(b, bg=A.CHAT)
        bar.pack(fill="x")
        A.FlatButton(bar, "Add chats", lambda: self.pick_archive_chats(top),
                     font_size=9, padx=10, pady=4).pack(side="left")
        A.FlatButton(bar, "Import a backup", lambda: self.import_archive_backup(render),
                     bg=A.SELECTED, hover=A.HOVER, font_size=9, padx=10, pady=4).pack(
            side="left", padx=6)
        self.sync_btn = A.FlatButton(bar, "Update now", lambda: self.sync_archive(manual=True),
                                     bg=A.SELECTED, hover=A.HOVER, font_size=9, padx=10, pady=4)
        self.sync_btn.pack(side="left")
        auto = tk.BooleanVar(value=self.settings.get("archive_autosync", True) is not False)
        A.OptionCheck(b, "Keep the archive up to date by itself (every 6 hours while the app "
                         "is open)", auto, A.CHAT,
                      command=lambda: (self.settings.__setitem__("archive_autosync", auto.get()),
                                       self.save_settings())).pack(anchor="w", pady=8)
        self.sync_lbl = tk.Label(b, notr=True, text="", bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9),
                                 anchor="w")
        self.sync_lbl.pack(fill="x")
        sf = A.ScrollFrame(b, A.CHAT)
        sf.pack(fill="both", expand=True, pady=(6, 0))

        def render():
            sf.clear()
            rows = ar.chats(me)
            if not rows:
                tk.Label(sf.inner, text="No chats yet. Click Add chats.", bg=A.CHAT,
                         fg=A.MUTED, font=(A.FONT, 10)).pack(pady=30)
            for c in rows:
                f = tk.Frame(sf.inner, bg=A.SIDEBAR, padx=10, pady=6)
                f.pack(fill="x", pady=2, padx=(0, 10))
                tk.Label(f, notr=True, text=c["name"], bg=A.SIDEBAR, fg=A.WHITE,
                         font=(A.FONT, 10, "bold")).pack(side="left")
                state = i18n.tr("complete") if c.get("complete") else i18n.tr("still loading")
                when = _fmt_ts(c["synced"]) if c.get("synced") else i18n.tr("never")
                tk.Label(f, notr=True, text=f"  {c['count']:,} · {state} · {when}",
                         bg=A.SIDEBAR, fg=A.MUTED, font=(A.FONT, 8)).pack(side="left")
                x = tk.Label(f, text="✕", bg=A.SIDEBAR, fg=A.MUTED, cursor="hand2")
                x.pack(side="right")
                x.bind("<Button-1>", lambda e, c=c: remove(c))
                A.Tooltip(x, lambda: "Remove from the archive")

        def remove(c):
            if A.messagebox.askyesno(A.APP_NAME, _t("Remove {name} and its {n} saved messages "
                                                   "from this PC?", name=c["name"], n=c["count"])):
                ar.remove_chat(me, c["channel_id"])
                render()
        self._arch_render = render
        render()

    def pick_archive_chats(self, parent_top=None):
        A = self._A
        top, b = self.dialog(i18n.tr("Add chats"), 520, 620)
        me = self.me_id()
        ar = self.archive()
        tk.Label(b, text="Add chats to the archive", bg=A.CHAT, fg=A.WHITE,
                 font=(A.FONT, 13, "bold"), anchor="w").pack(fill="x")
        tk.Label(b, text="Tip: for a server channel, open it and use its ⋯ / right-click menu "
                         "\"Archive this chat\".", bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 8),
                 anchor="w", wraplength=460, justify="left").pack(fill="x", pady=(2, 8))
        sf = A.ScrollFrame(b, A.CHAT)
        sf.pack(fill="both", expand=True)
        picks = {}
        items = [(d["id"], d["name"], d["kind"], None) for d in self.dms or []]
        p = self.preview
        if p and p.get("source") == "live" and p.get("channel_id") not in [i[0] for i in items]:
            cid = p["channel_id"]
            items.insert(0, (cid, self.chat_name_of(cid), "channel", self.channel_guild.get(cid)))
        for cid, name, kind, gid in items:
            if ar.has_chat(me, cid):
                continue
            v = tk.BooleanVar(value=False)
            picks[cid] = (v, name, kind, gid)
            oc = A.OptionCheck(sf.inner, name, v, A.CHAT)
            oc.label._notr = True
            oc.label.configure(text=name)
            oc.pack(anchor="w", pady=2)

        def all_on():
            for v, *_ in picks.values():
                v.set(True)

        def add():
            n = 0
            for cid, (v, name, kind, gid) in picks.items():
                if v.get():
                    ar.add_chat(me, cid, name, kind, gid)
                    n += 1
            top.destroy()
            if n:
                self.sync_archive(manual=True)
                render = getattr(self, "_arch_render", None)
                if render:
                    try:
                        render()
                    except tk.TclError:
                        pass
        bar = tk.Frame(b, bg=A.CHAT)
        bar.pack(fill="x", pady=(8, 0))
        A.FlatButton(bar, "Add", add).pack(side="right")
        A.FlatButton(bar, "Select all", all_on, bg=A.SELECTED, hover=A.HOVER).pack(side="right",
                                                                                   padx=6)

    def archive_open_chat(self):
        p = self.preview
        if not p or p.get("source") != "live":
            return
        cid = p["channel_id"]
        d = next((x for x in self.dms or [] if x["id"] == cid), None)
        self.archive().add_chat(self.me_id(), cid, d["name"] if d else self.chat_name_of(cid),
                                d["kind"] if d else "channel", self.channel_guild.get(cid))
        self.set_status(i18n.tr("Added to the archive. It keeps loading in the background."))
        self.sync_archive(manual=True)

    def import_archive_backup(self, then=None):
        A = self._A
        folder = A.filedialog.askdirectory(title="Pick a backup folder (it has messages.json)")
        if not folder:
            return
        try:
            title, n = self.archive().import_backup(self.me_id(), folder)
            A.messagebox.showinfo(A.APP_NAME, _t("Imported {n} messages from {name}.", n=n,
                                                 name=title))
        except Exception as e:
            A.messagebox.showerror(A.APP_NAME, _t("Could not import that backup: {e}", e=e))
        if then:
            then()

    def sync_archive(self, manual=False):
        if self._sync_busy:
            return
        me = self.me_id()
        if not me:
            return
        self._sync_busy = True
        stop = self._A.threading.Event()
        self._sync_stop = stop
        sleep = (lambda s: None) if self.demo is not None else stop.wait

        def say(text):
            def ui():
                lbl = getattr(self, "sync_lbl", None)
                try:
                    if lbl is not None and lbl.winfo_exists():
                        lbl.configure(text=text)
                except tk.TclError:
                    pass
                if manual:
                    self.set_status(text)
            self.after(0, ui)

        def work():
            total = 0
            try:
                total = self.archive().sync_all(
                    self.make_api(), me, stop.is_set, sleep,
                    lambda name, n: say(_t("Archive: {name}, {n} new…", name=name, n=f"{n:,}")))
            except Exception as e:
                say(str(e))

            def done():
                self._sync_busy = False
                self.settings["archive_synced"] = time.time()
                self.save_settings()
                say(_t("Archive up to date ({n} new messages).", n=f"{total:,}"))
                render = getattr(self, "_arch_render", None)
                if render:
                    try:
                        render()
                    except tk.TclError:
                        pass
            self.after(0, done)
        self._bg(work)

    def archive_auto_tick(self):
        try:
            if self.settings.get("archive_autosync", True) is not False and \
                    time.time() - float(self.settings.get("archive_synced", 0) or 0) > AUTO_SYNC_S \
                    and not self.running and self.archive().chats(self.me_id()):
                self.sync_archive()
        finally:
            self.after(30 * 60 * 1000, self.archive_auto_tick)

    # ================================================================ recap
    def open_recap(self, year=None):
        A = self._A
        me = self.me_id()
        ar = self.archive()
        years = ar.years(me)
        top, outer = self.dialog(i18n.tr("Your year"), 820, 760)
        sf = A.ScrollFrame(outer, A.CHAT)
        sf.pack(fill="both", expand=True)
        b = sf.inner
        if not years:
            tk.Label(b, text="Your year", bg=A.CHAT, fg=A.WHITE, font=(A.FONT, 15, "bold")).pack(
                anchor="w")
            tk.Label(b, text="This is made from your archive, so add some chats first. "
                             "Nothing is sent anywhere.", bg=A.CHAT, fg=A.MUTED,
                     font=(A.FONT, 10), wraplength=600).pack(anchor="w", pady=10)
            A.FlatButton(b, "Add chats", lambda: (top.destroy(), self.pick_archive_chats())).pack(
                anchor="w")
            return
        if year is None:
            year = years[0]
        r = ar.recap(me, self.me["id"], year or None)
        head = tk.Frame(b, bg=A.CHAT)
        head.pack(fill="x")
        tk.Label(head, notr=True, text=f"{i18n.tr('Your year')} · "
                 f"{year or i18n.tr('All time')}", bg=A.CHAT, fg=A.WHITE,
                 font=(A.FONT, 15, "bold")).pack(side="left")
        A.FlatButton(head, "Save as a page to share", lambda: self.save_recap(r),
                     bg=A.SELECTED, hover=A.HOVER, font_size=9, padx=10, pady=4).pack(side="right")
        ys = tk.Frame(b, bg=A.CHAT)
        ys.pack(fill="x", pady=(6, 10))
        for y in years + [0]:
            on = y == year
            w = tk.Label(ys, notr=True, text=str(y) if y else i18n.tr("All time"),
                         bg=A.BLURPLE if on else A.SIDEBAR, fg="white" if on else A.TEXT,
                         font=(A.FONT, 9), padx=9, pady=3, cursor="hand2")
            w.pack(side="left", padx=(0, 4))
            w.bind("<Button-1>", lambda e, y=y: (top.destroy(), self.open_recap(y)))
        cards = tk.Frame(b, bg=A.CHAT)
        cards.pack(fill="x")
        hour = r["busiest_hour"]
        for label, value in (("Messages you sent", f"{r['mine']:,}"),
                             ("Days you talked", f"{r['active_days']:,}"),
                             ("Best streak (days in a row)", f"{r['streak']:,}"),
                             ("Busiest hour", "—" if hour is None else f"{hour}:00")):
            c = tk.Frame(cards, bg=A.SIDEBAR, padx=14, pady=10)
            c.pack(side="left", padx=(0, 8), fill="x", expand=True)
            tk.Label(c, notr=True, text=value, bg=A.SIDEBAR, fg=A.WHITE,
                     font=(A.FONT, 17, "bold"), anchor="w").pack(fill="x")
            tk.Label(c, text=label, bg=A.SIDEBAR, fg=A.MUTED, font=(A.FONT, 8),
                     anchor="w").pack(fill="x")
        self.recap_bars(b, "By hour", r["hours"], [str(i) if i % 3 == 0 else "" for i in range(24)])
        self.recap_bars(b, "By month", r["months"], archive.MONTH_NAMES)
        lists = tk.Frame(b, bg=A.CHAT)
        lists.pack(fill="x", pady=(8, 0))
        for i, (title, items) in enumerate((("People who talked to you most", r["people"]),
                                            ("Busiest chats", r["chats"]),
                                            ("Your words", r["words"][:8]),
                                            ("Your emojis", r["emojis"]))):
            box = tk.Frame(lists, bg=A.SIDEBAR, padx=12, pady=8)
            box.grid(row=i // 2, column=i % 2, sticky="nsew", padx=4, pady=4)
            tk.Label(box, text=title, bg=A.SIDEBAR, fg=A.WHITE, font=(A.FONT, 10, "bold"),
                     anchor="w").pack(fill="x")
            for k, v in items or [("—", 0)]:
                ln = tk.Frame(box, bg=A.SIDEBAR)
                ln.pack(fill="x")
                tk.Label(ln, notr=True, text=str(k), bg=A.SIDEBAR, fg=A.TEXT,
                         font=(A.FONT, 9)).pack(side="left")
                tk.Label(ln, notr=True, text=f"{v:,}" if v else "", bg=A.SIDEBAR, fg=A.MUTED,
                         font=(A.FONT, 9)).pack(side="right")
        lists.grid_columnconfigure(0, weight=1, uniform="r")
        lists.grid_columnconfigure(1, weight=1, uniform="r")
        tk.Label(b, text="Only chats in your archive are counted.", bg=A.CHAT, fg=A.MUTED,
                 font=(A.FONT, 8), anchor="w").pack(fill="x", pady=(8, 0))

    def recap_bars(self, parent, title, values, labels):
        A = self._A
        box = tk.Frame(parent, bg=A.SIDEBAR, padx=12, pady=8)
        box.pack(fill="x", pady=(8, 0))
        tk.Label(box, text=title, bg=A.SIDEBAR, fg=A.WHITE, font=(A.FONT, 10, "bold"),
                 anchor="w").pack(fill="x")
        w, h = 740, 120
        c = tk.Canvas(box, width=w, height=h, bg=A.SIDEBAR, highlightthickness=0)
        c.pack(fill="x")
        top = max(values) or 1
        n = len(values)
        bw = (w - 10) / n
        for i, v in enumerate(values):
            x0 = 5 + i * bw + 2
            bh = (h - 22) * v / top
            c.create_rectangle(x0, h - 16 - bh, x0 + bw - 4, h - 16, fill=A.BLURPLE, width=0)
            if labels[i]:
                c.create_text(x0 + (bw - 4) / 2, h - 7, text=labels[i], fill=A.MUTED,
                              font=(A.FONT, 7))

    def save_recap(self, r):
        A = self._A
        folder = os.path.join(os.path.expanduser("~"), "Documents", "Discord Cleaner Backups")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"Your year {r['year'] or 'all time'}.html")
        archive.recap_html(r, self.my_name(), path)
        A.open_path(path)
        self.set_status(_t("Saved: {path}", path=path))

    # ================================================================ reminders
    def ask_time(self, title, then, default=""):
        """Small dialog: quick choices + type your own ("6pm", "tomorrow 9am", "45m")."""
        A = self._A
        top, b = self.dialog(title, 440, 400)
        tk.Label(b, notr=True, text=title, bg=A.CHAT, fg=A.WHITE, font=(A.FONT, 13, "bold"),
                 anchor="w").pack(fill="x")
        for label, ts in planner.quick_times():
            A.FlatButton(b, label, lambda ts=ts: (top.destroy(), then(ts)), bg=A.SIDEBAR,
                         hover=A.HOVER, font_size=9, pady=5, bold=False).pack(fill="x", pady=2)
        tk.Label(b, text="Or type a time: 6pm, 18:30, tomorrow 9am, 45m, monday 8am",
                 bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 8), anchor="w").pack(fill="x", pady=(8, 2))
        row = tk.Frame(b, bg=A.CHAT)
        row.pack(fill="x")
        box, e = A.entry_box(row, "When?", width=22)
        box.pack(side="left")
        if default:
            e.insert(0, default)
        shown = tk.Label(b, notr=True, text="", bg=A.CHAT, fg=A.GOOD_FG, font=(A.FONT, 9),
                         anchor="w")
        shown.pack(fill="x", pady=4)

        def parsed():
            return planner.parse_when(e.get())

        def key(_e=None):
            ts = parsed()
            shown.configure(text=datetime.fromtimestamp(ts).strftime("%a %b %d, %H:%M")
                            if ts else "", fg=A.GOOD_FG)

        def ok(_e=None):
            ts = parsed()
            if not ts or ts < time.time():
                shown.configure(text=i18n.tr("I don't understand that time."), fg=A.ERROR_FG)
                return
            top.destroy()
            then(ts)
        e.bind("<KeyRelease>", key)
        e.bind("<Return>", ok)
        A.FlatButton(row, "OK", ok, font_size=9, padx=12, pady=4).pack(side="left", padx=6)
        e.focus_set()
        return top

    def add_remind_menu(self, menu, m):
        sub = tk.Menu(menu, tearoff=0, bg=self._A.TIP_BG, fg=self._A.TEXT,
                      activebackground=self._A.BLURPLE, activeforeground="white", bd=0)
        for label, ts in planner.quick_times():
            sub.add_command(label=label, command=lambda ts=ts: self.remind_about(m, ts))
        sub.add_command(label="Pick a time…", command=lambda: self.ask_time(
            i18n.tr("Remind me about this"), lambda ts: self.remind_about(m, ts)))
        menu.add_cascade(label=i18n.tr("Remind me about this"), menu=sub)

    def remind_about(self, m, ts, note=""):
        cid = m.get("channel_id")
        planner.add_reminder(self.me_id(), ts, note, m, self.chat_name_of(cid),
                             self.channel_guild.get(cid))
        self.set_status(_t("I'll remind you {when}.", when=planner.when_text(ts)))

    def open_reminder_target(self, r):
        self.show_from_tray()
        if r.get("channel_id"):
            self.goto_message(r["channel_id"], r.get("message_id"), r.get("guild"))
        else:
            self.open_reminders()

    def open_reminders(self):
        A = self._A
        top, b = self.dialog(i18n.tr("Reminders"), 640, 640)
        me = self.me_id()
        head = tk.Frame(b, bg=A.CHAT)
        head.pack(fill="x")
        tk.Label(head, text="Reminders", bg=A.CHAT, fg=A.WHITE, font=(A.FONT, 14, "bold")).pack(
            side="left")
        A.FlatButton(head, "New reminder", lambda: new(), font_size=9, padx=10, pady=4).pack(
            side="right")
        tk.Label(b, text="Right-click any message → Remind me about this. You get a "
                         "notification, even with the window in the tray.", bg=A.CHAT,
                 fg=A.MUTED, font=(A.FONT, 9), anchor="w", wraplength=580,
                 justify="left").pack(fill="x", pady=(2, 8))
        sf = A.ScrollFrame(b, A.CHAT)
        sf.pack(fill="both", expand=True)

        def new():
            top2, b2 = self.dialog(i18n.tr("New reminder"), 420, 200)
            tk.Label(b2, text="What should I remind you about?", bg=A.CHAT, fg=A.WHITE,
                     font=(A.FONT, 10, "bold"), anchor="w").pack(fill="x")
            box, e = A.entry_box(b2, "Call Alex back", width=36)
            box.pack(fill="x", pady=8)

            def nxt():
                note = e.get().strip()
                if not note:
                    return
                top2.destroy()
                self.ask_time(i18n.tr("When?"), lambda ts: (planner.add_reminder(
                    me, ts, note), render()))
            A.FlatButton(b2, "Next", nxt).pack(anchor="e")
            e.bind("<Return>", lambda _e: nxt())
            e.focus_set()

        def render():
            sf.clear()
            rs = sorted(planner.reminders(me), key=lambda r: (r.get("done"), r["at"]))
            if not rs:
                tk.Label(sf.inner, text="No reminders yet.", bg=A.CHAT, fg=A.MUTED,
                         font=(A.FONT, 10)).pack(pady=30)
            for r in rs:
                bg = A.SIDEBAR if not r.get("done") else A.CHAT
                f = tk.Frame(sf.inner, bg=bg, padx=10, pady=6)
                f.pack(fill="x", pady=2, padx=(0, 10))
                hd = tk.Frame(f, bg=bg)
                hd.pack(fill="x")
                when = planner.when_text(r["at"])
                tk.Label(hd, notr=True, text=("✓ " if r.get("done") else "⏰ ") + when, bg=bg,
                         fg=A.MUTED if r.get("done") else A.WHITE,
                         font=(A.FONT, 9, "bold")).pack(side="left")
                tk.Label(hd, notr=True, text="  " + " · ".join(x for x in (r.get("author"),
                                                                        r.get("chat")) if x),
                         bg=bg, fg=A.MUTED, font=(A.FONT, 8)).pack(side="left")
                x = tk.Label(hd, text="✕", bg=bg, fg=A.MUTED, cursor="hand2")
                x.pack(side="right")
                x.bind("<Button-1>", lambda e, r=r: (planner.delete_reminder(r["id"]), render()))
                if r.get("channel_id"):
                    A.LinkLabel(hd, "Open", lambda r=r: (top.destroy(), self.open_reminder_target(
                        r)), bg, font_size=8).pack(side="right", padx=6)
                A.LinkLabel(hd, "Snooze 1 hour", lambda r=r: (planner.finish_reminder(
                    r["id"], time.time() + 3600), render()), bg, font_size=8).pack(side="right")
                txt = r.get("note") or r.get("text") or ""
                if r.get("note") and r.get("text"):
                    txt += f"\n“{r['text'][:140]}”"
                tk.Label(f, notr=True, text=txt, bg=bg, fg=A.TEXT, font=(A.FONT, 9),
                         anchor="w", justify="left", wraplength=540).pack(fill="x")
            if any(r.get("done") for r in rs):
                A.LinkLabel(sf.inner, "Clear finished reminders",
                            lambda: (planner.clear_done_reminders(me), render()), A.CHAT,
                            font_size=8).pack(anchor="e", pady=6, padx=10)
        render()

    # ================================================================ send later
    def send_later(self):
        A = self._A
        if not self.can_chat():
            return
        if not self.risk_gate("send"):
            return
        text = self.mention_convert(self.composer.get("1.0", "end-1c").strip())
        if not text:
            A.messagebox.showinfo(A.APP_NAME, "Write the message first, then pick when to send it.")
            return
        cid = self.preview["channel_id"]
        reply = (self.reply_to or {}).get("id")

        def go(ts):
            try:
                planner.schedule(self.me_id(), cid, self.chat_name_of(cid), text, ts, reply)
            except ValueError as e:
                A.messagebox.showwarning(A.APP_NAME, str(e))
                return
            self.composer.delete("1.0", "end")
            self.cancel_reply(quiet=True)
            self.on_composer_key()
            self.toast("🕓 " + i18n.tr("Scheduled"),
                       _t("It will be sent {when}. Keep the app open (the tray is fine).",
                          when=planner.when_text(ts)), action=self.open_scheduled)
        self.ask_time(i18n.tr("Send later"), go)

    def open_scheduled(self):
        A = self._A
        top, b = self.dialog(i18n.tr("Scheduled messages"), 660, 620)
        me = self.me_id()
        tk.Label(b, text="Scheduled messages", bg=A.CHAT, fg=A.WHITE,
                 font=(A.FONT, 14, "bold"), anchor="w").pack(fill="x")
        tk.Label(b, text="Write a message, then click 🕓 next to the box. The app sends it at "
                         "that time if it's open (the tray is fine). If it was closed, the "
                         "message waits here as missed: nothing is sent by surprise.",
                 bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9), anchor="w", wraplength=600,
                 justify="left").pack(fill="x", pady=(2, 8))
        sf = A.ScrollFrame(b, A.CHAT)
        sf.pack(fill="both", expand=True)
        names = {"pending": "Waiting", "missed": "Missed (app was closed)", "sent": "Sent",
                 "failed": "Failed", "sending": "Sending…"}
        colors = {"missed": A.ERROR_FG, "failed": A.ERROR_FG, "sent": A.GOOD_FG}

        def render():
            sf.clear()
            items = sorted(planner.scheduled(me), key=lambda x: (x["status"] == "sent", x["at"]))
            if not items:
                tk.Label(sf.inner, text="Nothing scheduled.", bg=A.CHAT, fg=A.MUTED,
                         font=(A.FONT, 10)).pack(pady=30)
            for x in items:
                f = tk.Frame(sf.inner, bg=A.SIDEBAR, padx=10, pady=6)
                f.pack(fill="x", pady=2, padx=(0, 10))
                hd = tk.Frame(f, bg=A.SIDEBAR)
                hd.pack(fill="x")
                tk.Label(hd, notr=True, text=f"{x.get('chat', '')}  ·  {planner.when_text(x['at'])}",
                         bg=A.SIDEBAR, fg=A.WHITE, font=(A.FONT, 9, "bold")).pack(side="left")
                tk.Label(hd, text=names.get(x["status"], x["status"]), bg=A.SIDEBAR,
                         fg=colors.get(x["status"], A.MUTED), font=(A.FONT, 8)).pack(
                    side="left", padx=8)
                dl = tk.Label(hd, text="✕", bg=A.SIDEBAR, fg=A.MUTED, cursor="hand2")
                dl.pack(side="right")
                dl.bind("<Button-1>", lambda e, x=x: (planner.delete_send(x["id"]), render()))
                if x["status"] in ("pending", "missed", "failed"):
                    A.LinkLabel(hd, "Send now", lambda x=x: (self.send_scheduled(x, True),
                                                            self.after(600, render)),
                                A.SIDEBAR, font_size=8).pack(side="right", padx=6)
                    A.LinkLabel(hd, "Change time", lambda x=x: self.ask_time(
                        i18n.tr("Send later"), lambda ts, x=x: (planner.update_send(
                            x["id"], at=ts, status="pending"), render())),
                        A.SIDEBAR, font_size=8).pack(side="right")
                tk.Label(f, notr=True, text=x["content"][:400], bg=A.SIDEBAR, fg=A.TEXT,
                         font=(A.FONT, 9), anchor="w", justify="left", wraplength=580).pack(fill="x")
                if x.get("error"):
                    tk.Label(f, notr=True, text=x["error"], bg=A.SIDEBAR, fg=A.ERROR_FG,
                             font=(A.FONT, 8), anchor="w").pack(fill="x")
        render()

    # ================================================================ snippets
    def setup_everyday_composer(self, box):
        A = self._A
        for icon, tip, fn in (("🕓", "Send later", self.send_later),
                              ("📝", "Saved replies", self.snippet_menu)):
            w = tk.Label(box, notr=True, text=icon, bg=A.FIELD_BG, fg=A.ICON_MUTED,
                         font=(A.FONT, 11), cursor="hand2", padx=3)
            w.pack(side="right", padx=(0, 2), pady=9, anchor="n")
            w.bind("<Button-1>", lambda e, fn=fn: self.can_chat() and fn(e))
            A.Tooltip(w, lambda tip=tip: tip)
        self.composer.bind("<Tab>", self.expand_snippet, add="+")

    def snippet_menu(self, event=None):
        A = self._A
        menu = tk.Menu(self, tearoff=0, bg=A.TIP_BG, fg=A.TEXT, activebackground=A.BLURPLE,
                       activeforeground="white", bd=0, font=(A.FONT, 9))
        for s in planner.snippets()[:25]:
            menu.add_command(label=f";{s['name']}   {s['text'][:40]}",
                             command=lambda s=s: self.insert_snippet(s["text"]))
        if planner.snippets():
            menu.add_separator()
        menu.add_command(label=i18n.tr("Manage saved replies…"), command=self.open_snippets)
        try:
            x = event.x_root if event is not None else self.winfo_pointerx()
            y = event.y_root if event is not None else self.winfo_pointery()
            menu.tk_popup(x, y - 40)
        finally:
            menu.grab_release()

    def insert_snippet(self, text):
        self.composer.insert("insert", text)
        self.composer.focus_set()
        self.on_composer_key()

    def expand_snippet(self, _e=None):
        if self.mention_visible():
            return None
        try:
            before = self.composer.get("insert linestart", "insert")
        except tk.TclError:
            return None
        word = before.split(" ")[-1] if before else ""
        text = planner.expand(word)
        if text is None:
            return None
        self.composer.delete(f"insert-{len(word)}c", "insert")
        self.composer.insert("insert", text)
        self.on_composer_key()
        return "break"

    def open_snippets(self, prefill=""):
        A = self._A
        top, b = self.dialog(i18n.tr("Saved replies"), 600, 640)
        tk.Label(b, text="Saved replies", bg=A.CHAT, fg=A.WHITE, font=(A.FONT, 14, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(b, text="Type ;name then Tab in the message box, or click 📝.", bg=A.CHAT,
                 fg=A.MUTED, font=(A.FONT, 9), anchor="w").pack(fill="x", pady=(2, 8))
        form = tk.Frame(b, bg=A.SIDEBAR, padx=10, pady=8)
        form.pack(fill="x")
        nbox, ne = A.entry_box(form, "name (like thanks)", width=18)
        nbox.pack(anchor="w")
        txt = tk.Text(form, height=4, bg=A.FIELD_BG, fg=A.TEXT, insertbackground=A.TEXT,
                      font=(A.FONT, 10), bd=0, wrap="word", padx=6, pady=6)
        txt.pack(fill="x", pady=6)
        if prefill:
            txt.insert("1.0", prefill)
        editing = {"id": None}

        def save():
            try:
                planner.save_snippet(ne.get(), txt.get("1.0", "end-1c"), editing["id"])
            except ValueError as e:
                A.messagebox.showwarning(A.APP_NAME, str(e))
                return
            ne.delete(0, "end")
            txt.delete("1.0", "end")
            editing["id"] = None
            render()
        A.FlatButton(form, "Save", save, font_size=9, padx=12, pady=4).pack(anchor="e")
        sf = A.ScrollFrame(b, A.CHAT)
        sf.pack(fill="both", expand=True, pady=(8, 0))

        def edit(s):
            editing["id"] = s["id"]
            ne.delete(0, "end")
            ne.insert(0, s["name"])
            txt.delete("1.0", "end")
            txt.insert("1.0", s["text"])

        def render():
            sf.clear()
            for s in planner.snippets():
                f = tk.Frame(sf.inner, bg=A.CODE_BG, padx=10, pady=6)
                f.pack(fill="x", pady=2, padx=(0, 10))
                hd = tk.Frame(f, bg=A.CODE_BG)
                hd.pack(fill="x")
                tk.Label(hd, notr=True, text=";" + s["name"], bg=A.CODE_BG, fg=A.WHITE,
                         font=(A.FONT, 10, "bold")).pack(side="left")
                x = tk.Label(hd, text="✕", bg=A.CODE_BG, fg=A.MUTED, cursor="hand2")
                x.pack(side="right")
                x.bind("<Button-1>", lambda e, s=s: (planner.delete_snippet(s["id"]), render()))
                A.LinkLabel(hd, "Edit", lambda s=s: edit(s), A.CODE_BG, font_size=8).pack(
                    side="right", padx=6)
                tk.Label(f, notr=True, text=s["text"][:300], bg=A.CODE_BG, fg=A.TEXT,
                         font=(A.FONT, 9), anchor="w", justify="left", wraplength=520).pack(fill="x")
        render()

    # ================================================================ keyword alerts
    def check_keyword(self, m):
        me = self.me_id()
        if self._alert_cfg is None:
            self._alert_cfg = planner.alert_settings()
        cfg = self._alert_cfg
        word = planner.check_alert(m, me, cfg)
        if not word:
            return
        cid, gid = m.get("channel_id"), m.get("guild_id")
        if cfg.get("ignore_muted", True) and self.mute_of(cid, gid) == "all":
            return
        chat = self.chat_name_of(cid, gid)
        planner.add_to_inbox(me, m, word, chat)
        a = m.get("author") or {}
        who = a.get("global_name") or a.get("username") or "?"
        self.notify_always(f"🔔 {word} · {chat}", f"{who}: {(m.get('content') or '')[:120]}",
                           action=lambda: (self.show_from_tray(), self.goto_message(
                               cid, m.get("id"), gid)))

    def open_alerts(self):
        A = self._A
        me = self.me_id()
        cfg = planner.alert_settings()
        top, outer = self.dialog(i18n.tr("Keyword alerts"), 660, 720)
        b = outer
        tk.Label(b, text="Keyword alerts", bg=A.CHAT, fg=A.WHITE, font=(A.FONT, 14, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(b, text="Get a notification when someone says one of these words in your DMs "
                         "or servers, while the app is open. Only reads messages Discord "
                         "already sends to the app.", bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9),
                 anchor="w", wraplength=600, justify="left").pack(fill="x", pady=(2, 8))
        tk.Label(b, text="Words (one per line or with commas; /regex/ works too)", bg=A.CHAT,
                 fg=A.TEXT, font=(A.FONT, 9, "bold"), anchor="w").pack(fill="x")
        words = tk.Text(b, height=4, bg=A.FIELD_BG, fg=A.TEXT, insertbackground=A.TEXT,
                        font=(A.FONT, 10), bd=0, wrap="word", padx=6, pady=6)
        words.pack(fill="x", pady=4)
        words.insert("1.0", "\n".join(cfg.get("words") or []))
        vs = {k: tk.BooleanVar(value=bool(cfg.get(k, True))) for k in
              ("enabled", "dms", "servers", "ignore_muted")}
        for k, label in (("enabled", "Alerts on"), ("dms", "In DMs"),
                         ("servers", "In servers"), ("ignore_muted", "Not in muted chats")):
            A.OptionCheck(b, label, vs[k], A.CHAT).pack(anchor="w", pady=1)

        def save():
            planner.save_alert_settings(dict({k: v.get() for k, v in vs.items()},
                                             words=planner.parse_words(words.get("1.0", "end-1c"))))
            self._alert_cfg = None
            self.set_status(i18n.tr("Keyword alerts saved."))
        A.FlatButton(b, "Save", save, font_size=9, padx=12, pady=4).pack(anchor="e")
        hd = tk.Frame(b, bg=A.CHAT)
        hd.pack(fill="x", pady=(10, 2))
        tk.Label(hd, text="Inbox", bg=A.CHAT, fg=A.WHITE, font=(A.FONT, 11, "bold")).pack(
            side="left")
        A.LinkLabel(hd, "Clear", lambda: (planner.clear_inbox(me), render()), A.CHAT,
                    font_size=8).pack(side="right")
        sf = A.ScrollFrame(b, A.CHAT)
        sf.pack(fill="both", expand=True)

        def render():
            sf.clear()
            items = planner.alert_inbox(me)
            if not items:
                tk.Label(sf.inner, text="Nothing yet.", bg=A.CHAT, fg=A.MUTED,
                         font=(A.FONT, 10)).pack(pady=20)
            for x in items[:150]:
                bg = A.SIDEBAR if not x.get("seen") else A.CODE_BG
                f = tk.Frame(sf.inner, bg=bg, padx=10, pady=5)
                f.pack(fill="x", pady=2, padx=(0, 10))
                h = tk.Frame(f, bg=bg)
                h.pack(fill="x")
                tk.Label(h, notr=True, text=f"🔔 {x['word']}  ·  {x['author']}  ·  {x.get('chat', '')}"
                         f"  ·  {_fmt_ts(x['at'])}", bg=bg, fg=A.WHITE,
                         font=(A.FONT, 9, "bold")).pack(side="left")
                A.LinkLabel(h, "Open", lambda x=x: (top.destroy(), self.goto_message(
                    x["channel_id"], x["id"], x.get("guild"))), bg, font_size=8).pack(side="right")
                tk.Label(f, notr=True, text=x["text"], bg=bg, fg=A.TEXT, font=(A.FONT, 9),
                         anchor="w", justify="left", wraplength=580).pack(fill="x")
            planner.mark_inbox_seen(me)
        render()

    # ================================================================ privacy sweeper
    def open_sweeper(self, tab="servers"):
        A = self._A
        top, b = self.dialog(i18n.tr("Privacy sweeper"), 700, 740)
        tk.Label(b, text="Privacy sweeper", bg=A.CHAT, fg=A.WHITE, font=(A.FONT, 14, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(b, text="Tidy up your account. Safe mode does these one at a time with random "
                         "pauses and a small daily limit, so it looks like you doing it by hand.",
                 bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9), anchor="w", wraplength=640,
                 justify="left").pack(fill="x", pady=(2, 8))
        tabs = tk.Frame(b, bg=A.CHAT)
        tabs.pack(fill="x")
        for key, label in (("servers", "Leave servers"), ("dms", "Close old DMs"),
                           ("friends", "Inactive friends")):
            on = key == tab
            w = tk.Label(tabs, text=label, bg=A.BLURPLE if on else A.SIDEBAR,
                         fg="white" if on else A.TEXT, font=(A.FONT, 9), padx=10, pady=4,
                         cursor="hand2")
            w.pack(side="left", padx=(0, 4))
            w.bind("<Button-1>", lambda e, k=key: (top.destroy(), self.open_sweeper(k)))
        opts = tk.Frame(b, bg=A.CHAT)
        opts.pack(fill="x", pady=8)
        days_v = tk.StringVar(value=str(self.settings.get("sweep_days", 90)))
        status = tk.Label(b, notr=True, text="", bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9),
                          anchor="w")
        sf = A.ScrollFrame(b, A.CHAT)
        picks = {}
        kind = {"servers": "leave", "dms": "close", "friends": "unfriend"}[tab]

        def days():
            try:
                return max(1, int(days_v.get()))
            except (TypeError, ValueError):
                return 90

        if tab != "servers":
            tk.Label(opts, text="No messages for more than", bg=A.CHAT, fg=A.TEXT,
                     font=(A.FONT, 9)).pack(side="left")
            e = tk.Entry(opts, textvariable=days_v, width=5, bg=A.FIELD_BG, fg=A.TEXT, bd=0,
                         insertbackground=A.TEXT, font=(A.FONT, 10), justify="center")
            e.pack(side="left", padx=6, ipady=3)
            tk.Label(opts, text="days", bg=A.CHAT, fg=A.TEXT, font=(A.FONT, 9)).pack(side="left")
            A.FlatButton(opts, "Find", lambda: (self.settings.__setitem__("sweep_days", days()),
                                                 self.save_settings(), render()),
                         bg=A.SELECTED, hover=A.HOVER, font_size=9, padx=10, pady=3).pack(
                side="left", padx=8)
        status.pack(fill="x")
        sf.pack(fill="both", expand=True, pady=(6, 0))
        bar = tk.Frame(b, bg=A.CHAT)
        bar.pack(fill="x", pady=(8, 0))
        verb = {"servers": "Leave selected servers", "dms": "Close selected DMs",
                "friends": "Remove selected friends"}[tab]
        go_btn = A.FlatButton(bar, verb, lambda: run(), bg=A.RED, hover=A.RED_HI)
        go_btn.pack(side="right")
        stop_btn = A.FlatButton(bar, "Stop", lambda: self._sweep_stop and self._sweep_stop.set(),
                                bg=A.SELECTED, hover=A.HOVER)
        left_lbl = tk.Label(bar, notr=True, text="", bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 8))
        left_lbl.pack(side="left")

        def last_seen(uid):
            for d in self.dms or []:
                if d.get("kind") == "dm" and d.get("user_id") == uid:
                    return d.get("last") or 0
            return 0

        def age_days(sf_id):
            if not sf_id:
                return None
            ts = ((int(sf_id) >> 22) + 1420070400000) / 1000
            return (time.time() - ts) / 86400

        def rows():
            if tab == "servers":
                return [(g["id"], g["name"], i18n.tr("you own it") if g.get("owner") else "",
                         not g.get("owner")) for g in self.guilds]
            if tab == "dms":
                out = []
                for d in self.dms or []:
                    a = age_days(d.get("last"))
                    if a is None or a >= days():
                        tag = (_t("{n} days", n=int(a)) if a is not None else i18n.tr("empty"))
                        if d.get("kind") == "group":
                            tag += " · " + i18n.tr("leaves the group")
                        out.append((d["id"], d["name"], tag, True))
                return out
            out = []
            for r in self.relationships or []:
                if r.get("type") != 1:
                    continue
                a = age_days(last_seen(r["id"]))
                if a is None or a >= days():
                    u = r.get("user") or {}
                    name = u.get("global_name") or u.get("username") or "?"
                    out.append((r["id"], name, _t("{n} days", n=int(a)) if a is not None else
                                i18n.tr("never talked in DMs"), True))
            return out

        def render():
            sf.clear()
            picks.clear()
            if tab == "friends" and self.relationships is None:
                status.configure(text=i18n.tr("Loading your friends…"))
                self.load_relationships(then=render)
                return
            items = rows()
            status.configure(text=_t("{n} found", n=len(items)))
            left_lbl.configure(text=_t("Safe mode: {n} left today", n=safety.left(kind))
                               if safety.enabled() else i18n.tr("Safe mode is off"))
            for iid, name, tag, ok in items:
                v = tk.BooleanVar(value=False)
                f = tk.Frame(sf.inner, bg=A.CHAT)
                f.pack(fill="x", pady=1)
                if ok:
                    picks[iid] = (v, name)
                    oc = A.OptionCheck(f, name, v, A.CHAT)
                    oc.label._notr = True
                    oc.label.configure(text=name)
                    oc.pack(side="left")
                else:
                    tk.Label(f, notr=True, text="   " + name, bg=A.CHAT, fg=A.MUTED,
                             font=(A.FONT, 9)).pack(side="left")
                tk.Label(f, notr=True, text=tag, bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 8)).pack(
                    side="right", padx=10)

        def run():
            chosen = [(i, n) for i, (v, n) in picks.items() if v.get()]
            if not chosen:
                return
            if not self.risk_gate("sweeper"):
                return
            allowed = safety.left(kind)
            if allowed <= 0:
                A.messagebox.showinfo(A.APP_NAME, "Safe mode: today's limit for this is reached. "
                                                  "Try again tomorrow.")
                return
            if len(chosen) > allowed:
                A.messagebox.showinfo(A.APP_NAME, _t("Safe mode allows {n} more today, so only "
                                                     "the first {n} will be done.", n=allowed))
                chosen = chosen[:allowed]
            msg = {"leave": "Leave {n} server(s)? You'd need a new invite to come back.",
                   "close": "Close {n} DM(s)? Messages are not deleted; group DMs are left.",
                   "unfriend": "Remove {n} friend(s)? They are not told, but they'll see it."}[kind]
            if not A.messagebox.askyesno(A.APP_NAME, _t(msg, n=len(chosen)), icon="warning"):
                return
            stop = A.threading.Event()
            self._sweep_stop = stop
            go_btn.set_enabled(False)
            stop_btn.pack(side="right", padx=6)
            wait = (lambda s: None) if self.demo is not None else stop.wait

            def work():
                done = 0
                for i, (iid, name) in enumerate(chosen):
                    if stop.is_set():
                        break
                    if i:
                        wait(safety.gap(kind))
                        if stop.is_set():
                            break
                    path = {"leave": f"/users/@me/guilds/{iid}", "close": f"/channels/{iid}",
                            "unfriend": f"/users/@me/relationships/{iid}"}[kind]
                    st, data = self._call("DELETE", path,
                                          {"lurking": False} if kind == "leave" else None)
                    ok = st in (200, 204)
                    if ok:
                        done += 1
                        safety.use(kind)
                    self.after(0, lambda name=name, ok=ok, st=st, data=data, i=i: (
                        status.winfo_exists() and status.configure(
                            text=f"{i + 1}/{len(chosen)}  {'✓' if ok else '✗'} {name}"
                                 + ("" if ok else "  " + self._err(st, data, "do that")))))
                    if st in (401, 403) and not ok and isinstance(data, dict) and "captcha" in str(data):
                        break
                self.after(0, lambda: finish(done))
            self._bg(work)

        def finish(done):
            try:
                go_btn.set_enabled(True)
                stop_btn.pack_forget()
            except tk.TclError:
                pass
            self.log(_t("Privacy sweeper: {n} done.", n=done), "good")
            if tab == "friends":
                self.relationships = None
            self.refresh()
            try:
                if top.winfo_exists():
                    top.destroy()
            except tk.TclError:
                pass
            self.set_status(_t("Privacy sweeper: {n} done.", n=done))
        render()

    # ================================================================ safety
    def open_safety(self):
        A = self._A
        top, b = self.dialog(i18n.tr("Safe mode"), 600, 640)
        tk.Label(b, text="Safe mode", bg=A.CHAT, fg=A.WHITE, font=(A.FONT, 14, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(b, text="Tools that use your account automatically are against Discord's "
                         "rules, and no app can make that risk zero. Safe mode keeps it as low "
                         "as possible: automatic deletes go one chat at a time, at least 2.5 "
                         "seconds apart with random pauses; bulk actions wait several random "
                         "seconds between each; everything has a daily limit. Reading (archive, "
                         "search, stats, alerts) is not limited.", bg=A.CHAT, fg=A.MUTED,
                 font=(A.FONT, 9), anchor="w", wraplength=540, justify="left").pack(
            fill="x", pady=(2, 10))
        on = tk.BooleanVar(value=safety.enabled())

        def toggle():
            if not on.get() and not A.messagebox.askyesno(
                    A.APP_NAME, "Turn safe mode off? Automatic actions will go faster and "
                                "have no daily limit, which makes a ban more likely.",
                    icon="warning"):
                on.set(True)
                return
            safety.set_enabled(on.get())
            render()
        A.OptionCheck(b, "Safe mode (recommended)", on, A.CHAT, command=toggle).pack(anchor="w")
        table = tk.Frame(b, bg=A.CHAT)
        table.pack(fill="x", pady=10)
        entries = {}

        def render():
            for w in table.winfo_children():
                w.destroy()
            entries.clear()
            for i, (k, name, used, lim) in enumerate(safety.summary()):
                tk.Label(table, text=name, bg=A.CHAT, fg=A.TEXT, font=(A.FONT, 9),
                         anchor="w").grid(row=i, column=0, sticky="w", pady=2)
                tk.Label(table, notr=True, text=_t("{u} today", u=used), bg=A.CHAT,
                         fg=A.MUTED, font=(A.FONT, 9)).grid(row=i, column=1, padx=12)
                v = tk.StringVar(value=str(lim))
                e = tk.Entry(table, textvariable=v, width=6, bg=A.FIELD_BG, fg=A.TEXT, bd=0,
                             insertbackground=A.TEXT, justify="center", font=(A.FONT, 10))
                e.grid(row=i, column=2, ipady=2)
                tk.Label(table, text="per day", bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 8)).grid(
                    row=i, column=3, padx=6)
                entries[k] = v

        def save():
            for k, v in entries.items():
                try:
                    safety.set_limit(k, int(v.get()))
                except (TypeError, ValueError):
                    pass
            render()
            self.set_status(i18n.tr("Safe mode limits saved."))
        render()
        A.FlatButton(b, "Save limits", save, font_size=9, padx=12, pady=4).pack(anchor="e")
        tk.Label(b, text="Also good to know: do big clean-ups in small pieces over several days, "
                         "don't run the app on many accounts from one PC at the same time, and "
                         "if Discord asks for a captcha, stop and do that action in Discord.",
                 bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 8), anchor="w", wraplength=540,
                 justify="left").pack(fill="x", pady=(14, 0))

    # ================================================================ risk tab
    def risk_gate(self, feature):
        """True when this risky feature was switched on in the Risk tab. Otherwise explain
        and offer to open the Risk tab (nothing risky runs without it)."""
        if safety.risk_on(feature):
            return True
        A = self._A
        name = i18n.tr(safety.RISK_FEATURES[feature])
        if A.messagebox.askyesno(A.APP_NAME, _t(
                "'{name}' is a risky feature and it is switched off.\n\nTurn it on in the "
                "Risk tab if you accept the risk. Preview (delete nothing) always works.\n\n"
                "Open the Risk tab now?", name=name), icon="warning"):
            self.open_risk()
        return False

    def open_risk(self):
        A = self._A
        top, b = self.dialog(i18n.tr("Risk tab"), 620, 600)
        tk.Label(b, text="Risk tab", bg=A.CHAT, fg=A.WHITE, font=(A.FONT, 15, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(b, text="These actions use your account like a bot. Discord's rules don't "
                         "allow that, and accounts have been limited, disabled or banned for "
                         "it, even at slow speeds. They are OFF by default. Turn one on only "
                         "if you accept that risk.", bg=A.CHAT, fg=A.RED, font=(A.FONT, 10),
                 anchor="w", wraplength=560, justify="left").pack(fill="x", pady=(4, 12))
        vs = {}
        count = tk.Label(b, notr=True, text="", bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9),
                         anchor="w")

        def show_count():
            count.configure(text=_t("{n} of {m} risky features on", n=safety.risk_count(),
                                    m=len(safety.RISK_FEATURES)))

        def toggle(k):
            if vs[k].get() and not A.messagebox.askyesno(
                    A.APP_NAME, _t("Turn on '{name}'? This is against Discord's rules and your "
                                   "account may be limited, disabled or banned. You do this at "
                                   "your own risk.", name=i18n.tr(safety.RISK_FEATURES[k])),
                    icon="warning"):
                vs[k].set(False)
            safety.set_risk(k, vs[k].get())
            show_count()

        for k, label in safety.RISK_FEATURES.items():
            vs[k] = tk.BooleanVar(value=safety.risk_on(k))
            A.OptionCheck(b, label, vs[k], A.CHAT, command=lambda k=k: toggle(k)).pack(
                anchor="w", pady=3)
        count.pack(fill="x", pady=(10, 4))
        show_count()

        def off():
            safety.all_risk_off()
            for v in vs.values():
                v.set(False)
            show_count()
        A.FlatButton(b, "Turn off all risky features", off, bg=A.SELECTED, hover=A.HOVER,
                     font_size=9, padx=12, pady=5).pack(anchor="w", pady=(2, 12))
        tk.Label(b, text="Always safe: Preview, archive and search, your year, reminders, "
                         "saved replies and keyword alerts. They only read, or work on this "
                         "PC.", bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9), anchor="w",
                 wraplength=560, justify="left").pack(fill="x")
        A.FlatButton(b, "Safe mode", lambda: (top.destroy(), self.open_safety()), bg=A.SELECTED,
                     hover=A.HOVER, font_size=9, padx=12, pady=5).pack(anchor="w", pady=(12, 0))

    def first_launch_warning(self):
        """Shown once, before anything else: what this app can do to your account."""
        if safety.warning_seen():
            return
        safety.set_warning_seen()
        A = self._A
        top, b = self.dialog(i18n.tr("Before you start"), 560, 400)
        tk.Label(b, text="Before you start", bg=A.CHAT, fg=A.WHITE, font=(A.FONT, 15, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(b, text="This app uses your Discord account the way a bot would. Discord's "
                         "rules don't allow that, and accounts using tools like this have been "
                         "limited, disabled or banned, even with slow settings. The risky "
                         "actions (deleting in bulk, clean-up rules, privacy sweeper, "
                         "scheduled messages) are switched off until you turn them on in the "
                         "Risk tab. Reading features (archive, search, your year, reminders, "
                         "alerts and Preview) are low risk.", bg=A.CHAT, fg=A.TEXT,
                 font=(A.FONT, 10), anchor="w", wraplength=500, justify="left").pack(
            fill="x", pady=(8, 16))
        bar = tk.Frame(b, bg=A.CHAT)
        bar.pack(fill="x")
        A.FlatButton(bar, "I understand", top.destroy, font_size=10, padx=14, pady=6).pack(
            side="left")
        A.FlatButton(bar, "Open Risk tab", lambda: (top.destroy(), self.open_risk()),
                     bg=A.SELECTED, hover=A.HOVER, font_size=10, padx=14, pady=6).pack(
            side="left", padx=8)

    # ================================================================ accounts + startup
    def add_account_items(self, menu):
        others = [a for a in self.saved_accounts() if a["id"] != self.me_id()]
        if not others:
            menu.add_command(label=i18n.tr("Add another account…"), command=self.switch_account)
            return
        menu.add_separator()
        for a in others[:8]:
            menu.add_command(label=_t("Switch to {name}", name=a.get("name") or a["id"]),
                             command=lambda a=a: self.quick_switch(a["id"]))
        menu.add_command(label=i18n.tr("Add another account…"), command=self.switch_account)

    def saved_accounts(self):
        try:
            return self._A.securestore.list_accounts()
        except Exception:
            return []

    def quick_switch(self, account_id):
        if self.running:
            self._A.messagebox.showinfo(self._A.APP_NAME, "Stop the cleaner first.")
            return
        self.settings["last_account"] = account_id
        self.switch_account()
        self.after(100, lambda: self.login_account(account_id))

    def app_command(self):
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}" --tray'
        exe = sys.executable
        pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
        main = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        return f'"{pyw if os.path.exists(pyw) else exe}" "{main}" --tray'

    def app_autostart(self, on=None):
        if sys.platform != "win32":
            return False
        import winreg
        key = self._A.logger_service.RUN_KEY
        if on is None:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
                    winreg.QueryValueEx(k, RUN_NAME)
                return True
            except OSError:
                return False
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, self.app_command())
            else:
                try:
                    winreg.DeleteValue(k, RUN_NAME)
                except FileNotFoundError:
                    pass
        return True

    def open_startup(self):
        A = self._A
        top, b = self.dialog(i18n.tr("Start with Windows"), 520, 330)
        tk.Label(b, text="Start with Windows", bg=A.CHAT, fg=A.WHITE, font=(A.FONT, 14, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(b, text="The app opens hidden in the tray (next to the clock) when your PC "
                         "starts, so reminders, scheduled messages, alerts and notifications "
                         "work without you opening it. Needs a saved account (Remember me).",
                 bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9), anchor="w", wraplength=460,
                 justify="left").pack(fill="x", pady=(2, 10))
        on = tk.BooleanVar(value=bool(self.app_autostart()))
        tray = tk.BooleanVar(value=self.settings.get("close_to_tray", True) is not False)

        def set_on():
            ok = self.app_autostart(on.get())
            if not ok:
                on.set(False)
                A.messagebox.showinfo(A.APP_NAME, "This only works on Windows.")
            elif on.get() and not tray.get():
                tray.set(True)
                set_tray()

        def set_tray():
            self.settings["close_to_tray"] = tray.get()
            self.save_settings()
            self.apply_tray_setting()
        A.OptionCheck(b, "Open the app when Windows starts (in the tray)", on, A.CHAT,
                      command=set_on).pack(anchor="w", pady=2)
        A.OptionCheck(b, "Closing the window keeps it running in the tray", tray, A.CHAT,
                      command=set_tray).pack(anchor="w", pady=2)

    def start_hidden_if_asked(self):
        """--tray: start in the tray (used by Start with Windows)."""
        if "--tray" not in sys.argv:
            return
        self.withdraw()

        def fallback():
            if self.main_frame is None or self.tray is None:
                self.deiconify()
        self.after(20000, fallback)
