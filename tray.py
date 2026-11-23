"""Icon next to the Windows clock, so the app keeps running when you close the window.

Uses pystray (installed by the build script). Right-click the icon: Open, Deleted
messages, Saved messages, Quit. Double-click opens the window.
"""
import threading

import i18n


class Tray:
    def __init__(self, app, icon_path):
        import pystray
        from PIL import Image
        self.app = app
        self.pystray = pystray
        img = Image.open(icon_path)

        def ui(fn):
            return lambda icon=None, item=None: app.after(0, fn)

        menu = pystray.Menu(
            pystray.MenuItem(i18n.tr("Open"), ui(app.show_from_tray), default=True),
            pystray.MenuItem(i18n.tr("Deleted messages"),
                             ui(lambda: app.show_from_tray("deleted"))),
            pystray.MenuItem(i18n.tr("Saved messages"),
                             ui(lambda: (app.show_from_tray(), app.open_bookmarks()))),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(i18n.tr("Quit"), ui(app.quit_app)))
        self.icon = pystray.Icon("DiscordMessageCleaner", img, "Discord Message Cleaner", menu)

    def start(self):
        threading.Thread(target=self.icon.run, daemon=True).start()

    def notify(self, title, text):
        try:
            self.icon.notify(text, title)
        except Exception:
            pass

    def stop(self):
        try:
            self.icon.stop()
        except Exception:
            pass
