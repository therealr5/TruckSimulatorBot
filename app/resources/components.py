"""
This module provides several lists of buttons and selects
"""
from flask_discord_interactions.models.component import ActionRow, Button, SelectMenu, SelectMenuOption
from resources import companies, items, places, symbols, trucks
from resources.companies import Company
from resources.players import Player


def get_drive_buttons(player: Player) -> list:
    """
    Returns a list of buttons for the drive menu
    :param player: The player to get the buttons for
    :return: A list of buttons
    """
    buttons = []
    directional_buttons = []
    place = places.get(player.position)
    current_job = player.get_job()
    for symbol in symbols.get_all_drive_symbols():
        if symbol in symbols.get_drive_position_symbols(player.position):
            directional_buttons.append(
                Button(
                    style=1
                    if current_job is not None and places.get_direction(player, current_job.target_place) == symbol
                    else 2,
                    emoji={"name": "placeholder", "id": symbol},
                    custom_id=[str(symbol), player.id],
                )
            )
        else:
            directional_buttons.append(
                Button(style=2, emoji={"name": "placeholder", "id": symbol}, custom_id=str(symbol), disabled=True)
            )
    directional_buttons.append(
        Button(style=4, emoji={"name": "stop", "id": symbols.STOP}, custom_id=["stop", player.id])
    )
    buttons.append(ActionRow(components=directional_buttons))

    load_disabled = not len(player.loaded_items) < trucks.get(player.truck_id).loading_capacity
    unload_disabled = not len(player.loaded_items) > 0
    if not place:
        load_disabled = True
        unload_disabled = True

    action_buttons = [
        Button(
            style=1
            if current_job
            and place
            and current_job.state == 0
            and int(place.position) == int(current_job.place_from.position)
            else 2,
            emoji={"name": "load", "id": symbols.LOAD},
            custom_id=["load", player.id],
            disabled=load_disabled,
            label=f"Load your truck with {items.get(place.produced_item).name}" if place else "Load",
        ),
        Button(
            style=1
            if current_job
            and place
            and current_job.state == 1
            and int(place.position) == int(current_job.place_to.position)
            else 2,
            emoji={"name": "unload", "id": symbols.UNLOAD},
            custom_id=["unload", player.id],
            disabled=unload_disabled,
            label="Unload",
        ),
    ]

    if place and "refill" in place.available_actions:
        action_buttons.append(
            Button(
                style=2, label="Refill", emoji={"name": "refill", "id": symbols.REFILL}, custom_id=["refill", player.id]
            )
        )
    if place and "gambling" in place.available_actions:
        action_buttons.append(
            Button(
                style=3,
                label="Enter the casino",
                custom_id=["casino", player.id],
                emoji={"name": "money", "id": items.get(place.produced_item).emoji},
            )
        )

    buttons.append(ActionRow(components=action_buttons))
    buttons.append(
        ActionRow(
            components=[
                Button(
                    style=1 if current_job is None else 2,
                    label="New Job",
                    custom_id=["job_new", player.id],
                    disabled=(current_job is not None),
                ),
                Button(style=2, label="Show Job", custom_id=["job_show", player.id], disabled=(current_job is None)),
                Button(style=3, label="Home", custom_id=["home", player.id]),
            ]
        )
    )

    return buttons


def get_home_buttons(player: Player) -> list:
    """
    Returns a list of buttons for the home menu
    :param player: The player to get the buttons for
    :return: A list of buttons
    """
    return [
        ActionRow(
            components=[
                Button(
                    custom_id=["manage_truck", player.id],
                    style=2,
                    label="Manage your truck",
                    emoji=symbols.parse_emoji(trucks.get(player.truck_id).emoji),
                ),
                Button(
                    custom_id=["manage_company", player.id],
                    style=2,
                    label="Show your company",
                    emoji=symbols.parse_emoji(companies.get(player.company).logo)
                    if player.company
                    else {"name": "???????", "id": None},
                ),
                Button(
                    custom_id=["top", player.id],
                    style=2,
                    label="View the leaderboard",
                    emoji={"name": "????", "id": None},
                ),
            ]
        ),
        ActionRow(
            components=[
                Button(
                    custom_id=["continue_drive", player.id],
                    style=3,
                    label="Back to the road",
                    emoji={"name": "logo_round", "id": "955233759278559273"},
                ),
            ]
        ),
    ]


def get_company_buttons(player: Player, company: Company) -> list:
    """
    Returns a list of buttons for the company menu
    :param player: The player to get the buttons for
    :param company: The company to get the buttons for
    :return: A list of buttons
    """
    components = [
        ActionRow(
            components=[
                Button(
                    label="Update",
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
            ]
        ),
        ActionRow(
            components=[
                Button(
                    style=2,
                    label="Back",
                    custom_id=["home", player.id],
                ),
            ]
        ),
    ]
    company_members = company.get_members()
    if len(company_members) > 1:
        components.insert(
            1,
            ActionRow(
                components=[
                    SelectMenu(
                        placeholder="Select a member to fire",
                        custom_id=["company_fire", player.id],
                        options=[
                            SelectMenuOption(label=f"{plr.name}#{plr.discriminator}", value=plr.id)
                            for plr in company.get_members()
                            if plr.id != player.id
                        ],
                        disabled=(player.id != company.founder),
                    )
                ]
            ),
        )
    return components


def get_truck_components(player: Player) -> list:
    """
    Returns a list of buttons for the truck menu
    :param player: The player to get the buttons for
    :return: A list of buttons
    """
    return [
        ActionRow(
            components=[
                SelectMenu(
                    custom_id=["truck_view", player.id],
                    options=get_truck_options(player),
                    placeholder="View details about a truck",
                )
            ]
        ),
        ActionRow(
            components=[
                SelectMenu(
                    custom_id=["truck_buy", player.id],
                    options=get_truck_options(player, check_money=True),
                    placeholder="Buy a new truck",
                ),
            ]
        ),
        ActionRow(
            components=[
                Button(custom_id=["home", player.id], label="Back", style=2),
            ]
        ),
    ]


def get_truck_options(player, check_money=False) -> list[SelectMenuOption]:
    """Returns choices shown up in several truck commands"""
    choices = []
    for truck in trucks.get_all():
        if check_money:
            if player.money < truck.price:
                continue
        choices.append(
            SelectMenuOption(
                label=truck.name,
                description=truck.description,
                value=str(truck.truck_id),
                emoji=symbols.parse_emoji(truck.emoji),
            )
        )
    return choices


def get_casino_buttons(player) -> list:
    """
    Returns a list of buttons for the casino menu
    :param player: The player to get the buttons for
    :return: A list of buttons
    """
    return [
        ActionRow(
            components=[
                Button(
                    custom_id=["slots_init", player.id],
                    style=2,
                    label="Spin a slot machine",
                    emoji={"name": "????", "id": None},
                ),
                Button(
                    custom_id=["blackjack", player.id],
                    style=2,
                    label="Coming soon",
                    emoji={"name": "??????", "id": None},
                    disabled=True,
                ),
            ]
        ),
        ActionRow(
            components=[
                Button(
                    custom_id=["continue_drive", player.id],
                    style=3,
                    label="Back to the road",
                    emoji={"name": "logo_round", "id": "955233759278559273"},
                ),
            ]
        ),
    ]
