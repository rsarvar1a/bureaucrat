import json

from bureaucrat.models.config import Config
from bureaucrat.models.state import State
from bureaucrat.models.configure import ormar
from bureaucrat.models import games
from bureaucrat.models.games import ActiveGame, Game
from bureaucrat.utility import checks, embeds
from discord import Interaction
from scriptmaker import Datastore, Script
from tempfile import NamedTemporaryFile, TemporaryDirectory
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
            channel_id = self.bot.get_channel_id(interaction.channel)
            channel = await self.bot.fetch_channel(channel_id)
            await channel.edit(name=kwargs["name"])

        # Handle script updates specifically as well.
        if "script" in kwargs and kwargs["script"] is not None:
            with TemporaryDirectory() as workspace:
                with NamedTemporaryFile() as f:
                    try:
                        script_url = self.bot.aws.s3_url(bucket="scripts", key=kwargs["script"], stem="script.json")
                        urlretrieve(script_url, f.name)
                        script_json = json.load(f)

                        with NamedTemporaryFile() as g:
                            try:
                                nights_url = self.bot.aws.s3_url(bucket="scripts", key=kwargs["script"], stem="nights.json")
                                urlretrieve(nights_url, g.name)
                                nights_json = json.load(g)
                            except:
                                nights_json = None
                        
                        state = State.load(game.state)

                        datastore = Datastore(workspace=workspace)
                        datastore.add_official_characters()
                        script = datastore.load_script(script_json, nights_json)
                        script.finalize()

                        state.script = [{k: v for k, v in script.meta.__dict__.items() if k != "icon"}]
                        for character in script.characters:
                            state.script.append(character.__dict__)
                        state.nights = script.nightorder

                        game.state = state.dump()
                    except Exception as e:
                        self.bot.logger.error(e)

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
