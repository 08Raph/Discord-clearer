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
    "Copy message link": "Copier le lien du message",
    "Message link copied.": "Lien du message copié.",
    "Keep deleted messages for": "Garder les messages supprimés pendant",
    "days (0 = forever)": "jours (0 = toujours)",
    "Online": "En ligne",
    "Idle": "Inactif",
    "Do Not Disturb": "Ne pas déranger",
    "Invisible": "Invisible",
    "Offline": "Hors ligne",
    "Set a custom status…": "Définir un statut personnalisé…",
    "Set a custom status": "Définir un statut personnalisé",
    "Edit my profile…": "Modifier mon profil…",
    "Edit my profile": "Modifier mon profil",
    "My profile card": "Ma carte de profil",
    "Custom status": "Statut personnalisé",
    "What's happening?": "Quoi de neuf ?",
    "Friends": "Amis",
    "Friend request": "Demande d'ami",
    "All": "Tous",
    "Pending": "En attente",
    "Blocked": "Bloqués",
    "Add Friend": "Ajouter un ami",
    "You can add friends with their Discord username.": "Vous pouvez ajouter des amis avec leur nom d'utilisateur Discord.",
    "Enter a username": "Entrez un nom d'utilisateur",
    "Send Friend Request": "Envoyer la demande",
    "Friend request sent to ": "Demande d'ami envoyée à ",
    "No one's around.": "Personne pour l'instant.",
    "Incoming friend request": "Demande d'ami reçue",
    "Outgoing friend request": "Demande d'ami envoyée",
    "Remove friend": "Retirer l'ami",
    "Remove ": "Retirer ",
    " from your friends?": " de vos amis ?",
    "Call": "Appeler",
    "Message": "Message",
    "Ignore": "Ignorer",
    "Accept": "Accepter",
    "Cancel": "Annuler",
    "Unblock": "Débloquer",
    "Block": "Bloquer",
    "Calls happen in Discord: opening it now.": "Les appels se font dans Discord : ouverture…",
    "Pinned messages": "Messages épinglés",
    "📌  Pinned messages": "📌  Messages épinglés",
    "This chat doesn't have any pinned messages yet.": "Ce chat n'a encore aucun message épinglé.",
    "About me": "À propos de moi",
    "Mutual servers": "Serveurs en commun",
    "💬  Message": "💬  Message",
    "📞  Call": "📞  Appeler",
    "Display name": "Nom d'affichage",
    "Status": "Statut",
    "Open Discord's full settings ↗": "Ouvrir tous les paramètres de Discord ↗",
    "Discord asked for a captcha. Do this one in the Discord app.": "Discord demande un captcha. Faites-le dans l'app Discord.",
    "Show or hide the cleaning tools": "Afficher ou masquer les outils de nettoyage",
    "Start a call (opens Discord)": "Lancer un appel (ouvre Discord)",
    "Set your status": "Définir votre statut",
    "Edit my profile (display name, About me, status)…": "Modifier mon profil (nom, à propos, statut)…",
    "Show the cleaning tools (delete panel, checkboxes, red highlights)": "Afficher les outils de nettoyage (panneau, cases, surlignage rouge)",
    "Show Deleted messages (⊘) in the server bar": "Afficher Messages supprimés (⊘) dans la barre",    "Mute": "Mettre en sourdine",
    "Only @mentions": "Seulement les @mentions",
    "All messages": "Tous les messages",
    "Mark as read": "Marquer comme lu",
    "Unmuted ": "Son réactivé : ",
    "Muted ": "En sourdine : ",
    "Send a GIF": "Envoyer un GIF",
    "Search GIFs": "Chercher des GIF",
    "Powered by Tenor, through Discord.": "Fourni par Tenor, via Discord.",
    "Nothing found.": "Rien trouvé.",
    "GIF search needs a real account (demo mode).": "La recherche de GIF demande un vrai compte (mode démo).",
    "Members": "Membres",
    "Active in this channel": "Actifs dans ce salon",
    "Message deleted": "Message supprimé",
    "Undo": "Annuler",
    "No edited messages saved yet.": "Aucun message modifié enregistré pour l'instant.",
    " edited messages.": " messages modifiés.",
    "Dashboard": "Tableau de bord",
    "📊  Dashboard": "📊  Tableau de bord",
    "📊 Dashboard": "📊 Tableau de bord",
    "deleted messages (30 days)": "messages supprimés (30 jours)",
    "ghost pings (30 days)": "pings fantômes (30 jours)",
    "saved in total": "enregistrés au total",
    "edited messages": "messages modifiés",
    "Per day: deleted (blue) and ghost pings (grey)": "Par jour : supprimés (bleu) et pings fantômes (gris)",
    "Who deletes the most": "Qui supprime le plus",
    "Export edit history…": "Exporter l'historique des modifications…",
    "Open the last chat when the app starts": "Ouvrir le dernier chat au démarrage",
    "Give me 10 seconds to undo when I delete one message": "Me laisser 10 secondes pour annuler quand je supprime un message",
    "Accent colour": "Couleur d'accent",
    "Size of everything": "Taille de l'interface",
    "Compact messages (less space between people)": "Messages compacts (moins d'espace entre les personnes)",
    "24-hour clock (20:15 instead of 8:15 PM)": "Horloge 24 h (20:15 au lieu de 8:15 PM)",
    "Restart the app now to use the new look?": "Redémarrer l'app maintenant pour appliquer le nouveau style ?",
    "Midnight": "Minuit",
    "Forest": "Forêt",
    "Grape": "Raisin",
})

FR.update({
    'A scheduled message was not sent': "Un message programmé n'a pas été envoyé",
    'Add another account…': 'Ajouter un autre compte…',
    'Add chats': 'Ajouter des chats',
    'Add chats and the app keeps a copy on this PC that you can search, even offline or after messages are deleted.': "Ajoute des chats et l'app en garde une copie sur ce PC que tu peux fouiller, même hors ligne ou après la suppression des messages.",
    'Add chats to the archive': "Ajouter des chats à l'archive",
    'Added to the archive. It keeps loading in the background.': "Ajouté à l'archive. Le chargement continue en arrière-plan.",
    'Alerts on': 'Alertes activées',
    'All time': 'Depuis toujours',
    "Also good to know: do big clean-ups in small pieces over several days, don't run the app on many accounts from one PC at the same time, and if Discord asks for a captcha, stop and do that action in Discord.": "Bon à savoir : fais les gros nettoyages en petits morceaux sur plusieurs jours, n'utilise pas l'app sur plein de comptes depuis le même PC en même temps, et si Discord demande un captcha, arrête et fais cette action dans Discord.",
    'Any time': "N'importe quand",
    'Archive': 'Archive',
    'Archive and search': 'Archive et recherche',
    'Archive this chat': 'Archiver ce chat',
    'Archive up to date ({n} new messages).': 'Archive à jour ({n} nouveaux messages).',
    'Archive: {name}, {n} new…': 'Archive : {name}, {n} nouveaux…',
    'Around it': 'Autour',
    'Automatic deletes': 'Suppressions automatiques',
    'Best streak (days in a row)': "Meilleure série (jours d'affilée)",
    'Busiest chats': 'Chats les plus actifs',
    'Busiest hour': 'Heure la plus active',
    'By hour': 'Par heure',
    'By month': 'Par mois',
    'Call Alex back': 'Rappeler Alex',
    'Change time': "Changer l'heure",
    'Chats in the archive': "Chats dans l'archive",
    'Clear finished reminders': 'Effacer les rappels terminés',
    'Close old DMs': 'Fermer les vieux MP',
    'Close selected DMs': 'Fermer les MP choisis',
    'Close {n} DM(s)? Messages are not deleted; group DMs are left.': 'Fermer {n} MP ? Les messages ne sont pas supprimés ; tu quittes les groupes.',
    'Closing the window keeps it running in the tray': 'Fermer la fenêtre la garde ouverte dans la zone de notification',
    'Could not import that backup: {e}': "Impossible d'importer cette sauvegarde : {e}",
    'DMs closed': 'MP fermés',
    'Days you talked': 'Jours où tu as parlé',
    'Discord messages can be 2000 characters max.': 'Les messages Discord font 2000 caractères max.',
    'Everyday tools': 'Outils du quotidien',
    'Everyday tools (archive, reminders, send later, alerts, safe mode)…': 'Outils du quotidien (archive, rappels, envoi plus tard, alertes, mode sûr)…',
    'Everyday tools: archive, reminders, send later, alerts…': 'Outils du quotidien : archive, rappels, envoi plus tard, alertes…',
    'Failed': 'Échec',
    'Find': 'Chercher',
    'Friends removed': 'Amis retirés',
    'Get a notification when someone says one of these words in your DMs or servers, while the app is open. Only reads messages Discord already sends to the app.': "Reçois une notification quand quelqu'un dit un de ces mots dans tes MP ou serveurs, tant que l'app est ouverte. Lit seulement les messages que Discord envoie déjà à l'app.",
    'Give the reply a short name and some text.': 'Donne un petit nom et du texte à la réponse.',
    "I don't understand that time.": 'Je ne comprends pas cette heure.',
    "I'll remind you {when}.": 'Je te le rappellerai {when}.',
    'Import a backup': 'Importer une sauvegarde',
    'Imported {n} messages from {name}.': '{n} messages importés depuis {name}.',
    'In 1 hour': 'Dans 1 heure',
    'In 20 minutes': 'Dans 20 minutes',
    'In 3 hours': 'Dans 3 heures',
    'In DMs': 'Dans les MP',
    'In servers': 'Dans les serveurs',
    'Inactive friends': 'Amis inactifs',
    'Inbox': 'Boîte de réception',
    'It will be sent {when}. Keep the app open (the tray is fine).': "Il sera envoyé {when}. Garde l'app ouverte (la zone de notification suffit).",
    'Keep the archive up to date by itself (every 6 hours while the app is open)': "Garder l'archive à jour toute seule (toutes les 6 heures quand l'app est ouverte)",
    'Keyword alerts': 'Alertes mots-clés',
    'Keyword alerts saved.': 'Alertes mots-clés enregistrées.',
    'Leave selected servers': 'Quitter les serveurs choisis',
    'Leave servers': 'Quitter des serveurs',
    'Leave servers, close old DMs, find inactive friends': 'Quitter des serveurs, fermer les vieux MP, trouver les amis inactifs',
    "Leave {n} server(s)? You'd need a new invite to come back.": 'Quitter {n} serveur(s) ? Il te faudra une nouvelle invitation pour revenir.',
    'Loading your friends…': 'Chargement de tes amis…',
    'Manage saved replies…': 'Gérer les réponses enregistrées…',
    'Messages you sent': 'Messages envoyés',
    'Missed (app was closed)': "Manqué (l'app était fermée)",
    'New reminder': 'Nouveau rappel',
    'No chats yet. Click Add chats.': "Aucun chat pour l'instant. Clique sur Ajouter des chats.",
    'No messages for more than': 'Aucun message depuis plus de',
    'No reminders yet.': "Aucun rappel pour l'instant.",
    'Not in muted chats': 'Pas dans les chats en sourdine',
    'Nothing scheduled.': 'Rien de programmé.',
    'OK': 'OK',
    'Only chats in your archive are counted.': 'Seuls les chats de ton archive sont comptés.',
    'Only my messages': 'Seulement mes messages',
    'Only reads messages, never changes anything on Discord. It goes slowly on purpose (about 100 messages every 2 seconds).': 'Lit seulement les messages, ne change jamais rien sur Discord. Va lentement exprès (environ 100 messages toutes les 2 secondes).',
    'Only this chat': 'Seulement ce chat',
    'Open in the tray when your PC starts': "S'ouvre dans la zone de notification au démarrage du PC",
    'Open the app when Windows starts (in the tray)': "Ouvrir l'app au démarrage de Windows (dans la zone de notification)",
    'Or type a time: 6pm, 18:30, tomorrow 9am, 45m, monday 8am': 'Ou tape une heure : 18:30, tomorrow 9am, 45m, monday 8am',
    'Past month': 'Le mois dernier',
    'Past week': 'La semaine dernière',
    'Past year': "L'année dernière",
    'People who talked to you most': "Ceux qui t'ont le plus parlé",
    'Person': 'Personne',
    'Pick a backup folder (it has messages.json)': 'Choisis un dossier de sauvegarde (avec messages.json)',
    'Pick a time at least one minute from now.': 'Choisis une heure dans au moins une minute.',
    'Pick a time…': 'Choisir une heure…',
    'Privacy sweeper': 'Grand ménage',
    'Privacy sweeper: {n} done.': 'Grand ménage : {n} fait(s).',
    'Remind me about this': 'Me le rappeler',
    'Reminder': 'Rappel',
    'Reminders': 'Rappels',
    'Remove from the archive': "Retirer de l'archive",
    'Remove selected friends': 'Retirer les amis choisis',
    'Remove {name} and its {n} saved messages from this PC?': 'Retirer {name} et ses {n} messages enregistrés de ce PC ?',
    "Remove {n} friend(s)? They are not told, but they'll see it.": 'Retirer {n} ami(s) ? Ils ne sont pas prévenus, mais ils le verront.',
    'Right-click any message → Remind me about this. You get a notification, even with the window in the tray.': 'Clic droit sur un message → Me le rappeler. Tu reçois une notification, même avec la fenêtre dans la zone de notification.',
    'Safe mode': 'Mode sûr',
    'Safe mode (recommended)': 'Mode sûr (conseillé)',
    'Safe mode allows {n} more today, so only the first {n} will be done.': "Le mode sûr en permet encore {n} aujourd'hui, donc seuls les {n} premiers seront faits.",
    'Safe mode is off': 'Le mode sûr est désactivé',
    'Safe mode limits saved.': 'Limites du mode sûr enregistrées.',
    'Safe mode: at most {n} messages can wait to be sent.': "Mode sûr : {n} messages au plus peuvent attendre d'être envoyés.",
    'Safe mode: daily limit for scheduled messages': 'Mode sûr : limite du jour pour les messages programmés',
    "Safe mode: today's limit for automatic deletes is reached. The rule continues tomorrow.": 'Mode sûr : la limite du jour pour les suppressions automatiques est atteinte. La règle continue demain.',
    "Safe mode: today's limit for this is reached. Try again tomorrow.": 'Mode sûr : la limite du jour est atteinte. Réessaie demain.',
    'Safe mode: {n} left today': "Mode sûr : encore {n} aujourd'hui",
    'Save as a page to share': 'Enregistrer comme page à partager',
    'Save limits': 'Enregistrer les limites',
    'Save the text as a saved reply': 'Enregistrer le texte comme réponse',
    'Saved replies': 'Réponses enregistrées',
    'Saved: {path}': 'Enregistré : {path}',
    'Scheduled': 'Programmé',
    'Scheduled message sent to {chat}.': 'Message programmé envoyé à {chat}.',
    'Scheduled messages': 'Messages programmés',
    'Scheduled messages sent': 'Messages programmés envoyés',
    'Search the archive': "Chercher dans l'archive",
    'Search words ("exact phrase" works)': 'Mots à chercher ("phrase exacte" marche)',
    'Send later': 'Envoyer plus tard',
    'Send now': 'Envoyer maintenant',
    'Sending…': 'Envoi…',
    'Sent': 'Envoyé',
    'Servers left': 'Serveurs quittés',
    'Shortcuts: Ctrl+Shift+F search the archive · Ctrl+Shift+R reminders': "Raccourcis : Ctrl+Maj+F chercher dans l'archive · Ctrl+Maj+R rappels",
    'Snooze 1 hour': "Repousser d'1 heure",
    'Switch to {name}': 'Passer à {name}',
    'The app opens hidden in the tray (next to the clock) when your PC starts, so reminders, scheduled messages, alerts and notifications work without you opening it. Needs a saved account (Remember me).': "L'app s'ouvre cachée dans la zone de notification (près de l'horloge) au démarrage du PC : rappels, messages programmés, alertes et notifications marchent sans que tu l'ouvres. Il faut un compte enregistré (Se souvenir de moi).",
    'The app was closed when it was due ({chat}). Open Scheduled messages to send it or delete it.': "L'app était fermée à l'heure prévue ({chat}). Ouvre Messages programmés pour l'envoyer ou le supprimer.",
    'Things that work every day, not just for cleaning. Everything stays on this PC.': 'Des choses utiles tous les jours, pas seulement pour nettoyer. Tout reste sur ce PC.',
    'This evening (8 PM)': 'Ce soir (20 h)',
    'This is made from your archive, so add some chats first. Nothing is sent anywhere.': "C'est fait à partir de ton archive, alors ajoute d'abord des chats. Rien n'est envoyé nulle part.",
    'This only works on Windows.': 'Ça ne marche que sous Windows.',
    'Tidy up your account. Safe mode does these one at a time with random pauses and a small daily limit, so it looks like you doing it by hand.': 'Range ton compte. Le mode sûr les fait un par un avec des pauses au hasard et une petite limite par jour, comme si tu le faisais à la main.',
    'Tip: for a server channel, open it and use its ⋯ / right-click menu "Archive this chat".': 'Astuce : pour un salon de serveur, ouvre-le et utilise le clic droit « Archiver ce chat ».',
    'Tomorrow morning (9 AM)': 'Demain matin (9 h)',
    "Tools that use your account automatically are against Discord's rules, and no app can make that risk zero. Safe mode keeps it as low as possible: automatic deletes go one chat at a time, at least 2.5 seconds apart with random pauses; bulk actions wait several random seconds between each; everything has a daily limit. Reading (archive, search, stats, alerts) is not limited.": "Les outils qui utilisent ton compte automatiquement sont contre les règles de Discord, et aucune app ne peut rendre ce risque nul. Le mode sûr le garde le plus bas possible : les suppressions automatiques se font un chat à la fois, à au moins 2,5 secondes d'écart avec des pauses au hasard ; les actions en masse attendent plusieurs secondes au hasard entre chacune ; tout a une limite par jour. La lecture (archive, recherche, stats, alertes) n'est pas limitée.",
    'Turn safe mode off? Automatic actions will go faster and have no daily limit, which makes a ban more likely.': 'Désactiver le mode sûr ? Les actions automatiques iront plus vite sans limite par jour, ce qui rend un bannissement plus probable.',
    'Type ;name then Tab in the message box, or click 📝.': 'Tape ;nom puis Tab dans la zone de message, ou clique sur 📝.',
    'Update now': 'Mettre à jour',
    'Waiting': 'En attente',
    'What should I remind you about?': 'De quoi dois-je te rappeler ?',
    'When?': 'Quand ?',
    'Who you talk to, when, your words and emojis': 'À qui tu parles, quand, tes mots et tes emojis',
    'Words (one per line or with commas; /regex/ works too)': 'Mots (un par ligne ou avec des virgules ; /regex/ marche aussi)',
    'Write a message first.': "Écris d'abord un message.",
    "Write a message, then click 🕓 next to the box. The app sends it at that time if it's open (the tray is fine). If it was closed, the message waits here as missed: nothing is sent by surprise.": "Écris un message, puis clique sur 🕓 à côté de la zone. L'app l'envoie à cette heure si elle est ouverte (la zone de notification suffit). Si elle était fermée, le message attend ici comme manqué : rien n'est envoyé par surprise.",
    'Write the message first, then pick when to send it.': "Écris d'abord le message, puis choisis quand l'envoyer.",
    'Your archive is empty.': 'Ton archive est vide.',
    'Your emojis': 'Tes emojis',
    'Your words': 'Tes mots',
    'Your year': 'Ton année',
    'a chat': 'un chat',
    'complete': 'complet',
    'never': 'jamais',
    'empty': 'vide',
    'in {n} min': 'dans {n} min',
    'leaves the group': 'quitte le groupe',
    'name (like thanks)': 'nom (comme merci)',
    'never talked in DMs': 'jamais parlé en MP',
    'per day': 'par jour',
    'still loading': 'chargement en cours',
    'today at {t}': "aujourd'hui à {t}",
    'tomorrow at {t}': 'demain à {t}',
    'you own it': 'tu en es le propriétaire',
    '{n} coming up': '{n} à venir',
    '{n} days': '{n} jours',
    '{n} found': '{n} trouvé(s)',
    '{n} messages saved on this PC': '{n} messages enregistrés sur ce PC',
    '{n} new': '{n} nouveau(x)',
    '{n} results · {t} messages from {c} chats on this PC': '{n} résultats · {t} messages de {c} chats sur ce PC',
    '{n} saved · type ;name then Tab': '{n} enregistrée(s) · tape ;nom puis Tab',
    '{n} waiting': '{n} en attente',
    '{u} today': "{u} aujourd'hui",
})

FR.update({
    "Risk tab": "Onglet Risque",
    "These actions use your account like a bot. Discord's rules don't allow that, and accounts have been limited, disabled or banned for it, even at slow speeds. They are OFF by default. Turn one on only if you accept that risk.": "Ces actions utilisent ton compte comme un robot. Les règles de Discord ne l'autorisent pas, et des comptes ont été limités, désactivés ou bannis pour ça, même à faible vitesse. Elles sont désactivées par défaut. N'en active une que si tu acceptes ce risque.",
    "Delete messages (the cleaner)": "Supprimer des messages (le nettoyeur)",
    "Automatic clean-up rules that delete": "Règles de nettoyage automatique qui suppriment",
    "Privacy sweeper (leave servers, close DMs, remove friends)": "Nettoyage de confidentialité (quitter des serveurs, fermer des MP, retirer des amis)",
    "Scheduled messages (send later)": "Messages programmés (envoyer plus tard)",
    "Turn off all risky features": "Désactiver toutes les fonctions risquées",
    "Always safe: Preview, archive and search, your year, reminders, saved replies and keyword alerts. They only read, or work on this PC.": "Toujours sans danger : l'aperçu, l'archive et la recherche, ton année, les rappels, les réponses enregistrées et les alertes de mots. Ils ne font que lire ou travaillent sur ce PC.",
    "Before you start": "Avant de commencer",
    "This app uses your Discord account the way a bot would. Discord's rules don't allow that, and accounts using tools like this have been limited, disabled or banned, even with slow settings. The risky actions (deleting in bulk, clean-up rules, privacy sweeper, scheduled messages) are switched off until you turn them on in the Risk tab. Reading features (archive, search, your year, reminders, alerts and Preview) are low risk.": "Cette app utilise ton compte Discord comme le ferait un robot. Les règles de Discord ne l'autorisent pas, et des comptes utilisant ce genre d'outils ont été limités, désactivés ou bannis, même avec des réglages lents. Les actions risquées (suppression en masse, règles de nettoyage, nettoyage de confidentialité, messages programmés) sont désactivées tant que tu ne les actives pas dans l'onglet Risque. Les fonctions de lecture (archive, recherche, ton année, rappels, alertes et aperçu) présentent peu de risque.",
    "I understand": "Je comprends",
    "Open Risk tab": "Ouvrir l'onglet Risque",
    "'{name}' is a risky feature and it is switched off.\n\nTurn it on in the Risk tab if you accept the risk. Preview (delete nothing) always works.\n\nOpen the Risk tab now?": "« {name} » est une fonction risquée et elle est désactivée.\n\nActive-la dans l'onglet Risque si tu acceptes le risque. L'aperçu (ne supprime rien) fonctionne toujours.\n\nOuvrir l'onglet Risque maintenant ?",
    "Turn on '{name}'? This is against Discord's rules and your account may be limited, disabled or banned. You do this at your own risk.": "Activer « {name} » ? C'est contre les règles de Discord et ton compte peut être limité, désactivé ou banni. Tu le fais à tes propres risques.",
    "{n} of {m} risky features on": "{n} fonction(s) risquée(s) sur {m} activée(s)",
    "Risky feature is off: nothing was deleted. Turn it on in the Risk tab if you accept the risk.": "Fonction risquée désactivée : rien n'a été supprimé. Active-la dans l'onglet Risque si tu acceptes le risque.",
    "Scheduled messages are a risky feature and are off": "Les messages programmés sont une fonction risquée et sont désactivés",
    "Risk tab (risky features, off by default)…": "Onglet Risque (fonctions risquées, désactivées par défaut)…",
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
    (r"^Removed (\d+) saved deleted message\(s\) older than (\d+) days\.$", r"\1 message(s) supprimé(s) de plus de \2 jours retiré(s)."),
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
