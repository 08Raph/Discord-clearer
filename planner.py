"""Everyday helpers that live on this PC: reminders, messages to send later, saved replies
(snippets) and keyword alerts. Everything is a small JSON file next to the settings.

Only "send later" talks to Discord, and only one normal message at a time, when it's due.
If the app was closed when a message was due, it is NOT sent by surprise later: it waits
in the list as "missed" until you choose Send now or Delete."""
import json
import os
import re
import threading
import time
import uuid
from datetime import datetime, timedelta

LATE_OK_S = 10 * 60          # sent up to 10 minutes late, after that it's "missed"
_lock = threading.Lock()


def _path(name):
    root = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    return os.path.join(root, "DiscordMessageCleaner", name)


def _load(name, default):
    try:
        with open(_path(name), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, type(default)) else default
    except Exception:
        return default


def _save(name, data):
    with _lock:
        os.makedirs(os.path.dirname(_path(name)), exist_ok=True)
        tmp = _path(name) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, _path(name))


def new_id():
    return uuid.uuid4().hex[:10]


# ------------------------------------------------------------------ time words
_UNITS = {"m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60, "h": 3600, "hr": 3600,
          "hrs": 3600, "hour": 3600, "hours": 3600, "d": 86400, "day": 86400, "days": 86400,
          "w": 604800, "week": 604800, "weeks": 604800}


def parse_when(text, now=None):
    """'20m', 'in 2 hours', '18:30', '6pm', 'tomorrow', 'tomorrow 9am', '2026-12-01 14:00',
    'monday 8am'. Returns a timestamp or None."""
    now = now or datetime.now()
    t = (text or "").strip().lower()
    if not t:
        return None
    t = re.sub(r"^(in|at|on)\s+", "", t)
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([a-z]+)", t)
    if m and m.group(2) in _UNITS:
        return (now + timedelta(seconds=float(m.group(1)) * _UNITS[m.group(2)])).timestamp()
    try:
        return datetime.fromisoformat(t.replace("/", "-")).timestamp()
    except ValueError:
        pass
    day = now.date()
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    words = t.split()
    hour_part = t
    if words and words[0] in ("today", "tonight", "tomorrow") + tuple(days):
        w = words[0]
        if w == "tomorrow":
            day = day + timedelta(days=1)
        elif w in days:
            ahead = (days.index(w) - now.weekday()) % 7 or 7
            day = day + timedelta(days=ahead)
        hour_part = " ".join(words[1:]) or {"tonight": "8pm", "today": ""}.get(w, "9am")
        if not hour_part:
            return None
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", hour_part.replace(" ", ""))
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if h > 23 or mi > 59:
        return None
    dt = datetime.combine(day, datetime.min.time()).replace(hour=h, minute=mi)
    if dt <= now and hour_part == t:          # "18:30" that already passed -> tomorrow
        dt += timedelta(days=1)
    return dt.timestamp()


def quick_times(now=None):
    """Choices for the menus: (label, timestamp)."""
    now = now or datetime.now()
    morning = datetime.combine(now.date() + timedelta(days=1), datetime.min.time()).replace(hour=9)
    evening = now.replace(hour=20, minute=0, second=0, microsecond=0)
    out = [("In 20 minutes", (now + timedelta(minutes=20)).timestamp()),
           ("In 1 hour", (now + timedelta(hours=1)).timestamp()),
           ("In 3 hours", (now + timedelta(hours=3)).timestamp())]
    if evening > now + timedelta(minutes=30):
        out.append(("This evening (8 PM)", evening.timestamp()))
    out.append(("Tomorrow morning (9 AM)", morning.timestamp()))
    return out


def _tr(text, **kw):
    try:
        import i18n
        text = i18n.tr(text)
    except Exception:
        pass
    try:
        return text.format(**kw)
    except (KeyError, IndexError, ValueError):
        return text


def when_text(ts, now=None):
    now = now or time.time()
    d = ts - now
    dt = datetime.fromtimestamp(ts)
    if d < 0:
        return dt.strftime("%Y-%m-%d %H:%M")
    if d < 3600:
        return _tr("in {n} min", n=max(1, int(d // 60)))
    if dt.date() == datetime.fromtimestamp(now).date():
        return _tr("today at {t}", t=dt.strftime("%H:%M"))
    if dt.date() == (datetime.fromtimestamp(now) + timedelta(days=1)).date():
        return _tr("tomorrow at {t}", t=dt.strftime("%H:%M"))
    return dt.strftime("%Y-%m-%d %H:%M")


# ------------------------------------------------------------------ reminders
def reminders(account=None):
    r = _load("reminders.json", [])
    return [x for x in r if account is None or x.get("account") == account]


def add_reminder(account, at, note="", msg=None, chat=None, guild=None):
    m = msg or {}
    a = m.get("author") or {}
    r = {"id": new_id(), "account": account, "at": float(at), "note": note or "",
         "message_id": m.get("id"), "channel_id": m.get("channel_id"), "guild": guild,
         "chat": chat or "", "author": a.get("global_name") or a.get("username") or "",
         "text": (m.get("content") or "")[:300], "done": False, "created": time.time()}
    _save("reminders.json", _load("reminders.json", []) + [r])
    return r


def due_reminders(account, now=None):
    now = now or time.time()
    return [r for r in reminders(account) if not r.get("done") and r["at"] <= now]


def finish_reminder(rid, snooze_to=None):
    rs = _load("reminders.json", [])
    for r in rs:
        if r["id"] == rid:
            if snooze_to:
                r["at"] = float(snooze_to)
                r["done"] = False
            else:
                r["done"] = True
    _save("reminders.json", rs)


def delete_reminder(rid):
    _save("reminders.json", [r for r in _load("reminders.json", []) if r["id"] != rid])


def clear_done_reminders(account):
    _save("reminders.json", [r for r in _load("reminders.json", [])
                             if not (r.get("done") and r.get("account") == account)])


# ------------------------------------------------------------------ send later
def scheduled(account=None):
    s = _load("scheduled.json", [])
    return [x for x in s if account is None or x.get("account") == account]


def pending_count(account):
    return sum(1 for x in scheduled(account) if x["status"] in ("pending", "missed"))


def schedule(account, channel_id, chat, content, at, reply_to=None):
    import safety
    if len(content) > 2000:
        raise ValueError(_tr("Discord messages can be 2000 characters max."))
    if not content.strip():
        raise ValueError(_tr("Write a message first."))
    if at < time.time() + 30:
        raise ValueError(_tr("Pick a time at least one minute from now."))
    if safety.enabled() and pending_count(account) >= safety.MAX_PENDING_SENDS:
        raise ValueError(_tr("Safe mode: at most {n} messages can wait to be sent.",
                             n=safety.MAX_PENDING_SENDS))
    s = {"id": new_id(), "account": account, "channel_id": channel_id, "chat": chat,
         "content": content, "at": float(at), "reply_to": reply_to, "status": "pending",
         "created": time.time(), "error": ""}
    _save("scheduled.json", _load("scheduled.json", []) + [s])
    return s


def due_sends(account, now=None):
    """(send_now, missed): due messages to send, and ones that are too late (marked missed).
    At most one is returned to send per call, so they never go out in a burst."""
    now = now or time.time()
    s = _load("scheduled.json", [])
    send, missed, changed = [], [], False
    for x in s:
        if x.get("account") != account or x["status"] != "pending" or x["at"] > now:
            continue
        if now - x["at"] > LATE_OK_S:
            x["status"] = "missed"
            missed.append(x)
            changed = True
        elif not send:
            send.append(x)
    if changed:
        _save("scheduled.json", s)
    return send, missed


def set_send_status(sid, status, error=""):
    s = _load("scheduled.json", [])
    for x in s:
        if x["id"] == sid:
            x["status"] = status
            x["error"] = error
            if status == "pending":
                x["at"] = max(x["at"], time.time() + 5)
    _save("scheduled.json", s)


def update_send(sid, **kw):
    s = _load("scheduled.json", [])
    for x in s:
        if x["id"] == sid:
            x.update(kw)
    _save("scheduled.json", s)


def delete_send(sid):
    _save("scheduled.json", [x for x in _load("scheduled.json", []) if x["id"] != sid])


# ------------------------------------------------------------------ snippets
def snippets():
    return _load("snippets.json", [])


def save_snippet(name, text, sid=None):
    name = re.sub(r"\s+", "-", (name or "").strip().lower())[:30]
    if not name or not text.strip():
        raise ValueError(_tr("Give the reply a short name and some text."))
    items = [s for s in snippets() if s["id"] != sid and s["name"] != name]
    items.append({"id": sid or new_id(), "name": name, "text": text})
    items.sort(key=lambda s: s["name"])
    _save("snippets.json", items)


def delete_snippet(sid):
    _save("snippets.json", [s for s in snippets() if s["id"] != sid])


def expand(word):
    """';name' -> the snippet text, or None."""
    if not word.startswith(";") or len(word) < 2:
        return None
    for s in snippets():
        if s["name"] == word[1:].lower():
            return s["text"]
    return None


# ------------------------------------------------------------------ keyword alerts
DEFAULT_ALERTS = {"enabled": True, "words": [], "dms": True, "servers": True,
                  "ignore_muted": True}


def alert_settings():
    return dict(DEFAULT_ALERTS, **_load("alerts.json", {}))


def save_alert_settings(d):
    cur = _load("alerts.json", {})
    cur.update(d)
    _save("alerts.json", cur)


def parse_words(text):
    out = []
    for w in re.split(r"[,\n]", text or ""):
        w = w.strip()
        if w and w.lower() not in [x.lower() for x in out]:
            out.append(w[:60])
    return out[:50]


def _rx(word):
    if word.startswith("/") and word.endswith("/") and len(word) > 2:
        try:
            return re.compile(word[1:-1], re.I)
        except re.error:
            return None
    w = re.escape(word)
    return re.compile(rf"(?<!\w){w}(?!\w)" if re.match(r"\w", word[0]) and re.match(r"\w", word[-1])
                      else w, re.I)


def match_words(text, words):
    """First keyword found in text (whole words, any case; /regex/ allowed), or None."""
    for w in words or []:
        r = _rx(w)
        if r and r.search(text or ""):
            return w
    return None


def check_alert(msg, me_id, cfg=None):
    """Keyword that this live message hits, or None."""
    cfg = cfg or alert_settings()
    if not cfg.get("enabled") or not cfg.get("words"):
        return None
    a = msg.get("author") or {}
    if a.get("id") == me_id or a.get("bot"):
        return None
    if msg.get("guild_id") and not cfg.get("servers", True):
        return None
    if not msg.get("guild_id") and not cfg.get("dms", True):
        return None
    return match_words(msg.get("content") or "", cfg["words"])


def alert_inbox(account):
    return [x for x in _load("alert_inbox.json", []) if x.get("account") == account]


def add_to_inbox(account, msg, word, chat):
    a = msg.get("author") or {}
    items = _load("alert_inbox.json", [])
    items.insert(0, {"id": msg.get("id"), "account": account, "word": word, "chat": chat,
                     "channel_id": msg.get("channel_id"), "guild": msg.get("guild_id"),
                     "author": a.get("global_name") or a.get("username") or "?",
                     "text": (msg.get("content") or "")[:300], "at": time.time(),
                     "seen": False})
    _save("alert_inbox.json", items[:300])


def mark_inbox_seen(account):
    items = _load("alert_inbox.json", [])
    for x in items:
        if x.get("account") == account:
            x["seen"] = True
    _save("alert_inbox.json", items)


def clear_inbox(account):
    _save("alert_inbox.json", [x for x in _load("alert_inbox.json", [])
                               if x.get("account") != account])
