# pylint: disable=too-few-public-methods
"Some configuration values"
from os import getenv

from i18n import t

MAP_BORDER = 25
LOG_FORMAT = "%(levelname)s [%(module)s.%(funcName)s]: %(message)s"
EMBED_COLOR = int("0x2f3136", 16)
SELF_AVATAR_URL = "https://cdn.discordapp.com/avatars/831052837353816066/c9b904f935580ac68f54f184f6fc620c.png"


def info_links() -> list:
    """
    :return: the link buttons as a list
    """
    return [
        {
            "name": t("info.links.support"),
            "url": "https://discord.gg/FzAxtGTUhN",
            "emoji": {"name": "discord", "id": "974289421706854450"},
        },
        {
            "name": "GitHub",
            "url": "https://github.com/therealr5/TruckSimulatorBot",
            "emoji": {"name": "github", "id": "974289493823729714"},
        },
        {"name": t("info.links.terms"), "url": "https://trucksimulatorbot.rfive.de/terms.html"},
        {"name": t("info.links.privacy"), "url": "https://trucksimulatorbot.rfive.de/privacypolicy.html"},
    ]


DATABASE_ARGS = {
    "host": getenv("MYSQL_HOST"),
    "user": getenv("MYSQL_USER"),
    "passwd": getenv("MYSQL_PASSWORD"),
    "database": getenv("MYSQL_DATABASE"),
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
    "use_unicode": True,
}


class Guilds:
    "Guild id used for command registration"
    SUPPORT = "839580174282260510"


class Users:
    "User ids to determine some important roles"
    ADMIN = "692796548282712074"


class I18n:
    "I18n configuration values"
    AVAILABLE_LOCALES = ["en-US", "de"]
    FILENAME_FORMAT = "{locale}{format}"
    FALLBACK = "en-US"
