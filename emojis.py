"""Emoji helpers: find emojis in text, and a small searchable catalog for the picker.

Pictures come from Twemoji (the same emoji pictures Discord uses), so emojis look the
same as in Discord instead of the black-and-white Windows font.
"""
import re

_BASE = ("\U0001F000-\U0001FAFF☀-➿⌀-⏿⬀-⯿"
         "⤴⤵〰〽㊗㊙")
_TEXTY = "©®‼⁉™ℹ↔-↙↩↪"   # need U+FE0F
_MOD = "️\U0001F3FB-\U0001F3FF"
_ATOM = f"(?:[{_BASE}][{_MOD}]*|[{_TEXTY}]️)"
EMOJI_RE = re.compile(
    "(?:[\U0001F1E6-\U0001F1FF]{2}"                    # flags
    "|[0-9#*]️?⃣"                             # keycaps 1️⃣
    f"|{_ATOM}(?:‍{_ATOM})*[\U000E0020-\U000E007F]*)")
CUSTOM_RE = re.compile(r"<(a?):(\w+):(\d+)>")


def find(text):
    """[(start, end, chars)] of the unicode emojis in text."""
    return [(m.start(), m.end(), m.group()) for m in EMOJI_RE.finditer(text or "")]


def only_emojis(text, max_count=27):
    """True when a message is just emojis (Discord then shows them big)."""
    text = (text or "").strip()
    if not text:
        return False
    n = len(CUSTOM_RE.findall(text)) + len(EMOJI_RE.findall(CUSTOM_RE.sub("", text)))
    rest = EMOJI_RE.sub("", CUSTOM_RE.sub("", text)).strip()
    return 0 < n <= max_count and not rest


# name -> emoji. Searchable in the picker (English + a few French words).
CATALOG = [
    ("thumbsup like +1 pouce", "👍"), ("thumbsdown dislike -1", "👎"), ("heart love coeur", "❤️"),
    ("joy laugh lol mdr", "😂"), ("sob cry pleure", "😭"), ("skull dead mort", "💀"),
    ("fire feu lit", "🔥"), ("pray please thanks merci", "🙏"), ("eyes look", "👀"),
    ("rofl rolling laugh", "🤣"), ("smile happy content", "😊"), ("grin", "😁"),
    ("heart_eyes love", "😍"), ("thinking hmm", "🤔"), ("ok_hand ok parfait", "👌"),
    ("clap bravo", "👏"), ("100 hundred", "💯"), ("tada party fete", "🎉"),
    ("sparkles", "✨"), ("check yes oui done", "✅"), ("x no non cross", "❌"),
    ("wave hi hello bonjour salut", "👋"), ("muscle strong", "💪"), ("sunglasses cool", "😎"),
    ("wink", "😉"), ("blush", "😳"), ("smirk", "😏"), ("rolling_eyes eyeroll", "🙄"),
    ("angry mad fache", "😡"), ("rage", "🤬"), ("scream shock", "😱"),
    ("cold_sweat sweat", "😅"), ("upside_down", "🙃"), ("relieved", "😌"),
    ("sleeping sleep dodo", "😴"), ("yawn tired", "🥱"), ("nerd", "🤓"),
    ("clown", "🤡"), ("moai", "🗿"), ("pleading puppy", "🥺"), ("hugging hug calin", "🤗"),
    ("salute", "🫡"), ("melting", "🫠"), ("face_holding_back_tears", "🥹"),
    ("kiss bisou", "😘"), ("stuck_out_tongue tongue", "😛"), ("zany crazy", "🤪"),
    ("money_mouth money argent", "🤑"), ("shush shh", "🤫"), ("zipper_mouth", "🤐"),
    ("neutral", "😐"), ("expressionless", "😑"), ("unamused", "😒"), ("grimacing", "😬"),
    ("confused", "😕"), ("worried", "😟"), ("frowning sad triste", "☹️"),
    ("pensive", "😔"), ("disappointed", "😞"), ("weary", "😩"), ("tired_face", "😫"),
    ("exploding_head mind blown", "🤯"), ("partying party", "🥳"), ("star_struck wow", "🤩"),
    ("innocent angel", "😇"), ("smiling_imp devil", "😈"), ("ghost", "👻"), ("alien", "👽"),
    ("robot", "🤖"), ("poop", "💩"), ("cat chat", "🐱"), ("dog chien", "🐶"),
    ("goat goat", "🐐"), ("monkey see_no_evil", "🙈"), ("snake", "🐍"), ("butterfly", "🦋"),
    ("point_up", "☝️"), ("point_right", "👉"), ("point_left", "👈"), ("point_down", "👇"),
    ("raised_hands", "🙌"), ("handshake deal", "🤝"), ("fingers_crossed luck", "🤞"),
    ("v peace", "✌️"), ("metal rock", "🤘"), ("call_me", "🤙"), ("middle_finger", "🖕"),
    ("facepalm", "🤦"), ("shrug idk", "🤷"), ("person_bowing", "🙇"), ("brain", "🧠"),
    ("broken_heart", "💔"), ("blue_heart", "💙"), ("purple_heart", "💜"),
    ("green_heart", "💚"), ("yellow_heart", "💛"), ("orange_heart", "🧡"),
    ("black_heart", "🖤"), ("white_heart", "🤍"), ("sparkling_heart", "💖"),
    ("star etoile", "⭐"), ("zap lightning", "⚡"), ("boom", "💥"), ("rainbow", "🌈"),
    ("sun soleil", "☀️"), ("moon lune", "🌙"), ("snowflake neige", "❄️"),
    ("rocket fusee", "🚀"), ("gem diamond", "💎"), ("crown roi", "👑"), ("trophy", "🏆"),
    ("medal", "🥇"), ("video_game game jeu", "🎮"), ("headphones", "🎧"),
    ("musical_note music", "🎵"), ("camera photo", "📸"), ("computer pc", "💻"),
    ("phone", "📱"), ("bell", "🔔"), ("lock", "🔒"), ("key cle", "🔑"),
    ("bulb idea", "💡"), ("moneybag", "💰"), ("gift cadeau", "🎁"), ("balloon", "🎈"),
    ("pizza", "🍕"), ("hamburger burger", "🍔"), ("fries frites", "🍟"),
    ("popcorn", "🍿"), ("cake gateau", "🎂"), ("cookie", "🍪"), ("coffee cafe", "☕"),
    ("beer biere", "🍺"), ("wine vin", "🍷"), ("soccer foot", "⚽"),
    ("basketball", "🏀"), ("hockey", "🏒"), ("car voiture", "🚗"), ("airplane avion", "✈️"),
    ("house maison", "🏠"), ("canada maple", "🍁"), ("flag_ca canada", "🇨🇦"),
    ("flag_fr france", "🇫🇷"), ("flag_us usa", "🇺🇸"), ("warning", "⚠️"),
    ("question", "❓"), ("exclamation", "❗"), ("no_entry stop", "⛔"),
    ("white_check_mark", "✔️"), ("hourglass time", "⏳"), ("alarm_clock", "⏰"),
    ("speech_balloon chat", "💬"), ("zzz", "💤"), ("sweat_drops", "💦"),
    ("dash", "💨"), ("one 1", "1️⃣"), ("two 2", "2️⃣"), ("three 3", "3️⃣"),
]

QUICK = ["👍", "❤️", "😂", "😭", "💀", "🔥", "👀", "🙏"]


def search(query, limit=200):
    q = (query or "").strip().lower().strip(":")
    if not q:
        return [c for _, c in CATALOG][:limit]
    return [c for names, c in CATALOG if any(n.startswith(q) or q in n
                                             for n in names.split())][:limit]


def name_of(chars):
    for names, c in CATALOG:
        if c == chars:
            return names.split()[0]
    return chars
