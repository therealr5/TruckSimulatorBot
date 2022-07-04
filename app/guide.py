"Blueprint file containing the guide command and its component handlers"
# pylint: disable=unused-argument
from os import listdir

import config
from flask_discord_interactions import Context, DiscordInteractionsBlueprint, Embed, Message
from flask_discord_interactions.models.component import ActionRow, Button, SelectMenu, SelectMenuOption
from flask_discord_interactions.models.embed import Author, Field, Media
from flask_discord_interactions.models.option import CommandOptionType, Option
from i18n import t
from resources import assets, items, places, players, symbols
from utils import get_localizations, log_command

guide_bp = DiscordInteractionsBlueprint()


@guide_bp.custom_handler(custom_id="guide_minijobs")
def minijobs(ctx: Context) -> Message:
    """Prints out all permanently running minijobs."""
    player = players.get(ctx.author.id)
    minijob_list = ""
    for place in places.get_all():
        if place.accepted_item is not None:
            minijob_list += (
                f"\n{symbols.LIST_ITEM}**{place}** will give you "
                f"${place.item_reward*(player.level+1):,} if you bring them *{place.accepted_item}*."
            )
    return Message(
        embed=Embed(title="All available minijobs", description=minijob_list, color=config.EMBED_COLOR),
        update=True,
        components=get_guide_selects(),
    )


@guide_bp.custom_handler(custom_id="guide_item")
def iteminfo(ctx: Context) -> Message:
    """Prints some information about a specific item."""
    requested_item = items.get(ctx.values[0])
    item_embed = Embed(
        title=f"Item info for {requested_item.name}",
        description=requested_item.description,
        color=config.EMBED_COLOR,
        thumbnail=Media(url=f"https://cdn.discordapp.com/emojis/{requested_item.emoji}.webp"),
        fields=[],
    )
    for place in places.get_all():
        if place.produced_item == requested_item.name:
            item_embed.fields.append(Field(name="Found at", value=place.name))
    return Message(embed=item_embed, components=get_guide_selects(topic="items"), update=True)


@guide_bp.custom_handler(custom_id="guide_place")
def placeinfo(ctx: Context) -> Message:
    """Prints some information about a specific place."""
    player = players.get(ctx.author.id)
    place = ctx.values[0]
    try:
        queried_place = places.get(place)
    except ValueError:
        return Message("Place not found")
    position_embed = Embed(
        title=f"Place info for {queried_place.name}",
        color=config.EMBED_COLOR,
        fields=[Field(name="Position", value=str(queried_place.position))],
    )
    if queried_place.image_url_default is not None:
        position_embed.fields.append(Field(name="Produced item", value=str(items.get(queried_place.produced_item))))
        position_embed.image = Media(url=assets.get_place_image(player, queried_place))
    if queried_place.accepted_item:
        position_embed.fields.append(Field(name="Accepted item", value=str(items.get(queried_place.accepted_item))))

    return Message(embed=position_embed, components=get_guide_selects(topic="places"), update=True)


@guide_bp.command(
    name=t("commands.guide.name", locale=config.I18n.FALLBACK),
    name_localizations=get_localizations("commands.guide.name"),
    description=t("commands.guide.description", locale=config.I18n.FALLBACK),
    description_localizations=get_localizations("commands.guide.description"),
    options=[
        Option(
            name=t("commands.guide.options.topic.name", locale=config.I18n.FALLBACK),
            name_localizations=get_localizations("commands.guide.options.topic.name"),
            description=t("commands.guide.options.topic.description", locale=config.I18n.FALLBACK),
            description_localizations=get_localizations("commands.guide.options.topic.description"),
            type=CommandOptionType.STRING,
            choices=[
                {"name": f[: f.find(".")].replace("_", " "), "value": f[: f.find(".")]}
                for f in sorted(listdir("./guide"))
            ],
        )
    ],
)
def guide(ctx: Context, topic: str = "introduction") -> Message:
    """Opens a guide to help you understand this game."""
    log_command(ctx)
    return Message(embed=get_guide_embed(topic), components=get_guide_selects(topic=topic))


@guide_bp.custom_handler(custom_id="guide_topic")
def guide_topic(ctx: Context):
    """Handler for the topic select"""
    return Message(embed=get_guide_embed(ctx.values[0]), components=get_guide_selects(topic=ctx.values[0]), update=True)


def get_guide_embed(topic: str) -> Embed:
    """Returns the fitting guide embed for a topic"""
    with open(f"./guide/{topic}.md", "r", encoding="utf8") as guide_file:
        topic = str.lower(topic)
        image_url = guide_file.readline()
        guide_embed = Embed(
            title=f"{str.upper(topic[0])}{topic[1:]}".replace("_", " "),
            description=guide_file.read(),
            color=config.EMBED_COLOR,
            author=Author(name="Truck Simulator Guide", icon_url=config.SELF_AVATAR_URL),
        )
        if image_url.startswith("https"):
            guide_embed.image = Media(url=image_url)
        else:
            guide_embed.description = image_url + guide_embed.description
        return guide_embed


def get_guide_selects(topic: str = ""):
    """Builder for the topic select"""
    selects = [
        ActionRow(
            components=[
                SelectMenu(
                    custom_id="guide_topic",
                    options=[
                        SelectMenuOption(
                            label=str.upper(f[:1]) + f[1 : f.find(".")].replace("_", " "), value=f[: f.find(".")]
                        )
                        for f in sorted(listdir("./guide"))
                    ],
                    placeholder="Select a topic",
                )
            ]
        )
    ]
    if topic == "places":
        selects.append(
            ActionRow(
                components=[
                    SelectMenu(
                        custom_id="guide_place",
                        options=[
                            SelectMenuOption(
                                label=place.name,
                                value=str(int(place.position)),
                                emoji={"name": "place", "id": items.get(place.produced_item).emoji},
                            )
                            for place in places.get_all()
                        ],
                        placeholder="Select a place to view",
                    )
                ]
            )
        )
    if topic == "items":
        selects.append(
            ActionRow(
                components=[
                    SelectMenu(
                        custom_id="guide_item",
                        options=[
                            SelectMenuOption(
                                label=item.name,
                                value=item.name,
                                emoji={"name": "item", "id": item.emoji},
                            )
                            for item in items.get_all()
                        ],
                        placeholder="Select an item to view",
                    )
                ]
            )
        )
    if topic == "minijobs":
        selects.append(ActionRow(components=[Button(label="View minijobs", custom_id="guide_minijobs", style=2)]))
    if topic == "introduction":
        selects.append(
            ActionRow(
                components=[
                    Button(
                        style=5,
                        label=config.info_links()[0]["name"],
                        url=config.info_links()[0]["url"],
                        emoji=config.info_links()[0]["emoji"],
                    )
                ]
            )
        )
    return selects
