"Blueprint file containing all company-related commands and handlers"
# pylint: disable=unused-argument
import re

from flask_discord_interactions import DiscordInteractionsBlueprint, Message, Embed, User, ApplicationCommandType, Modal
from flask_discord_interactions.models.component import (
    ActionRow,
    Button,
    Component,
    TextInput,
)
from flask_discord_interactions.models.embed import Author, Field, Footer, Media

import config

from resources import players
from resources import places
from resources import companies

company_bp = DiscordInteractionsBlueprint()


def get_company_embed(user, player, company) -> Embed:
    """Returns an embed with the company details"""
    founder = players.get(company.founder)
    company_embed = Embed(
        title=company.name,
        color=config.EMBED_COLOR,
        description=company.description,
        author=Author(name=f"{player.name}'s company", icon_url=user.avatar_url),
        footer=Footer(text=f"Founded by {founder.name}"),
        fields=[],
    )
    logo_is_discord_emoji = re.match(r"<(a?):\w*:(\d+)>", company.logo)
    if logo_is_discord_emoji:
        logo_animated = logo_is_discord_emoji.groups()[0] == "a"
        logo_id = logo_is_discord_emoji.groups()[1]
        company_embed.thumbnail = Media(
            url=f"https://cdn.discordapp.com/emojis/{logo_id}.{'gif' if logo_animated else 'png'}"
        )

    company_embed.fields.append(Field(name="Headquarters position", value=str(company.hq_position)))
    company_embed.fields.append(Field(name="Net worth", value=f"${company.net_worth}", inline=False))
    company_members = company.get_members()
    members = ""
    for member in company_members:
        members += f"{member} \n"
    company_embed.fields.append(Field(name=f"Members ({len(company_members)}/25)", value=members, inline=False))
    return company_embed


def get_company_components(player, company) -> list[Component]:
    """Returns the buttons to manage a company"""
    return [
        ActionRow(
            components=[
                Button(
                    label="Manage",
                    custom_id=["company_update", player.id],
                    style=1,
                    disabled=(player.id != company.founder),
                ),
                Button(
                    label="Leave",
                    custom_id=["company_leave", player.id],
                    style=4,
                    disabled=(player.id == company.founder),
                ),
                Button(custom_id=["discard", player.id], label="Close Menu", style=2),
            ]
        )
    ]


@company_bp.custom_handler(custom_id="cancel_company_action")
def cancel(ctx, player_id: str):
    """Cancel hire and fire"""
    if ctx.author.id != player_id:
        raise players.WrongPlayer()
    return Message(content=ctx.message.content, embeds=ctx.message.embeds, components=[], update=True)


@company_bp.custom_handler(custom_id="company_main")
def back(ctx, player_id: str):
    """Shows the main buttons again"""
    player = players.get(ctx.author.id, check=player_id)
    company = companies.get(player.company)
    return Message(
        embed=get_company_embed(ctx.author, player, company),
        components=get_company_components(player, company),
        update=True,
    )


@company_bp.custom_handler(custom_id="company_found")
def found(ctx, player_id: str):
    """Returns a modal to found a company"""
    player = players.get(ctx.author.id, check=player_id)
    if player.company is not None:
        return Message("You already have a company. You can't found another one!", ephemeral=True)
    if player.position in [p.position for p in places.get_all()] or player.position in [
        c.hq_position for c in companies.get_all()
    ]:
        return Message("You can't found a company on this position, please drive to an empty field.", ephemeral=True)

    return Modal(
        custom_id="modal_company_found",
        title="Found a company",
        components=[
            ActionRow(
                [
                    TextInput(
                        custom_id="modal_company_found_name",
                        label="Name",
                        placeholder="Your company's name.",
                        min_length=3,
                        max_length=256,
                    )
                ]
            ),
            ActionRow(
                [
                    TextInput(
                        custom_id="modal_company_found_description",
                        label="Description",
                        placeholder="Describe your company",
                        style=2,
                        required=False,
                        max_length=1000,
                    )
                ]
            ),
        ],
    )


@company_bp.custom_handler(custom_id="modal_company_found")
def confirm_found(ctx):
    """Modal handler for the company founding"""
    name = ctx.get_component("modal_company_found_name").value
    description = ctx.get_component("modal_company_found_description").value

    if companies.exists(name):
        return Message("A company with this make already exists, please choose another name", ephemeral=True)
    player = players.get(ctx.author.id)
    company = companies.Company(name, player.position, ctx.author.id, description=description)
    companies.insert(company)
    players.update(player, company=name)
    return Message(
        embed=Embed(
            title="Company creation successful",
            description=f"{company.logo} **{company.name}** has been created and placed in the market. "
            f"Your company's headquarters have been built at {company.hq_position}.",
            color=config.EMBED_COLOR,
        ),
        components=[ActionRow(components=[Button(label="Check it out", custom_id=["company_main", player.id])])],
        update=True,
    )


@company_bp.command(name="Hire", type=ApplicationCommandType.USER)
def hire(ctx, user: User):
    """Context menu command to hire a player"""
    player = players.get(ctx.author.id)
    invited_player = players.get(user.id)
    company = companies.get(player.company)
    if len(company.get_members()) > 24:
        return Message("Your company can't have more than 25 members!", ephemeral=True)
    if ctx.author.id != company.founder:
        return Message("You are not the company founder!", ephemeral=True)
    if invited_player.company is not None:
        return Message(f"**{invited_player.name}** already is member of a company.", ephemeral=True)

    confirm_buttons: list[Component] = [
        ActionRow(
            components=[
                Button(style=2, label="Cancel", custom_id=["cancel_company_action", invited_player.id]),
                Button(style=3, label="Confirm", custom_id=["confirm_company_hire", company.name, invited_player.id]),
            ]
        )
    ]
    return Message(
        f"<@{invited_player.id}> **{player.name}** wants to hire you for their company. "
        f"Please confirm that you want to work for {company.logo} **{company.name}**",
        components=confirm_buttons,
    )


@company_bp.custom_handler(custom_id="confirm_company_hire")
def confirm_hire(ctx, company: str, player_id: str):
    """Confirm button the hired player has to click"""
    invited_player = players.get(ctx.author.id, check=player_id)

    players.update(invited_player, company=company)
    return Message(
        f"It's official! **{invited_player.name}** is now a member of **{company}** <:PandaHappy:869202868555624478>",
        components=[],
        update=True,
    )


@company_bp.command(name="Fire", type=ApplicationCommandType.USER)
def fire(ctx, user: User):
    """Context menu command to fire a player"""
    player = players.get(ctx.author.id)
    fired_player = players.get(user.id)
    company = companies.get(player.company)
    if ctx.author.id == user.id:
        return Message("You can't fire yourself!", ephemeral=True)
    if ctx.author.id != company.founder:
        return Message("You are not the company founder!", ephemeral=True)
    if fired_player.company != company.name:
        return Message(f"**{fired_player.name}** is not a member of your company.", ephemeral=True)

    confirm_buttons: list[Component] = [
        ActionRow(
            components=[
                Button(style=2, label="Cancel", custom_id=["cancel_company_action", player.id]),
                Button(
                    style=4,
                    label="Confirm",
                    custom_id=["confirm_company_fire", company.name, player.id, fired_player.id],
                ),
            ]
        )
    ]
    return Message(f"Are you sure you want to fire {fired_player.name}?", components=confirm_buttons)


@company_bp.custom_handler(custom_id="confirm_company_fire")
def confirm_fire(ctx, company: str, player_id: str, fired_player_id: str):
    """Confirm button for the company owner"""
    if ctx.author.id != player_id:
        raise players.WrongPlayer()
    fired_player = players.get(fired_player_id)
    fired_player.remove_from_company()
    return Message(content=f"**{fired_player.name}** was removed from **{company}**", update=True, components=[])


@company_bp.custom_handler(custom_id="company_leave")
def leave(ctx, player_id: str):
    """Leave your company"""
    if ctx.author.id != player_id:
        raise players.WrongPlayer()
    confirm_buttons: list[Component] = [
        ActionRow(
            components=[
                Button(style=2, label="Cancel", custom_id=["cancel_company_action", ctx.author.id]),
                Button(style=4, label="Confirm", custom_id=["confirm_company_leave", ctx.author.id]),
            ]
        )
    ]
    return Message("Are you sure that you want to leave your company?", components=confirm_buttons)


@company_bp.custom_handler(custom_id="confirm_company_leave")
def confirm_leave(ctx, player_id: str):
    """Confirm button to leave a company"""
    player = players.get(ctx.author.id, check=player_id)
    player.remove_from_company()
    return Message(f"<@{player.id}> You left **{player.company}**", components=[], update=True)


@company_bp.custom_handler(custom_id="company_update")
def company_update(ctx, player_id: str):
    """A button handler that promts a select to select the options than should be changed"""
    player = players.get(ctx.author.id, check=player_id)
    company = companies.get(player.company)
    if ctx.author.id != company.founder:
        return "You are not the company founder!"

    return Modal(
        custom_id="modal_company_update",
        title="Update your company",
        components=[
            ActionRow(
                [
                    TextInput(
                        custom_id="modal_company_update_name",
                        label="Name",
                        placeholder="Your company's name, must start with a letter",
                        min_length=3,
                        max_length=256,
                        value=company.name,
                    )
                ]
            ),
            ActionRow(
                [
                    TextInput(
                        custom_id="modal_company_update_description",
                        label="Description",
                        placeholder="Describe your company",
                        style=2,
                        required=False,
                        value=company.description,
                        max_length=1000,
                    )
                ]
            ),
            ActionRow(
                [
                    TextInput(
                        custom_id="modal_company_update_logo",
                        label="Logo (empty to reset)",
                        placeholder="Your company's logo, must be an emoji",
                        min_length=1,
                        max_length=256,
                        value=company.logo,
                        required=False,
                    )
                ]
            ),
        ],
    )


@company_bp.custom_handler(custom_id="modal_company_update")
def update(ctx):
    """Update a company's attributes"""
    player = players.get(ctx.author.id)
    company = companies.get(player.company)
    name: str = ctx.get_component("modal_company_update_name").value
    description: str = ctx.get_component("modal_company_update_description").value
    logo: str = ctx.get_component("modal_company_update_logo").value
    if name != company.name and companies.exists(name):
        return Message("A company with this make already exists, please choose another name", ephemeral=True)
    companies.update(company, name=name, description=description)
    if logo == "":
        logo = "🏛️"
    if not re.match(
        # did I mention that I love regex?
        # match any emoji
        r"^([\u2600-\u26ff]|[\U0001f000-\U0001faff])|<a*:\w*:\d+>$",
        logo,
    ):
        return Message("The provided logo couldn't be matched as an emoji", ephemeral=True)
    companies.update(company, logo=logo)
    return Message(
        embed=get_company_embed(ctx.author, player, company),
        components=get_company_components(player, company),
        update=True,
    )


@company_bp.command(name="company", annotations={"user": "A user whose company you want to view"})
def company_show(ctx):
    """Manages your company."""

    player = players.get(ctx.author.id)
    try:
        company = companies.get(player.company)
    except companies.CompanyNotFound:
        return Message(
            "You are not member of a company at the moment",
            components=(
                [ActionRow(components=[Button(label="Found one", custom_id=["company_found", player.id])])]
                if player.truck_id > 0
                else []
            ),
        )
    return Message(
        embed=get_company_embed(ctx.author, player, company),
        components=get_company_components(player, company),
    )


@company_bp.command(name="Show company", type=ApplicationCommandType.USER)
def show_company(ctx, user: User):
    """Context menu command to view a user's company"""
    player = players.get(user.id)
    try:
        company = companies.get(player.company)
    except companies.CompanyNotFound:
        return Message(content=f"**{user.username}** is not member of a company at the moment", ephemeral=True)
    return Message(embed=get_company_embed(user, player, company), ephemeral=True)
