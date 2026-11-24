# Discord Message Cleaner

A free Windows app that deletes **your own** Discord messages from DMs, group DMs and servers,
in a window that works like Discord.

> Not affiliated with or endorsed by Discord Inc. Using automation on a user account goes
> against Discord's Terms of Service and may get your account limited or banned.
> Use at your own risk. Deleted messages cannot be recovered.

**Website:** see `docs/` (GitHub Pages) · **Download:** the Releases page

## What's new in 7.7: Risk tab

This app uses your Discord account like a bot, which Discord's rules don't allow. A recent
real-world report: running the cleaner got an account a spam violation (limited access, kept on
the account's record for 2 years), even with Safe mode on. So everything that **writes** to your
account now starts **switched off**:

- **Risk tab** (✦ Everyday tools → Risk tab, or Settings): one box each for *Delete messages*,
  *Automatic clean-up rules*, *Privacy sweeper* and *Scheduled messages*. All unticked until you
  tick them (with a confirmation). "Turn off all risky features" switches them off again.
- **Before you start**: a one-time warning on first launch explaining the risk.
- **Always works**: Preview (deletes nothing), archive and search, Your year, reminders, saved
  replies and keyword alerts. They only read, or work on your PC.
- Deleting messages by hand, one at a time, in the app or in Discord, is not affected.
- Nothing in the app tries to hide from Discord's detection, and it can't promise to avoid it.

## What's new in 7.6: everyday tools

Click **✦** in the server bar (or the tray icon) for tools that make the app useful every day:

- **Archive and search**: keep a copy of your chats on this PC and search them offline (words,
  "exact phrases", a person, dates, only your messages). It only reads, slowly, and keeps itself
  up to date every 6 hours while the app is open. Backups made by the app can be imported.
- **Your year**: messages you sent, active days, best streak, busiest hour, by hour/month, who
  talks to you most, your words and emojis. Save it as a page to share.
- **Reminders**: right-click a message → Remind me about this (20 min, 1 h, tonight, tomorrow,
  or type "6pm", "tomorrow 9am", "45m").
- **Send later**: write a message, click 🕓. Sent at that time while the app is open (tray is fine).
  If the app was closed, it waits as *missed*: nothing is ever sent by surprise.
- **Saved replies**: type `;name` then Tab, or click 📝.
- **Keyword alerts**: notification + inbox when someone says one of your words (`/regex/` works).
- **Privacy sweeper**: leave servers, close old DMs, find friends you haven't talked to in months.
- **Safe mode** (on by default): rules delete one chat at a time, at least 2.5 s apart with random
  pauses and a daily limit (300); sweeper actions wait 2–14 random seconds with small daily limits.
  Using automation on a user account is against Discord's terms and no tool can make the risk
  zero; safe mode keeps it as low as it can.
- **Quick account switching** from your status menu, and **Start with Windows** (opens in the tray).

## What's new in 7.5
- **Calls, pins and people joining** show like in Discord ("Alex started a call that lasted 5
  minutes.", "You missed a call from Alex.") instead of "[system message]".
- **Customize**: 6 themes (Dark, Black, Light, Midnight, Forest, Grape), 8 accent colours, size of
  everything (90–150%), compact messages and a 24-hour clock.
- **Automatic releases**: when a new version reaches `main`, GitHub builds the .exe and publishes
  the release by itself.

## What's new in 7.4
- **Mute** any DM, channel or server, or get **only @mentions** (right-click it). Servers show an
  unread mark and turn red when you're mentioned. **Ctrl+Shift+M** mutes the open chat.
- **@mention suggestions** while you type, and a **GIF picker** (Discord's own Tenor search).
- **Search with filters** like Discord: `from:` `mentions:` `has:link/image/file/video` `before:`
  `after:` `during:` `pinned:true`.
- **Members** (👥) for server channels: the people active in the channel, with their status.
- **Undo** for 10 seconds after deleting one message.
- Opens your **last chat** on start. **Alt+↑ / Alt+↓** move between chats.
- Logger **dashboard** (deleted messages and ghost pings per day, who deletes the most) and
  **edit-history export**.

## What's new in 7.3
- **Use it as your everyday Discord.** The 🧹 button in the chat header (or Settings) hides every
  cleaning tool: the delete panel, checkboxes, red highlights and the Data package icon. The ⊘
  Deleted messages icon can be hidden separately.
- **Friends page** as the home screen: Online / All / Pending / Blocked, Add Friend, accept, ignore,
  remove, block and unblock. Friends show a green / yellow / red status dot.
- **Your status**: click your name at the bottom left for Online, Idle, Do Not Disturb, Invisible
  and a custom status.
- **Profile cards**: click a name or avatar for their About me, mutual servers and buttons to
  message, call, add or block.
- **Pinned messages** (📌) and **Edit my profile** (display name, About me, status).
- **Calls** open in the Discord app (or discord.com): Discord's encrypted voice can't run inside
  this app.

## What's new in 7.2
- Role mentions show the role's real name (for example @Moderators).
- Right-click a message → **Copy message link**.
- Unread messages are counted in the window title.
- Logger: **Keep deleted messages for N days** (0 = forever); the always-on logger applies it too.
- There's also a web version that runs in the browser: <https://github.com/08Raph/Discord-web-cleaner>.

## What's new in 7.1
- **See unedited messages**: the original text of an edited message shows under it, in
  yellow. Works in every chat you have open, and in DMs even when the app was closed
  (the logger keeps it)
- **Always-on logger in one command** for a Raspberry Pi / Linux PC or an Android phone
  (`server/`). It starts by itself after a reboot and writes a file every 10 minutes; the app
  imports it automatically (**Auto-import a synced file…**)
- **Search and export all deleted messages** (HTML, text and JSON)
- **Muted chats**: tell the logger to ignore noisy groups or bots
- **Scheduled backups**: Auto-clean rules → **Back up these chats on a schedule** (daily or
  weekly, keeps the 4 newest copies, works when the app is closed too)
- **Media gallery**: Chat ▾ → **Media, files and links…**
- **Check my setup**: Settings ⚙ → one-click diagnostics with a report you can copy
- **New languages**: Español, Português, Deutsch (5 in total)
- Website: tour with screenshots and a changelog page

## What's new in 7.0
- **Chat from the app**: send, reply, edit (or press ↑), upload files, paste screenshots
  (Ctrl+V), emoji picker. New messages, edits, reactions and "typing…" show up live, and
  unread DMs get a red badge
- **Emojis and reactions like Discord**: colour emoji pictures (the same Twemoji set Discord
  uses), custom and animated server emojis inside the text, big emojis, reaction pills you
  can click, see who reacted, add any reaction from the hover toolbar
- **GIFs and videos play**: Tenor/Giphy GIFs loop, videos play inline with a seek bar
  (🔊 Sound opens them in your video player), animated WebP too
- **Rich text**: **bold**, *italic*, __underline__, ~~strike~~, `code`, spoilers you click,
  headers, lists, clickable links, @mentions and #channels
- **Keeps running next to the clock** when you close the window (Settings ⚙ → App behaviour),
  with Windows notifications
- **Things Discord doesn't give you**: ghost-ping catcher, "no longer friends" alerts,
  🔖 saved messages that survive deletion, deleted messages stay visible in red in open chats
- **Offline catch-up**: when your PC turns back on, the logger finds messages that were
  deleted or edited while it was off (for messages it had already seen). To catch everything
  24/7, run the logger on an always-on device and import its file (see below)
- **Sharp icon** at every size (taskbar, title bar, Alt-Tab) and an optional sharp mode for
  scaled screens

## Features
**Easy to start**
- **Try the demo (no account)**: a pretend account with sample DMs, servers, threads,
  pictures and reactions. Nothing real is touched, so it's also perfect for recording a video
- **First-time tour**: 5 short tips that show where everything is (Settings ⚙ → Show the tour
  again)
- **English, French, Spanish, Portuguese and German** (Settings ⚙ → Language; picked
  automatically from Windows)

**Looks and works like Discord**
- Dark title bar, server bar with rounded icons, DMs with profile pictures, channels by
  category, threads and forum posts, your account at the bottom
- **Themes**: Dark, Black (OLED) and Light (Settings ⚙)
- **Ctrl+K quick switcher**, smooth scrolling, **hold the mouse wheel** to auto-scroll
- **Ctrl+F: find words in a chat**, jump between matches, or **search the whole chat** with
  Discord search and jump straight to any old message

**Conversation preview**
- Messages like in Discord: date dividers, mentions, code blocks, quotes, link cards, reactions
- **Pictures, animated GIFs, video thumbnails, stickers and big emojis**. Click a picture to
  open it big and save it
- Messages that would be deleted are **highlighted in red**, live as you change the filters
- **Only my messages**, **Jump to a date**, **Statistics** (messages per month, your most used
  words, when you write) in the **Chat ▾** menu
- **Right-click a message** to delete just that one, **keep** it, or copy it

**Cleaning**
- Tick DMs, channels, **threads**, or **whole servers**
- **Data package import** finds every chat you've ever used, including closed DMs
- **Keywords** with 3 match modes: **Whole word**, **Starts with** (`hello` → hellos),
  **Anywhere**, plus **caps matter**
- **More filters**: with files, with pictures, with links, only replies, message length,
  **older than N days**, date range, keep pinned, max per chat
- **Also remove my reactions** from everyone's messages
- **Close DMs / leave group DMs** when they're cleaned
- Discord search for speed, **Auto speed**, 1–5 chats at once, **Pause / Resume**,
  **continue after closing the app**
- **Auto-clean rules**: e.g. every day, delete my messages older than 30 days in these chats.
  They run while the app is open and, if you want, every day at 3 AM even when it's closed
  (Windows Task Scheduler)

**Deleted messages logger**
- Turn it on in the red ⊘ section: it runs in the background (no window) and saves messages
  people delete in your DMs and group DMs, so you can still read them. Edits keep the
  original text too
- Only messages that arrive while it's on can be saved (Discord doesn't keep deleted
  messages). Your own messages and servers are ignored. Everything stays on your PC
- Very light: one connection that sleeps until Discord sends something (a heartbeat every
  ~41 s), no window, no polling. Pictures are only downloaded if you turn that on
- Optional **Start with Windows**; keeps recent messages for 7 days by default
- Also catches **ghost pings** in servers (only messages that @mention you are kept) and
  tells you when you lose a friend (Activity)

### Running the logger on an always-on device (optional)
Discord erases deleted messages, so something must be online when a message arrives. To
cover the hours your PC is off, run the logger on a Raspberry Pi / Linux machine
(`bash server/install_linux.sh`) or an Android phone with Termux
(`bash server/install_termux.sh`). See `server/README.md`. Then sync its export file to
your PC (Syncthing is free) and pick it once with **Auto-import a synced file…** in the
⊘ section. Only do this on a device you own: your token gives full access to your account.

**Saving**
- **Save whole conversations** (everyone's messages + pictures + files, works offline),
  for one chat, all ticked chats, or automatically before deleting
- Quick export to HTML or TXT, JSON backup of everything deleted

**Accounts and safety**
- **Several saved accounts** (Remember me), switch in one click
- Tokens are encrypted with your Windows account and never written to the log
- **Log file** and **Report a problem** (Settings ⚙) so users can send you what went wrong
- Counts how many messages you've cleaned in total; flashes the taskbar when a run ends

## Install
Run `DiscordMessageCleaner-Setup-7.7.0.exe` and follow the wizard (no admin rights needed),
or unzip `DiscordMessageCleaner_v7.7.0_windows.zip` and run the .exe.
It adds a Start menu shortcut, an optional desktop icon, and an uninstaller.

## How to use
1. Paste your token and press **Connect**. Tick **Remember me** to skip this next time.
   Get your token in your browser: discord.com/app → F12 → Network → filter `api` →
   click a chat → click a request → Headers → Request Headers → copy the value next to
   `authorization`. Never share it. Changing your password resets it.
2. Click DMs and channels to preview them, and tick the ones you want to clean.
   For closed DMs and old chats, open **Data package** (green icon) and import your package.
3. Set your filters (the preview shows what matches in red) and press **Preview**.
4. If it looks right, untick **Preview only** and press **Delete messages**.

### Getting your data package
Discord → User Settings → Data & Privacy → **Request all of my Data** (tick Messages).
Discord emails you a download link, sometimes after a few days. Import the .zip as it is.
Messages in servers you've left can't be deleted. The app skips those chats.

## Publish on GitHub (website + automatic .exe builds)
1. Create a **public** repository (e.g. `DiscordMessageCleaner`) and upload everything in
   this folder (drag and drop on github.com works, including the hidden `.github` folder:
   use **Add file → Upload files** and drag the whole folder content).
2. **Website**: Settings → Pages → Source: *Deploy from a branch* → Branch `main`, folder
   `/docs` → Save. After a minute it's live at `https://YOUR-NAME.github.io/REPO/`.
   The download buttons find your latest release by themselves.
3. **The .exe**: push to `main` with a new VERSION in app.py (or publish a release with tag `v7.7.0`). GitHub builds
   the single .exe zip and the setup wizard on a Windows machine (Actions tab, ~5 min) and
   attaches them to the release. Free for public repos. Next version: change `VERSION` in
   `app.py` (+ `version_info.txt`, `installer.iss`) and publish a new tag.

## Build it yourself
Install Python 3.10+ from python.org (tick "Add python.exe to PATH"). The scripts install
everything from `requirements.txt` (Pillow, OpenCV for videos, pystray for the tray icon).
- `build_exe.bat` builds the app into `dist\DiscordMessageCleaner\`
- `build_installer.bat` builds the app and the setup wizard into `installer_output\`
  (needs the free [Inno Setup 6](https://jrsoftware.org/isdl.php))
- `build_single_exe.bat` builds ONE .exe file into `dist_single\` that you can move anywhere
  (easiest to share, but gets more antivirus false alarms)

> With `build_exe.bat`, keep `DiscordMessageCleaner.exe` together with its `_internal` folder.
> Moving the .exe alone gives "Failed to start embedded python interpreter".

The app is built as a folder rather than a single .exe because single-file PyInstaller apps
get far more antivirus false alarms. Publishing the source code (e.g. on GitHub) next to the
installer lets people check that the token only goes to discord.com.

## Recording a how-to video
Use the demo so no real account or token appears on screen:
1. Start the app and press **Try the demo (no account)**.
2. Record with **Win + Alt + R** (Xbox Game Bar) or the Snipping Tool's video mode
   (**Win + Shift + S** → record), or [OBS](https://obsproject.com) for more control.
3. Suggested 60-second plan:
   - 0-10 s: the Discord-style window, click a server, open a thread (⋯)
   - 10-25 s: open a DM, scroll, type `hello` in Keywords, show the red highlights, switch
     between Whole word / Starts with
   - 25-40 s: tick 2 DMs, press **Preview**, then untick Preview only and **Delete messages**
   - 40-50 s: **Chat ▾ → Statistics**, then **Ctrl+F**
   - 50-60 s: Settings ⚙ → themes and language
4. For a GIF, convert the video with [ScreenToGif](https://www.screentogif.com) (free).

## Privacy
- Your token is only sent to discord.com. Pictures load from cdn.discordapp.com without it.
- "Remember me" stores the token with Windows DPAPI: it can't be read on another PC or by
  another Windows user. Other programs running as you could still decrypt it, so only use it
  on your own PC. **Log out** deletes it.
- Emoji pictures load from cdn.jsdelivr.net (Twemoji), without your token.
- Settings, saved accounts, keep list, rules, logs, saved deleted messages, bookmarks and resume info are in
  `%APPDATA%\DiscordMessageCleaner`. Picture and video cache: `%LOCALAPPDATA%\DiscordMessageCleaner`.
  The uninstaller offers to remove them.

## Files
| File | What it is |
|---|---|
| `app.py` | The window |
| `widgets.py` | Discord-style widgets (avatars, checkboxes, scrolling lists) |
| `cleaner_core.py` | Filters, Discord requests, search, export (no GUI code) |
| `package.py` | Reads the Discord data package |
| `i18n.py`, `i18n_keys.py`, `lang_es.py`, `lang_pt.py`, `lang_de.py` | Interface languages |
| `demo.py` | Sample account for the demo mode |
| `securestore.py` | Saved accounts, encrypted with Windows DPAPI |
| `main.py` | Starts the app, or a background mode without loading the window |
| `rules.py` | Auto-clean rules and the `--run-rules` mode for Task Scheduler |
| `gateway.py` | Small real-time Discord connection (standard library only) |
| `logger_service.py`, `msglog.py` | Deleted-messages logger (`--logger`) and its local database |
| `applog.py` | Log file and crash reports (tokens are masked) |
| `build_exe.bat`, `version_info.txt` | Builds the app with PyInstaller (folder) |
| `build_single_exe.bat` | Builds a single portable .exe |
| `build_installer.bat`, `installer.iss`, `installer_info.txt` | Builds the setup wizard |
| `richtext.py`, `emojis.py` | Discord-style message text, emoji pictures and the emoji picker list |
| `media.py` | Video / GIF player (OpenCV) |
| `tray.py` | Icon next to the clock (pystray) |
| `social.py` | Friends, status, profiles, pins, mutes, mentions, GIFs, customize |
| `everyday.py` | Everyday tools window: archive, recap, reminders, send later, snippets, alerts, sweeper |
| `archive.py` | Local searchable archive (SQLite full-text search) and "Your year" |
| `planner.py` | Reminders, scheduled messages, saved replies, keyword alerts (JSON files) |
| `safety.py` | Safe mode: random pauses and daily limits for automatic actions |
| `tools/make_icon.py` | Draws the icons at every size (sharp everywhere) |
| `docs/` | The website (GitHub Pages): `index.html`, `changelog.html`, screenshots |
| `server/` | Always-on logger setup for Raspberry Pi / Linux and Android |
| `.github/workflows/build.yml` | Builds the .exe + setup on GitHub when you publish a release |
| `requirements.txt` | Python packages the app uses |
| `icon.ico`, `icon*.png` | App icons |

## License
MIT. See `LICENSE`.
