"""
Some nice autocomplete handlers that are used everywhere
"""

from i18n import set as set_i18n
from i18n import t
from flask_discord_interactions.models.option import Choice
from resources import players


def amount_all(ctx, *args):
    """Some enhancements for int options"""
    set_i18n("locale", ctx.locale)
    player = players.get(ctx.author.id)
    amount = None
    for option in args:
        if option.name == "amount":
            amount = option
    lst = []
    if not amount:
        return []
    if len(amount.value) == 0 or amount.value in "all":
        lst.append(Choice(name=t("autocomplete.all"), value=player.money))
    if len(amount.value) == 0 or amount.value in "half":
        lst.append(Choice(name=t("autocomplete.half"), value=round(player.money / 2)))
    if amount.value.isnumeric() and player.money >= int(amount.value):
        lst.append(Choice(name=amount.value, value=int(amount.value)))
    if amount.value.isnumeric() and player.money >= int(amount.value) * 1000:
        lst.append(Choice(name=t("autocomplete.thousand", amount=amount.value), value=int(amount.value) * 1000))
    if amount.value.isnumeric() and player.money >= int(amount.value) * 1000000:
        lst.append(Choice(name=t("autocomplete.million", amount=amount.value), value=int(amount.value) * 1000000))

    return lst
