"Blueprint file containing all truck-related commands and handlers"
# pylint: disable=unused-argument
from math import log
from typing import Union

import config
from flask_discord_interactions import Context, DiscordInteractionsBlueprint, Embed, Message
from flask_discord_interactions.models.component import ActionRow, Button, ButtonStyles
from flask_discord_interactions.models.embed import Author, Field, Media
from i18n import set as set_i18n
from i18n import t
from resources import components, players, symbols, trucks
from utils import commatize

truck_bp = DiscordInteractionsBlueprint()


def get_truck_embed(truck: trucks.Truck) -> Embed:
    """Returns an embed with details about the given Truck"""
    truck_embed = Embed(
        title=truck.name,
        description=truck.description,
        color=config.EMBED_COLOR,
        image=Media(url=truck.image_url),
        fields=[],
    )
    truck_embed.fields.append(
        Field(
            name=t("truck.gas.consumption.title"),
            value=t("truck.gas.consumption.text", consumption=truck.gas_consumption),
        )
    )
    truck_embed.fields.append(
        Field(
            name=t("truck.gas.capacity.title"),
            value=t("truck.gas.capacity.text", capacity=commatize(truck.gas_capacity)),
        )
    )
    truck_embed.fields.append(Field(name=t("truck.price"), value="$" + commatize(truck.price)))
    truck_embed.fields.append(
        Field(
            name=t("truck.loading_capacity.title"),
            value=t("truck.loading_capacity.text", amount=truck.loading_capacity),
        )
    )
    return truck_embed


@truck_bp.custom_handler(custom_id="manage_truck")
def show_truck_button(ctx: Context, player_id: str):
    """Shows the main truck page"""
    set_i18n("locale", ctx.locale)
    player = players.get(ctx.author.id, check=player_id)
    truck = trucks.get(player.truck_id)
    truck_embed = get_truck_embed(truck)
    truck_embed.author = Author(name=t("truck.author", player=player.name), icon_url=ctx.author.avatar_url)
    return Message(embed=truck_embed, components=components.get_truck_components(player), update=True)


@truck_bp.custom_handler(custom_id="truck_buy")
def buy(ctx: Context, player_id: str) -> Union[Message, str]:
    """Select handler to buy a new truck"""
    set_i18n("locale", ctx.locale)
    player = players.get(ctx.author.id, check=player_id)
    old_truck = trucks.get(player.truck_id)
    new_truck = trucks.get(int(ctx.values[0]))
    selling_price = round(old_truck.price - (old_truck.price / 10) * log(player.truck_miles + 1))
    end_price = new_truck.price - selling_price
    # this also adds money if the end price is negative
    player.debit_money(end_price)
    player.truck_miles = 0
    player.gas = new_truck.gas_capacity
    player.truck_id = new_truck.truck_id
    answer_embed = Embed(
        description=t(
            "truck.buy.text",
            old_name=old_truck.name,
            selling_price=commatize(selling_price),
            new_name=new_truck.name,
            price=commatize(new_truck.price),
        ),
        color=config.EMBED_COLOR,
        author=Author(name=t("truck.buy.author"), icon_url=config.SELF_AVATAR_URL),
    )
    return Message(
        embed=answer_embed,
        components=[
            ActionRow(
                components=[
                    Button(
                        label=t("truck.buy.checkout"),
                        custom_id=["manage_truck", player.id],
                        emoji=symbols.parse_emoji(new_truck.emoji),
                    )
                ]
            )
        ],
        update=True,
    )


@truck_bp.custom_handler(custom_id="truck_view")
def view(ctx: Context, player_id: str) -> Message:
    """View details about a specific truck"""
    set_i18n("locale", ctx.locale)
    if ctx.author.id != player_id:
        raise players.WrongPlayer()
    truck_embed = get_truck_embed(trucks.get(int(ctx.values[0])))
    return Message(
        embed=truck_embed,
        components=[
            ActionRow(
                components=[
                    Button(label=t("back"), custom_id=["manage_truck", player_id], style=ButtonStyles.SECONDARY)
                ]
            )
        ],
        update=True,
    )
