"Blueprint file containing all stat-related commands and handlers"
# pylint: disable=unused-argument, missing-function-docstring
import config
from flask_discord_interactions import Context, DiscordInteractionsBlueprint, Embed, Message
from flask_discord_interactions.models.component import ActionRow, Button, SelectMenu, SelectMenuOption
from flask_discord_interactions.models.embed import Author, Field, Footer, Media
from flask_discord_interactions.models.option import CommandOptionType, Option
from flask_discord_interactions.models.user import User
from i18n import set as set_i18n
from i18n import t
from resources import companies, components, levels, players, trucks
from utils import commatize, get_localizations, log_command

profile_bp = DiscordInteractionsBlueprint()


@profile_bp.command(
    name=t("commands.profile.name", locale=config.I18n.FALLBACK),
    name_localizations=get_localizations("commands.profile.name"),
    description=t("commands.profile.description", locale=config.I18n.FALLBACK),
    description_localizations=get_localizations("commands.profile.description"),
    options=[
        Option(
            type=CommandOptionType.USER,
            name=t("commands.profile.options.user.name", locale=config.I18n.FALLBACK),
            name_localizations=get_localizations("commands.profile.options.user.name"),
            description=t("commands.profile.options.user.description", locale=config.I18n.FALLBACK),
            description_localizations=get_localizations("commands.profile.options.user.description"),
        )
    ],
)
def profile(ctx: Context, user: User = None) -> Message:
    "Shows your profile."
    log_command(ctx)
    set_i18n("locale", ctx.locale)
    return Message(embed=get_profile_embed(user if user else ctx.author))


@profile_bp.custom_handler(custom_id="profile_register")
def register(ctx: Context):
    set_i18n("locale", ctx.locale)
    if players.registered(ctx.author.id):
        return Message(update=True, deferred=True)
    with open("./messages/welcome.md", "r", encoding="utf8") as welcome_file:
        welcome_embed = Embed(
            title="Hey there, fellow Trucker,",
            description=welcome_file.read(),
            color=config.EMBED_COLOR,
            author=Author(
                name="Welcome to the Truck Simulator",
                icon_url=config.SELF_AVATAR_URL,
            ),
            footer=Footer(text="Your profile has been created", icon_url=ctx.author.avatar_url),
        )
    rules_embed = Embed(title="Rules", color=config.EMBED_COLOR, fields=[])
    rules_embed.fields.append(
        Field(
            name="Trading ingame currency for real money",
            value="Not only that it is pretty stupid to trade real world's money in exchange of a number "
            "somewhere in a random database it will also get you banned from this bot.",
            inline=False,
        )
    )
    rules_embed.fields.append(
        Field(
            name="Autotypers",
            value="Don't even try, it's just wasted work only to get you blacklisted.",
        )
    )
    players.insert(
        players.Player(ctx.author.id, ctx.author.username, discriminator=ctx.author.discriminator, money=1000, gas=600)
    )
    return Message(
        embeds=[welcome_embed, rules_embed],
        components=[
            ActionRow(
                components=[
                    Button(
                        label="Let's go!",
                        custom_id=["initial_drive", ctx.author.id],
                        style=3,
                        emoji={"name": "default_truck", "id": 861674264737087519},
                    )
                ]
            )
        ],
    )


@profile_bp.custom_handler(custom_id="home")
def profile_home(ctx: Context, player_id):
    """Shows your profile."""
    set_i18n("locale", ctx.locale)
    player = players.get(ctx.author.id, check=player_id)
    return Message(embed=get_profile_embed(ctx.author), components=components.get_home_buttons(player), update=True)


def get_profile_embed(user: User) -> Embed:
    player: players.Player = players.get(user.id)
    truck: trucks.Truck = trucks.get(player.truck_id)
    # Detect, when the player is renamed
    if player.name != user.username:
        player.name = user.username
    if player.discriminator != user.discriminator:
        player.discriminator = user.discriminator
    profile_embed = Embed(
        author=Author(name=t("profile.author", player=player.name)),
        thumbnail=Media(url=user.avatar_url),
        color=config.EMBED_COLOR,
        fields=[],
        image=Media(url=truck.image_url),
    )
    profile_embed.fields.append(
        Field(
            name=t("profile.level"),
            value=f"{player.level} ({player.xp:,}/{levels.get_next_xp(player.level):,} xp)",
            inline=False,
        )
    )
    profile_embed.fields.append(Field(name=t("profile.money"), value=f"${player.money:,}"))
    profile_embed.fields.append(
        Field(
            name=t("profile.miles"),
            value=f"{player.miles:,}\n" + t("profile.truck_miles", miles=commatize(player.truck_miles)),
            inline=False,
        )
    )
    profile_embed.fields.append(Field(name=t("profile.gas"), value=f"{player.gas:,} l", inline=False))
    profile_embed.fields.append(Field(name=t("profile.truck"), value=truck.name))
    if player.loaded_items:
        profile_embed.fields.append(
            Field(
                name=t("profile.load")
                + f" ({len(player.loaded_items)}/{trucks.get(player.truck_id).loading_capacity})",
                value="".join([str(item) + "\n" for item in player.loaded_items]),
            )
        )

    try:
        company = companies.get(player.company)
        profile_embed.fields.append(Field(name=t("profile.company"), value=f"{company.logo} {company.name}"))
    except companies.CompanyNotFound:
        pass
    return profile_embed


@profile_bp.custom_handler(custom_id="top")
def top(ctx: Context, player_id) -> Message:
    "Presents the top players."
    set_i18n("locale", ctx.locale)
    return Message(
        embed=get_top_embed(), components=get_top_select(players.get(ctx.author.id, check=player_id)), update=True
    )


@profile_bp.custom_handler(custom_id="top_select")
def top_select(ctx: Context, player_id) -> Message:
    "Handler for the toplist select"
    set_i18n("locale", ctx.locale)
    if ctx.author.id != player_id:
        raise players.WrongPlayer()
    return Message(embed=get_top_embed(ctx.values[0]), update=True)


def get_top_embed(key="level") -> Embed:
    "Returns the top embed"
    top_players = players.get_top(key)
    top_body = ""
    count = 0
    top_embed = Embed(title=t("top.title"), color=config.EMBED_COLOR, fields=[])

    for player in top_players[0]:
        if key == "money":
            val = f"{player.money:,}"
        elif key == "miles":
            val = f"{player.miles:,}"
        else:
            val = f"{player.level:,} ({player.xp:,}/{levels.get_next_xp(player.level):,} xp)"
        count += 1
        top_body += f"**{count}**. {player} ~ {val}{top_players[1]}\n"
    top_embed.fields.append(Field(name=t(f"top.fields.{key}"), value=top_body))
    top_embed.footer = Footer(text=t("top.footer"), icon_url=config.SELF_AVATAR_URL)
    return top_embed


def get_top_select(player):
    "Returns the select appearing below /top"
    return [
        ActionRow(
            components=[
                SelectMenu(
                    custom_id=["top_select", player.id],
                    placeholder=t("top.select"),
                    options=[
                        SelectMenuOption(label=t("top.keys.level"), value="level", emoji={"name": "🎉", "id": None}),
                        SelectMenuOption(
                            label=t("top.keys.money"),
                            value="money",
                            emoji={"name": "ts_money", "id": "868480873157242930"},
                        ),
                        SelectMenuOption(
                            label=t("top.keys.miles"),
                            value="miles",
                            emoji={"name": "default_truck", "id": "861674264737087519"},
                        ),
                    ],
                )
            ]
        ),
        ActionRow(components=[components.back_home(player.id)]),
    ]
