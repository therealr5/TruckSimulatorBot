"Blueprint file containing all driving-related commands and handlers"
# pylint: disable=missing-function-docstring
import threading
from datetime import datetime
from random import randint

import config
import requests
from flask_discord_interactions import DiscordInteractionsBlueprint, Embed, Message
from flask_discord_interactions.context import Context
from flask_discord_interactions.models.component import ActionRow, Button, SelectMenu, SelectMenuOption
from flask_discord_interactions.models.embed import Author, Field, Footer, Media
from resources import assets, companies, components, items, jobs, levels, places, players, symbols, trucks
from resources.position import Position
from utils import log_command

driving_bp = DiscordInteractionsBlueprint()


def get_drive_embeds(player: players.Player, avatar_url: str) -> list:
    """Returns the drive embed that includes all the information about the current position and gas"""
    place = places.get(player.position)
    all_companies = companies.get_all()
    image_embed = Embed(color=config.EMBED_COLOR)
    drive_embed = Embed(
        color=config.EMBED_COLOR,
        timestamp=datetime.utcnow().replace(microsecond=0).isoformat(),
        author=Author(name=f"{player.name} is driving", icon_url=avatar_url),
        footer=Footer(text=f"Loaded items: {len(player.loaded_items)}/{trucks.get(player.truck_id).loading_capacity}"),
        fields=[],
    )

    drive_embed.fields.append(Field(name="Minimap", value=generate_minimap(player, all_companies), inline=False))
    drive_embed.fields.append(Field(name="Position", value=str(player.position)))
    drive_embed.fields.append(
        Field(name="Gas left", value=f"{player.gas} l" if player.gas > 100 else f"{player.gas} l :warning:")
    )

    current_job = player.get_job()
    if current_job is not None:
        navigation_place = current_job.target_place
        drive_embed.fields.append(
            Field(
                name=f"Navigation: Drive to {navigation_place}",
                value=f"<:n:{places.get_direction(player, navigation_place)}>",
            )
        )

    if place is not None:
        drive_embed.fields.append(
            Field(
                name="What is here?",
                value=f"<:i:{items.get(place.produced_item).emoji}> {place}",
                inline=False,
            )
        )
        image_embed.image = Media(url=assets.get_place_image(player, place))
    else:
        image_embed.image = Media(url=assets.get_default(player))
    drive_embed.image = Media(
        url="https://cdn.discordapp.com/attachments/965229095447306240/965229146873675786/transparent.png"
    )
    if int(player.position) in [int(c.hq_position) for c in all_companies]:
        for company in all_companies:
            if int(company.hq_position) == int(player.position):
                drive_embed.fields.append(
                    Field(
                        name="What is here?",
                        value=f"A company called {company.logo} **{company}**",
                        inline=False,
                    )
                )
    return [image_embed, drive_embed]


def generate_minimap(player: players.Player, all_companies: list[companies.Company]) -> str:
    """Generate the minimap shown in /drive"""
    minimap_array = []
    for i in range(0, 7):
        minimap_array.append([])
        for j in range(0, 7):
            minimap_array[i].append("")
            position = Position(player.position.x - 3 + j, player.position.y + 3 - i)
            map_place = places.get(position)
            # show other trucks on the map
            if map_place:
                minimap_array[i][j] = f"<:i:{items.get(map_place.produced_item).emoji}>"
            elif int(position) in [int(c.hq_position) for c in all_companies]:
                for company in all_companies:
                    if int(company.hq_position) == int(position):
                        minimap_array[i][j] = company.logo
            elif position.x in [-1, config.MAP_BORDER + 1] or position.y in [-1, config.MAP_BORDER + 1]:
                # Mark the map border with symbols
                minimap_array[i][j] = ":small_orange_diamond:"
                if (
                    # Small correction mechanism to prevent the lines from going beyond the border
                    position.x < -1
                    or position.x > config.MAP_BORDER + 1
                    or position.y < -1
                    or position.y > config.MAP_BORDER + 1
                ):
                    minimap_array[i][j] = symbols.MAP_BACKGROUND
            else:
                minimap_array[i][j] = symbols.MAP_BACKGROUND

    minimap_array[3][3] = trucks.get(player.truck_id).emoji
    minimap = ""
    for i in range(0, 7):
        for j in range(0, 7):
            minimap = minimap + minimap_array[i][j]
        minimap = minimap + "\n"
    return minimap


@driving_bp.custom_handler(custom_id="stop")
def stop(ctx: Context, player_id: str):
    player = players.get(ctx.author.id, check=player_id)
    return Message(
        embeds=get_drive_embeds(player, ctx.author.avatar_url),
        components=[],
        update=True,
    )


@driving_bp.custom_handler(custom_id="load")
def load(ctx: Context, player_id: str):
    player = players.get(ctx.author.id, check=player_id)

    item = items.get(places.get(player.position).produced_item)
    if item.name not in [i.name for i in player.loaded_items]:
        player.load_item(item)
    job_message = None

    current_job = player.get_job()
    if current_job is not None and item.name == current_job.place_from.produced_item:
        current_job.state = jobs.STATE_LOADED
        job_message = jobs.get_state(current_job)
        player.update_job(current_job, state=current_job.state)

    drive_embeds = get_drive_embeds(player, ctx.author.avatar_url)
    drive_embeds[1].fields.append(
        Field(
            name="Loading successful",
            value=f"You loaded {item} into your truck",
            inline=False,
        )
    )
    if job_message is not None:
        return Message(
            embeds=drive_embeds
            + [
                Embed(title="Job Notification", description=job_message, color=config.EMBED_COLOR),
            ],
            components=components.get_drive_buttons(player),
            update=True,
        )
    return Message(embeds=drive_embeds, components=components.get_drive_buttons(player), update=True)


@driving_bp.custom_handler(custom_id="unload")
def unload(ctx: Context, player_id: str):
    player = players.get(ctx.author.id, check=player_id)
    current_job = player.get_job()

    item_options: list[SelectMenuOption] = []
    for item in player.loaded_items:
        if item.name not in [o.value for o in item_options]:
            item_options.append(
                SelectMenuOption(
                    label=f"{item.name} (Required for your job)"
                    if current_job is not None and item.name == current_job.place_from.produced_item
                    else item.name,
                    value=item.name,
                    emoji={"name": item.name, "id": item.emoji},
                )
            )
    select = SelectMenu(
        custom_id=["unload_items", player.id],
        placeholder="Choose which items to unload",
        options=item_options,
        min_values=1,
        max_values=len(item_options),
    )
    cancel_button = Button(custom_id=["cancel", player.id], label="Cancel", style=4)
    return Message(
        embeds=get_drive_embeds(player, ctx.author.avatar_url),
        components=[ActionRow(components=[select]), ActionRow(components=[cancel_button])],
        update=True,
    )


@driving_bp.custom_handler(custom_id="unload_items")
def unload_items(ctx: Context, player_id: str):
    player = players.get(ctx.author.id, check=player_id)

    item_string = ""
    for name in ctx.values:
        item = items.get(name)
        player.unload_item(item)
        if name == ctx.values[0]:
            item_string += str(item)
        elif name == ctx.values[-1]:
            item_string += " and " + str(item)
        else:
            item_string += ", " + str(item)

    place = places.get(player.position)
    current_job = player.get_job()
    drive_embeds = get_drive_embeds(player, ctx.author.avatar_url)

    drive_embeds[1].fields.append(
        Field(name="Unloading successful", value=f"You removed {item_string} from your truck", inline=False)
    )

    # add a notification embed if a job is done
    if (
        current_job is not None
        and current_job.place_from.produced_item in ctx.values
        and int(player.position) == int(current_job.place_to.position)
    ):
        current_job.state = jobs.STATE_DONE
        player.add_money(current_job.reward)
        player.remove_job(current_job)
        job_message = jobs.get_state(current_job) + player.add_xp(levels.get_job_reward_xp(player.level))
        if player.company is not None:
            company = companies.get(player.company)
            company.add_net_worth(int(current_job.reward / 10))
            job_message += f"\nYour company's net worth was increased by ${int(current_job.reward/10):,}"
        # get the drive embed egain to fit the job update
        drive_embeds = get_drive_embeds(player, ctx.author.avatar_url)
        drive_embeds[1].fields.append(
            Field(name="Unloading successful", value=f"You removed {item_string} from your truck", inline=False)
        )
        drive_embeds.append(
            Embed(title="Job Notification", description=job_message, color=config.EMBED_COLOR),
        )

    # add a notification embed if a minijob is done
    if place.accepted_item in ctx.values and place.item_reward:
        player.add_money(place.item_reward)
        drive_embeds.append(
            Embed(
                title="Minijob Notification",
                description=(
                    f"{place} gave you ${place.item_reward * (player.level + 1):,} for bringing them "
                    f"{place.accepted_item}"
                ),
                color=config.EMBED_COLOR,
            )
        )

    return Message(embeds=drive_embeds, components=components.get_drive_buttons(player), update=True)


@driving_bp.custom_handler(custom_id="job_new")
def new_job(ctx: Context, player_id: str) -> Message:
    player = players.get(ctx.author.id, check=player_id)
    job_embed = Embed(
        color=config.EMBED_COLOR,
        author=Author(name=f"{player.name}'s Job", icon_url=ctx.author.avatar_url),
        fields=[],
    )
    job = jobs.generate(player)
    player.add_job(job)

    item = items.get(job.place_from.produced_item)
    job_message = f"{job.place_to} needs {item} from {job.place_from}. You get ${job.reward:,} for this transport"
    job_embed.fields.append(Field(name="You got a new Job", value=job_message, inline=False))
    job_embed.fields.append(Field(name="Current state", value=jobs.get_state(job)))
    return Message(
        embeds=get_drive_embeds(player, ctx.author.avatar_url) + [job_embed],
        components=components.get_drive_buttons(player),
        update=True,
    )


@driving_bp.custom_handler(custom_id="cancel")
def cancel(ctx: Context, player_id: str):
    player = players.get(ctx.author.id, check=player_id)
    return Message(
        embeds=get_drive_embeds(player, ctx.author.avatar_url),
        components=components.get_drive_buttons(player),
        update=True,
    )


@driving_bp.custom_handler(custom_id=str(symbols.LEFT))
def left(ctx: Context, player_id: str):
    return move(ctx, symbols.LEFT, player_id)


@driving_bp.custom_handler(custom_id=str(symbols.UP))
def up(ctx: Context, player_id: str):
    return move(ctx, symbols.UP, player_id)


@driving_bp.custom_handler(custom_id=str(symbols.DOWN))
def down(ctx: Context, player_id: str):
    return move(ctx, symbols.DOWN, player_id)


@driving_bp.custom_handler(custom_id=str(symbols.RIGHT))
def right(ctx: Context, player_id: str):
    return move(ctx, symbols.RIGHT, player_id)


def move(ctx: Context, direction, player_id):
    """Centralized function for all the directional buttons"""
    player = players.get(ctx.author.id, check=player_id)

    new_position = player.position
    if direction == symbols.LEFT:
        new_position.x -= 1

    if direction == symbols.UP:
        new_position.y += 1

    if direction == symbols.DOWN:
        new_position.y -= 1

    if direction == symbols.RIGHT:
        new_position.x += 1

    player.miles += 1
    player.truck_miles += 1
    player.gas -= trucks.get(player.truck_id).gas_consumption
    player.position = new_position

    if player.gas <= 0:
        return Message(
            content=(
                "You messed up and ran out of gas. What do you want to do?\n\n"
                "`Hitchhike` You are trying to hitchhike someone and get to the city.\n"
                "`Walk` You walk to the gas station. But while doing so, you will lose a level.\n"
                "`Try to rob some gas` Someone left their car over there. Go steal some gas from them."
            ),
            components=[
                ActionRow(
                    components=[
                        Button(label="Hitchhike", custom_id=["event_hitchhike", ctx.author.id], style=2),
                        Button(label="Walk", custom_id=["event_walk", ctx.author.id], style=2),
                        Button(label="Rob some gas", custom_id=["event_rob", ctx.author.id], style=2),
                    ]
                )
            ],
            update=True,
        )

    return Message(
        embeds=get_drive_embeds(player, ctx.author.avatar_url),
        components=components.get_drive_buttons(player),
        update=True,
    )


@driving_bp.custom_handler(custom_id="event_hitchhike")
def event_hitchhike(ctx: Context, player_id: str) -> Message:
    player = players.get(ctx.author.id, check=player_id)
    try:
        player.debit_money(3000)
    except players.NotEnoughMoney:
        pass
    if randint(0, 1) == 0:
        return Message(
            (
                "Someone stopped to take you with them, but.. **OH NO!** It's Mr. Thomas Ruck, the president of this "
                "country. He had to have your truck towed away and you will pay $3000 for this incident."
            ),
            components=[components.get_home_buttons(player)[1]],
            update=True,
        )
    player.gas = 140
    player.position = Position.from_int(458759)
    return Message(
        "You found someone to go with. They even were so kind to gift you some gas. You should thank them.",
        components=[components.get_home_buttons(player)[1]],
        update=True,
    )


@driving_bp.custom_handler(custom_id="event_walk")
def event_walk(ctx: Context, player_id: str) -> Message:
    player = players.get(ctx.author.id, check=player_id)
    if player.level > 0:
        player.level -= 1
        player.xp = 0
        player.position = Position.from_int(458759)
    return Message(
        "You started walking to the gas station. As you arrived, you noticed that you lost a level.",
        components=[components.get_home_buttons(player)[1]],
        update=True,
    )


@driving_bp.custom_handler(custom_id="event_rob")
def event_rob(ctx: Context, player_id: str) -> Message:
    player = players.get(ctx.author.id, check=player_id)
    if randint(0, 1) == 0:
        player.gas += 250
        return Message(
            "Phew. Nobdody looked and you stole some gas. Be careful next time.",
            components=[components.get_home_buttons(player)[1]],
            update=True,
        )
    return Message(
        "Oh no! You got caught. Nothing happened but the car owner drove away angrily.",
        components=[components.get_home_buttons(player)[1]],
        update=True,
    )


@driving_bp.custom_handler(custom_id="continue_drive")
def continue_drive(ctx: Context, player_id: str):
    player = players.get(ctx.author.id, check=player_id)
    return Message(
        embeds=get_drive_embeds(player, ctx.author.avatar_url),
        components=components.get_drive_buttons(player),
        update=True,
    )


@driving_bp.custom_handler(custom_id="initial_drive")
def initial_drive(ctx: Context, player_id: str = None):
    if player_id:
        player = players.get(ctx.author.id, check=player_id)
    else:
        player = players.get(ctx.author.id)

    def start_drive():
        requests.post(
            ctx.followup_url(),
            json=Message(
                embeds=get_drive_embeds(player, ctx.author.avatar_url),
                components=components.get_drive_buttons(player),
            ).dump_followup(),
        ).raise_for_status()

    threading.Thread(target=start_drive).start()
    return Message(content=ctx.message.content, embeds=ctx.message.embeds, components=[], update=True)


@driving_bp.command()
def drive(ctx: Context) -> Message:
    """Starts the game."""
    log_command(ctx)
    player = players.get(ctx.author.id)
    # Detect, when the player is renamed
    if player.name != ctx.author.username:
        player.name = ctx.author.username
    if player.discriminator != ctx.author.discriminator:
        player.discriminator = ctx.author.discriminator

    return Message(
        embeds=get_drive_embeds(player, ctx.author.avatar_url),
        components=components.get_drive_buttons(player),
    )
