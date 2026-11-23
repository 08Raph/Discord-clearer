"""Demo mode: a pretend Discord account with sample chats, so people can try the app
(or you can record a how-to video) without a token. Nothing real is touched: "deleting"
only removes messages from this in-memory sample."""
import random
import threading
from datetime import datetime, timedelta

import cleaner_core as core

ME = {"id": "100000000000000001", "username": "you", "global_name": "You (demo)",
      "avatar": None, "discriminator": "0"}

_PEOPLE = [("alex", "Alex"), ("sam", "Sam"), ("jordan", "Jordan"), ("maya", "Maya"),
           ("leo", "Léo"), ("nina", "Nina")]
_LINES_ME = ["hello!", "hellos everyone", "hi", "lol that's funny", "gg wp", "brb",
             "can you send the file?", "see you tomorrow", "hello there", "ok",
             "did you see the new update?", "haha", "this is my old message",
             "https://example.com/cool-page", "```py\nprint('hello world')\n```",
             "> quoted text\nmy answer", "hellooo", "what time is the game?", "nice pic",
             "I'll be online at 8"]
_LINES_THEM = ["hey", "what's up?", "hello!", "look at this", "lmao", "ready?",
               "sure", "where are you", "sending it now", "good night", "wow", "same"]
_SERVERS = [("Gaming Squad", ["general", "clips", "memes", "lfg"]),
            ("Homework Help", ["general", "math", "science"]),
            ("Art Club", ["share-your-art", "feedback"])]


def _sf(dt, n):
    return str(core.date_to_snowflake(dt) + n)


class DemoApi:
    """Answers the same requests as DiscordApi, from sample data."""

    def __init__(self):
        rnd = random.Random(42)
        self.lock = threading.Lock()
        self.users = {u: {"id": str(200000000000000000 + i), "username": u, "global_name": g,
                          "avatar": None, "discriminator": "0"}
                      for i, (u, g) in enumerate(_PEOPLE)}
        self.channels = {}      # id -> channel object
        self.messages = {}      # channel id -> list (newest first)
        self.guilds = []
        self.guild_channels = {}
        self.threads = {}
        now = datetime.now()
        n = 0

        def make_msgs(cid, others, count, days):
            nonlocal n
            out = []
            for i in range(count):
                dt = now - timedelta(days=rnd.uniform(0, days), hours=rnd.uniform(0, 23))
                mine = rnd.random() < 0.55
                author = ME if mine else rnd.choice(others)
                text = rnd.choice(_LINES_ME if mine else _LINES_THEM)
                n += 1
                m = {"id": _sf(dt, n), "channel_id": cid, "author": author, "type": 0,
                     "content": text, "timestamp": dt.astimezone().isoformat(),
                     "attachments": [], "embeds": [], "mentions": [], "pinned": False}
                r = rnd.random()
                if r < 0.06:
                    who = rnd.choice(list(self.users.values()))
                    m["attachments"] = [{"id": str(n), "filename": "picture.png",
                                         "content_type": "image/png",
                                         "url": core.user_avatar_url(who, 256),
                                         "proxy_url": core.user_avatar_url(who, 256)}]
                    m["content"] = "check this out" if mine else "look"
                elif r < 0.12:
                    m["reactions"] = [{"emoji": {"name": "👍", "id": None}, "count": 2,
                                       "me": rnd.random() < 0.6},
                                      {"emoji": {"name": "😂", "id": None}, "count": 1,
                                       "me": False}]
                elif r < 0.15 and not mine:
                    m["mentions"] = [ME]
                    m["content"] = "@You (demo) are you there?"
                elif r < 0.17:
                    m["pinned"] = True
                out.append(m)
            out.sort(key=lambda m: -int(m["id"]))
            self.messages[cid] = out

        # DMs
        for i, (u, g) in enumerate(_PEOPLE):
            cid = str(300000000000000000 + i)
            self.channels[cid] = {"id": cid, "type": 1, "recipients": [self.users[u]]}
            make_msgs(cid, [self.users[u]], rnd.randint(60, 180), 400)
            self.channels[cid]["last_message_id"] = self.messages[cid][0]["id"]
        # group DM
        cid = "300000000000000099"
        grp = [self.users["alex"], self.users["sam"], self.users["maya"]]
        self.channels[cid] = {"id": cid, "type": 3, "name": "Weekend plans", "recipients": grp}
        make_msgs(cid, grp, 90, 120)
        self.channels[cid]["last_message_id"] = self.messages[cid][0]["id"]
        # servers
        for gi, (gname, chans) in enumerate(_SERVERS):
            gid = str(400000000000000000 + gi)
            self.guilds.append({"id": gid, "name": gname, "icon": None})
            lst = []
            for ci, cname in enumerate(chans):
                cid = str(500000000000000000 + gi * 100 + ci)
                ch = {"id": cid, "type": 0, "name": cname, "guild_id": gid, "position": ci}
                self.channels[cid] = ch
                lst.append(ch)
                make_msgs(cid, list(self.users.values()), rnd.randint(80, 220), 500)
                if ci == 0:
                    tid = str(600000000000000000 + gi)
                    self.threads[cid] = [{"id": tid, "name": "Long discussion",
                                          "parent_id": cid, "thread_metadata": {}}]
                    self.channels[tid] = {"id": tid, "type": 11, "name": "Long discussion",
                                          "guild_id": gid}
                    make_msgs(tid, list(self.users.values()), 40, 60)
            self.guild_channels[gid] = lst

    # -------------------------------------------------------------- requests
    def request(self, method, path, body=None, files=None):
        with self.lock:
            return self._request(method, path, body, files)

    def _request(self, method, path, body=None, files=None):
        p, _, q = path.partition("?")
        params = dict(kv.split("=", 1) for kv in q.split("&") if "=" in kv)
        parts = p.strip("/").split("/")
        if p == "/users/@me":
            return 200, ME
        if p == "/users/@me/channels":
            return 200, [c for c in self.channels.values() if c["type"] in (1, 3)]
        if parts[0] == "channels" and parts[-1] == "typing":
            return 204, None
        if p == "/users/@me/guilds":
            return 200, self.guilds
        if len(parts) == 3 and parts[0] == "guilds" and parts[2] == "channels":
            return 200, self.guild_channels.get(parts[1], [])
        if len(parts) == 4 and parts[0] == "guilds" and parts[2:] == ["threads", "active"]:
            return 200, {"threads": []}
        if "threads" in parts and parts[0] == "channels":
            return 200, {"threads": self.threads.get(parts[1], []), "has_more": False}
        if parts[-2:] == ["messages", "search"]:
            return 200, self._search(parts, params)
        if parts[0] == "channels" and len(parts) == 2:
            ch = self.channels.get(parts[1])
            if method == "DELETE":       # close DM / leave group
                if ch and ch["type"] in (1, 3):
                    self.channels.pop(parts[1])
                    return 200, ch
                return 404, None
            return (200, ch) if ch else (404, None)
        if parts[0] == "channels" and len(parts) >= 3 and parts[2] == "messages":
            cid = parts[1]
            msgs = self.messages.get(cid)
            if msgs is None:
                return 404, None
            if len(parts) == 3 and method == "POST":
                m = {"id": str(core.date_to_snowflake(datetime.now()) + random.randint(0, 999)),
                     "channel_id": cid, "author": ME, "content": (body or {}).get("content", ""),
                     "timestamp": datetime.now().astimezone().isoformat(), "type": 0,
                     "attachments": [{"id": str(i), "filename": n, "size": len(b),
                                      "url": "", "proxy_url": ""}
                                     for i, (n, b) in enumerate(files or [])],
                     "embeds": [], "mentions": [], "reactions": []}
                ref = (body or {}).get("message_reference")
                if ref:
                    m["type"] = 19
                    m["message_reference"] = ref
                    m["referenced_message"] = next(
                        (x for x in msgs if x["id"] == ref.get("message_id")), None)
                msgs.insert(0, m)
                return 200, m
            if len(parts) == 3:
                return 200, self._page(msgs, params)
            mid = parts[3]
            target = next((x for x in msgs if x["id"] == mid), None)
            if len(parts) == 4 and method == "PATCH" and target:
                if target["author"]["id"] != ME["id"]:
                    return 403, None
                target["content"] = (body or {}).get("content", "")
                target["edited_timestamp"] = datetime.now().astimezone().isoformat()
                return 200, target
            if "reactions" in parts and parts[-1] == "@me" and target is not None:
                from urllib.parse import unquote
                raw = unquote(parts[5])
                name, _, eid = raw.partition(":")
                core.apply_reaction(target, {"id": eid or None, "name": name},
                                    method == "PUT")
                return 204, None
            if len(parts) == 4 and method == "DELETE":
                for i, m in enumerate(msgs):
                    if m["id"] == mid:
                        if m["author"]["id"] != ME["id"]:
                            return 403, None
                        msgs.pop(i)
                        return 204, None
                return 404, None
            if "reactions" in parts and method == "DELETE":
                for m in msgs:
                    if m["id"] == mid:
                        for r in m.get("reactions", []):
                            r["me"] = False
                return 204, None
        return 404, None

    def _page(self, msgs, params):
        limit = int(params.get("limit", 50))
        if "around" in params:
            ids = [m["id"] for m in msgs]
            try:
                i = ids.index(params["around"])
            except ValueError:
                return []
            lo = max(0, i - limit // 2)
            return msgs[lo:lo + limit]
        if "before" in params:
            b = int(params["before"])
            msgs = [m for m in msgs if int(m["id"]) < b]
        return msgs[:limit]

    def _search(self, parts, params):
        if parts[0] == "guilds":
            gid = parts[1]
            chans = [params["channel_id"]] if "channel_id" in params else [
                c["id"] for c in self.guild_channels.get(gid, [])]
        else:
            chans = [parts[1]]
        res = []
        for cid in chans:
            for m in self.messages.get(cid, []):
                if "author_id" in params and m["author"]["id"] != params["author_id"]:
                    continue
                if "content" in params:
                    from urllib.parse import unquote
                    if unquote(params["content"]).lower() not in (m["content"] or "").lower():
                        continue
                if "min_id" in params and int(m["id"]) <= int(params["min_id"]):
                    continue
                if "max_id" in params and int(m["id"]) >= int(params["max_id"]):
                    continue
                if params.get("has") == "image" and not m["attachments"]:
                    continue
                res.append(m)
        res.sort(key=lambda m: -int(m["id"]))
        off = int(params.get("offset", 0))
        return {"total_results": len(res),
                "messages": [[dict(m, hit=True)] for m in res[off:off + 25]]}
