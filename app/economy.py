"Blueprint file containing all economy-related commands and handlers"
# pylint: disable=unused-argument,missing-function-docstring
import config
from flask_discord_interactions import Context, DiscordInteractionsBlueprint, Embed, Message
from flask_discord_interactions.models.embed import Author, Field, Footer
from flask_discord_interactions.models.option import CommandOptionType, Option
from flask_discord_interactions.models.user import User
from resources import items, jobs, levels, players, trucks
from resources.autocompletes import amount_all
from utils import log_command

economy_bp = DiscordInteractionsBlueprint()


@economy_bp.custom_handler(custom_id="job_show")
def show_job(ctx: Context, player_id: str) -> Message:
    player = players.get(player_id)

    current_job = player.get_job()
    if current_job is None:
        raise players.WrongPlayer()
    job_embed = Embed(
        color=config.EMBED_COLOR,
        author=Author(name=f"{player.name}'s Job"),
        fields=[],
    )
    place_from = current_job.place_from
    place_to = current_job.place_to
    item = items.get(place_from.produced_item)
    job_message = f"Bring {item} from {place_from.name} to {place_to.name}."
    job_embed.fields.append(Field(name="Current job", value=job_message, inline=False))
    job_embed.fields.append(Field(name="Current state", value=jobs.get_state(current_job)))
    return Message(embed=job_embed, ephemeral=True)


@economy_bp.custom_handler(custom_id="refill")
def refill(ctx: Context, player_id: str):
    player = players.get(ctx.author.id, check=player_id)
    gas_amount = trucks.get(player.truck_id).gas_capacity - player.gas
    price = round(gas_amount * 1.2)

    try:
        player.debit_money(price)
    except players.NotEnoughMoney:
        if player.gas < 170:
            if player.level > 2:
                player.level -= 2
            player.gas += 100
            player.xp = 0
            return Message(
                f"<@{ctx.author.id}> We have a problem: You don't have enough money. Lets make a deal. "
                "I will give you 100 litres of gas, and you lose 2 levels",
                ephemeral=True,
            )
        return Message(
            f"<@{ctx.author.id}> you don't have enough money to do this. "
            "Do some jobs and come back if you have enough",
            ephemeral=True,
        )

    refill_embed = Embed(
        title="Thank you for visiting our gas station",
        description=f"You filled {gas_amount} litres into your truck and payed ${price}",
        color=config.EMBED_COLOR,
        footer=Footer(text="Current gas price: $1.2 per litre"),
    )

    player.gas = trucks.get(player.truck_id).gas_capacity
    drive_embed = ctx.message.embeds[1]
    drive_embed.fields[2]["value"] = str(player.gas)

    return Message(embeds=[ctx.message.embeds[0], drive_embed, refill_embed], update=True)


@economy_bp.command(
    options=[
        Option(
            name="user", description="The user you want to give money to.", type=CommandOptionType.USER, required=True
        ),
        Option(
            name="amount",
            description="The amount you want to give.",
            type=CommandOptionType.INTEGER,
            min_value=1,
            max_value=1000000,
            autocomplete=True,
            required=True,
        ),
    ]
)
def give(ctx: Context, user: User, amount: int) -> Message:
    """Transfers money to a specific user."""
    log_command(ctx)
    acceptor = players.get(user.id)
    donator = players.get(ctx.author.id)

    if ctx.author.id == acceptor.id:
        return Message(
            embed=Embed(
                title=f"Hey {ctx.author.username}",
                description="You can't give money to yourself!",
                color=config.EMBED_COLOR,
            )
        )

    cap = levels.coincap(acceptor.level)
    if amount > cap:
        return Message(
            embed=Embed(
                title=f"Hey {ctx.author.username}",
                description=f"You can't give more than ${cap:,} to this user.",
                color=config.EMBED_COLOR,
            )
        )

    donator.debit_money(amount)
    acceptor.add_money(amount)
    return Message(embed=Embed(description=f"{donator.name} gave ${amount} to {acceptor}", color=config.EMBED_COLOR))


economy_bp.add_autocomplete_handler(amount_all, "give")
