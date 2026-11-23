"""English / French / Spanish / Portuguese / German interface.

The app is written in English. When French is chosen, every text shown in the window
(labels, buttons, menus, dialogs, tooltips, status and log lines) goes through tr().
Chat content (names, messages, servers) is never translated: those labels are created
with notr=True.
"""
import json
import os
import re

LANGUAGES = {"en": "English", "fr": "Français", "es": "Español", "pt": "Português",
             "de": "Deutsch"}


def _saved_language():
    try:
        root = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
        with open(os.path.join(root, "DiscordMessageCleaner", "settings.json"),
                  encoding="utf-8") as f:
            lang = json.load(f).get("language")
        if lang in LANGUAGES:
            return lang
    except Exception:
        pass
    try:   # first start: follow Windows' language
        import locale
        loc = ((locale.getlocale()[0] or "") + " " + (os.environ.get("LANG") or "")).lower()
        for code, words in (("fr", ("fr", "french")), ("es", ("es_", "es-", "spanish")),
                            ("pt", ("pt_", "pt-", "portuguese")),
                            ("de", ("de_", "de-", "german"))):
            if loc.startswith(code) or any(w in loc for w in words):
                return code
    except Exception:
        pass
    return "en"


LANG = _saved_language()

# ------------------------------------------------------------------ exact texts
FR = {
    # login / accounts
    "Delete your own messages from DMs and servers.":
        "Supprimez vos propres messages des MP et des serveurs.",
    "Saved accounts": "Comptes enregistrés",
    "Or add another account": "Ou ajoutez un autre compte",
    "Your token": "Votre jeton",
    "Paste your token here": "Collez votre jeton ici",
    "Show token": "Afficher le jeton",
    "Where do I find my token?": "Où trouver mon jeton ?",
    "Find your token": "Trouver votre jeton",
    "Find my token": "Trouver mon jeton",
    "Remember me on this PC (saved encrypted with your Windows account)":
        "Se souvenir de moi sur ce PC (chiffré avec votre compte Windows)",
    "Connect": "Se connecter",
    "Connecting…": "Connexion…",
    "Signing in…": "Connexion…",
    "Your token stays on this PC and is only sent to discord.com.\n"
    "This app is not made by or affiliated with Discord.":
        "Votre jeton reste sur ce PC et n'est envoyé qu'à discord.com.\n"
        "Cette app n'est pas faite par Discord ni affiliée à Discord.",
    "Remove this saved account from this PC": "Retirer ce compte enregistré de ce PC",
    "That saved account couldn't be read. Paste your token again.":
        "Ce compte enregistré n'a pas pu être lu. Collez à nouveau votre jeton.",
    "Remove this account from this PC too?\n\nYes = log out and forget it\n"
    "No = log out but keep it saved (to switch accounts)":
        "Retirer aussi ce compte de ce PC ?\n\nOui = se déconnecter et l'oublier\n"
        "Non = se déconnecter mais le garder (pour changer de compte)",
    "Stop the cleaner first.": "Arrêtez d'abord le nettoyage.",
    # rail / sidebar
    "Direct Messages": "Messages privés",
    "Data package (every chat you ever used)":
        "Données Discord (toutes les discussions que vous avez utilisées)",
    "Refresh DMs and servers": "Actualiser les MP et les serveurs",
    "Settings, accounts, help": "Paramètres, comptes, aide",
    "Find a conversation": "Rechercher une conversation",
    "Direct messages": "Messages privés",
    "Group DMs": "Groupes privés",
    "Servers": "Serveurs",
    "Select all": "Tout sélectionner",
    "Added by link": "Ajoutés par lien",
    "Log out": "Se déconnecter",
    "Connected": "Connecté",
    "No open DMs.\nUse 'Add by link' on the right\nfor closed DMs.":
        "Aucun MP ouvert.\nUtilisez « Ajouter par lien » à droite\npour les MP fermés.",
    "Clean the whole server": "Nettoyer tout le serveur",
    "All your messages in every channel (fastest)":
        "Tous vos messages dans chaque salon (le plus rapide)",
    "Loading channels…": "Chargement des salons…",
    "No text channels you can see.": "Aucun salon textuel visible.",
    "Loading threads…": "Chargement des fils…",
    "No threads found.": "Aucun fil trouvé.",
    "Show threads / posts": "Afficher les fils / publications",
    "  (archived)": "  (archivé)",
    # data package
    "Data package": "Données Discord",
    "Find EVERY chat you've ever sent a message in, including closed DMs, using your "
    "Discord data package.":
        "Retrouvez TOUTES les discussions où vous avez écrit, même les MP fermés, grâce à "
        "vos données Discord.",
    "Import package (.zip)": "Importer les données (.zip)",
    "I already unzipped it (pick folder)": "Je l'ai déjà décompressé (choisir le dossier)",
    "How do I get my data package?": "Comment obtenir mes données ?",
    "Import another": "Importer un autre",
    "Search chats": "Rechercher",
    "Pick your Discord data package": "Choisissez vos données Discord",
    "Pick the extracted data package folder": "Choisissez le dossier décompressé",
    "Zip file": "Fichier zip",
    "All files": "Tous les fichiers",
    "Could not read that file.": "Impossible de lire ce fichier.",
    "Could not read the data package.": "Impossible de lire les données.",
    "Reading your data package…": "Lecture de vos données…",
    "From your data package": "Depuis vos données Discord",
    "These are your messages from your data package.":
        "Voici vos messages tirés de vos données Discord.",
    "Your Discord data package lists EVERY chat you've ever sent a message in, including "
    "closed DMs and servers you left, together with the IDs of your messages.\n\n"
    "HOW TO GET IT\n1. Discord > User Settings > Data & Privacy.\n"
    "2. Scroll down to 'Request all of my Data', tick Messages, and request it.\n"
    "3. Discord emails you a download link (this can take a few days).\n"
    "4. Download the .zip and import it here (no need to unzip).\n\n"
    "Messages in servers you left can't be deleted (Discord doesn't allow it). "
    "The app skips those chats automatically.":
        "Vos données Discord listent TOUTES les discussions où vous avez écrit, y compris "
        "les MP fermés et les serveurs quittés, avec les identifiants de vos messages.\n\n"
        "COMMENT LES OBTENIR\n1. Discord > Paramètres utilisateur > Données et "
        "confidentialité.\n2. Descendez jusqu'à « Demander toutes mes données », cochez "
        "Messages et faites la demande.\n3. Discord vous envoie un lien par courriel "
        "(cela peut prendre quelques jours).\n4. Téléchargez le .zip et importez-le ici "
        "(pas besoin de le décompresser).\n\nLes messages des serveurs quittés ne peuvent "
        "pas être supprimés (Discord ne le permet pas). L'app ignore ces discussions.",
    # chat preview
    "Preview": "Aperçu",
    "Chat ▾": "Discussion ▾",
    "Clean this chat": "Nettoyer cette discussion",
    "Will be cleaned": "Sera nettoyée",
    "Whole server ticked": "Tout le serveur est coché",
    "Pick a chat to preview it": "Choisissez une discussion pour l'afficher",
    "Ctrl+K  find a chat": "Ctrl+K  trouver une discussion",
    "Click a DM or channel on the left to preview it here.":
        "Cliquez sur un MP ou un salon à gauche pour l'afficher ici.",
    "Your messages that match the filters are highlighted in red.":
        "Vos messages qui correspondent aux filtres sont surlignés en rouge.",
    "Loading messages…": "Chargement des messages…",
    "Loading…": "Chargement…",
    "Load older messages": "Charger les messages plus anciens",
    "No messages here yet.": "Aucun message ici.",
    "This is the beginning of this chat.": "C'est le début de cette discussion.",
    "WILL BE DELETED": "SERA SUPPRIMÉ",
    "KEPT": "GARDÉ",
    "pinned": "épinglé",
    "  (edited)": "  (modifié)",
    "[system message]": "[message système]",
    "[embed]": "[intégration]",
    "You're viewing older messages   •   Jump to present":
        "Vous regardez des messages anciens   •   Revenir au présent",
    "None of your messages in this part of the chat. Load older messages to see more.":
        "Aucun de vos messages dans cette partie. Chargez des messages plus anciens.",
    "  you": "  vous",
    "Show only my messages": "Afficher seulement mes messages",
    "Jump to a date…": "Aller à une date…",
    "Jump to a date": "Aller à une date",
    "Jump to present": "Revenir au présent",
    "Statistics…": "Statistiques…",
    "Save whole conversation (offline, with pictures and files)":
        "Sauvegarder toute la conversation (hors ligne, avec images et fichiers)",
    "Quick export as web page (.html)": "Export rapide en page web (.html)",
    "Quick export as text (.txt)": "Export rapide en texte (.txt)",
    "Show messages from which day?\n(YYYY-MM-DD, e.g. 2025-06-15)":
        "Afficher les messages de quel jour ?\n(AAAA-MM-JJ, ex. 2025-06-15)",
    "Dates must look like 2025-06-15": "Les dates doivent ressembler à 2025-06-15",
    "Dates must look like 2026-11-21": "Les dates doivent ressembler à 2026-11-21",
    "Delete this message": "Supprimer ce message",
    "Keep (never delete this one)": "Garder (ne jamais supprimer celui-ci)",
    "Remove from keep list": "Retirer de la liste à garder",
    "Copy text": "Copier le texte",
    "Copy message ID": "Copier l'identifiant",
    "Delete message?": "Supprimer le message ?",
    "Wait for the cleaner to finish first.": "Attendez la fin du nettoyage.",
    "Save picture…": "Enregistrer l'image…",
    "Save picture": "Enregistrer l'image",
    "Open in browser": "Ouvrir dans le navigateur",
    "Close": "Fermer",
    "Picture": "Image",
    "Export chat": "Exporter la discussion",
    "Web page (looks like Discord)": "Page web (comme Discord)",
    "Text file": "Fichier texte",
    "Exporting…": "Export…",
    "Where should the conversation be saved?": "Où sauvegarder la conversation ?",
    "Where should the conversations be saved?": "Où sauvegarder les conversations ?",
    "Tick some DMs or channels first. (Whole servers are too big to save as one chat.)":
        "Cochez d'abord des MP ou des salons. (Un serveur entier est trop gros pour être "
        "sauvegardé d'un coup.)",
    "Search for servers, channels or DMs": "Rechercher des serveurs, salons ou MP",
    "Where would you like to go?": "Où voulez-vous aller ?",
    "↑ ↓ to choose   •   Enter to open   •   Esc to close":
        "↑ ↓ pour choisir   •   Entrée pour ouvrir   •   Échap pour fermer",
    "No matches.": "Aucun résultat.",
    "Direct message": "Message privé",
    "Server": "Serveur",
    # stats
    "Loading every message of this chat…": "Chargement de tous les messages…",
    "Messages": "Messages",
    "Yours": "Les vôtres",
    "Yours with files": "Vos messages avec fichiers",
    "Characters you typed": "Caractères écrits",
    "Messages per month (yours in blue)": "Messages par mois (les vôtres en bleu)",
    "Your most used words": "Vos mots les plus utilisés",
    "When you write (hour of day)": "Quand vous écrivez (heure)",
    "Not enough text.": "Pas assez de texte.",
    # cleaner panel
    "Cleaner": "Nettoyage",
    "Help": "Aide",
    "Selected (0)": "Sélection (0)",
    "Clear": "Vider",
    "Save chats": "Sauvegarder",
    "Nothing yet. Tick DMs, channels or a whole\nserver on the left.":
        "Rien pour l'instant. Cochez des MP, des salons\nou un serveur à gauche.",
    "Add by link (closed DMs)": "Ajouter par lien (MP fermés)",
    "Add": "Ajouter",
    "Add by link": "Ajouter par lien",
    "Paste a chat link like https://discord.com/channels/@me/123… or a Channel ID.":
        "Collez un lien comme https://discord.com/channels/@me/123… ou un identifiant "
        "de salon.",
    "Which messages": "Quels messages",
    "Keywords, e.g. hello, hi  (empty = all)": "Mots-clés, ex. salut, allo  (vide = tous)",
    "Match": "Recherche",
    "Whole word": "Mot entier",
    "Starts with": "Commence par",
    "Anywhere": "N'importe où",
    "Caps matter": "Respecter les majuscules",
    "Keep pinned messages": "Garder les épinglés",
    "From YYYY-MM-DD": "Du AAAA-MM-JJ",
    "To YYYY-MM-DD": "Au AAAA-MM-JJ",
    "Max per chat": "Max par discussion",
    "0 = all": "0 = tous",
    "More filters ▸": "Plus de filtres ▸",
    "More filters ▾": "Plus de filtres ▾",
    "With files": "Avec fichiers",
    "With pictures": "Avec images",
    "With links": "Avec liens",
    "Only replies": "Réponses seulement",
    "Length": "Longueur",
    "to": "à",
    "characters (0 = any)": "caractères (0 = tous)",
    "Older than": "Plus vieux que",
    "days (0 = any)": "jours (0 = tous)",
    "Options": "Options",
    "Delay": "Délai",
    "sec": "s",
    "Run": "Lancer",
    "chats at once": "discussions à la fois",
    "Preview only (delete nothing)": "Aperçu seulement (rien n'est supprimé)",
    "Save whole conversations before deleting":
        "Sauvegarder les conversations avant de supprimer",
    "Back up deleted messages": "Copie de sécurité des messages supprimés",
    "Auto speed": "Vitesse auto",
    "Use search (faster)": "Utiliser la recherche (plus rapide)",
    "Also remove my reactions": "Retirer aussi mes réactions",
    "Close DMs / leave group DMs when done": "Fermer les MP / quitter les groupes à la fin",
    "Auto-clean rules…": "Règles de nettoyage auto…",
    "Delete messages": "Supprimer les messages",
    "Pause": "Pause",
    "Resume": "Reprendre",
    "Stop": "Arrêter",
    "Ready.": "Prêt.",
    "Log": "Journal",
    "Save": "Enregistrer",
    "Backups": "Copies",
    "Slows down when Discord limits you, speeds up again after":
        "Ralentit quand Discord vous limite, puis réaccélère",
    "Find only your messages with Discord search instead of reading the whole chat":
        "Trouve seulement vos messages avec la recherche Discord au lieu de tout lire",
    "Takes your reactions off everyone's messages (reads the whole chat)":
        "Retire vos réactions des messages de tout le monde (lit toute la discussion)",
    "Saves everyone's messages + pictures/files to Documents\\Discord Cleaner "
    "Backups\\Conversations first":
        "Sauvegarde d'abord les messages de tous + images/fichiers dans "
        "Documents\\Discord Cleaner Backups\\Conversations",
    # confirmations / errors
    "Check your settings": "Vérifiez vos réglages",
    "Check your input": "Vérifiez vos informations",
    "Delete messages?": "Supprimer les messages ?",
    "Delay must be a number, like 1.5": "Le délai doit être un nombre, comme 1.5",
    "Max per chat must be a whole number (0 = all).":
        "Le max par discussion doit être un nombre entier (0 = tous).",
    "'Chats at once' must be 1 to 5.": "« Discussions à la fois » doit être de 1 à 5.",
    "The 'From' date is after the 'To' date.": "La date « Du » est après la date « Au ».",
    "The minimum length is bigger than the maximum length.":
        "La longueur minimale est plus grande que la maximale.",
    "Tick at least one DM, channel or server first.\n\n"
    "Use the boxes next to the names on the left.":
        "Cochez d'abord au moins un MP, salon ou serveur.\n\n"
        "Utilisez les cases à côté des noms à gauche.",
    "You can't change the selection while the cleaner is running.":
        "Impossible de changer la sélection pendant le nettoyage.",
    "The whole server is ticked. Untick it to pick single channels.":
        "Tout le serveur est coché. Décochez-le pour choisir des salons.",
    "Continue where you left off?": "Reprendre là où vous étiez ?",
    "Not finished. The app will offer to continue next time you open it.":
        "Pas terminé. L'app proposera de continuer à la prochaine ouverture.",
    "Paused. Press Resume to continue.": "En pause. Appuyez sur Reprendre pour continuer.",
    "Resumed.": "Repris.",
    "Stopping…": "Arrêt…",
    "Still running. Stop and quit?\n\nYou can continue where you left off next time you "
    "open the app.":
        "Le nettoyage tourne encore. Arrêter et quitter ?\n\nVous pourrez reprendre à la "
        "prochaine ouverture.",
    "Saving whole conversations before deleting…":
        "Sauvegarde des conversations avant suppression…",
    "Problem report copied.": "Rapport copié.",
    "Before you use this app:\n\n• It only deletes YOUR OWN messages. Deleted messages "
    "cannot be recovered.\n• Using scripts on a user account goes against Discord's Terms "
    "of Service. Your account could be limited or banned. You use this app at your own "
    "risk.\n• Your token stays on this PC. It is only sent to discord.com and is never "
    "saved.\n• Never give your token to anyone.\n\nDo you understand and want to continue?":
        "Avant d'utiliser cette app :\n\n• Elle supprime seulement VOS messages. Les "
        "messages supprimés ne peuvent pas être récupérés.\n• Utiliser des scripts sur un "
        "compte utilisateur va contre les conditions d'utilisation de Discord. Votre compte "
        "pourrait être limité ou banni. Vous utilisez cette app à vos risques.\n• Votre "
        "jeton reste sur ce PC. Il n'est envoyé qu'à discord.com et n'est jamais "
        "enregistré.\n• Ne donnez jamais votre jeton à personne.\n\nVous comprenez et "
        "voulez continuer ?",
    "1. Open discord.com/app in Chrome or Edge and log in.\n2. Press F12 and open the "
    "Network tab.\n3. Type 'api' in the filter box, then click on any chat.\n4. Click a "
    "request (e.g. 'messages') > Headers > Request Headers.\n5. Copy the value next to "
    "'authorization' and paste it here.\n\nIt's about 70 characters with two dots. Never "
    "share it with anyone.\nChanging your Discord password resets it.":
        "1. Ouvrez discord.com/app dans Chrome ou Edge et connectez-vous.\n2. Appuyez sur "
        "F12 et ouvrez l'onglet Réseau (Network).\n3. Tapez « api » dans le filtre, puis "
        "cliquez sur une discussion.\n4. Cliquez sur une requête (ex. « messages ») > "
        "En-têtes > En-têtes de requête.\n5. Copiez la valeur à côté de « authorization » "
        "et collez-la ici.\n\nElle fait environ 70 caractères avec deux points. Ne la "
        "partagez jamais.\nChanger votre mot de passe Discord la réinitialise.",
    # settings / help
    "Settings": "Paramètres",
    "My account": "Mon compte",
    "Switch account": "Changer de compte",
    "Sign in automatically when the app starts (saved accounts)":
        "Se connecter automatiquement au démarrage (comptes enregistrés)",
    "Appearance": "Apparence",
    "Language": "Langue",
    "Auto-clean": "Nettoyage auto",
    "Report a problem": "Signaler un problème",
    "Open log folder": "Ouvrir le dossier du journal",
    "Copy report": "Copier le rapport",
    "Show the tour again": "Revoir la visite guidée",
    "Try the demo (no account)": "Essayer la démo (sans compte)",
    "Copy this and send it to the developer, with what you were doing when it happened. "
    "Your token is never included.":
        "Copiez ceci et envoyez-le au développeur, avec ce que vous faisiez à ce moment-là. "
        "Votre jeton n'est jamais inclus.",
    "Restart the app now to use the new theme?":
        "Redémarrer l'app maintenant pour appliquer le thème ?",
    "Restart the app now to use the new language?":
        "Redémarrer l'app maintenant pour changer de langue ?",
    "The new theme will be used next time you open the app.":
        "Le nouveau thème sera utilisé à la prochaine ouverture.",
    "Dark": "Sombre",
    "Black (OLED)": "Noir (OLED)",
    "Light": "Clair",
    # rules
    "Auto-clean rules": "Règles de nettoyage auto",
    "Rules clean chats again and again on their own, for example: every day, delete my "
    "messages older than 30 days in these chats. They run while the app is open, and if "
    "you turn it on below, once a day even when it's closed.":
        "Les règles nettoient des discussions toutes seules, encore et encore. Par exemple : "
        "chaque jour, supprimer mes messages de plus de 30 jours dans ces discussions. Elles "
        "tournent quand l'app est ouverte et, si vous l'activez plus bas, une fois par jour "
        "même quand elle est fermée.",
    "No rules yet.": "Aucune règle.",
    "Run now": "Lancer",
    "Delete": "Supprimer",
    "New rule from what you've ticked": "Nouvelle règle avec ce que vous avez coché",
    "Tick some DMs, channels or servers first (data package chats can't be used).":
        "Cochez d'abord des MP, salons ou serveurs (les discussions des données Discord ne "
        "peuvent pas être utilisées).",
    "Rule name, e.g. Clean old DMs": "Nom de la règle, ex. Vieux MP",
    "Delete my messages older than": "Supprimer mes messages de plus de",
    "days": "jours",
    "Every hour": "Chaque heure",
    "Every day": "Chaque jour",
    "Every week": "Chaque semaine",
    "Uses your current keywords and filters from the cleaner panel.":
        "Utilise vos mots-clés et filtres actuels du panneau de nettoyage.",
    "Create rule": "Créer la règle",
    "When the app is closed": "Quand l'app est fermée",
    "Run due rules every day at 3:00 AM, even when the app is closed (Windows Task "
    "Scheduler)":
        "Lancer les règles chaque jour à 3 h, même quand l'app est fermée (Planificateur "
        "de tâches Windows)",
    "Tick some chats first.": "Cochez d'abord des discussions.",
    "This rule belongs to another account. Switch to that account to run it.":
        "Cette règle appartient à un autre compte. Changez de compte pour la lancer.",
    "Log in with 'Remember me' ticked first, so rules can sign in without you.":
        "Connectez-vous d'abord avec « Se souvenir de moi » coché, pour que les règles "
        "puissent se connecter sans vous.",
    "Auto-clean will also run every day at 3:00 AM.":
        "Le nettoyage auto tournera aussi chaque jour à 3 h.",
    # deleted messages logger
    "Deleted messages": "Messages supprimés",
    "Deleted messages (people's deleted DMs)": "Messages supprimés (MP effacés par les autres)",
    "Turn on": "Activer",
    "Turn off": "Désactiver",
    "On": "Activé",
    "Off": "Désactivé",
    "Starting…": "Démarrage…",
    "Start with Windows": "Démarrer avec Windows",
    "Also save pictures (uses more disk)": "Sauvegarder aussi les images (plus d'espace disque)",
    "Remember messages for": "Garder les messages",
    "Only DMs. It can only save messages that arrive while it's on, and keeps everything on "
    "this PC. Your own messages are skipped.":
        "MP seulement. Il ne peut sauvegarder que les messages reçus pendant qu'il est activé, "
        "et tout reste sur ce PC. Vos propres messages sont ignorés.",
    "Clear all": "Tout effacer",
    "Nothing yet.\nDeleted DM messages will show up here.":
        "Rien pour l'instant.\nLes messages supprimés dans vos MP apparaîtront ici.",
    "Remove from this list": "Retirer de cette liste",
    "DELETED": "SUPPRIMÉ",
    "before edit:": "avant modification :",
    "Messages people deleted after sending them to you.":
        "Messages que des gens ont supprimés après vous les avoir envoyés.",
    "The change applies the next time the logger starts.":
        "Le changement s'appliquera au prochain démarrage de l'enregistreur.",
    "The logger needs a real account (it's not available in the demo).":
        "L'enregistreur a besoin d'un vrai compte (pas disponible dans la démo).",
    "The logger only works on Windows.": "L'enregistreur fonctionne seulement sur Windows.",
    "To run in the background, the logger needs this account saved on this PC (encrypted, "
    "like 'Remember me').\n\nSave it now?":
        "Pour tourner en arrière-plan, l'enregistreur a besoin que ce compte soit enregistré "
        "sur ce PC (chiffré, comme « Se souvenir de moi »).\n\nL'enregistrer maintenant ?",
    "Remove all saved deleted messages from this PC?":
        "Effacer tous les messages supprimés sauvegardés sur ce PC ?",
    "no saved account (log in with Remember me)":
        "aucun compte enregistré (connectez-vous avec « Se souvenir de moi »)",
    "Your token is wrong or expired.": "Votre jeton est invalide ou expiré.",
    "Deleted-messages logger: stopping.": "Enregistreur de messages supprimés : arrêt.",
    "Deleted-messages logger: starting in the background.":
        "Enregistreur de messages supprimés : démarrage en arrière-plan.",
    # find in chat
    "Find in this chat": "Rechercher dans la discussion",
    "Find in this chat…   Ctrl+F": "Rechercher dans la discussion…   Ctrl+F",
    "Search the whole chat": "Rechercher dans toute la discussion",
    "No matches here. Try 'Search the whole chat'.":
        "Aucun résultat ici. Essayez « Rechercher dans toute la discussion ».",
    "Discord search isn't available in this chat.":
        "La recherche Discord n'est pas disponible dans cette discussion.",
    "The new language will be used next time you open the app.":
        "La nouvelle langue sera utilisée à la prochaine ouverture.",
    # tour
    "Your DMs and servers": "Vos MP et serveurs",
    "Click a server to see its channels. The top icon is your DMs, the green one is your "
    "Discord data package (every chat you ever used).":
        "Cliquez sur un serveur pour voir ses salons. L'icône du haut, ce sont vos MP; la "
        "verte, vos données Discord (toutes les discussions que vous avez utilisées).",
    "Tick what to clean": "Cochez quoi nettoyer",
    "Use the boxes next to the names. Click a name to read the chat in the middle. Tick "
    "'Clean the whole server' at the top of a server to clean all of it.":
        "Utilisez les cases à côté des noms. Cliquez sur un nom pour lire la discussion au "
        "milieu. Cochez « Nettoyer tout le serveur » en haut d'un serveur pour tout nettoyer.",
    "Preview the chat": "Aperçu de la discussion",
    "Your messages that would be deleted are red. Right-click a message to delete or keep "
    "just that one. The Chat menu has only-my-messages, jump to a date, statistics and "
    "saving. Ctrl+F searches, Ctrl+K jumps to any chat.":
        "Vos messages qui seraient supprimés sont en rouge. Clic droit sur un message pour "
        "supprimer ou garder seulement celui-là. Le menu Discussion offre : seulement mes "
        "messages, aller à une date, statistiques et sauvegarde. Ctrl+F recherche, Ctrl+K "
        "ouvre n'importe quelle discussion.",
    "Choose which messages": "Choisissez quels messages",
    "Leave it empty for all your messages, or type words like hello, hi. Pick Whole word, "
    "Starts with or Anywhere, and open More filters for files, links, dates and more.":
        "Laissez vide pour tous vos messages, ou tapez des mots comme salut, allo. Choisissez "
        "Mot entier, Commence par ou N'importe où, et ouvrez Plus de filtres pour les "
        "fichiers, liens, dates et plus.",
    "Preview first, then delete": "D'abord l'aperçu, ensuite la suppression",
    "Press Preview to see what would be deleted. When it looks right, untick 'Preview only' "
    "and press Delete messages. You can pause, stop and continue later.":
        "Appuyez sur Aperçu pour voir ce qui serait supprimé. Si tout est bon, décochez « Aperçu "
        "seulement » et appuyez sur Supprimer les messages. Vous pouvez mettre en pause, "
        "arrêter et reprendre plus tard.",
    # tour
    "Next": "Suivant",
    "Done": "Terminé",
    "Skip": "Passer",
    # demo
    "Demo mode: nothing is really deleted.": "Mode démo : rien n'est vraiment supprimé.",
    "Welcome to #": "Bienvenue dans #",
    "Message ": "Écrire à ",
    "   ·   preview only, right-click your messages to delete or keep them":
        "   ·   aperçu seulement, clic droit sur vos messages pour les supprimer ou garder",
}

# texts built with values: (regex, French template)
# ---- version 7 (chat, emojis, videos, tray, activity)
FR.update({
    "Activity": "Activité",
    "Catch ghost pings in servers": "Détecter les pings fantômes dans les serveurs",
    "Tell me when I lose a friend": "Me dire quand je perds un ami",
    "Check what changed while my PC was off": "Vérifier ce qui a changé pendant que mon PC était éteint",
    "Saves messages people delete in your DMs, and pings that get deleted in servers. "
    "Everything stays on this PC. Your own messages are skipped.":
        "Garde les messages que les gens suppriment dans vos MP, et les pings supprimés dans "
        "les serveurs. Tout reste sur ce PC. Vos propres messages sont ignorés.",
    "Saved messages 🔖": "Messages enregistrés 🔖",
    "Saved messages": "Messages enregistrés",
    "Keep it running when this PC is off…": "Le garder actif quand ce PC est éteint…",
    "Import from another device…": "Importer depuis un autre appareil…",
    "Nothing yet.\nDeleted messages will show up here.":
        "Rien pour l'instant.\nLes messages supprimés apparaîtront ici.",
    "Nothing yet.": "Rien pour l'instant.",
    "while your PC was off": "pendant que votre PC était éteint",
    "GHOST PING": "PING FANTÔME",
    "Keep running next to the clock when I close the window":
        "Rester actif près de l'horloge quand je ferme la fenêtre",
    "Show notifications (new DMs, deleted messages, ghost pings)":
        "Afficher les notifications (nouveaux MP, messages supprimés, pings fantômes)",
    "Let me chat, react and reply from the app":
        "Me laisser écrire, réagir et répondre depuis l'app",
    "Live updates (new messages appear by themselves)":
        "Mises à jour en direct (les nouveaux messages apparaissent tout seuls)",
    "Keep messages people delete visible (in red) in open chats":
        "Garder visibles (en rouge) les messages que les gens suppriment",
    "Sharp mode for scaled screens (125%, 150%…) - needs a restart":
        "Mode net pour écrans agrandis (125 %, 150 %…) - redémarrage requis",
    "App behaviour": "Comportement de l'app",
    "Videos open in your browser because OpenCV isn't installed (the build script adds it).":
        "Les vidéos s'ouvrent dans le navigateur car OpenCV n'est pas installé (le script "
        "de build l'ajoute).",
    "Messages you saved with 🔖. They stay on this PC even if the message gets deleted on "
    "Discord.": "Les messages enregistrés avec 🔖. Ils restent sur ce PC même si le message "
                "est supprimé sur Discord.",
    "Nothing saved yet. Hover a message and click 🔖.":
        "Rien d'enregistré. Survolez un message et cliquez sur 🔖.",
    "Removed from saved messages.": "Retiré des messages enregistrés.",
    "Saved. Find it in Saved messages (🔖 at the top).":
        "Enregistré. Retrouvez-le dans Messages enregistrés (🔖 en haut).",
    "Jump to message": "Aller au message",
    "Things Discord doesn't tell you: ghost pings (someone pinged you, then deleted it) and "
    "friends you lost. Needs the logger to be on.":
        "Ce que Discord ne vous dit pas : les pings fantômes (quelqu'un vous a mentionné puis "
        "l'a supprimé) et les amis perdus. Le journal doit être activé.",
    "When your PC is off": "Quand votre PC est éteint",
    "Keep it running when this PC is off": "Le garder actif quand ce PC est éteint",
    "Discord really erases deleted messages, so something has to be online when a message "
    "arrives to keep a copy. When this PC is off, nothing on it can do that.\n\n"
    "WHAT ALREADY WORKS\n"
    "When your PC turns back on, the logger checks your DMs: messages it had seen that got "
    "deleted or edited while the PC was off are found and saved (marked 'while your PC was "
    "off'). Friends you lost meanwhile are listed in Activity.\n\n"
    "TO CATCH EVERYTHING, 24/7\n"
    "Run the logger on a device that stays on: an old laptop, a Raspberry Pi, or an Android "
    "phone with Termux. Free, Python only:\n"
    "1. Copy the app's source folder to that device (it's on GitHub).\n"
    "2. Run server/install_linux.sh (Raspberry Pi, Linux) or server/install_termux.sh "
    "(Android). It asks for your token once and starts by itself after a reboot.\n"
    "3. Sync the file it writes to this PC (Syncthing is free) and use 'Auto-import a "
    "synced file'. The app then imports it by itself.\n\n"
    "Your token gives full access to your account: only put it on a device you own, never "
    "on a shared or public server.":
        "Discord efface vraiment les messages supprimés : il faut que quelque chose soit en "
        "ligne quand un message arrive pour en garder une copie. Quand ce PC est éteint, "
        "rien dessus ne peut le faire.\n\n"
        "CE QUI MARCHE DÉJÀ\n"
        "Quand votre PC se rallume, le journal vérifie vos MP : les messages déjà vus qui ont "
        "été supprimés ou modifiés pendant que le PC était éteint sont retrouvés et gardés "
        "(marqués « pendant que votre PC était éteint »). Les amis perdus entre-temps sont "
        "listés dans Activité.\n\n"
        "POUR TOUT ATTRAPER, 24 H/24\n"
        "Lancez le journal sur un appareil toujours allumé : un vieux portable, un Raspberry "
        "Pi ou un téléphone Android avec Termux. Gratuit, juste Python :\n"
        "1. Copiez le dossier source de l'app sur cet appareil (il est sur GitHub).\n"
        "2. Lancez server/install_linux.sh (Raspberry Pi, Linux) ou server/install_termux.sh "
        "(Android). Il demande votre token une fois et redémarre tout seul après un "
        "redémarrage.\n"
        "3. Synchronisez le fichier qu'il écrit vers ce PC (Syncthing est gratuit) et "
        "utilisez « Importer automatiquement un fichier synchronisé ». L'app l'importe "
        "ensuite toute seule.\n\n"
        "Votre token donne un accès complet à votre compte : ne le mettez que sur un appareil "
        "à vous, jamais sur un serveur partagé ou public.",
    "Upload a file": "Envoyer un fichier",
    "Upload files": "Envoyer des fichiers",
    "Add reaction": "Ajouter une réaction",
    "Reply": "Répondre",
    "Edit": "Modifier",
    "Save for later": "Enregistrer pour plus tard",
    "More": "Plus",
    "Replying to ": "Réponse à ",
    "Editing message  ·  Enter to save, Esc to cancel":
        "Modification  ·  Entrée pour enregistrer, Échap pour annuler",
    "Message ": "Envoyer un message à ",
    "preview only": "aperçu seulement",
    "chatting is turned off in Settings": "l'écriture est désactivée dans les Paramètres",
    " is typing…": " est en train d'écrire…",
    " are typing…": " sont en train d'écrire…",
    "sent an attachment": "a envoyé une pièce jointe",
    "reacted": "a réagi",
    "Find the perfect emoji": "Trouver l'emoji parfait",
    "Recent": "Récents",
    "This server": "Ce serveur",
    "Emojis": "Emojis",
    "Results": "Résultats",
    "Open": "Ouvrir",
    "Deleted messages": "Messages supprimés",
    "Quit": "Quitter",
    "Still running here. Right-click this icon to open or quit. You can change this in "
    "Settings.": "Toujours actif ici. Clic droit sur cette icône pour ouvrir ou quitter. "
                 "Modifiable dans les Paramètres.",
    "Deleted message saved": "Message supprimé enregistré",
    "Friend list": "Liste d'amis",
    "Ghost ping": "Ping fantôme",
    " (while your PC was off)": " (pendant que votre PC était éteint)",
    "Discord refused that reaction.": "Discord a refusé cette réaction.",
    "Can't play here - use Sound to open it": "Lecture impossible ici - utilisez Son pour l'ouvrir",
    "🔊 Sound": "🔊 Son",
    "Pick deleted_messages.db from the other device":
        "Choisissez deleted_messages.db de l'autre appareil",
    "Show threads / posts": "Afficher les fils / publications",
    "Click a DM or channel on the left to preview it here.":
        "Cliquez sur un MP ou un salon à gauche pour l'afficher ici.",
})

# ---- version 7.1
FR.update({
    "Show the original text of edited messages": "Afficher le texte d'origine des messages modifiés",
    "Muted for the logger": "Ignorés par le journal",
    "Ticked chats are not saved by the logger (noisy group chats, bots...). Changes apply "
    "right away.": "Les discussions cochées ne sont pas enregistrées par le journal (groupes "
                   "bruyants, bots...). S'applique tout de suite.",
    "Server (ghost pings)": "Serveur (pings fantômes)",
    "DM": "MP",
    "Search in deleted messages": "Recherche dans les messages supprimés",
    "Search deleted messages": "Chercher dans les messages supprimés",
    "There are no deleted messages to export yet.": "Il n'y a pas encore de messages supprimés à exporter.",
    "Where to save the export": "Où enregistrer l'export",
    "Pick the synced deleted_messages_export.db": "Choisissez le deleted_messages_export.db synchronisé",
    "Done. The app now imports this file by itself every time it changes.":
        "C'est fait. L'app importe maintenant ce fichier toute seule à chaque changement.",
    "Auto-import a synced file…": "Importer automatiquement un fichier synchronisé…",
    "Muted chats…": "Discussions ignorées…",
    "Export all deleted messages…": "Exporter tous les messages supprimés…",
    "Open a DM or channel first.": "Ouvrez d'abord un MP ou un salon.",
    "Pictures": "Images",
    "Videos": "Vidéos",
    "Files": "Fichiers",
    "Links": "Liens",
    "Nothing here.": "Rien ici.",
    "Discord search isn't available for this chat.": "La recherche Discord n'est pas disponible pour cette discussion.",
    "Media, files and links…": "Médias, fichiers et liens…",
    "Check my setup": "Vérifier mon installation",
    "Back up these chats on a schedule": "Sauvegarder ces discussions régulièrement",
    "Tick some DMs or channels first (whole servers can't be backed up as one chat).":
        "Cochez d'abord des MP ou des salons (un serveur entier ne peut pas être sauvegardé "
        "comme une seule discussion).",
    "(empty)": "(vide)",
    "Report copied.": "Rapport copié.",
})

PATTERNS = [
    (r"^SELECTED  \((\d+)\)$", r"SÉLECTION  (\1)"),
    (r"^Direct messages  \((\d+)\)$", r"Messages privés  (\1)"),
    (r"^Group DMs  \((\d+)\)$", r"Groupes privés  (\1)"),
    (r"^Servers  \((\d+)\)$", r"Serveurs  (\1)"),
    (r"^≈ ([\d,]+) of your messages$", r"≈ \1 de vos messages"),
    (r"^Activity \((\d+)\)$", r"Activité (\1)"),
    (r"^Deleted messages  \((\d+)\)$", r"Messages supprimés  (\1)"),
    (r"^You're no longer friends with (.+)$", r"Vous n'êtes plus ami avec \1"),
    (r"^(.+) pinged you in (.+) and deleted it$", r"\1 vous a mentionné dans \2 puis l'a supprimé"),
    (r"^(\d+) new in Deleted messages$", r"\1 nouveau(x) dans Messages supprimés"),
    (r"^Imported (\d+) deleted messages and (\d+) events\.$",
     r"\1 messages supprimés et \2 événements importés."),
    (r"^(.+) is bigger than 10 MB \(Discord's limit without Nitro\)\.$",
     r"\1 dépasse 10 Mo (limite de Discord sans Nitro)."),
    (r"^([\d,]+) of your messages$", r"\1 de vos messages"),
    (r"^Connected  •  ([\d,]+) cleaned$", r"Connecté  •  \1 nettoyés"),
    (r"^Loading (.+)…$", r"Chargement de \1…"),
    (r"^Statistics · (.+)$", r"Statistiques · \1"),
    (r"^Busiest day: (\w+)$", r"Jour le plus actif : \1"),
    (r"^Remove (.+) from this PC\?$", r"Retirer \1 de ce PC ?"),
    (r"^Delete the rule '(.+)'\?$", r"Supprimer la règle « \1 » ?"),
    (r"^Saved (\d+) of (\d+) conversation\(s\)\.(.*)$", r"\1 conversation(s) sur \2 sauvegardée(s).\3"),
    (r"^Saving (\d+) conversation\(s\)…$", r"Sauvegarde de \1 conversation(s)…"),
    (r"^([\d,]+) result\(s\)$", r"\1 résultat(s)"),
    (r"^Deleted in DMs  \((\d+)\)$", r"Supprimés dans les MP  (\1)"),
    (r"^On: watching (\d+) DMs$", r"Activé : surveille \1 MP"),
    (r"^([\d,]+) deleted messages saved$", r"\1 messages supprimés sauvegardés"),
    (r"^Search: (.+)$", r"Recherche : \1"),
    (r"^Backing up (\d+) chat\(s\)…$", r"Sauvegarde de \1 discussion(s)…"),
    (r"^Exported (\d+) deleted messages\.$", r"\1 messages supprimés exportés."),
    (r"^Load more \(([\d,]+) / ([\d,]+)\)$", r"Charger plus (\1 / \2)"),
    (r"^Backup done: (\d+) chat\(s\) saved$", r"Sauvegarde terminée : \1 discussion(s)"),
    (r"^Save a full copy of (\d+) chat\(s\) (.+)\?\n\n(.*)$",
     r"Sauvegarder une copie complète de \1 discussion(s) (\2) ?\n\n\3"),
]
_PATTERNS = [(re.compile(a, re.S | re.I), b) for a, b in PATTERNS]

# pieces of longer texts (status line, confirmations, log): longest first
FRAGMENTS = sorted({
    "Everyone's messages, pictures and files go to:\n":
        "Les messages de tout le monde, les images et les fichiers vont dans :\n",
    "\n\nThe 4 newest copies of each chat are kept.":
        "\n\nLes 4 copies les plus récentes de chaque discussion sont gardées.",
    "This will permanently delete ": "Cela va supprimer définitivement ",
    "ALL your messages": "TOUS vos messages",
    "your messages containing: ": "vos messages contenant : ",
    " in:\n\n": " dans :\n\n",
    "\nThis cannot be undone. Continue?": "\nC'est irréversible. Continuer ?",
    "\n\nThis cannot be undone.": "\n\nC'est irréversible.",
    "Delete this message?": "Supprimer ce message ?",
    "\nLimit: ": "\nLimite : ",
    " per chat.": " par discussion.",
    " message(s) in your keep list will be skipped.":
        " message(s) de votre liste à garder seront ignorés.",
    "\nThe whole conversations are saved first.":
        "\nLes conversations sont d'abord sauvegardées.",
    "\nYour reactions are removed too.": "\nVos réactions sont aussi retirées.",
    "\nCleaned DMs are closed and group DMs are left.":
        "\nLes MP nettoyés sont fermés et les groupes quittés.",
    "  (whole server)": "  (serveur entier)",
    "  · whole server": "  · serveur entier",
    "\n  … and ": "\n  … et ",
    " more": " de plus",
    "Your last cleanup didn't finish.\n\n": "Votre dernier nettoyage n'est pas terminé.\n\n",
    " messages were deleted, ": " messages ont été supprimés, ",
    " chats are left:\n\n": " discussions restent :\n\n",
    "\n\nContinue now?": "\n\nContinuer maintenant ?",
    "PAUSED  •  ": "EN PAUSE  •  ",
    "Found ": "Trouvés ",
    "Deleted ": "Supprimés ",
    "  •  Checked ": "  •  Vérifiés ",
    "  •  Chats ": "  •  Discussions ",
    "  •  Failed ": "  •  Échecs ",
    "  •  Reactions ": "  •  Réactions ",
    "s each": " s chacun",
    " shown  •  ": " affichés  •  ",
    " yours  •  ": " à vous  •  ",
    " match your filters": " correspondent aux filtres",
    "   ·   preview only, right-click your messages to delete or keep them":
        "   ·   aperçu seulement, clic droit sur vos messages pour les supprimer ou garder",
    "Saving ": "Sauvegarde de ",
    " conversation(s)…": " conversation(s)…",
    "Saved ": "Sauvegardé ",
    " conversation(s).": " conversation(s).",
    "\n\nOpen the folder?": "\n\nOuvrir le dossier ?",
    "Exported ": "Exporté ",
    " messages.\n\nOpen the file now?": " messages.\n\nOuvrir le fichier ?",
    " messages loaded": " messages chargés",
    ": loading ": " : chargement ",
    "Exporting… ": "Export… ",
    "Reading your data package… ": "Lecture de vos données… ",
    "Data package loaded: ": "Données chargées : ",
    " chats, ": " discussions, ",
    " messages.": " messages.",
    " chats  •  ": " discussions  •  ",
    " of your messages": " de vos messages",
    " message(s) in your keep list.": " message(s) dans votre liste à garder.",
    "Could not save: ": "Impossible d'enregistrer : ",
    "Could not restart: ": "Impossible de redémarrer : ",
    "Windows didn't accept the task: ": "Windows a refusé la tâche : ",
    "Windows didn't accept it: ": "Windows a refusé : ",
    "Could not start the logger: ": "Impossible de démarrer l'enregistreur : ",
    "Something went wrong, sorry!\n\n": "Désolé, un problème est survenu !\n\n",
    "\n\nThe app keeps working. Open the problem report so you can send it to the "
    "developer?":
        "\n\nL'app continue de fonctionner. Ouvrir le rapport pour l'envoyer au développeur ?",
    "Create a rule that deletes your messages older than ":
        "Créer une règle qui supprime vos messages de plus de ",
    " days in ": " jours dans ",
    " chat(s), ": " discussion(s), ",
    "every hour": "chaque heure", "every day": "chaque jour", "every week": "chaque semaine",
    "?\n\nIt deletes for real (no preview).": " ?\n\nElle supprime pour de vrai (pas d'aperçu).",
    "Chats: ": "Discussions : ",
    "  •  last run: ": "  •  dernier passage : ",
    " deleted": " supprimés",
    "older than ": "plus de ",
    " days": " jours",
    "keywords: ": "mots-clés : ",
    " chat(s)": " discussion(s)",
    "Exported": "Exporté",
    " - click to play in your browser": " - cliquez pour lire dans votre navigateur",
    "  •  MIT license  •  not affiliated with Discord": "  •  licence MIT  •  non affilié à Discord",
    "  •  last run: never": "  •  dernier passage : jamais",
    "Could not load: ": "Chargement impossible : ",
    " finds  ": " trouve  ",
    "   but not  ": "   mais pas  ",
    "   (anywhere in a word)": "   (n'importe où dans un mot)",
    "Saving whole conversations": "Sauvegarde des conversations",
}.items(), key=lambda kv: -len(kv[0]))

# log lines (after the "[1: chat] " prefix). Message previews are left as they are.
LOG = [(re.compile(a), b) for a, b in (
    (r"^Deleted #(\d+)", r"Supprimé n°\1"),
    (r"^Already gone", "Déjà supprimé"),
    (r"^Failed \(HTTP (\d+)\)", r"Échec (HTTP \1)"),
    (r"^\[preview\]", "[aperçu]"),
    (r"^Started: ", "Début : "),
    (r"^Done\. Checked ([\d,]+) messages, ([\d,]+) would be deleted",
     r"Terminé. \1 messages vérifiés, \2 seraient supprimés"),
    (r"^Done\. Checked ([\d,]+) messages, ([\d,]+) deleted",
     r"Terminé. \1 messages vérifiés, \2 supprimés"),
    (r"^Preview: nothing will be deleted\.", "Aperçu : rien ne sera supprimé."),
    (r"^Deleting messages\.\.\.", "Suppression des messages…"),
    (r"^Keywords: ", "Mots-clés : "),
    (r"^Limit: (\d+) messages", r"Limite : \1 messages"),
    (r"^Only messages: ", "Seulement les messages : "),
    (r"^Reached the limit of (\d+) messages\.", r"Limite de \1 messages atteinte."),
    (r"^Discord found about ([\d,]+) of your messages here\.",
     r"Discord a trouvé environ \1 de vos messages ici."),
    (r"^Discord asked us to slow down, waiting ([\d.]+)s\.\.\.",
     r"Discord demande de ralentir, attente de \1 s…"),
    (r"^Discord is indexing this (\w+), waiting (\d+)s\.\.\.",
     r"Discord indexe, attente de \2 s…"),
    (r"^Network problem: (.*)\. Retrying in 5s\.\.\.", r"Problème réseau : \1. Nouvel essai dans 5 s…"),
    (r"^Backup saved: ", "Copie enregistrée : "),
    (r"^Removed your reaction ", "Réaction retirée "),
    (r"^Stopped\.", "Arrêté."),
    (r"^Connected as (.+): (\d+) DMs and (\d+) servers\.",
     r"Connecté en tant que \1 : \2 MP et \3 serveurs."),
    (r"^Preview of (\d+) target\(s\), (\d+) at a time\.",
     r"Aperçu de \1 discussion(s), \2 à la fois."),
    (r"^Cleaning (\d+) target\(s\), (\d+) at a time\.",
     r"Nettoyage de \1 discussion(s), \2 à la fois."),
    (r"^Resuming (\d+) target\(s\), (\d+) at a time\.",
     r"Reprise de \1 discussion(s), \2 à la fois."),
    (r"^TOTAL: ([\d,]+) would be deleted", r"TOTAL : \1 seraient supprimés"),
    (r"^TOTAL: ([\d,]+) deleted", r"TOTAL : \1 supprimés"),
    (r"^(\d+)\. (.+): ([\d,]+) would be deleted", r"\1. \2 : \3 seraient supprimés"),
    (r"^(\d+)\. (.+): ([\d,]+) deleted", r"\1. \2 : \3 supprimés"),
    (r"^Step 1: ", "Étape 1 : "),
)]


def tr(text):
    """Translate interface text (English -> current language)."""
    if LANG == "en" or not isinstance(text, str) or not text.strip():
        return text
    try:
        if text in FR:
            return FR[text]
        up = _UPPER.get(text)
        if up:
            return up
        for rx, rep in _PATTERNS:
            if rx.match(text):
                out = rx.sub(rep, text)
                return out.upper() if text.isupper() else out
        out = text
        for en, fr in FRAGMENTS:
            if en in out:
                out = out.replace(en, fr)
        return out
    except Exception:
        return text


def tr_log(line):
    if LANG == "en":
        return line
    try:
        m = re.match(r"^(\[\d+: [^\]]*\] )?(.*)$", line, re.S)
        prefix, rest = m.group(1) or "", m.group(2)
        for rx, rep in LOG:
            if rx.match(rest):
                return prefix + rx.sub(rep, rest, count=1)
        return prefix + (FR.get(rest) or rest)
    except Exception:
        return line


_UPPER = {k.upper(): v.upper() for k, v in FR.items() if len(k) < 60}

MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
             "septembre", "octobre", "novembre", "décembre"]
DAYS_FR = {"Monday": "lundi", "Tuesday": "mardi", "Wednesday": "mercredi",
           "Thursday": "jeudi", "Friday": "vendredi", "Saturday": "samedi", "Sunday": "dimanche"}


_MONTHS, _DAYS, _DATE = MONTHS_FR, DAYS_FR, "{d} {m} {y}"


def long_date(d):
    if LANG != "en":
        return _DATE.format(d=d.day, m=_MONTHS[d.month - 1], y=d.year)
    return d.strftime("%B %d, %Y").replace(" 0", " ")


def day_name(name):
    return _DAYS.get(name, name) if LANG != "en" else name


# ------------------------------------------------------------------ hook into Tkinter
_installed = False


def install():
    """Make every Label/Button/Menu/dialog text go through tr(). Safe to call twice."""
    global _installed
    if _installed:
        return
    _installed = True
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog

    orig_init = tk.Label.__init__
    orig_conf = tk.Label.configure

    def label_init(self, master=None, cnf=None, **kw):
        notr = kw.pop("notr", False)
        if not notr and "text" in kw:
            kw["text"] = tr(kw["text"])
        orig_init(self, master, cnf or {}, **kw)
        self._notr = notr

    def label_conf(self, cnf=None, **kw):
        if "text" in kw and not getattr(self, "_notr", False):
            kw["text"] = tr(kw["text"])
        return orig_conf(self, cnf, **kw)

    tk.Label.__init__ = label_init
    tk.Label.configure = tk.Label.config = label_conf
    if LANG == "en":
        return    # English: only strip notr=, nothing to translate

    for name in ("add_command", "add_checkbutton"):
        orig = getattr(tk.Menu, name)

        def wrapped(self, cnf=None, _orig=orig, **kw):
            if "label" in kw:
                kw["label"] = tr(kw["label"])
            return _orig(self, cnf or {}, **kw)
        setattr(tk.Menu, name, wrapped)

    orig_title = tk.Wm.wm_title

    def title(self, string=None):
        return orig_title(self, tr(string) if string else string)
    tk.Wm.wm_title = tk.Wm.title = title

    def wrap_dialog(mod, name):
        orig = getattr(mod, name)

        def f(title=None, message=None, *a, **kw):
            if "filetypes" in kw:
                kw["filetypes"] = [(tr(d), p) for d, p in kw["filetypes"]]
            if "title" in kw:
                kw["title"] = tr(kw["title"])
            if "prompt" in kw:
                kw["prompt"] = tr(kw["prompt"])
            return orig(tr(title) if isinstance(title, str) else title,
                        tr(message) if isinstance(message, str) else message, *a, **kw)
        setattr(mod, name, f)

    for name in ("showinfo", "showerror", "showwarning", "askyesno", "askyesnocancel"):
        wrap_dialog(messagebox, name)
    wrap_dialog(simpledialog, "askstring")
    for name in ("asksaveasfilename", "askopenfilename", "askdirectory"):
        orig = getattr(filedialog, name)

        def fd(*a, _orig=orig, **kw):
            if "title" in kw:
                kw["title"] = tr(kw["title"])
            if "filetypes" in kw:
                kw["filetypes"] = [(tr(d), p) for d, p in kw["filetypes"]]
            return _orig(*a, **kw)
        setattr(filedialog, name, fd)


# ------------------------------------------------------------------ other languages
def _use_language(code):
    """Spanish / Portuguese / German come from lang_xx.py files (by position in
    i18n_keys). The log panel stays in English for those languages."""
    global FR, _UPPER, _PATTERNS, FRAGMENTS, LOG, _MONTHS, _DAYS, _DATE
    import importlib
    import i18n_keys as keys
    mod = importlib.import_module(f"lang_{code}")
    FR = {keys.KEYS[i]: t for i, t in enumerate(mod.T) if t and i < len(keys.KEYS)}
    _UPPER = {k.upper(): v.upper() for k, v in FR.items() if len(k) < 60}
    _PATTERNS = [(re.compile(keys.PATTERN_KEYS[i], re.S | re.I), r)
                 for i, r in enumerate(mod.P) if r and i < len(keys.PATTERN_KEYS)]
    FRAGMENTS = sorted(((keys.FRAGMENT_KEYS[i], t) for i, t in enumerate(mod.F)
                        if t and i < len(keys.FRAGMENT_KEYS)), key=lambda kv: -len(kv[0]))
    LOG = []
    _MONTHS, _DAYS, _DATE = mod.MONTHS, mod.DAYS, mod.DATE


if LANG in ("es", "pt", "de"):
    try:
        _use_language(LANG)
    except Exception:          # missing/broken language file: fall back to English
        LANG = "en"
