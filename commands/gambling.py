"""
Tis module contains the Cog for all gambling-related commands
"""
from random import randint, sample, choices
import discord

from discord.ext import commands

import players
import places
import items


class Gambling(commands.Cog):
    """
    Lose your money here
    """

    @commands.command(aliases=["cf"])
    async def coinflip(self, ctx, side=None, amount=None) -> None:
        """
        Test your luck while throwing a coin
        """
        player = players.get(ctx.author.id)
        if "coinflip" not in places.get(player.position).commands:
            raise places.WrongPlaceError("We are not in Las Vegas!!!")
        try:
            if amount == "all":
                amount = player.money
            elif amount == "half":
                amount = round(player.money / 2)
            else:
                amount = int(amount)

            if str.lower(side) not in ["h", "head", "t", "tails"]:
                await ctx.channel.send("**Syntax:** `t.coinflip [h/t] <amount>`")
                return

            if side == "h":
                side = "heads"
            elif side == "t":
                side = "tails"
            players.debit_money(player, amount)
            if randint(0, 1) == 0:
                result = "heads"
            else:
                result = "tails"

            if result == side:
                await ctx.channel.send("Congratulations, it was {}. You won ${}".format(result, "{:,}".format(amount)))
                players.add_money(player, amount*2)
            else:
                await ctx.channel.send("Nope, it was {}. You lost ${}".format(result, "{:,}".format(amount)))
        except (TypeError, ValueError):
            await ctx.channel.send("**Syntax:** `t.coinflip [h/t] <amount>`")

    @commands.command()
    async def slots(self, ctx, amount=None) -> None:
        """
        SLOTS SLOTS SLOTS
        """
        player = players.get(ctx.author.id)
        if "slots" not in places.get(player.position).commands:
            raise places.WrongPlaceError("We are not in Las Vegas!!!")
        try:
            if amount == "all":
                amount = player.money
            elif amount == "half":
                amount = round(player.money / 2)
            else:
                amount = int(amount)
            players.debit_money(player, amount)

            chosen_items = choices(sample(items.get_all(), 8), k=3)
            machine = "<|"
            for item in chosen_items:
                machine += item.emoji
                machine += "|"
            machine += ">"

            slots_embed = discord.Embed(description=machine, colour=discord.Colour.gold())
            slots_embed.set_author(name=f"{ctx.author.name}'s slots", icon_url=ctx.author.avatar_url)

            if chosen_items.count(chosen_items[0]) == 3:
                slots_embed.add_field(name="Result", value=":tada: Congratulations, you won {:,} :tada:".format(amount*10))
                players.add_money(player, amount*11)
            elif chosen_items.count(chosen_items[0]) == 2 or chosen_items.count(chosen_items[1]) == 2: 
                slots_embed.add_field(name="Result", value="You won ${:,}".format(amount))
                players.add_money(player, amount*2)
            else:
                slots_embed.add_field(name="Result", value="You lost ${:,}".format(amount))

            await ctx.channel.send(embed=slots_embed)

        except (TypeError, ValueError):
            await ctx.channel.send("**Syntax:** `t.slots <amount>`")
