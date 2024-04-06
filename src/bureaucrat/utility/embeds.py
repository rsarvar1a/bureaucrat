from datetime import datetime
from discord import Embed
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


def make_base_embed(bot: "Bureaucrat"):
    return Embed(timestamp=datetime.now()).set_footer(text="Bureaucrat", icon_url=bot.user.avatar.url)


def make_embed(bot: "Bureaucrat", title=None, description=None, image=None, thumb=None):
    embed = make_base_embed(bot)
    embed.title = title
    embed.description = description
    embed.set_image(url=image)
    embed.set_thumbnail(url=thumb)
    return embed


def make_error(bot: "Bureaucrat", *, message: str | None = None, error: Exception | None = None):
    embed = make_base_embed(bot)
    embed.title = "Something went wrong..."
    codeblock = f"\n```\n{error}\n```" if error is not None else ""
    message = message if message else ""
    embed.description = f"{message}{codeblock}"
    return embed


def unauthorized(bot: "Bureaucrat", message: str):
    embed = make_base_embed(bot)
    embed.title = "Sorry, you can't do that."
    embed.description = message
    return embed


def guild_only(bot: "Bureaucrat"):
    return unauthorized(bot, "You must run this command inside a server.")
