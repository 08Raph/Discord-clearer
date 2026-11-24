"""Archive: a copy of your chats on this PC that you can search offline.

  * Chats you add are downloaded once (everyone's messages, text only, no files), then
    only the new messages are fetched ("sync"). Reading only: it never changes anything
    on Discord, so it carries almost no ban risk. It still goes slowly (about one page of
    100 messages every 1.5 s) so it looks like someone scrolling up.
  * Search runs on this PC: words, a person, a chat, dates.
  * "Your year" (recap) is computed from the archive, no requests at all.
  * Backups made by the app (messages.json) can be imported.

Stored in archive.db (SQLite, full-text search when available) next to the settings."""
import json
import os
import random
import re
import sqlite3
import threading
import time
from collections import Counter
from datetime import datetime

import cleaner_core as core

PAGE_GAP = (1.2, 2.2)     # seconds between pages (random)
WORD_RE = re.compile(r"[\w']{3,}", re.U)
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
STOP = set("""the and you that for are with this have was but not what all just your can
its it's i'm dont don't like get got lol yes yeah okay que les des une pour pas est qui
und der die das ist nicht ich ein eine los las por con para una""".split())


def db_path():
    root = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    return os.path.join(root, "DiscordMessageCleaner", "archive.db")


def _ts(m):
    try:
        return int(datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00")).timestamp())
    except Exception:
        try:
            return int(((int(m["id"]) >> 22) + 1420070400000) / 1000)
        except Exception:
            return 0


class Archive:
    def __init__(self, path=None):
        self.path = path or db_path()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self.lock:
            self.db.executescript("""
            CREATE TABLE IF NOT EXISTS chats(account TEXT, channel_id TEXT, name TEXT,
                kind TEXT, guild TEXT, newest TEXT, oldest TEXT, complete INTEGER DEFAULT 0,
                auto INTEGER DEFAULT 1, synced REAL DEFAULT 0, PRIMARY KEY(account, channel_id));
            CREATE TABLE IF NOT EXISTS msgs(account TEXT, id TEXT, channel_id TEXT,
                author_id TEXT, author TEXT, ts INTEGER, content TEXT, files TEXT,
                PRIMARY KEY(account, id));
            CREATE INDEX IF NOT EXISTS msgs_chat ON msgs(account, channel_id, ts);
            CREATE INDEX IF NOT EXISTS msgs_author ON msgs(account, author_id, ts);
            """)
            try:
                self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5("
                                "content, author, account UNINDEXED, id UNINDEXED)")
                self.fts = True
            except sqlite3.OperationalError:
                self.fts = False
            self.db.commit()

    # ------------------------------------------------------------------ chats
    def add_chat(self, account, channel_id, name, kind="dm", guild=None):
        with self.lock:
            self.db.execute("INSERT OR IGNORE INTO chats(account, channel_id, name, kind, guild)"
                            " VALUES(?,?,?,?,?)", (account, channel_id, name, kind, guild))
            self.db.execute("UPDATE chats SET name=?, auto=1 WHERE account=? AND channel_id=?",
                            (name, account, channel_id))
            self.db.commit()

    def remove_chat(self, account, channel_id, keep_messages=False):
        with self.lock:
            self.db.execute("DELETE FROM chats WHERE account=? AND channel_id=?",
                            (account, channel_id))
            if not keep_messages:
                ids = [r[0] for r in self.db.execute(
                    "SELECT id FROM msgs WHERE account=? AND channel_id=?", (account, channel_id))]
                self.db.execute("DELETE FROM msgs WHERE account=? AND channel_id=?",
                                (account, channel_id))
                if self.fts and ids:
                    self.db.executemany("DELETE FROM fts WHERE account=? AND id=?",
                                        [(account, i) for i in ids])
            self.db.commit()

    def chats(self, account):
        with self.lock:
            rows = self.db.execute(
                "SELECT c.*, (SELECT COUNT(*) FROM msgs m WHERE m.account=c.account AND "
                "m.channel_id=c.channel_id) AS count FROM chats c WHERE account=? "
                "ORDER BY name COLLATE NOCASE", (account,)).fetchall()
        return [dict(r) for r in rows]

    def has_chat(self, account, channel_id):
        with self.lock:
            return self.db.execute("SELECT 1 FROM chats WHERE account=? AND channel_id=?",
                                   (account, channel_id)).fetchone() is not None

    def total(self, account):
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM msgs WHERE account=?",
                                   (account,)).fetchone()[0]

    # ------------------------------------------------------------------ store
    def put(self, account, channel_id, messages):
        rows, fts = [], []
        for m in messages:
            if not m.get("id"):
                continue
            a = m.get("author") or {}
            name = a.get("global_name") or a.get("username") or "?"
            text = core.render_content(m) if m.get("content") else ""
            files = [x.get("filename") or "" for x in m.get("attachments") or []]
            rows.append((account, m["id"], channel_id, a.get("id"), name, _ts(m), text,
                         json.dumps(files) if files else None))
            fts.append((text, name, account, m["id"]))
        if not rows:
            return 0
        with self.lock:
            before = self.db.total_changes
            self.db.executemany("INSERT OR IGNORE INTO msgs VALUES(?,?,?,?,?,?,?,?)", rows)
            added = self.db.total_changes - before
            if self.fts and added:
                new = {r[0] for r in self.db.execute(
                    "SELECT id FROM msgs WHERE account=? AND id IN (%s)" % ",".join(
                        "?" * len(rows)), [account] + [r[1] for r in rows])}
                have = {r[0] for r in self.db.execute(
                    "SELECT id FROM fts WHERE account=? AND id IN (%s)" % ",".join(
                        "?" * len(rows)), [account] + [r[1] for r in rows])}
                self.db.executemany("INSERT INTO fts VALUES(?,?,?,?)",
                                    [f for f in fts if f[3] in new and f[3] not in have])
            self.db.commit()
        return added

    def _set(self, account, channel_id, **kw):
        with self.lock:
            for k, v in kw.items():
                self.db.execute(f"UPDATE chats SET {k}=? WHERE account=? AND channel_id=?",
                                (v, account, channel_id))
            self.db.commit()

    def _chat(self, account, channel_id):
        with self.lock:
            r = self.db.execute("SELECT * FROM chats WHERE account=? AND channel_id=?",
                                (account, channel_id)).fetchone()
        return dict(r) if r else None

    # ------------------------------------------------------------------ sync
    def sync_chat(self, api, account, channel_id, should_stop=lambda: False,
                  sleep=time.sleep, progress=lambda n: None, max_pages=None, rnd=random):
        """Fetch new messages, then keep going back in history until the start of the chat.
        Read-only and paced. Returns the number of new messages."""
        c = self._chat(account, channel_id)
        if c is None:
            return 0
        added, pages = 0, 0

        def wait():
            sleep(rnd.uniform(*PAGE_GAP))

        # 1) newer than what we have
        after = c.get("newest")
        while after and not should_stop():
            st, msgs = api.request("GET", f"/channels/{channel_id}/messages?limit=100&after={after}")
            if st != 200 or not msgs:
                break
            msgs = sorted((m for m in msgs if int(m["id"]) > int(after)), key=lambda m: int(m["id"]))
            if not msgs:
                break
            added += self.put(account, channel_id, msgs)
            after = msgs[-1]["id"]
            self._set(account, channel_id, newest=after)
            progress(added)
            pages += 1
            if len(msgs) < 100 or (max_pages and pages >= max_pages):
                break
            wait()
        # 2) back in time until the first message
        before = c.get("oldest")
        while not c.get("complete") and not should_stop() and not (max_pages and pages >= max_pages):
            if pages:
                wait()
            st, msgs = core.fetch_messages(api, channel_id, before, 100)
            pages += 1
            if st != 200:
                break
            if not msgs:
                self._set(account, channel_id, complete=1)
                break
            added += self.put(account, channel_id, msgs)
            ids = sorted(int(m["id"]) for m in msgs)
            before = str(ids[0])
            upd = {"oldest": before}
            if not self._chat(account, channel_id).get("newest"):
                upd["newest"] = str(ids[-1])
            self._set(account, channel_id, **upd)
            progress(added)
            if len(msgs) < 100:
                self._set(account, channel_id, complete=1)
                break
        self._set(account, channel_id, synced=time.time())
        return added

    def sync_all(self, api, account, should_stop=lambda: False, sleep=time.sleep,
                 progress=lambda name, n: None, only_auto=True):
        total = 0
        for c in self.chats(account):
            if should_stop():
                break
            if only_auto and not c.get("auto"):
                continue
            total += self.sync_chat(api, account, c["channel_id"], should_stop, sleep,
                                    lambda n, c=c: progress(c["name"], n))
        return total

    # ------------------------------------------------------------------ backups
    def import_backup(self, account, path):
        """messages.json from a saved conversation (or a folder that has one)."""
        if os.path.isdir(path):
            path = os.path.join(path, "messages.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        msgs = data.get("messages") if isinstance(data, dict) else data
        cid = (data.get("channel_id") if isinstance(data, dict) else None) or (
            msgs[0].get("channel_id") if msgs else None) or "backup"
        title = (data.get("title") if isinstance(data, dict) else None) or os.path.basename(
            os.path.dirname(path))
        if not self.has_chat(account, cid):
            self.add_chat(account, cid, title, "backup")
            self._set(account, cid, auto=0)
        return title, self.put(account, cid, msgs or [])

    # ------------------------------------------------------------------ search
    def search(self, account, text="", channel_id=None, author=None, since=None, until=None,
               only_author_id=None, limit=300):
        q = ["m.account=?"]
        args = [account]
        text = (text or "").strip()
        if text and self.fts:
            terms = [t for t in re.findall(r'"[^"]+"|\S+', text)]
            match = " ".join(t if t.startswith('"') else '"' + t.replace('"', "") + '"*'
                             for t in terms)
            q.append("m.id IN (SELECT id FROM fts WHERE fts MATCH ? AND account=?)")
            args += [f"content : ({match})", account]
        elif text:
            for t in text.split():
                q.append("m.content LIKE ?")
                args.append(f"%{t.strip(chr(34))}%")
        if channel_id:
            q.append("m.channel_id=?")
            args.append(channel_id)
        if author:
            q.append("m.author LIKE ?")
            args.append(f"%{author}%")
        if only_author_id:
            q.append("m.author_id=?")
            args.append(only_author_id)
        if since:
            q.append("m.ts>=?")
            args.append(int(since))
        if until:
            q.append("m.ts<?")
            args.append(int(until))
        sql = ("SELECT m.*, c.name AS chat, c.guild AS guild FROM msgs m LEFT JOIN chats c ON "
               "c.account=m.account AND c.channel_id=m.channel_id WHERE " + " AND ".join(q) +
               " ORDER BY m.ts DESC LIMIT ?")
        args.append(int(limit))
        try:
            with self.lock:
                rows = self.db.execute(sql, args).fetchall()
        except sqlite3.OperationalError:          # odd search text for FTS: plain search
            if text and self.fts:
                self.fts = False
                try:
                    return self.search(account, text, channel_id, author, since, until,
                                       only_author_id, limit)
                finally:
                    self.fts = True
            raise
        return [dict(r) for r in rows]

    def context(self, account, channel_id, ts, n=6):
        with self.lock:
            before = self.db.execute("SELECT * FROM msgs WHERE account=? AND channel_id=? AND "
                                     "ts<=? ORDER BY ts DESC LIMIT ?",
                                     (account, channel_id, ts, n + 1)).fetchall()
            after = self.db.execute("SELECT * FROM msgs WHERE account=? AND channel_id=? AND "
                                    "ts>? ORDER BY ts LIMIT ?", (account, channel_id, ts, n)).fetchall()
        return [dict(r) for r in reversed(before)] + [dict(r) for r in after]

    # ------------------------------------------------------------------ recap
    def recap(self, account, me_id, year=None):
        """Numbers for "Your year": everything is computed from the archive."""
        if year:
            lo = int(datetime(year, 1, 1).timestamp())
            hi = int(datetime(year + 1, 1, 1).timestamp())
        else:
            lo, hi = 0, 2 ** 40
        with self.lock:
            rows = self.db.execute(
                "SELECT m.channel_id, m.author_id, m.author, m.ts, m.content, c.name AS chat, "
                "c.kind AS kind FROM msgs m LEFT JOIN chats c ON c.account=m.account AND "
                "c.channel_id=m.channel_id WHERE m.account=? AND m.ts>=? AND m.ts<?",
                (account, lo, hi)).fetchall()
        hours, days, months = [0] * 24, [0] * 7, [0] * 12
        people, chats, words, emojis, active = Counter(), Counter(), Counter(), Counter(), set()
        mine = 0
        first = last = None
        for r in rows:
            dt = datetime.fromtimestamp(r["ts"])
            first = dt if first is None or dt < first else first
            last = dt if last is None or dt > last else last
            chats[r["chat"] or "?"] += 1
            if r["author_id"] != me_id:
                people[r["author"] or "?"] += 1
                continue
            mine += 1
            hours[dt.hour] += 1
            days[dt.weekday()] += 1
            months[dt.month - 1] += 1
            active.add(dt.date())
            text = r["content"] or ""
            for w in WORD_RE.findall(text.lower()):
                if w not in STOP and not w.isdigit() and not w.startswith("http"):
                    words[w] += 1
            for e in EMOJI_RE.findall(text):
                emojis[e] += 1
        streak = best = 0
        prev = None
        for d in sorted(active):
            streak = streak + 1 if prev and (d - prev).days == 1 else 1
            best = max(best, streak)
            prev = d
        return {"year": year, "total": len(rows), "mine": mine, "hours": hours, "days": days,
                "months": months, "people": people.most_common(8), "chats": chats.most_common(8),
                "words": words.most_common(12), "emojis": emojis.most_common(8),
                "active_days": len(active), "streak": best, "first": first, "last": last,
                "busiest_hour": max(range(24), key=lambda h: hours[h]) if mine else None,
                "busiest_day": max(range(7), key=lambda d: days[d]) if mine else None}

    def years(self, account):
        with self.lock:
            r = self.db.execute("SELECT MIN(ts), MAX(ts) FROM msgs WHERE account=?",
                                (account,)).fetchone()
        if not r or not r[0]:
            return []
        return list(range(datetime.fromtimestamp(r[1]).year,
                          datetime.fromtimestamp(r[0]).year - 1, -1))

    def close(self):
        try:
            self.db.close()
        except Exception:
            pass


DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
               "Dec"]


def recap_html(r, name, path):
    """A one-page "Your year" you can open in a browser and screenshot / share."""
    import html as h

    def bars(vals, labels):
        top = max(vals) or 1
        return "".join(f'<div class="bar"><i style="height:{max(2, v * 100 // top)}%"></i>'
                       f'<span>{h.escape(lb)}</span></div>' for v, lb in zip(vals, labels))

    def lst(items):
        return "".join(f"<li><b>{h.escape(str(k))}</b><span>{v:,}</span></li>" for k, v in items) \
            or "<li>—</li>"
    hour = r.get("busiest_hour")
    day = r.get("busiest_day")
    title = f"{name} · {r['year'] or 'All time'}"
    doc = f"""<!doctype html><meta charset="utf-8"><title>{h.escape(title)}</title>
<style>body{{background:#1e1f22;color:#dbdee1;font:15px system-ui,Segoe UI,sans-serif;margin:0;padding:30px}}
.w{{max-width:860px;margin:auto}}h1{{color:#fff;margin:0}}.sub{{color:#949ba4;margin:4px 0 22px}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.c{{background:#2b2d31;border-radius:10px;padding:14px}}
.c b{{display:block;font-size:26px;color:#fff}}.c span{{color:#949ba4;font-size:12px}}
.g{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}}.box{{background:#2b2d31;border-radius:10px;padding:14px}}
h3{{margin:0 0 10px;color:#fff;font-size:14px}}.bars{{display:flex;align-items:flex-end;height:120px;gap:3px}}
.bar{{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;height:100%}}
.bar i{{display:block;width:100%;background:#5865f2;border-radius:3px 3px 0 0}}.bar span{{font-size:9px;color:#949ba4}}
ul{{list-style:none;margin:0;padding:0}}li{{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #3f4147}}
.f{{color:#6d6f78;font-size:11px;margin-top:18px}}</style><div class="w">
<h1>{h.escape(title)}</h1><div class="sub">Made on your PC from your archive by Discord Message Cleaner</div>
<div class="cards"><div class="c"><b>{r['mine']:,}</b><span>messages you sent</span></div>
<div class="c"><b>{r['active_days']:,}</b><span>days you talked</span></div>
<div class="c"><b>{r['streak']:,}</b><span>days in a row (best)</span></div>
<div class="c"><b>{'' if hour is None else f'{hour}:00'}</b><span>busiest hour{'' if day is None else ' · ' + DAY_NAMES[day]}</span></div></div>
<div class="g"><div class="box"><h3>By hour</h3><div class="bars">{bars(r['hours'], [str(i) if i % 3 == 0 else '' for i in range(24)])}</div></div>
<div class="box"><h3>By month</h3><div class="bars">{bars(r['months'], MONTH_NAMES)}</div></div>
<div class="box"><h3>People who talked to you most</h3><ul>{lst(r['people'])}</ul></div>
<div class="box"><h3>Busiest chats</h3><ul>{lst(r['chats'])}</ul></div>
<div class="box"><h3>Your words</h3><ul>{lst(r['words'][:8])}</ul></div>
<div class="box"><h3>Your emojis</h3><ul>{lst(r['emojis'])}</ul></div></div>
<div class="f">Only chats in your archive are counted.</div></div>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return path
