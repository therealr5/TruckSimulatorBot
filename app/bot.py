"Main service file that is loaded into gunicorn"
# pylint: disable=unused-argument
import logging
import sys
import traceback
from os import getenv

import config
from admin import admin_bp
from companies import company_bp
from driving import driving_bp
from economy import economy_bp
from flask import Flask, json, request
from flask_discord_interactions import DiscordInteractions, Message
from flask_discord_interactions.models.component import ActionRow, Button
from flask_discord_interactions.models.embed import Embed, Footer
from gambling import gambling_bp
from guide import guide_bp
from resources import companies, players
from stats import profile_bp
from system import system_bp
from truck import truck_bp
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
discord = DiscordInteractions(app)

app.config["DISCORD_CLIENT_ID"] = getenv("DISCORD_CLIENT_ID", default="")
app.config["DISCORD_PUBLIC_KEY"] = getenv("DISCORD_PUBLIC_KEY", default="")
app.config["DISCORD_CLIENT_SECRET"] = getenv("DISCORD_CLIENT_SECRET", default="")

if "--debug" in sys.argv:
    app.config["DONT_VALIDATE_SIGNATURE"] = True


logger = logging.getLogger()
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
logger.addHandler(console_handler)


@app.errorhandler(players.NotEnoughMoney)
def not_enough_money(error):
    """Error handler in case a player doesn't have enough money"""
    return Message(content="You don't have enough money to do this.", ephemeral=True).dump()


@app.errorhandler(players.WrongPlayer)
def not_driving(error):
    """Defer buttons if the wrong player clicked them"""
    return Message(
        "This isn't your truck. Use <:logo_round:955233759278559273>`/drive` or click the button to hop into your own.",
        ephemeral=True,
        components=[
            ActionRow(
                components=[
                    Button(
                        label="Start driving",
                        style=2,
                        custom_id="initial_drive",
                        emoji={"name": "logo_round", "id": 955233759278559273},
                    )
                ]
            )
        ],
    ).dump()


@app.errorhandler(players.PlayerNotRegistered)
def not_registered(error):
    """Error handler in case a player isn't found in the database"""
    interaction_data = request.json
    author = (
        interaction_data.get("member").get("user").get("id")
        if interaction_data.get("member", None)
        else interaction_data.get("user").get("id")
    )
    if author == error.requested_id:
        content = f"<@{error.requested_id}> You are not registered yet. Click the button below to get started."
        components = [ActionRow(components=[Button(label="Click here to register", custom_id="profile_register")])]
    else:
        content = f"<@{error.requested_id}> is not registered yet. Maybe somebody should tell them to do so."
        components = []

    return Message(
        content=content,
        components=components,
        ephemeral=True,
    ).dump()


@app.errorhandler(companies.CompanyNotFound)
def company_not_found(error):
    """Error handler in case a player's company isn't found in the database"""
    return Message(
        content="You don't have a company at the moment. Get hired or found one.",
        ephemeral=True,
    ).dump()


@app.errorhandler(players.PlayerBlacklisted)
def blacklisted(error: players.PlayerBlacklisted):
    """Error handler in case a player is on the blalist"""
    return Message(
        content=f"<@{error.requested_id}> You are blacklisted for the following reason: {error.reason}", ephemeral=True
    ).dump()


@app.errorhandler(Exception)
def general_error(error):
    """Log any error to journal and to discord"""
    logging.error(error)
    traceback.print_tb(error.__traceback__)
    return Message(
        embed=Embed(
            title="Looks like we got an error here.",
            description=f" ```py\n {error.__class__.__name__}: {error}```",
            footer=Footer(
                text="If this occurs multiple times feel free to report it.",
                icon_url=config.SELF_AVATAR_URL,
            ),
            color=int("ff0000", 16),
        ),
        components=[
            ActionRow(components=[Button(style=5, label="Support Server", url="https://discord.gg/FzAxtGTUhN")])
        ],
    ).dump()


@app.errorhandler(HTTPException)
def handle_exception(error):
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = error.get_response()
    # replace the body with JSON
    response.data = json.dumps(
        {
            "code": error.code,
            "name": error.name,
            "description": error.description,
        }
    )
    response.content_type = "application/json"
    return response


if "--remove-global" in sys.argv:
    discord.update_commands()
    sys.exit()

if "--clear-admin" in sys.argv:
    discord.update_commands(guild_id=config.Guilds.SUPPORT)
    sys.exit()

if "--admin" in sys.argv:
    discord.register_blueprint(admin_bp)
    discord.update_commands(guild_id=config.Guilds.SUPPORT)
    sys.exit()

discord.register_blueprint(system_bp)
discord.register_blueprint(profile_bp)
discord.register_blueprint(driving_bp)
discord.register_blueprint(economy_bp)
discord.register_blueprint(gambling_bp)
discord.register_blueprint(guide_bp)
discord.register_blueprint(truck_bp)
discord.register_blueprint(company_bp)


if "--deploy" in sys.argv:
    discord.update_commands()
    sys.exit()

discord.register_blueprint(admin_bp)


@discord.command()
def complain(ctx) -> str:
    "No description."
    complain_localizations = {
        "en-US": (
            "What a crap bot this is! :rage: "
            "Hours of time wasted on this useless procuct of a terrible coder and a lousy artist "
            ":rage: :rage: Is this bot even TESTED before the updates are published... "
            "Horrible, just HORRIBLE this spawn of incopetence. Who tf made this? A 12 year old child? "
            "This child would probably have made it better than THAT :rage:"
        ),
        "fr": (
            "Mais quel bot de merde ! J'arrive pas ?? croire que j'ai perdu mon temps sur ce truc ridicule. "
            "Le d??veloppeur est pourrave, l'artiste est nulle :rage: :rage:  Est-ce que quelqu'un TESTE les mises ?? "
            "jour avant leur sortie ? Horrible, juste HORRIBLE, pur concentr?? d'incomp??tence. Qui a cr???? cette daube ? "
            "Un gamin de 12 ans ? Franchement un gamin aurait fait MIEUX que cette CHOSE :rage:"
        ),
        "de": (
            "Junge WAS IST DENN DAS F??R EIN SCHMUTZ :rage:. Und damit hab ich jetzt mehrere Tage verbracht :rage:. "
            "Wird das Zeug ??berhaupt getestet bevor es unter die Leute geworfen wird? :rage: Einfach nur schrecklich "
            "diese Ausgeburt der Inkompetenz; Die Spielmechanik macht keinen Sinn, der Dev macht kaum etwas und ??ber "
            "den Zeichner der Bilder wollen wir am besten gar nicht erst reden..."
        ),
    }
    locale = request.get_json().get("locale")
    return complain_localizations[locale] if locale in complain_localizations else complain_localizations["en-US"]


discord.set_route("/interactions")


if __name__ == "__main__":
    app.run(port=9001, debug=True)
