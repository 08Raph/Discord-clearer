"""Safe mode: keeps the app's automatic actions slow and small so they look like a person
using Discord, not a bot. Nothing here can make a user-account tool "allowed" by Discord,
but it keeps the ban risk as low as it can be:

  * automatic deleting (rules) goes one chat at a time, at least 2.5 s apart, with random
    pauses, and stops for the day after a daily limit;
  * bulk actions in the privacy sweeper (leave servers, close DMs, remove friends) wait
    several random seconds between each one and have small daily limits;
  * scheduled messages are capped and never sent in a burst.

Counts are kept per day in safety.json next to the other settings."""
import json
import os
import random
import threading
import time

# kind -> (default daily limit, min gap s, max gap s)
LIMITS = {
    "auto_delete": (300, 2.5, 4.5),   # deletes made by auto-clean rules
    "leave": (10, 6.0, 14.0),         # leaving servers
    "close": (40, 2.0, 5.0),          # closing DMs (messages are not deleted)
    "unfriend": (10, 6.0, 14.0),      # removing friends
    "send": (30, 0.0, 0.0),           # scheduled messages sent
}
NAMES = {"auto_delete": "Automatic deletes", "leave": "Servers left", "close": "DMs closed",
         "unfriend": "Friends removed", "send": "Scheduled messages sent"}
MIN_RULE_DELAY = 2.5
JITTER = 0.45                          # +0 … +45 % random extra wait
MAX_PENDING_SENDS = 20
_lock = threading.Lock()


def _path():
    root = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    return os.path.join(root, "DiscordMessageCleaner", "safety.json")


def _today():
    return time.strftime("%Y-%m-%d")


def _read():
    try:
        with open(_path(), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _write(d):
    os.makedirs(os.path.dirname(_path()), exist_ok=True)
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, _path())


def enabled():
    return _read().get("safe_mode", True) is not False


def set_enabled(on):
    with _lock:
        d = _read()
        d["safe_mode"] = bool(on)
        _write(d)


def limit(kind):
    d = _read()
    try:
        return max(0, int((d.get("limits") or {}).get(kind, LIMITS[kind][0])))
    except (TypeError, ValueError):
        return LIMITS[kind][0]


def set_limit(kind, n):
    with _lock:
        d = _read()
        d.setdefault("limits", {})[kind] = max(0, int(n))
        _write(d)


def used(kind):
    d = _read()
    day = d.get("counts") or {}
    return int(day.get(kind, 0)) if day.get("day") == _today() else 0


def left(kind):
    """How many more of this action are allowed today (unlimited when safe mode is off)."""
    if not enabled():
        return 10 ** 9
    return max(0, limit(kind) - used(kind))


def use(kind, n=1):
    with _lock:
        d = _read()
        c = d.get("counts") or {}
        if c.get("day") != _today():
            c = {"day": _today()}
        c[kind] = int(c.get(kind, 0)) + n
        d["counts"] = c
        _write(d)


def gap(kind, rnd=random):
    """Random wait (seconds) before the next action of this kind."""
    _n, lo, hi = LIMITS[kind]
    if not enabled():
        return lo / 2
    return rnd.uniform(lo, hi)


def jittered(delay, rnd=random):
    return delay * (1 + rnd.uniform(0, JITTER)) if enabled() else delay


def harden_rule_options(d):
    """Options dict of an auto-clean rule -> safe version (one chat at a time, slower)."""
    if not enabled():
        return d
    d = dict(d)
    d["parallel"] = 1
    d["auto_speed"] = True
    try:
        d["delay"] = max(MIN_RULE_DELAY, float(d.get("delay", MIN_RULE_DELAY)))
    except (TypeError, ValueError):
        d["delay"] = MIN_RULE_DELAY
    return d


def harden_pacer(pacer, stop=None, kind="auto_delete"):
    """Random extra wait after each delete, count it, and call stop() at the daily limit."""
    if not enabled():
        return pacer
    pacer.jitter = JITTER
    pacer.budget_left = left(kind)

    def counted():
        use(kind)
        pacer.budget_left -= 1
        if pacer.budget_left <= 0 and stop:
            stop()
    pacer.on_delete = counted
    if pacer.budget_left <= 0 and stop:
        stop()
    return pacer


def summary():
    return [(k, NAMES[k], used(k), limit(k)) for k in LIMITS]
