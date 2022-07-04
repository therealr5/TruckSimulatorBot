"Blueprint file containing all gambling-related commands and handlers"
# pylint: disable=unused-argument, missing-function-docstring
from random import choices, sample

import config
from flask import request
from flask_discord_interactions import Context, DiscordInteractionsBlueprint, Embed, Message
from flask_discord_interactions.discord import InteractionType
from flask_discord_interactions.models.component import ActionRow, Button, ButtonStyles, TextInput
from flask_discord_interactions.models.embed import Author, Field, Media
from flask_discord_interactions.models.modal import Modal
from i18n import set as set_i18n
from i18n import t
from resources import components, items, players
from utils import commatize

gambling_bp = DiscordInteractionsBlueprint()


@gambling_bp.custom_handler(custom_id="casino")
def casino(ctx: Context, player_id: str) -> Message:
    set_i18n("locale", ctx.locale)
    player = players.get(ctx.author.id, check=player_id)
    return Message(
        embed=Embed(
            title=t("casino.welcome"),
            color=config.EMBED_COLOR,
            image=Media(
                url=(
                    "https://media.discordapp.net/attachments/868822515282231346/871394792947482674"
                    "/vegass-default_truck.png"
                )
            ),
        ),
        components=components.get_casino_buttons(player),
        update=True,
    )


def get_slots_embed(player: players.Player, amount: int) -> Embed:
    player.debit_money(amount)

    chosen_items = choices(sample(items.get_all(), 8), k=3)
    machine = "<|"
    for item in chosen_items:
        machine += f"<:n:{item.emoji}>"
        machine += "|"
    machine += ">"

    slots_embed = Embed(
        description=machine,
        color=config.EMBED_COLOR,
        author=Author(name=t("casino.slots.author", name=player.name)),
        fields=[],
    )

    if chosen_items.count(chosen_items[0]) == 3:
        slots_embed.fields.append(
            Field(
                name=t("casino.slots.result.title"), value=t("casino.slots.result.win3", amount=commatize(amount * 10))
            )
        )
        player.add_money(amount * 11)
    elif chosen_items.count(chosen_items[0]) == 2 or chosen_items.count(chosen_items[1]) == 2:
        slots_embed.fields.append(
            Field(name=t("casino.slots.result.title"), value=t("casino.slots.result.win2", amount=commatize(amount)))
        )
        player.add_money(amount * 2)
    else:
        slots_embed.fields.append(
            Field(name=t("casino.slots.result.title"), value=t("casino.slots.result.loss", amount=commatize(amount)))
        )
    return slots_embed


def get_slots_components(player: players.Player, amount: int) -> list:
    return [
        ActionRow(
            components=[
                Button(
                    label=t("casino.slots.button.again2"),
                    custom_id=[slots_handler, player.id, amount * 2],
                    style=ButtonStyles.SUCCESS,
                    emoji={"name": "🎰"},
                ),
                Button(
                    label=t("casino.slots.button.again"),
                    custom_id=[slots_handler, player.id, amount],
                    style=ButtonStyles.SECONDARY,
                ),
            ]
        ),
        ActionRow(components=[Button(label=t("back"), style=2, custom_id=["casino", player.id])]),
    ]


@gambling_bp.custom_handler(custom_id="slots_init")
def slots_modal(ctx: Context, player_id):
    set_i18n("locale", ctx.locale)
    player = players.get(ctx.author.id, check=player_id)
    return Modal(
        custom_id=["slots", player.id],
        title=t("casino.slots.modal.title"),
        components=[
            ActionRow(
                components=[
                    TextInput(
                        label=t("casino.slots.modal.amount.label"),
                        custom_id="input_amount",
                        placeholder=t("casino.slots.modal.amount.placeholder"),
                    )
                ]
            )
        ],
    )


@gambling_bp.custom_handler(custom_id="slots")
def slots_handler(ctx: Context, player_id: str, amount=0):
    set_i18n("locale", ctx.locale)
    player = players.get(ctx.author.id, check=player_id)
    if ctx.author.id != player_id:
        raise players.WrongPlayer()
    if ctx.author.id != player_id:
        raise players.WrongPlayer()
    # replace this when pr is merged
    type = request.json.get("type")
    if type == InteractionType.MODAL_SUBMIT:
        amount = ctx.get_component("input_amount").value.replace(" ", "").replace("k", "000").replace("m", "000000")
        if amount == "all":
            amount = str(player.money)
    if str.isnumeric(amount):
        amount = int(amount)
    else:
        return Message(t("casino.invalid_amount"), ephemeral=True)
    return Message(
        embed=get_slots_embed(player, amount),
        components=get_slots_components(player, amount),
        update=True,
    )
