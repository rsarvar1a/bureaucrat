import json

from bureaucrat.models.config import Config
from bureaucrat.models.state import State
from bureaucrat.models.configure import ormar
from bureaucrat.models import games
from bureaucrat.models.games import ActiveGame, Game
from bureaucrat.utility import checks, embeds
from discord import Interaction
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING
from urllib.request import urlretrieve

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat
    from bureaucrat.games import Games


class Configure:

    def __init__(self, parent: "Games") -> None:
        self.bot: "Bureaucrat" = parent.bot
        self.parent = parent

    async def edit(self, interaction: Interaction, *args, **kwargs):
        """
        Edits the configuration dynamically.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return

        if not await self.bot.ensure_privileged(interaction, game):
            return

        config = Config.load(game.config)
        non_null = {k: v for k, v in kwargs.items() if v is not None}
        config.__dict__.update(**non_null)
        game.config = config.dump()

        # Handle this side effect explicitly.
        if "name" in kwargs and kwargs["name"] is not None:
            channel_id = self.parent.get_channel_id(interaction.channel)
            channel = await self.bot.fetch_channel(channel_id)
            await channel.edit(name=kwargs["name"])

        # Handle script updates specifically as well.
        if "script" in kwargs and kwargs["script"] is not None:
            with NamedTemporaryFile() as f:
                try:
                    script_url = self.bot.aws.s3_url(bucket="scripts", key=kwargs["script"], stem="script.json")
                    urlretrieve(script_url, f.name)
                    
                    state = State.load(game.state)
                    state.script = json.load(f)
                    game.state = state.dump()
                except:
                    pass

        await game.update()
        await self.show(interaction)

    async def show(self, interaction: Interaction):
        """
        Shows the configuration.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return

        if not await self.bot.ensure_privileged(interaction, game):
            return

        channel = await self.bot.fetch_channel(game.channel)
        config = Config.load(game.config)
        title = "Game Configuration"
        description = f"id: `{game.id}`\ncreated <t:{int(game.created.timestamp())}:R>\n{repr(config)}"

        await interaction.response.send_message(
            embed=embeds.make_embed(self.bot, title=title, description=description), ephemeral=True
        )
