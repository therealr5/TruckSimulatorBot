"Blueprint file containing all stat-related commands and handlers"
# pylint: disable=unused-argument, missing-function-docstring
import config
from flask_discord_interactions import Context, DiscordInteractionsBlueprint, Embed, Message
from flask_discord_interactions.models.component import ActionRow, Button, SelectMenu, SelectMenuOption
from flask_discord_interactions.models.embed import Author, Field, Footer, Media
from flask_discord_interactions.models.user import User
from resources import companies, components, levels, players, trucks
from utils import log_command

profile_bp = DiscordInteractionsBlueprint()


@profile_bp.command(annotations={"user": "A user you want to view."})
def profile(ctx: Context, user: User = None) -> Message:
    "Shows your profile."
    log_command(ctx)
    return Message(embed=get_profile_embed(user if user else ctx.author))


@profile_bp.custom_handler(custom_id="profile_register")
def register(ctx: Context):
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
        author=Author(name=f"{player.name}'s profile"),
        thumbnail=Media(url=user.avatar_url),
        color=config.EMBED_COLOR,
        fields=[],
        image=Media(url=truck.image_url),
    )
    profile_embed.fields.append(
        Field(
            name="Level", value=f"{player.level} ({player.xp:,}/{levels.get_next_xp(player.level):,} xp)", inline=False
        )
    )
    profile_embed.fields.append(Field(name="Money", value=f"${player.money:,}"))
    profile_embed.fields.append(
        Field(name="Miles driven", value=f"{player.miles:,}\n({player.truck_miles:,} with current truck)", inline=False)
    )
    profile_embed.fields.append(Field(name="Gas left", value=f"{player.gas} l", inline=False))
    profile_embed.fields.append(Field(name="Current truck", value=truck.name))
    if player.loaded_items:
        profile_embed.fields.append(
            Field(
                name=f"Current load ({len(player.loaded_items)}/{trucks.get(player.truck_id).loading_capacity})",
                value="".join([str(item) + "\n" for item in player.loaded_items]),
            )
        )

    try:
        company = companies.get(player.company)
        profile_embed.fields.append(Field(name="Company", value=f"{company.logo} {company.name}"))
    except companies.CompanyNotFound:
        pass
    return profile_embed


@profile_bp.custom_handler(custom_id="top")
def top(ctx: Context, player_id) -> Message:
    "Presents the top players."
    return Message(
        embed=get_top_embed(), components=get_top_select(players.get(ctx.author.id, check=player_id)), update=True
    )


@profile_bp.custom_handler(custom_id="top_select")
def top_select(ctx: Context, player_id) -> Message:
    "Handler for the toplist select"
    if ctx.author.id != player_id:
        raise players.WrongPlayer()
    return Message(embed=get_top_embed(ctx.values[0]), update=True)


def get_top_embed(key="level") -> Embed:
    "Returns the top embed"
    top_players = players.get_top(key)
    top_body = ""
    count = 0
    top_embed = Embed(title="Truck Simulator top list ????", color=config.EMBED_COLOR, fields=[])

    for player in top_players[0]:
        if key == "money":
            val = f"{player.money:,}"
        elif key == "miles":
            val = f"{player.miles:,}"
        else:
            val = f"{player.level:,} ({player.xp:,}/{levels.get_next_xp(player.level):,} xp)"
        count += 1
        top_body += f"**{count}**. {player} ~ {val}{top_players[1]}\n"
    top_embed.fields.append(Field(name=f"Top players sorted by {key}", value=top_body))
    top_embed.footer = Footer(text="Congratulations if you see yourself in that list!", icon_url=config.SELF_AVATAR_URL)
    return top_embed


def get_top_select(player):
    "Returns the select appearing below /top"
    return [
        ActionRow(
            components=[
                SelectMenu(
                    custom_id=["top_select", player.id],
                    placeholder="View another toplist",
                    options=[
                        SelectMenuOption(label="Level", value="level", emoji={"name": "????", "id": None}),
                        SelectMenuOption(
                            label="Money", value="money", emoji={"name": "ts_money", "id": "868480873157242930"}
                        ),
                        SelectMenuOption(
                            label="Miles", value="miles", emoji={"name": "default_truck", "id": "861674264737087519"}
                        ),
                    ],
                )
            ]
        ),
        ActionRow(
            components=[
                Button(
                    label="Back",
                    custom_id=["home", player.id],
                    style=2,
                )
            ]
        ),
    ]
