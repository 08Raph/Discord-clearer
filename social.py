"""Everyday-Discord features for the app window: a switch that hides every cleaning tool,
the Friends page, your status and custom status, profile cards, pinned messages, editing
your display name / About me, and calls handed over to Discord.

Mixed into App (app.py). Widgets and colours come from the app module at run time so this
file has no import cycle."""
import os
import sys
import tkinter as tk
import webbrowser

import cleaner_core as core
import i18n

STATUS = [("online", "Online", "#23a55a"), ("idle", "Idle", "#f0b232"),
          ("dnd", "Do Not Disturb", "#f23f43"), ("invisible", "Invisible", "#80848e")]
STATUS_COLOR = {k: c for k, _n, c in STATUS}
STATUS_NAME = dict((k, n) for k, n, _c in STATUS)
STATUS_NAME["offline"] = "Offline"
SOCIAL_EVENTS = {"READY", "READY_SUPPLEMENTAL", "PRESENCE_UPDATE", "RELATIONSHIP_ADD",
                 "RELATIONSHIP_REMOVE", "RELATIONSHIP_UPDATE"}
TABS = [("online", "Online"), ("all", "All"), ("pending", "Pending"), ("blocked", "Blocked")]


def _name(u):
    return (u or {}).get("global_name") or (u or {}).get("username") or "?"


class SocialMixin:
    # defaults (class attributes, so Tk's attribute forwarding never kicks in)
    relationships = None
    presence = None
    friends_tab = None
    live_session = None
    friends_badge = None
    friends_row_frame = None
    me_avatar = None
    user_status = None
    _fr_pending = False
    _cleaner_packed = True

    # ------------------------------------------------------------------ helpers
    @property
    def _A(self):
        return sys.modules[type(self).__module__]

    def _bg(self, fn):
        self._A.threading.Thread(target=fn, daemon=True).start()

    def _call(self, method, path, body=None):
        """Request from a worker thread; returns (status, data)."""
        try:
            return self.make_api().request(method, path, body)
        except Exception as e:          # network problems
            return 0, {"message": str(e)}

    def _err(self, st, data, what):
        msg = (data or {}).get("message") if isinstance(data, dict) else None
        if isinstance(data, dict) and (data.get("captcha_key") or "captcha" in str(data).lower()):
            return i18n.tr("Discord asked for a captcha. Do this one in the Discord app.")
        return msg or core.friendly_error(st, what)

    # ------------------------------------------------------------------ cleaning tools on / off
    def clean_mode(self):
        return self.settings.get("show_cleaner", True) is not False

    def toggle_clean_mode(self):
        self.settings["show_cleaner"] = not self.clean_mode()
        self.save_settings()
        self.apply_clean_mode()

    def apply_clean_mode(self):
        """Show or hide the delete panel, checkboxes, red highlights and cleaner-only views."""
        if self.main_frame is None:
            return
        on = self.clean_mode()
        try:
            if on and not getattr(self, "_cleaner_packed", True):
                self.cleaner.pack(side="right", fill="y", before=self.sidebar)
            elif not on:
                self.cleaner.pack_forget()
            self._cleaner_packed = on
            self.clean_btn.configure(fg=self._A.RED if on else self._A.MUTED)
        except (tk.TclError, AttributeError):
            pass
        self.rebuild_rail()
        view = self.view if (on or self.view != "pkg") else "dms"
        if view == "deleted" and self.settings.get("show_deleted_view", True) is False:
            view = "dms"
        for v in list(self.view_frames):
            if v != view:
                self.invalidate_view(v)
        self.open_view(view, rebuild=True)
        self.update_chat_header_check()
        if self.preview:
            self.refresh_highlights()
        elif self.friends_showing():
            self.render_friends()

    def rebuild_rail(self):
        try:
            for w in self.rail.inner.winfo_children():
                w.destroy()
        except tk.TclError:
            return
        self.rail_items = {}
        self.build_rail()
        self.update_rail()

    # ------------------------------------------------------------------ presence & live events
    def my_status(self):
        return self.settings.get("my_status") or "online"

    def presence_payload(self):
        text = (self.settings.get("custom_status") or "").strip()
        return {"status": self.my_status(), "since": 0, "afk": False,
                "activities": [{"type": 4, "name": "Custom Status", "state": text}] if text else []}

    def set_my_status(self, status=None, custom=None):
        if status is not None:
            self.settings["my_status"] = status
        if custom is not None:
            self.settings["custom_status"] = custom.strip()[:128]
        self.save_settings()
        sess = getattr(self, "live_session", None)
        if sess is not None:
            sess.presence = self.presence_payload()
            sess.send(3, self.presence_payload())
        body = {"status": self.my_status()}
        if custom is not None:
            body["custom_status"] = {"text": self.settings["custom_status"]} \
                if self.settings["custom_status"] else None
        self._bg(lambda: self._call("PATCH", "/users/@me/settings", body))
        self.update_user_panel()

    def status_of(self, uid):
        return (getattr(self, "presence", None) or {}).get(uid, "offline")

    def on_social_event(self, t, d):
        pres = self.presence = getattr(self, "presence", None) or {}
        if t == "READY":
            users = {u.get("id"): u for u in d.get("users") or []}
            rels = []
            for r in d.get("relationships") or []:
                u = r.get("user") or users.get(r.get("user_id") or r.get("id")) or \
                    {"id": r.get("id"), "username": r.get("nickname") or "?"}
                rels.append({"id": r.get("id"), "type": r.get("type"), "user": u})
            if rels:
                self.relationships = rels
            for p in d.get("presences") or []:
                pres[(p.get("user") or {}).get("id") or p.get("user_id")] = p.get("status")
        elif t == "READY_SUPPLEMENTAL":
            for p in (d.get("merged_presences") or {}).get("friends") or []:
                pres[p.get("user_id")] = p.get("status")
        elif t == "PRESENCE_UPDATE" and not d.get("guild_id"):
            pres[(d.get("user") or {}).get("id")] = d.get("status")
        elif t.startswith("RELATIONSHIP_"):
            if t == "RELATIONSHIP_ADD" and d.get("type") == 3:
                self.notify(i18n.tr("Friend request"), _name(d.get("user")))
            self.load_relationships()
            return
        self.update_presence_dots()
        if self.friends_showing():
            self.schedule_friends_redraw()

    def schedule_friends_redraw(self):
        if getattr(self, "_fr_pending", False):
            return
        self._fr_pending = True

        def go():
            self._fr_pending = False
            if self.friends_showing():
                self.render_friends()
        self.after(400, go)

    def update_presence_dots(self):
        for d in getattr(self, "dms", []) or []:
            if d.get("kind") != "dm":
                continue
            row = self.row_frames.get(("dm", d["id"]))
            av = getattr(row, "avatar", None) if row is not None else None
            if av is None:
                continue
            st = self.status_of(d.get("user_id"))
            try:
                av.set_badge(st not in ("offline", None), STATUS_COLOR.get(st, "#80848e"))
            except (tk.TclError, AttributeError):
                pass

    # ------------------------------------------------------------------ user panel (bottom left)
    def update_user_panel(self):
        st = self.my_status()
        try:
            if getattr(self, "me_avatar", None) is not None:
                self.me_avatar.set_badge(True, STATUS_COLOR.get(st, "#23a55a"))
            if getattr(self, "user_status", None) is not None:
                custom = (self.settings.get("custom_status") or "").strip()
                self.user_status.configure(text=custom or i18n.tr(STATUS_NAME.get(st, "Online")))
        except tk.TclError:
            pass

    def open_status_menu(self, event=None):
        A = self._A
        menu = tk.Menu(self, tearoff=0, bg=A.SIDEBAR, fg=A.TEXT, activebackground=A.BLURPLE,
                       activeforeground="white", bd=0)
        for k, label, _c in STATUS:
            mark = "●  " if k == self.my_status() else "    "
            menu.add_command(label=mark + i18n.tr(label), command=lambda k=k: self.set_my_status(k))
        menu.add_separator()
        menu.add_command(label=i18n.tr("Set a custom status…"), command=self.ask_custom_status)
        menu.add_command(label=i18n.tr("Edit my profile…"), command=self.open_profile_editor)
        menu.add_command(label=i18n.tr("My profile card"), command=lambda: self.open_profile(self.me))
        if hasattr(self, "add_account_items"):
            self.add_account_items(menu)
        try:
            x = event.x_root if event else self.winfo_pointerx()
            y = event.y_root if event else self.winfo_pointery()
            menu.tk_popup(x, y - 220)
        finally:
            menu.grab_release()

    def ask_custom_status(self):
        A = self._A
        top, body = self.dialog(i18n.tr("Custom status"), 420, 210)
        tk.Label(body, text="Set a custom status", bg=A.CHAT, fg=A.WHITE,
                 font=(A.FONT, 13, "bold")).pack(anchor="w")
        box, ent = A.entry_box(body, "What's happening?", bg=A.INPUT)
        box.pack(fill="x", pady=12)
        ent.insert(0, self.settings.get("custom_status") or "")
        row = tk.Frame(body, bg=A.CHAT)
        row.pack(fill="x")

        def save(clear=False):
            self.set_my_status(custom="" if clear else ent.get())
            top.destroy()
        A.FlatButton(row, "Save", save, bg=A.BLURPLE, hover=A.BLURPLE_HI, font_size=9,
                     padx=14, pady=5).pack(side="right")
        A.FlatButton(row, "Clear", lambda: save(True), bg=A.SELECTED, hover=A.HOVER,
                     font_size=9, padx=14, pady=5).pack(side="right", padx=6)
        ent.bind("<Return>", lambda e: save())
        ent.focus_set()

    # ------------------------------------------------------------------ friends page
    def friends_showing(self):
        return self.main_frame is not None and self.open_key is None and self.preview is None \
            and getattr(self, "friends_tab", None) is not None

    def load_relationships(self, then=None):
        if self.demo is None and not getattr(self, "token_value", None):
            return

        def work():
            st, data = self._call("GET", "/users/@me/relationships")
            if st == 200 and isinstance(data, list):
                def done():
                    self.relationships = data
                    if self.demo is not None:
                        self.presence = dict(getattr(self.demo, "presence", {}) or {},
                                             **(getattr(self, "presence", None) or {}))
                    self.update_friend_badge()
                    self.update_presence_dots()
                    if then:
                        then()
                    elif self.friends_showing():
                        self.render_friends()
                self.after(0, done)
        self._bg(work)

    def pending_count(self):
        return sum(1 for r in getattr(self, "relationships", []) or [] if r.get("type") == 3)

    def update_friend_badge(self):
        lbl = getattr(self, "friends_badge", None)
        n = self.pending_count()
        try:
            if lbl is not None and lbl.winfo_exists():
                if n:
                    lbl.configure(text=f" {n} ")
                    lbl.pack(side="right", padx=10)
                else:
                    lbl.pack_forget()
        except tk.TclError:
            pass

    def friends_row(self, parent):
        """The 'Friends' entry at the top of the DM list."""
        A = self._A
        row = tk.Frame(parent, bg=A.SIDEBAR, cursor="hand2")
        row.pack(fill="x", padx=8, pady=(8, 2))
        icon = tk.Label(row, text="👥", bg=A.SIDEBAR, fg=A.TEXT, font=("Segoe UI Emoji", 13))
        icon.pack(side="left", padx=(10, 10), pady=6)
        lbl = tk.Label(row, text="Friends", bg=A.SIDEBAR, fg=A.TEXT, font=(A.FONT, 10, "bold"),
                       anchor="w")
        lbl.pack(side="left", fill="x", expand=True)
        self.friends_badge = tk.Label(row, text="", notr=True, bg=A.RED, fg="white",
                                      font=(A.FONT, 8, "bold"))
        self.friends_row_frame = row
        for w in (row, icon, lbl):
            w.bind("<Button-1>", lambda e: self.open_friends())
        self.update_friend_badge()
        self.mark_friends_row()
        return row

    def mark_friends_row(self):
        row = getattr(self, "friends_row_frame", None)
        try:
            if row is not None and row.winfo_exists():
                self._A.set_bg(row, self._A.SELECTED if self.friends_showing() else self._A.SIDEBAR)
        except tk.TclError:
            pass

    def open_friends(self, tab=None):
        if self.main_frame is None:
            return
        self.friends_tab = tab or getattr(self, "friends_tab", None) or "online"
        self.open_key = None
        self.preview = None
        try:
            if self.find_bar.winfo_ismapped():
                self.close_find()
            self.chat_icon.configure(text="👥")
            self.chat_title.configure(text=i18n.tr("Friends"))
            self.chat_sub.configure(text="")
        except tk.TclError:
            pass
        self.update_chat_header_check()
        self.update_composer()
        self.mark_open_row()
        self.mark_friends_row()
        self.render_friends()
        self.load_relationships()

    def render_friends(self):
        A = self._A
        self.messages.clear()
        self.msg_rows, self.text_labels, self.row_by_id = [], [], {}
        inner = self.messages.inner
        tab = self.friends_tab
        rels = getattr(self, "relationships", None) or []
        groups = {"online": [r for r in rels if r.get("type") == 1 and
                             self.status_of(r.get("id")) != "offline"],
                  "all": [r for r in rels if r.get("type") == 1],
                  "pending": [r for r in rels if r.get("type") in (3, 4)],
                  "blocked": [r for r in rels if r.get("type") == 2]}
        bar = tk.Frame(inner, bg=A.CHAT)
        bar.pack(fill="x", padx=20, pady=(14, 6))
        for key, label in TABS:
            n = self.pending_count() if key == "pending" else 0
            on = key == tab
            A.FlatButton(bar, i18n.tr(label) + (f"  {n}" if n else ""),
                         lambda k=key: self.open_friends(k),
                         bg=A.SELECTED if on else A.CHAT, hover=A.HOVER, font_size=9,
                         padx=10, pady=3).pack(side="left", padx=(0, 6))
        A.FlatButton(bar, "Add Friend", lambda: self.open_friends("add"),
                     bg=A.GREEN if tab != "add" else A.CHAT, hover=A.HOVER, font_size=9,
                     padx=10, pady=3).pack(side="left", padx=(6, 0))
        tk.Frame(inner, bg=A.BORDER, height=1).pack(fill="x", padx=20, pady=(4, 8))

        if tab == "add":
            tk.Label(inner, text="Add Friend", bg=A.CHAT, fg=A.WHITE,
                     font=(A.FONT, 12, "bold")).pack(anchor="w", padx=20)
            tk.Label(inner, text="You can add friends with their Discord username.",
                     bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9)).pack(anchor="w", padx=20, pady=(2, 8))
            row = tk.Frame(inner, bg=A.CHAT)
            row.pack(fill="x", padx=20)
            box, ent = A.entry_box(row, "Enter a username", bg=A.INPUT)
            box.pack(side="left", fill="x", expand=True)
            res = tk.Label(inner, text="", notr=True, bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9),
                           anchor="w")
            res.pack(fill="x", padx=20, pady=8)

            def send():
                name = ent.get().strip().lstrip("@")
                if not name:
                    return

                def work():
                    st, data = self._call("POST", "/users/@me/relationships",
                                          {"username": name, "discriminator": None})
                    ok = st in (200, 204)

                    def show():
                        try:
                            res.configure(fg=A.GREEN if ok else A.RED,
                                          text=i18n.tr("Friend request sent to ") + name if ok
                                          else self._err(st, data, "send the friend request"))
                        except tk.TclError:
                            pass
                        if ok:
                            self.load_relationships(lambda: None)
                    self.after(0, show)
                self._bg(work)
            A.FlatButton(row, "Send Friend Request", send, bg=A.BLURPLE, hover=A.BLURPLE_HI,
                         font_size=9, padx=12, pady=6).pack(side="left", padx=(8, 0))
            ent.bind("<Return>", lambda e: send())
            ent.focus_set()
            return

        lst = groups.get(tab, [])
        A.section_label(inner, f"{i18n.tr(dict(TABS)[tab])}  —  {len(lst)}", A.CHAT).pack(
            anchor="w", padx=20, pady=(2, 6))
        if not lst:
            tk.Label(inner, text="No one's around.", bg=A.CHAT, fg=A.MUTED,
                     font=(A.FONT, 10)).pack(pady=40)
        order = {"online": 0, "idle": 1, "dnd": 2}
        for r in sorted(lst, key=lambda r: (order.get(self.status_of(r.get("id")), 3),
                                            _name(r.get("user")).lower())):
            self.friend_line(inner, r)

    def friend_line(self, parent, r):
        A = self._A
        u = r.get("user") or {"id": r.get("id")}
        st = self.status_of(u.get("id"))
        row = tk.Frame(parent, bg=A.CHAT, cursor="hand2")
        row.pack(fill="x", padx=20, pady=1)
        av = A.Avatar(row, 36, A.CHAT, core.initials(_name(u))[:1], A.color_for(u.get("id")))
        av.pack(side="left", padx=(6, 12), pady=8)
        if u.get("avatar"):
            self.images.load(core.user_avatar_url(u), 36, av)
        if r.get("type") == 1 and st != "offline":
            av.set_badge(True, STATUS_COLOR.get(st, "#80848e"))
        txt = tk.Frame(row, bg=A.CHAT)
        txt.pack(side="left", fill="x", expand=True)
        top = tk.Frame(txt, bg=A.CHAT)
        top.pack(fill="x")
        tk.Label(top, text=_name(u), notr=True, bg=A.CHAT, fg=A.WHITE,
                 font=(A.FONT, 10, "bold")).pack(side="left")
        tk.Label(top, text="  " + (u.get("username") or ""), notr=True, bg=A.CHAT, fg=A.MUTED,
                 font=(A.FONT, 9)).pack(side="left")
        sub = {3: "Incoming friend request", 4: "Outgoing friend request", 2: "Blocked"}.get(
            r.get("type"), STATUS_NAME.get(st, "Offline"))
        tk.Label(txt, text=sub, bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 8), anchor="w").pack(fill="x")

        def btn(text, tip, fn, fg=None):
            b = tk.Label(row, text=text, notr=True, bg=A.SIDEBAR, fg=fg or A.TEXT,
                         font=("Segoe UI Emoji", 11), width=3, pady=4, cursor="hand2")
            b.pack(side="right", padx=4)
            b.bind("<Button-1>", lambda e: (fn(), "break")[1])
            A.Tooltip(b, lambda: i18n.tr(tip))

        t = r.get("type")
        if t == 1:
            btn("✕", "Remove friend", lambda: self.relationship_action(r, "remove"))
            btn("📞", "Call", lambda: self.call_user(u))
            btn("💬", "Message", lambda: self.message_user(u))
        elif t == 3:
            btn("✕", "Ignore", lambda: self.relationship_action(r, "remove"))
            btn("✔", "Accept", lambda: self.relationship_action(r, "accept"), fg=A.GREEN)
        elif t == 4:
            btn("✕", "Cancel", lambda: self.relationship_action(r, "remove"))
        elif t == 2:
            btn("⊘", "Unblock", lambda: self.relationship_action(r, "remove"))
        for w in (row, txt, top, av):
            w.bind("<Button-1>", lambda e: self.open_profile(u))
        row.bind("<Enter>", lambda e: A.set_bg(row, A.HOVER))
        row.bind("<Leave>", lambda e: A.set_bg(row, A.CHAT)
                 if not A.is_inside(self.winfo_containing(*self.winfo_pointerxy()), row) else None)

    def relationship_action(self, r, action):
        u = r.get("user") or {}
        if action == "remove" and r.get("type") == 1 and not self._A.messagebox.askyesno(
                i18n.tr("Remove friend"), i18n.tr("Remove ") + _name(u) + i18n.tr(" from your friends?"),
                parent=self):
            return
        rid = r.get("id")
        method, body = ("PUT", {}) if action == "accept" else \
            ("PUT", {"type": 2}) if action == "block" else ("DELETE", None)

        def work():
            st, data = self._call(method, f"/users/@me/relationships/{rid}", body)
            self.after(0, lambda: (self.log(self._err(st, data, "change this friend"), "bad")
                                   if st not in (200, 204) else None,
                                   self.load_relationships()))
        self._bg(work)

    # ------------------------------------------------------------------ DMs, calls
    def message_user(self, u):
        if not u or not u.get("id"):
            return

        def work():
            st, ch = self._call("POST", "/users/@me/channels", {"recipient_id": u["id"]})
            if st == 200 and isinstance(ch, dict):
                self.after(0, lambda: self._open_dm_channel(ch, u))
            else:
                self.after(0, lambda: self.log(self._err(st, ch, "open the DM"), "bad"))
        self._bg(work)

    def _open_dm_channel(self, ch, u):
        cid = ch["id"]
        d = next((x for x in self.dms if x["id"] == cid), None)
        if d is None:
            d = {"id": cid, "name": _name(u), "kind": "dm", "avatar": core.user_avatar_url(u)
                 if u.get("avatar") else None, "user_id": u["id"],
                 "recipients": [u], "last": int(ch.get("last_message_id") or 0)}
            self.dms.insert(0, d)
            self.invalidate_view("dms")
        if self.view != "dms":
            self.open_view("dms")
        self.open_chat(("dm", cid), cid, d["name"], "@", d.get("avatar"), d.get("user_id"))

    def open_in_discord(self, path):
        """Hand over to the Discord app (or discord.com if it isn't installed)."""
        self.log(i18n.tr("Calls happen in Discord: opening it now."))
        if sys.platform.startswith("win"):
            try:
                os.startfile("discord://-" + path)
                return
            except OSError:
                pass
        webbrowser.open("https://discord.com" + path)

    def call_user(self, u):
        def work():
            st, ch = self._call("POST", "/users/@me/channels", {"recipient_id": u["id"]})
            if st == 200 and isinstance(ch, dict):
                self.after(0, lambda: self.open_in_discord(f"/channels/@me/{ch['id']}"))
        self._bg(work)

    def call_open_chat(self):
        p = self.preview or {}
        cid = p.get("channel_id")
        if not cid:
            return
        gid = self.channel_guild.get(cid)
        self.open_in_discord(f"/channels/{gid or '@me'}/{cid}")

    # ------------------------------------------------------------------ pins
    def open_pins(self):
        p = self.preview or {}
        cid = p.get("channel_id")
        if not cid or p.get("source") != "live":
            return

        def work():
            st, pins = self._call("GET", f"/channels/{cid}/pins")
            self.after(0, lambda: self._show_pins(st, pins))
        self._bg(work)

    def _show_pins(self, st, pins):
        A = self._A
        top, body = self.dialog(i18n.tr("Pinned messages"), 520, 600)
        tk.Label(body, text="📌  Pinned messages", bg=A.CHAT, fg=A.WHITE,
                 font=(A.FONT, 13, "bold")).pack(anchor="w", pady=(0, 10))
        if st != 200 or not isinstance(pins, list):
            tk.Label(body, text=core.friendly_error(st, "load the pinned messages"), bg=A.CHAT,
                     fg=A.RED, font=(A.FONT, 10)).pack(anchor="w")
            return
        if not pins:
            tk.Label(body, text="This chat doesn't have any pinned messages yet.", bg=A.CHAT,
                     fg=A.MUTED, font=(A.FONT, 10)).pack(pady=30)
            return
        sf = A.ScrollFrame(body, A.CHAT)
        sf.pack(fill="both", expand=True)
        for m in pins:
            card = tk.Frame(sf.inner, bg=A.SIDEBAR, padx=12, pady=8, cursor="hand2")
            card.pack(fill="x", pady=4)
            head = tk.Label(card, notr=True, text=_name(m.get("author")) + "   " +
                            core.format_time(m.get("timestamp")), bg=A.SIDEBAR, fg=A.WHITE,
                            font=(A.FONT, 9, "bold"), anchor="w")
            head.pack(fill="x")
            body_l = tk.Label(card, notr=True, text=core.render_content(m)[:400] or "📎",
                              bg=A.SIDEBAR, fg=A.TEXT, font=(A.FONT, 10), anchor="w",
                              justify="left", wraplength=440)
            body_l.pack(fill="x")
            for w in (card, head, body_l):
                w.bind("<Button-1>", lambda e, m=m: (top.destroy(), self.jump_to_message(m)))

    # ------------------------------------------------------------------ profile card
    def open_profile(self, user):
        if not user or not user.get("id"):
            return
        uid = user["id"]

        def work():
            st, pr = self._call("GET", f"/users/{uid}/profile?with_mutual_guilds=true")
            self.after(0, lambda: self._show_profile(user, pr if st == 200 and
                                                     isinstance(pr, dict) else {}))
        self._bg(work)

    def _show_profile(self, user, pr):
        A = self._A
        u = dict(user, **(pr.get("user") or {}))
        mine = self.me and u.get("id") == self.me.get("id")
        rel = next((r for r in getattr(self, "relationships", None) or []
                    if r.get("id") == u.get("id")), None)
        top, body = self.dialog(_name(u), 440, 520)
        body.configure(padx=0, pady=0)
        colour = u.get("banner_color") or (f"#{u['accent_color']:06x}" if u.get("accent_color")
                                           else A.color_for(u.get("id")))
        tk.Frame(body, bg=colour, height=90).pack(fill="x")
        inner = tk.Frame(body, bg=A.CHAT, padx=20)
        inner.pack(fill="both", expand=True)
        av = A.Avatar(inner, 80, A.CHAT, core.initials(_name(u))[:1], A.color_for(u.get("id")),
                      font_size=26)
        av.pack(anchor="w", pady=(10, 4))
        if u.get("avatar"):
            self.images.load(core.user_avatar_url(u, 128), 80, av)
        st = self.my_status() if mine else self.status_of(u.get("id"))
        av.set_badge(st != "offline", STATUS_COLOR.get(st, "#80848e"))
        tk.Label(inner, text=_name(u), notr=True, bg=A.CHAT, fg=A.WHITE,
                 font=(A.FONT, 15, "bold"), anchor="w").pack(fill="x")
        tk.Label(inner, text=(u.get("username") or "") + "   •   " +
                 i18n.tr(STATUS_NAME.get(st, "Offline")), notr=True, bg=A.CHAT, fg=A.MUTED,
                 font=(A.FONT, 9), anchor="w").pack(fill="x")
        bio = u.get("bio") or (pr.get("user_profile") or {}).get("bio")
        if bio:
            box = tk.Frame(inner, bg=A.SIDEBAR, padx=10, pady=8)
            box.pack(fill="x", pady=(12, 0))
            A.section_label(box, "About me", A.SIDEBAR).pack(anchor="w")
            tk.Label(box, text=bio, notr=True, bg=A.SIDEBAR, fg=A.TEXT, font=(A.FONT, 9),
                     anchor="w", justify="left", wraplength=370).pack(fill="x", pady=(4, 0))
        mutual = [self.guild_by_id.get(g.get("id"), {}).get("name")
                  for g in pr.get("mutual_guilds") or []]
        mutual = [m for m in mutual if m]
        if mutual:
            box = tk.Frame(inner, bg=A.SIDEBAR, padx=10, pady=8)
            box.pack(fill="x", pady=(8, 0))
            A.section_label(box, "Mutual servers", A.SIDEBAR).pack(anchor="w")
            tk.Label(box, text="  •  ".join(mutual), notr=True, bg=A.SIDEBAR, fg=A.TEXT,
                     font=(A.FONT, 9), anchor="w", justify="left", wraplength=370).pack(fill="x")
        row = tk.Frame(inner, bg=A.CHAT)
        row.pack(fill="x", pady=14)
        if mine:
            A.FlatButton(row, "Edit my profile…", lambda: (top.destroy(), self.open_profile_editor()),
                         bg=A.BLURPLE, hover=A.BLURPLE_HI, font_size=9, padx=12, pady=6).pack(side="left")
            return
        A.FlatButton(row, "💬  Message", lambda: (top.destroy(), self.message_user(u)),
                     bg=A.BLURPLE, hover=A.BLURPLE_HI, font_size=9, padx=12, pady=6).pack(side="left")
        A.FlatButton(row, "📞  Call", lambda: self.call_user(u), bg=A.SELECTED, hover=A.HOVER,
                     font_size=9, padx=12, pady=6).pack(side="left", padx=6)
        if not rel or rel.get("type") not in (1, 2, 4):
            def add():
                def work():
                    st2, data = self._call("POST", "/users/@me/relationships",
                                           {"username": u.get("username"), "discriminator": None})
                    self.after(0, lambda: (self.log(i18n.tr("Friend request sent to ") + _name(u))
                                           if st2 in (200, 204) else
                                           self.log(self._err(st2, data, "send the friend request"),
                                                    "bad"), self.load_relationships(lambda: None)))
                self._bg(work)
            A.FlatButton(row, "Add Friend", add, bg=A.GREEN, hover=A.HOVER, font_size=9,
                         padx=12, pady=6).pack(side="left")
        if rel and rel.get("type") == 2:
            A.FlatButton(row, "Unblock", lambda: (top.destroy(), self.relationship_action(rel, "remove")),
                         bg=A.SELECTED, hover=A.HOVER, font_size=9, padx=12, pady=6).pack(side="right")
        else:
            A.FlatButton(row, "Block", lambda: (top.destroy(), self.relationship_action(
                rel or {"id": u.get("id"), "user": u}, "block")),
                         bg=A.SELECTED, hover=A.HOVER, font_size=9, padx=12, pady=6).pack(side="right")

    # ------------------------------------------------------------------ edit my profile
    def open_profile_editor(self):
        A = self._A
        top, body = self.dialog(i18n.tr("Edit my profile"), 480, 470)
        tk.Label(body, text="Edit my profile", bg=A.CHAT, fg=A.WHITE,
                 font=(A.FONT, 14, "bold")).pack(anchor="w")
        A.section_label(body, "Display name", A.CHAT).pack(anchor="w", pady=(14, 4))
        nbox, name = A.entry_box(body, "Display name", bg=A.INPUT)
        nbox.pack(fill="x")
        name.insert(0, (self.me or {}).get("global_name") or "")
        A.section_label(body, "About me", A.CHAT).pack(anchor="w", pady=(12, 4))
        bio = tk.Text(body, bg=A.INPUT, fg=A.TEXT, insertbackground=A.TEXT, height=4, bd=0,
                      wrap="word", font=(A.FONT, 10), padx=8, pady=6, highlightthickness=0)
        bio.pack(fill="x")
        A.section_label(body, "Status", A.CHAT).pack(anchor="w", pady=(12, 4))
        srow = tk.Frame(body, bg=A.CHAT)
        srow.pack(fill="x")
        choice = tk.StringVar(value=self.my_status())
        chips = {}

        def pick(k):
            choice.set(k)
            for key, chip in chips.items():
                try:
                    chip.configure(bg=A.BLURPLE if key == k else A.INPUT,
                                   fg="white" if key == k else A.TEXT)
                except tk.TclError:
                    pass
        for k, label, colour in STATUS:
            chip = tk.Label(srow, text="● " + i18n.tr(label), notr=True, bg=A.INPUT, fg=A.TEXT,
                            font=(A.FONT, 9), padx=10, pady=4, cursor="hand2")
            chip.pack(side="left", padx=(0, 6))
            chip.bind("<Button-1>", lambda e, k=k: pick(k))
            chips[k] = chip
        pick(choice.get())
        cbox, custom = A.entry_box(body, "Custom status", bg=A.INPUT)
        cbox.pack(fill="x", pady=(8, 0))
        custom.insert(0, self.settings.get("custom_status") or "")
        res = tk.Label(body, text="", notr=True, bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9),
                       anchor="w", wraplength=420, justify="left")
        res.pack(fill="x", pady=(10, 0))

        def load_bio():
            st, pr = self._call("GET", f"/users/{(self.me or {}).get('id')}/profile")
            text = ((pr or {}).get("user") or {}).get("bio") if st == 200 and isinstance(pr, dict) else None
            if text is None and st == 200 and isinstance(pr, dict):
                text = (pr.get("user_profile") or {}).get("bio")

            def put():
                try:
                    if text and not bio.get("1.0", "end-1c"):
                        bio.insert("1.0", text)
                except tk.TclError:
                    pass
            self.after(0, put)
        self._bg(load_bio)

        def save():
            new_name = name.get().strip()
            new_bio = bio.get("1.0", "end-1c")[:190]
            status, text = choice.get(), custom.get()

            def work():
                done, fails = [], []
                if new_name != ((self.me or {}).get("global_name") or ""):
                    st, data = self._call("PATCH", "/users/@me", {"global_name": new_name or None})
                    if st == 200:
                        (self.me or {}).update(global_name=new_name or None)
                        done.append("Display name")
                    else:
                        fails.append(self._err(st, data, "change your display name"))
                st, data = self._call("PATCH", "/users/@me/profile", {"bio": new_bio})
                (done.append("About me") if st in (200, 204) else
                 fails.append(self._err(st, data, "change About me")))

                def show():
                    self.set_my_status(status, text)
                    done.append("Status")
                    try:
                        res.configure(fg=A.RED if fails else A.GREEN,
                                      text="✔ " + ", ".join(i18n.tr(x) for x in done) +
                                      ("\n✘ " + "\n✘ ".join(fails) if fails else ""))
                    except tk.TclError:
                        pass
                self.after(0, show)
            self._bg(work)
        row = tk.Frame(body, bg=A.CHAT)
        row.pack(fill="x", side="bottom")
        A.FlatButton(row, "Save", save, bg=A.BLURPLE, hover=A.BLURPLE_HI, font_size=10,
                     padx=16, pady=6).pack(side="right")
        A.LinkLabel(row, "Open Discord's full settings ↗",
                    lambda: webbrowser.open("https://discord.com/channels/@me"), A.CHAT,
                    font_size=9).pack(side="left")


class MoreSocialMixin:
    """Mute / mentions-only, server unread marks, last chat, shortcuts, @mention suggestions,
    GIF picker, members, undo for single deletes, logger dashboard and edit-history export."""
    mention_box = None
    mention_items = ()
    mention_sel = 0
    mention_names = None
    server_unreads = None
    _undo = None

    # ------------------------------------------------------------------ mute & notifications
    def mutes(self):
        return self.settings.setdefault("mutes", {})

    def mute_of(self, cid, gid=None):
        m = self.mutes()
        return m.get(cid) or (m.get(gid) if gid else "") or ""

    def should_notify(self, m):
        mode = self.mute_of(m.get("channel_id"), m.get("guild_id"))
        if mode == "all":
            return False
        if mode == "mentions":
            return self.pings_me(m)
        return True

    def pings_me(self, m):
        me = (self.me or {}).get("id")
        return bool(m.get("mention_everyone") or any(u.get("id") == me for u in m.get("mentions") or []))

    def mute_menu(self, event, target, name=""):
        A = self._A
        mode = self.mutes().get(target, "")
        menu = tk.Menu(self, tearoff=0, bg=A.SIDEBAR, fg=A.TEXT, activebackground=A.BLURPLE,
                       activeforeground="white", bd=0)

        def setm(v):
            if v:
                self.mutes()[target] = v
            else:
                self.mutes().pop(target, None)
            self.save_settings()
            self.update_rail()
        for v, label in (("all", "Mute"), ("mentions", "Only @mentions"), ("", "All messages")):
            menu.add_command(label=("✓  " if mode == v else "     ") + i18n.tr(label),
                             command=lambda v=v: setm(v))
        menu.add_separator()
        menu.add_command(label=i18n.tr("Mark as read"),
                         command=lambda: (self.clear_unread(target), self.clear_server_unread(target)))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    def server_unread(self, m):
        gid = m.get("guild_id")
        if not gid:
            return
        if self.server_unreads is None:
            self.server_unreads = {}
        mode = self.mute_of(m.get("channel_id"), gid)
        ping = self.pings_me(m)
        if mode == "all" and not ping:
            return
        st = self.server_unreads.setdefault(gid, {"unread": False, "mentions": 0})
        if ping:
            st["mentions"] += 1
            if mode != "all":
                author = m.get("author") or {}
                self.notify("@ " + (author.get("global_name") or author.get("username", "?")),
                            (m.get("content") or "")[:120], flash=True)
        elif not mode:
            st["unread"] = True
        self.update_rail()

    def server_mark(self, gid):
        st = (self.server_unreads or {}).get(gid)
        if not st:
            return None
        return self._A.RED if st["mentions"] else (self._A.WHITE if st["unread"] else None)

    def clear_server_unread(self, gid):
        if self.server_unreads and gid in self.server_unreads:
            self.server_unreads.pop(gid, None)
            try:
                self.update_rail()
            except (tk.TclError, AttributeError):
                pass

    # ------------------------------------------------------------------ last chat & shortcuts
    def remember_last_chat(self, key, cid, title, icon, avatar, user_id, server):
        if key[0] not in ("dm", "channel", "link"):
            return
        self.settings["last_chat"] = {"key": list(key), "cid": cid, "title": title, "icon": icon,
                                      "avatar": avatar, "user_id": user_id, "server": server,
                                      "guild": self.channel_guild.get(cid)}
        self.save_settings()

    def reopen_last_chat(self):
        last = self.settings.get("last_chat")
        if not last or self.settings.get("reopen_last", True) is False or self.open_key:
            return
        key = tuple(last.get("key") or ())
        if key[:1] == ("dm",) and not any(d["id"] == last.get("cid") for d in self.dms):
            return
        gid = last.get("guild")
        if key[:1] == ("channel",):
            if gid not in self.guild_by_id:
                return
            self.channel_guild[last["cid"]] = gid
            self.open_view(gid)
        try:
            self.open_chat(key, last["cid"], last.get("title") or "", last.get("icon") or "#",
                           last.get("avatar"), last.get("user_id"), last.get("server"))
        except (tk.TclError, KeyError):
            pass

    def bind_social_keys(self):
        if getattr(self, "_social_keys", False):
            return
        self._social_keys = True
        self.bind_all("<Alt-Down>", lambda e: self.step_chat(1))
        self.bind_all("<Alt-Up>", lambda e: self.step_chat(-1))
        self.bind_all("<Control-M>", lambda e: self.toggle_mute_open())

    def chat_list(self):
        if self.view == "dms":
            return [(("dm", d["id"]), d["id"], d["name"], "@", d.get("avatar"), d.get("user_id"), None)
                    for d in self.dms]
        chans = self.guild_channels.get(self.view)
        if isinstance(chans, list):
            g = self.guild_by_id.get(self.view, {}).get("name")
            return [(("channel", c["id"]), c["id"], "#" + c.get("name", ""), "#", None, None, g)
                    for c in chans if isinstance(c, dict) and c.get("id")]
        return []

    def step_chat(self, d):
        items = self.chat_list()
        if not items:
            return "break"
        keys = [i[0] for i in items]
        i = keys.index(self.open_key) + d if self.open_key in keys else 0
        i = max(0, min(len(items) - 1, i))
        self.open_chat(*items[i])
        return "break"

    def toggle_mute_open(self):
        p = self.preview or {}
        cid = p.get("channel_id")
        if not cid:
            return "break"
        if self.mutes().get(cid):
            self.mutes().pop(cid, None)
            self.log(i18n.tr("Unmuted ") + (p.get("title") or ""))
        else:
            self.mutes()[cid] = "all"
            self.log(i18n.tr("Muted ") + (p.get("title") or ""))
        self.save_settings()
        return "break"

    # ------------------------------------------------------------------ @mention suggestions
    def chat_people(self):
        seen, out = set(), []
        me = (self.me or {}).get("id")

        def add(u):
            if u and u.get("id") and u["id"] not in seen and u["id"] != me:
                seen.add(u["id"])
                out.append(u)
        for r in reversed(getattr(self, "msg_rows", []) or []):
            add(r["msg"].get("author"))
        p = self.preview or {}
        for d in self.dms:
            if d["id"] == p.get("channel_id"):
                for u in d.get("recipients") or []:
                    add(u)
        for r in self.relationships or []:
            if r.get("type") == 1:
                add(r.get("user"))
        return out

    def setup_composer_extras(self, box, emoji_btn):
        A = self._A
        gif = tk.Label(box, text="GIF", bg=A.FIELD_BG, fg=A.ICON_MUTED, font=(A.FONT, 9, "bold"),
                       cursor="hand2", padx=4)
        gif.pack(side="right", padx=(0, 4), pady=10, anchor="n")
        gif.bind("<Button-1>", lambda e: self.can_chat() and self.open_gifs())
        A.Tooltip(gif, lambda: "Send a GIF")
        self.composer.bind("<Down>", lambda e: (self.mention_move(1), "break")[1]
                           if self.mention_visible() else None, add="+")
        self.composer.bind("<Tab>", lambda e: (self.mention_pick(), "break")[1]
                           if self.mention_visible() else None, add="+")
        self.composer.bind("<Escape>", lambda e: self.mention_hide(), add="+")
        self.composer.bind("<FocusOut>", lambda e: self.after(200, self.mention_hide), add="+")

    def mention_query(self):
        try:
            before = self.composer.get("insert linestart", "insert")
        except tk.TclError:
            return None
        import re
        m = re.search(r"(?:^|\s)@([\w.]*)$", before)
        return m.group(1) if m else None

    def mention_check(self):
        q = self.mention_query()
        if q is None or not self.can_chat():
            self.mention_hide()
            return
        ql = q.lower()
        items = [u for u in self.chat_people()
                 if ql in ((u.get("global_name") or "") + " " + (u.get("username") or "")).lower()][:8]
        if (self.preview or {}).get("key", ("",))[0] == "channel":
            items.append({"id": "everyone", "username": "everyone", "global_name": "everyone"})
        self.mention_items = items
        self.mention_sel = min(self.mention_sel, max(0, len(items) - 1))
        self.mention_draw()

    def mention_visible(self):
        try:
            return self.mention_box is not None and self.mention_box.winfo_ismapped() \
                and bool(self.mention_items)
        except tk.TclError:
            return False

    def mention_hide(self):
        try:
            if self.mention_box is not None:
                self.mention_box.place_forget()
        except tk.TclError:
            pass

    def mention_draw(self):
        A = self._A
        if not self.mention_items:
            return self.mention_hide()
        if self.mention_box is None or not self.mention_box.winfo_exists():
            self.mention_box = tk.Frame(self.chat, bg=A.SIDEBAR, padx=4, pady=4)
        for w in self.mention_box.winfo_children():
            w.destroy()
        for i, u in enumerate(self.mention_items):
            on = i == self.mention_sel
            row = tk.Frame(self.mention_box, bg=A.SELECTED if on else A.SIDEBAR, cursor="hand2")
            row.pack(fill="x")
            n = u.get("global_name") or u.get("username") or "?"
            l1 = tk.Label(row, text=n, notr=True, bg=row.cget("bg"), fg=A.WHITE,
                          font=(A.FONT, 10, "bold"), padx=8, pady=3)
            l1.pack(side="left")
            l2 = tk.Label(row, text=u.get("username") or "", notr=True, bg=row.cget("bg"),
                          fg=A.MUTED, font=(A.FONT, 9))
            l2.pack(side="left")
            for w in (row, l1, l2):
                w.bind("<Button-1>", lambda e, i=i: (setattr(self, "mention_sel", i),
                                                     self.mention_pick()))
        try:
            self.mention_box.place(in_=self.input_box, x=0, y=-4, relwidth=1.0, anchor="sw")
            self.mention_box.lift()
        except tk.TclError:
            pass

    def mention_move(self, d):
        if self.mention_items:
            self.mention_sel = (self.mention_sel + d) % len(self.mention_items)
            self.mention_draw()

    def mention_pick(self):
        if not self.mention_items:
            return
        u = self.mention_items[self.mention_sel]
        name = "everyone" if u["id"] == "everyone" else (u.get("global_name") or u.get("username"))
        q = self.mention_query() or ""
        try:
            self.composer.delete(f"insert-{len(q) + 1}c", "insert")
            self.composer.insert("insert", "@" + name + " ")
        except tk.TclError:
            pass
        if u["id"] != "everyone":
            if self.mention_names is None:
                self.mention_names = {}
            self.mention_names["@" + name] = u["id"]
        self.mention_items = []
        self.mention_hide()
        self.show_placeholder()

    def mention_convert(self, text):
        for tag, uid in sorted((self.mention_names or {}).items(), key=lambda kv: -len(kv[0])):
            text = text.replace(tag, f"<@{uid}>")
        return text

    # ------------------------------------------------------------------ GIF picker
    def open_gifs(self):
        A = self._A
        top, body = self.dialog(i18n.tr("GIF"), 560, 600)
        box, ent = A.entry_box(body, "Search GIFs", bg=A.INPUT)
        box.pack(fill="x")
        info = tk.Label(body, text="", notr=True, bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9),
                        anchor="w")
        info.pack(fill="x", pady=(6, 4))
        grid = A.ScrollFrame(body, A.CHAT)
        grid.pack(fill="both", expand=True)
        state = {"t": None, "req": 0}

        def show(req, gifs, err=None):
            if req != state["req"] or not top.winfo_exists():
                return
            grid.clear()
            info.configure(text=err or (i18n.tr("Powered by Tenor, through Discord.")
                                        if gifs else i18n.tr("Nothing found.")))
            row = None
            for i, g in enumerate(gifs[:24]):
                if i % 3 == 0:
                    row = tk.Frame(grid.inner, bg=A.CHAT)
                    row.pack(fill="x", pady=3)
                cell = tk.Label(row, text="GIF", notr=True, bg=A.SIDEBAR, fg=A.MUTED,
                                font=(A.FONT, 9), width=20, height=6)
                cell.pack(side="left", padx=3)
                cell.configure(cursor="hand2")
                prev = g.get("preview") or g.get("gif_src")
                if prev:
                    self.images.load(prev, (160, 110), cell, mode="thumb")
                cell.bind("<Button-1>", lambda e, g=g: (top.destroy(), self.send_gif(g)))

        def search(q):
            state["req"] += 1
            req = state["req"]
            if self.demo is not None:
                show(req, [], i18n.tr("GIF search needs a real account (demo mode)."))
                return
            import urllib.parse
            path = (f"/gifs/search?q={urllib.parse.quote(q)}&media_format=mp4&provider=tenor"
                    if q else "/gifs/trending-gifs?media_format=mp4&provider=tenor")

            def work():
                st, data = self._call("GET", path + "&locale=" + (i18n.LANG or "en"))
                gifs = data if isinstance(data, list) else (data or {}).get("gifs") or []
                self.after(0, lambda: show(req, gifs if st == 200 else [],
                                           None if st == 200 else core.friendly_error(st, "search GIFs")))
            self._bg(work)

        def typed(_e=None):
            if state["t"]:
                self.after_cancel(state["t"])
            state["t"] = self.after(400, lambda: search(ent.get().strip()))
        ent.bind("<KeyRelease>", typed)
        ent.focus_set()
        search("")

    def send_gif(self, g):
        url = g.get("url") or g.get("src")
        if not url or not self.can_chat():
            return
        keep = self.composer.get("1.0", "end-1c")
        self.composer.delete("1.0", "end")
        self.composer.insert("1.0", url)
        self.send_composer()
        if keep:
            self.composer.insert("1.0", keep)
            self.show_placeholder()

    # ------------------------------------------------------------------ members
    def open_members(self):
        A = self._A
        people = {}
        for r in getattr(self, "msg_rows", []) or []:
            a = r["msg"].get("author") or {}
            if a.get("id"):
                people[a["id"]] = a
        if self.me:
            people[self.me["id"]] = self.me
        me_id = (self.me or {}).get("id")
        online = [u for u in people.values() if u["id"] == me_id or self.status_of(u["id"]) != "offline"]
        offline = [u for u in people.values() if u not in online]
        top, body = self.dialog(i18n.tr("Members"), 360, 560)
        tk.Label(body, text="Active in this channel", bg=A.CHAT, fg=A.MUTED,
                 font=(A.FONT, 9)).pack(anchor="w")
        sf = A.ScrollFrame(body, A.CHAT)
        sf.pack(fill="both", expand=True, pady=(6, 0))
        for title, group in (("Online", online), ("Offline", offline)):
            A.section_label(sf.inner, f"{i18n.tr(title)}  —  {len(group)}", A.CHAT).pack(
                anchor="w", pady=(10, 4))
            for u in sorted(group, key=lambda u: (u.get("global_name") or u.get("username") or "").lower()):
                row = tk.Frame(sf.inner, bg=A.CHAT, cursor="hand2")
                row.pack(fill="x", pady=1)
                n = u.get("global_name") or u.get("username") or "?"
                av = A.Avatar(row, 32, A.CHAT, core.initials(n)[:1], A.color_for(u.get("id")))
                av.pack(side="left", padx=(0, 10))
                if u.get("avatar"):
                    self.images.load(core.user_avatar_url(u), 32, av)
                st = self.my_status() if u["id"] == me_id else self.status_of(u["id"])
                if st not in ("offline", "invisible"):
                    av.set_badge(True, STATUS_COLOR.get(st, "#23a55a"))
                lbl = tk.Label(row, text=n, notr=True, bg=A.CHAT,
                               fg=A.TEXT if title == "Online" else A.MUTED, font=(A.FONT, 10))
                lbl.pack(side="left")
                for w in (row, av, lbl):
                    w.bind("<Button-1>", lambda e, u=u: self.open_profile(u))

    # ------------------------------------------------------------------ undo for one delete
    def delete_with_undo(self, info):
        A = self._A
        if self._undo:
            self._undo["go"]()
        m = info["msg"]
        row = info.get("row")
        try:
            if row is not None:
                row.pack_forget()
        except tk.TclError:
            pass
        bar = tk.Frame(self.chat, bg=A.RAIL, padx=14, pady=8)
        lbl = tk.Label(bar, text="", notr=True, bg=A.RAIL, fg=A.TEXT, font=(A.FONT, 10))
        lbl.pack(side="left")
        state = {"n": 10, "job": None, "done": False}

        def finish():
            try:
                bar.destroy()
            except tk.TclError:
                pass
            self._undo = None

        def go():
            if state["done"]:
                return
            state["done"] = True
            if state["job"]:
                self.after_cancel(state["job"])
            finish()

            def work():
                try:
                    st = core.delete_message(self.make_api(), m["channel_id"], m["id"])
                except Exception:
                    st = 0
                self.after(0, lambda: self.on_single_deleted(info, st))
            self._bg(work)

        def undo():
            if state["done"]:
                return
            state["done"] = True
            if state["job"]:
                self.after_cancel(state["job"])
            finish()
            self.render_preview(scroll="keep")

        def tick():
            if state["done"]:
                return
            lbl.configure(text="🗑  " + i18n.tr("Message deleted") + f"   ({state['n']})")
            if state["n"] <= 0:
                go()
                return
            state["n"] -= 1
            state["job"] = self.after(1000, tick)
        A.FlatButton(bar, "Undo", undo, bg=A.BLURPLE, hover=A.BLURPLE_HI, font_size=9,
                     padx=12, pady=3).pack(side="right", padx=(16, 0))
        try:
            bar.place(in_=self.input_box, relx=0.5, y=-12, anchor="s")
            bar.lift()
        except tk.TclError:
            pass
        self._undo = {"go": go, "undo": undo}
        tick()

    # ------------------------------------------------------------------ logger extras
    def export_edit_history(self):
        import json
        A = self._A
        me = (self.me or {}).get("id")
        rows = self.store().all_edits(me) if me else []
        if not rows:
            A.messagebox.showinfo(A.APP_NAME, i18n.tr("No edited messages saved yet."))
            return
        path = A.filedialog.asksaveasfilename(defaultextension=".json", initialfile="edit_history.json",
                                              filetypes=[("JSON", "*.json"), ("Text", "*.txt")])
        if not path:
            return
        grouped = {}
        for r in rows:
            grouped.setdefault(r["message_id"], {"message_id": r["message_id"],
                                                 "channel_id": r["channel_id"], "versions": []})
            grouped[r["message_id"]]["versions"].append({"text": r["old"], "replaced_at": r["at"]})
        with open(path, "w", encoding="utf-8") as f:
            if path.lower().endswith(".txt"):
                for g in grouped.values():
                    f.write(f"Message {g['message_id']} (chat {g['channel_id']})\n")
                    for v in g["versions"]:
                        f.write(f"  - {v['text']}\n")
                    f.write("\n")
            else:
                json.dump(list(grouped.values()), f, ensure_ascii=False, indent=1)
        self.log(i18n.tr("Exported ") + f"{len(grouped)}" + i18n.tr(" edited messages."), "good")

    def open_dashboard(self):
        import time as _t
        A = self._A
        me = (self.me or {}).get("id")
        rows = self.store().all_deleted(me) if me else []
        events = self.store().events(me, 5000) if me else []
        now = _t.time()
        days = 30
        dele, ghost = [0] * days, [0] * days
        who = {}
        for r in rows:
            i = days - 1 - int((now - (r.get("deleted_at") or now)) // 86400)
            if 0 <= i < days:
                if r.get("note") == "ghost":
                    ghost[i] += 1
                else:
                    dele[i] += 1
            who[r.get("author_name") or "?"] = who.get(r.get("author_name") or "?", 0) + 1
        for e in events:
            if e.get("kind") == "ghost_ping":
                i = days - 1 - int((now - (e.get("at") or now)) // 86400)
                if 0 <= i < days:
                    ghost[i] += 1
        top, body = self.dialog(i18n.tr("Dashboard"), 720, 620)
        tk.Label(body, text="📊  Dashboard", bg=A.CHAT, fg=A.WHITE,
                 font=(A.FONT, 14, "bold")).pack(anchor="w")
        cards = tk.Frame(body, bg=A.CHAT)
        cards.pack(fill="x", pady=10)
        n_edits = len({r["message_id"] for r in (self.store().all_edits(me) if me else [])})
        for n, label in ((sum(dele), "deleted messages (30 days)"), (sum(ghost), "ghost pings (30 days)"),
                         (len(rows), "saved in total"), (n_edits, "edited messages")):
            c = tk.Frame(cards, bg=A.SIDEBAR, padx=14, pady=8)
            c.pack(side="left", padx=(0, 8))
            tk.Label(c, text=f"{n:,}", notr=True, bg=A.SIDEBAR, fg=A.WHITE,
                     font=(A.FONT, 15, "bold")).pack(anchor="w")
            tk.Label(c, text=label, bg=A.SIDEBAR, fg=A.MUTED, font=(A.FONT, 8)).pack(anchor="w")
        A.section_label(body, "Per day: deleted (blue) and ghost pings (grey)", A.CHAT).pack(
            anchor="w", pady=(6, 4))
        labels = [("-30" if i == 0 else "today" if i == days - 1 else "") for i in range(days)]
        self.bar_chart(body, [(labels[i], ghost[i], dele[i]) for i in range(days)], 120, 660)
        A.section_label(body, "Who deletes the most", A.CHAT).pack(anchor="w", pady=(12, 4))
        best = sorted(who.items(), key=lambda kv: -kv[1])[:10]
        if not best:
            tk.Label(body, text="Nothing yet.", bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9)).pack(anchor="w")
        for name, n in best:
            r = tk.Frame(body, bg=A.CHAT)
            r.pack(fill="x", pady=1)
            tk.Label(r, text=name, notr=True, bg=A.CHAT, fg=A.TEXT, font=(A.FONT, 9), width=22,
                     anchor="w").pack(side="left")
            bar = tk.Frame(r, bg=A.RED, height=10, width=max(4, int(380 * n / best[0][1])))
            bar.pack(side="left", padx=6)
            tk.Label(r, text=str(n), notr=True, bg=A.CHAT, fg=A.MUTED, font=(A.FONT, 9)).pack(side="left")


class CustomizeMixin:
    """Settings → Customize: accent colour, size of everything, compact messages, 24-hour clock."""

    def apply_ui_scale(self):
        scale = float(self.settings.get("ui_scale", 1.0) or 1.0)
        if abs(scale - 1.0) < 0.01:
            return
        try:
            base = float(self.tk.call("tk", "scaling"))
            self.tk.call("tk", "scaling", base * scale)
        except (tk.TclError, ValueError, TypeError):
            pass

    def build_customize(self, b, top):
        A = self._A
        import widgets
        A.section_label(b, "Accent colour", A.CHAT).pack(anchor="w", pady=(14, 6))
        row = tk.Frame(b, bg=A.CHAT)
        row.pack(fill="x")
        cur = self.settings.get("accent", "blurple")
        for name, (col, _hi) in widgets.ACCENTS.items():
            cell = tk.Frame(row, bg=A.WHITE if name == cur else A.CHAT, padx=2, pady=2)
            cell.pack(side="left", padx=(0, 6))
            sw = tk.Label(cell, text="✓" if name == cur else " ", notr=True, bg=col, fg="white",
                          font=(A.FONT, 10, "bold"), width=3, height=1, cursor="hand2")
            sw.pack()
            sw.bind("<Button-1>", lambda e, n=name: self.set_look("accent", n, top))
        A.section_label(b, "Size of everything", A.CHAT).pack(anchor="w", pady=(14, 6))
        srow = tk.Frame(b, bg=A.CHAT)
        srow.pack(fill="x")
        cur_s = float(self.settings.get("ui_scale", 1.0) or 1.0)
        for v in (0.9, 1.0, 1.1, 1.25, 1.5):
            on = abs(v - cur_s) < 0.01
            bt = tk.Label(srow, text=f"{int(v * 100)}%", notr=True,
                          bg=A.BLURPLE if on else A.INPUT, fg="white" if on else A.TEXT,
                          font=(A.FONT, 9, "bold"), padx=12, pady=5, cursor="hand2")
            bt.pack(side="left", padx=(0, 6))
            bt.bind("<Button-1>", lambda e, v=v: self.set_look("ui_scale", v, top))
        for key, label in (("compact", "Compact messages (less space between people)"),
                           ("clock_24h", "24-hour clock (20:15 instead of 8:15 PM)")):
            var = tk.BooleanVar(value=bool(self.settings.get(key)))

            def changed(k=key, v=var):
                self.settings[k] = v.get()
                self.save_settings()
                core.CLOCK_24 = bool(self.settings.get("clock_24h"))
                if self.preview:
                    self.render_preview(scroll="keep")
            A.OptionCheck(b, label, var, A.CHAT, command=changed).pack(anchor="w", pady=(6, 0))

    def set_look(self, key, value, top=None):
        if self.settings.get(key) == value:
            return
        self.settings[key] = value
        self.save_settings()
        if self._A.messagebox.askyesno(self._A.APP_NAME,
                                       i18n.tr("Restart the app now to use the new look?")):
            if top is not None:
                top.destroy()
            self.restart()
