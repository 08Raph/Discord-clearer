"""Read a Discord data package (Settings > Data & Privacy > Request Data).

The package lists EVERY chat you've sent messages in (also closed DMs and old
servers) together with the IDs of your messages, so they can be deleted directly
without scanning. Works with the .zip or the extracted folder, and with both the
newer (messages.json) and older (messages.csv) formats.
"""
import csv
import io
import json
import os
import re
import zipfile

_ENTRY = re.compile(r"(?i)(?:^|/)messages/(c?)(\d+)/(channel\.json|messages\.json|messages\.csv)$")
_INDEX = re.compile(r"(?i)(?:^|/)messages/index\.json$")

TYPE_NAMES = {0: "GUILD_TEXT", 1: "DM", 2: "GUILD_VOICE", 3: "GROUP_DM", 5: "GUILD_ANNOUNCEMENT",
              10: "ANNOUNCEMENT_THREAD", 11: "PUBLIC_THREAD", 12: "PRIVATE_THREAD",
              13: "GUILD_STAGE_VOICE", 15: "GUILD_FORUM"}


class _Source:
    """Uniform access to a zip file or an extracted folder."""

    def __init__(self, path):
        self.path = path
        if os.path.isdir(path):
            self.zip = None
            self.names = []
            for root, _dirs, files in os.walk(path):
                for f in files:
                    full = os.path.join(root, f)
                    self.names.append(os.path.relpath(full, path).replace(os.sep, "/"))
        else:
            self.zip = zipfile.ZipFile(path)
            self.names = self.zip.namelist()

    def read(self, name):
        if self.zip:
            return self.zip.read(name)
        with open(os.path.join(self.path, name), "rb") as f:
            return f.read()

    def close(self):
        if self.zip:
            self.zip.close()


def _text(data):
    return data.decode("utf-8-sig", errors="replace")


def _parse_messages(name, data):
    out = []
    if name.lower().endswith(".json"):
        rows = json.loads(_text(data)) or []
        for r in rows:
            mid = r.get("ID", r.get("id"))
            if mid is None:
                continue
            out.append({"id": str(mid), "timestamp": r.get("Timestamp") or r.get("timestamp") or "",
                        "content": r.get("Contents") or r.get("contents") or "",
                        "attachments": r.get("Attachments") or ""})
    else:
        reader = csv.DictReader(io.StringIO(_text(data)))
        for r in reader:
            mid = r.get("ID") or r.get("id")
            if not mid:
                continue
            out.append({"id": str(mid), "timestamp": r.get("Timestamp", ""),
                        "content": r.get("Contents", ""), "attachments": r.get("Attachments", "")})
    out.sort(key=lambda m: -int(m["id"]))
    return out


def _clean_index_name(name):
    if not name:
        return ""
    m = re.match(r"Direct Message with (.+?)(#0)?$", name)
    if m:
        return m.group(1)
    return name


def _type_name(t):
    if isinstance(t, int):
        return TYPE_NAMES.get(t, str(t))
    return str(t or "").upper()


def load_package(path, progress=None):
    """Return a list of chats:
    {id, name, kind: 'dm'|'group'|'channel', guild_id, guild_name, messages:[...]}
    sorted by number of messages (most first). Raises ValueError if nothing found."""
    src = _Source(path)
    try:
        index = {}
        found = {}
        for n in src.names:
            if _INDEX.search(n):
                try:
                    index = json.loads(_text(src.read(n))) or {}
                except ValueError:
                    index = {}
                continue
            m = _ENTRY.search(n)
            if m:
                found.setdefault(m.group(2), {})[m.group(3).lower()] = n

        if not found:
            raise ValueError("No messages found. Pick the Discord data package .zip "
                             "(or its extracted folder). It must contain a 'Messages' folder.")
        chats = []
        total = len(found)
        for i, (cid, files) in enumerate(found.items(), 1):
            if progress and (i % 25 == 0 or i == total):
                progress(i, total)
            info = {}
            if "channel.json" in files:
                try:
                    info = json.loads(_text(src.read(files["channel.json"]))) or {}
                except ValueError:
                    info = {}
            msg_file = files.get("messages.json") or files.get("messages.csv")
            if not msg_file:
                continue
            try:
                msgs = _parse_messages(msg_file, src.read(msg_file))
            except (ValueError, csv.Error, KeyError):
                continue
            if not msgs:
                continue
            t = _type_name(info.get("type"))
            guild = info.get("guild") or {}
            if t == "DM":
                kind = "dm"
            elif t == "GROUP_DM":
                kind = "group"
            else:
                kind = "channel"
            idx_name = _clean_index_name(index.get(cid) or index.get("c" + cid))
            if kind == "channel":
                ch_name = info.get("name") or (idx_name.split(" in ")[0] if idx_name else "")
                name = ("#" + ch_name) if ch_name else f"Channel {cid}"
            else:
                name = idx_name or info.get("name") or ("Group DM" if kind == "group"
                                                        else f"DM {cid}")
            for m in msgs:
                m["channel_id"] = cid
            chats.append({"id": cid, "name": name, "kind": kind,
                          "guild_id": str(guild.get("id")) if guild.get("id") else None,
                          "guild_name": guild.get("name") or (
                              idx_name.split(" in ", 1)[1] if kind == "channel"
                              and " in " in idx_name else ""),
                          "messages": msgs})
        if not chats:
            raise ValueError("The package was read but no messages were found in it.")
        chats.sort(key=lambda c: -len(c["messages"]))
        return chats
    finally:
        src.close()
