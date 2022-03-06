# pylint: disable=unused-argument
from flask_discord_interactions import DiscordInteractionsBlueprint, Message, Embed
from flask_discord_interactions.models.embed import Field

import config
from resources import players

misc_bp = DiscordInteractionsBlueprint()


@misc_bp.command()
def rules(ctx) -> Message:
    """Shows the rules for this bot."""
    rules_embed = Embed(title="Truck Simulator Ingame Rules", color=config.EMBED_COLOR, fields=[])
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
    return Message(embed=rules_embed)


@misc_bp.command()
def vote(ctx) -> Message:
    """Support the bot by voting for it on top.gg."""
    player = players.get(ctx.author.id)
    vote_embed = Embed(
        title="Click here to vote for the Truck Simulator",
        description="As a reward, you will get double xp for 30 minutes.",
        url="https://top.gg/bot/831052837353816066/vote",
        color=config.EMBED_COLOR,
        fields=[Field(name="Your last vote", value=f"<t:{player.last_vote}:R>")],
    )
    return Message(embed=vote_embed)
