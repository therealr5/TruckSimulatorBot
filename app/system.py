"Blueprint file containing the info command and some general button handlers for abort and back buttons"
# pylint: disable=unused-argument, missing-function-docstring
from datetime import datetime

import config
from flask_discord_interactions import Context, DiscordInteractionsBlueprint, Embed, Message
from flask_discord_interactions.models.component import ActionRow, Button, ButtonStyles
from flask_discord_interactions.models.embed import Field, Footer, Media
from i18n import set as set_i18n
from i18n import t
from resources import players
from utils import get_localizations, log_command

system_bp = DiscordInteractionsBlueprint()


def get_info_embed() -> Embed:
    info_embed = Embed(
        title="Truck Simulator Info",
        color=config.EMBED_COLOR,
        footer=Footer(text=t("info.developer")),
        thumbnail=Media(url=config.SELF_AVATAR_URL),
        timestamp=datetime.utcnow().replace(microsecond=0).isoformat(),
    )

    info_embed.fields = [
        Field(
            name=t("info.system.title"),
            value=t(
                "info.system.text",
                players=players.get_count("players"),
                jobs=players.get_count("jobs"),
                companies=players.get_count("companies"),
            ),
            inline=False,
        ),
        Field(name=t("info.credits.title"), value=t("info.credits.text"), inline=False),
    ]
    return info_embed


@system_bp.command(
    name=t("commands.info.name", locale=config.I18n.FALLBACK),
    name_localizations=get_localizations("commands.info.name"),
    description=t("commands.info.description", locale=config.I18n.FALLBACK),
    description_localizations=get_localizations("commands.info.description"),
)
def info(ctx: Context) -> Message:
    """Prints out general information about this app."""
    set_i18n("locale", ctx.locale)
    log_command(ctx)
    return Message(
        embed=get_info_embed(),
        components=[
            ActionRow(
                components=[
                    Button(style=5, url=link["url"], label=link["name"], emoji=link.get("emoji"))
                    for link in config.info_links()
                ]
            ),
            ActionRow(
                components=[
                    Button(
                        style=ButtonStyles.SECONDARY,
                        label=t("info.refresh"),
                        custom_id=str(refresh),
                        emoji={"name": "reload", "id": 903581225149665290},
                    )
                ]
            ),
        ],
    )


@system_bp.custom_handler(custom_id="refresh_system_info")
def refresh(ctx: Context):
    set_i18n("locale", ctx.locale)
    return Message(embed=get_info_embed(), update=True)
