"""Auto-clean rules: "every day, delete my messages older than 30 days in these chats".

Rules run while the app is open, and (optionally) once a day through Windows Task
Scheduler even when it's closed:  DiscordMessageCleaner.exe --run-rules
Running without the app needs a saved account ("Remember me").
"""
import json
import os
import subprocess
import sys
import threading
import time
import uuid

import applog
import cleaner_core as core
import securestore

TASK_NAME = "DiscordMessageCleaner AutoClean"
INTERVALS = {"hour": 3600, "day": 86400, "week": 7 * 86400}
INTERVAL_NAMES = {"hour": "Every hour", "day": "Every day", "week": "Every week"}


def _data(name):
    root = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    return os.path.join(root, "DiscordMessageCleaner", name)


def load_rules():
    try:
        with open(_data("rules.json"), encoding="utf-8") as f:
            rules = json.load(f)
        return rules if isinstance(rules, list) else []
    except Exception:
        return []


def save_rules(rules):
    os.makedirs(os.path.dirname(_data("rules.json")), exist_ok=True)
    tmp = _data("rules.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=1)
    os.replace(tmp, _data("rules.json"))


def new_rule(name, targets, options, account_id, every="day", older_than_days=30):
    opts = dict(options, dry_run=False, older_than_days=int(older_than_days))
    return {"id": uuid.uuid4().hex[:10], "name": name, "targets": targets, "options": opts,
            "account_id": account_id, "every": every, "enabled": True, "last_run": 0,
            "last_result": ""}


def new_backup_rule(name, targets, account_id, every="week", keep=4, folder=None):
    """Backup rule: save whole conversations (everyone's messages + files) on a schedule."""
    return {"id": uuid.uuid4().hex[:10], "kind": "backup", "name": name,
            "targets": [t for t in targets if t.get("kind") == "channel"],
            "options": {"keep": int(keep), "folder": folder or default_backup_folder(),
                        "with_files": True},
            "account_id": account_id, "every": every, "enabled": True, "last_run": 0,
            "last_result": ""}


def default_backup_folder():
    return os.path.join(os.path.expanduser("~"), "Documents", "Discord Cleaner Backups",
                        "Automatic backups")


def run_backup(rule, make_api, log=applog.write, should_stop=lambda: False):
    """Save every chat of a backup rule. Keeps the newest `keep` copies of each chat.
    Returns the number of chats saved."""
    o = rule.get("options") or {}
    base = o.get("folder") or default_backup_folder()
    os.makedirs(base, exist_ok=True)
    saved = 0
    for t in rule["targets"]:
        if should_stop():
            break
        title = t.get("short") or t.get("name") or t["id"]
        try:
            folder, n, files = core.save_conversation(make_api(), t["id"], title, base, log,
                                                      should_stop=should_stop,
                                                      with_files=o.get("with_files", True))
            saved += 1
            log(f"Backup '{rule['name']}': saved {title} ({n:,} messages, {files} files)")
        except Exception as e:
            log(f"Backup '{rule['name']}': {title} failed: {applog.mask(e)}")
        _keep_newest(base, core.safe_name(title), int(o.get("keep", 4) or 4))
    return saved


def _keep_newest(base, prefix, keep):
    import shutil
    try:
        olds = sorted((d for d in os.listdir(base) if d.startswith(prefix + "_")
                       and os.path.isdir(os.path.join(base, d))),
                      key=lambda d: os.path.getmtime(os.path.join(base, d)), reverse=True)
        for d in olds[keep:]:
            shutil.rmtree(os.path.join(base, d), ignore_errors=True)
    except OSError:
        pass


def is_due(rule, now=None):
    now = now or time.time()
    return rule.get("enabled") and now - rule.get("last_run", 0) >= INTERVALS.get(
        rule.get("every", "day"), 86400) - 60


def describe(rule):
    o = rule["options"]
    if rule.get("kind") == "backup":
        return (f"{INTERVAL_NAMES.get(rule.get('every'), 'Every week').lower()}, back up "
                f"{len(rule['targets'])} chat(s), keep {o.get('keep', 4)} copies")
    parts = [INTERVAL_NAMES.get(rule.get("every"), "Every day").lower()]
    if o.get("older_than_days"):
        parts.append(f"older than {o['older_than_days']} days")
    if o.get("keywords"):
        parts.append(f"keywords: {o['keywords']}")
    parts.append(f"{len(rule['targets'])} chat(s)")
    return ", ".join(parts)


def run_rule(rule, token, log=applog.write, should_stop=lambda: False, sleep=time.sleep,
             progress=lambda s: None):
    """Run one rule now (blocking). Returns the number of deleted messages."""
    keep = []
    try:
        with open(_data("keep.json"), encoding="utf-8") as f:
            keep = json.load(f)
    except Exception:
        pass
    backup = os.path.join(os.path.expanduser("~"), "Documents", "Discord Cleaner Backups")
    import safety
    if not safety.risk_on("rules"):
        log(f"Auto-clean rule '{rule['name']}' skipped: deleting rules are a risky feature and "
            "are switched off in the Risk tab.")
        return 0
    o = safety.harden_rule_options(dict(rule["options"], dry_run=False))
    opts = core.options_from_dict(o, keep, backup)
    opts.pacer = core.Pacer(opts.delay, auto=o.get("auto_speed", True))
    hit = []
    safety.harden_pacer(opts.pacer, stop=lambda: hit.append(1))
    if hit:
        log(f"Auto-clean rule '{rule['name']}': daily safety limit reached, skipped until tomorrow.")
        return 0
    first_stop = should_stop
    should_stop = lambda: bool(hit) or first_stop()   # noqa: E731

    def make_api():
        return core.DiscordApi(token, log, should_stop, sleep, pacer=opts.pacer)
    log(f"Auto-clean rule '{rule['name']}': {describe(rule)}")
    results = core.run_many(make_api, opts, rule["targets"],
                            int(o.get("parallel", 2) or 2), log, progress,
                            should_stop, sleep)
    deleted = sum(r.get("deleted", 0) for r in results)
    if hit:
        log(f"Auto-clean rule '{rule['name']}': daily safety limit reached, the rest waits for tomorrow.")
    log(f"Auto-clean rule '{rule['name']}' finished: {deleted} deleted.")
    return deleted


def run_headless():
    """Entry point for --run-rules (Windows Task Scheduler)."""
    applog.write("=== Auto-clean started without the app ===")
    rules = load_rules()
    total = 0
    for rule in rules:
        if not is_due(rule):
            continue
        token = securestore.get_account_token(rule.get("account_id"))
        if not token:
            rule["last_result"] = "No saved account: open the app and tick Remember me."
            applog.write(f"Rule '{rule['name']}': {rule['last_result']}")
            continue
        try:
            if rule.get("kind") == "backup":
                n = run_backup(rule, lambda: core.DiscordApi(token, applog.write,
                                                             lambda: False, time.sleep))
                rule["last_result"] = f"{n} chat(s) saved"
                rule["last_run"] = time.time()
                continue
            n = run_rule(rule, token)
            total += n
            rule["last_result"] = f"{n} deleted"
        except Exception as e:
            rule["last_result"] = f"Error: {e}"
            applog.write(f"Rule '{rule['name']}' failed: {applog.mask(e)}")
        rule["last_run"] = time.time()
    save_rules(rules)
    if total:
        try:
            path = _data("settings.json")
            with open(path, encoding="utf-8") as f:
                st = json.load(f)
            st["total_deleted"] = int(st.get("total_deleted", 0) or 0) + total
            with open(path, "w", encoding="utf-8") as f:
                json.dump(st, f, indent=2)
        except Exception:
            pass
    applog.write("=== Auto-clean done ===")


# ----------------------------------------------------------------- Windows Task Scheduler
def _command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --run-rules'
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    app = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    return f'"{pyw if os.path.exists(pyw) else exe}" "{app}" --run-rules'


def _schtasks(*args):
    flags = 0x08000000 if sys.platform == "win32" else 0   # CREATE_NO_WINDOW
    return subprocess.run(["schtasks", *args], capture_output=True, text=True,
                          creationflags=flags)


def task_installed():
    if sys.platform != "win32":
        return False
    try:
        return _schtasks("/Query", "/TN", TASK_NAME).returncode == 0
    except OSError:
        return False


def install_task(at="03:00"):
    """Run due rules every day at `at` (HH:MM), even when the app is closed."""
    r = _schtasks("/Create", "/F", "/SC", "DAILY", "/ST", at, "/TN", TASK_NAME,
                  "/TR", _command())
    if r.returncode != 0:
        raise OSError((r.stderr or r.stdout or "schtasks failed").strip())


def remove_task():
    _schtasks("/Delete", "/F", "/TN", TASK_NAME)


class RuleTimer:
    """Checks rules every few minutes while the app is open."""

    def __init__(self, app, run_callback, every_s=300):
        self.app = app
        self.run_callback = run_callback
        self.every_ms = every_s * 1000
        self.lock = threading.Lock()

    def start(self):
        self.app.after(60 * 1000, self.tick)

    def tick(self):
        try:
            for rule in load_rules():
                if is_due(rule):
                    if self.run_callback(rule):
                        break   # one at a time
        finally:
            self.app.after(self.every_ms, self.tick)
