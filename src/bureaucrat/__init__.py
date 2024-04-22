import logging
import tomllib

from bureaucrat import admin, archives, feedback, games, models, nominations, phases, reminders, scripts, seating, threads
from bureaucrat.models.games import ActiveCategory, ActiveGame, Game, Participant, RoleType
from bureaucrat.utility import aws, logging, embeds
from discord import AllowedMentions, Intents, Interaction, Thread
from discord.abc import GuildChannel
from discord.ext.commands import DefaultHelpCommand
from discord.ext.commands.bot import Bot
from dotmap import DotMap
from typing import List, Optional


class Config:

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)

    @classmethod 
    def load(cls, path):
        with open(path, "rb") as toml_file:
            obj = tomllib.load(toml_file)
        return Config(**obj)


class Bureaucrat(Bot):

    COG_MODULES = (admin, archives, feedback, games, nominations, phases, reminders, scripts, seating, threads)

    def __init__(self, *, config: Config):

        # Save the config.
        self.config = DotMap(config.__dict__)

        # Create a handle to AWS for S3 operations.
        # It authenticates by checking the environment for AWS access variables.
        self.aws = aws.AWSClient(self)

        # Create Bureaucrat's logging handle, so that all Bureaucrat-level modules use the same label.
        severity = logging.severity(config.log_level)

        self.logger, handler, formatter = logging.make_logger(name="Bureaucrat", severity=severity)
        self._severity = severity
        self.logger.debug("Debug mode enabled.")

        # Initialize the underlying client.
        options = {
            "allowed_mentions": AllowedMentions(everyone=False),
            "case_insensitive": True,
            "help_command": DefaultHelpCommand(dm_help=None, dm_help_threshold=500, sort_commands=True),
            "intents": Intents.all(),
        }
        super().__init__(config.prefix, **options)
        self.owner_ids = config.owners

        self.logger.debug(f"Owned by {', '.join(str(i) for i in self.owner_ids)}.")

    async def setup_hook(self) -> None:

        await models.setup()

        # Initialize the cogs.
        # Each module should expose a setup function.
        self.logger.info(f"Loading extensions: {', '.join(m.__name__.split('.')[1].capitalize() for m in Bureaucrat.COG_MODULES)}.")
        for module in Bureaucrat.COG_MODULES:
            await module.setup(self)

    def run(self, token: str, *, reconnect: bool = True) -> None:

        return super().run(token, reconnect=reconnect, log_level=self._severity + 10)

    # HELPERS

    async def ensure_active(self, interaction: Interaction) -> Optional[Game]:
        """
        Ensures that this channel has an active game.
        """
        in_channel: Optional[Game] = await self.get_active_game(interaction.channel)
        if in_channel is None:
            await interaction.response.send_message(
                embed=embeds.make_error(self, message="There is no active game in this channel."),
                delete_after=5,
                ephemeral=True,
            )
            return None
        else:
            return in_channel

    async def ensure_active_category(self, interaction: Interaction):
        """
        Ensures the category allows text games.
        """
        category = interaction.channel.category
        if category is None:
            await interaction.response.send_message(
                embed=embeds.make_error(self, message="You must be in a category."), delete_after=5, ephemeral=True
            )
            return False
        elif await ActiveCategory.objects.get_or_none(id=category.id) is None:
            await interaction.response.send_message(
                embed=embeds.make_error(self, message="Text games are not enabled in this category."),
                delete_after=5,
                ephemeral=True,
            )
            return False
        return True

    async def ensure_owner(self, interaction, game: Game):
        """
        Ensures the invoker is the owner of the current game.
        """
        if interaction.user.id in self.owner_ids:
            return True
        
        if interaction.user.id != game.owner:
            await interaction.response.send_message(
                embed=embeds.unauthorized(self, message=f"You are not the owner of this game, <@{game.owner}> is."),
                delete_after=5,
                ephemeral=True,
            )
            return False
        return True

    async def ensure_privileged(self, interaction: Interaction, game: Game):
        """
        Ensures the invoker is the owner of the game or a storyteller.
        """
        if interaction.user.id in self.owner_ids:
            return True
        
        as_member = await interaction.guild.fetch_member(interaction.user.id)
        participant = await Participant.objects.get_or_none(game=game, member=as_member.id)
        if game.owner != as_member.id and (participant is None or participant.role != RoleType.STORYTELLER):
            await interaction.response.send_message(
                embed=embeds.unauthorized(self, message="You must be a storyteller or game owner."),
                delete_after=5,
                ephemeral=True,
            )
            return False
        return True

    async def get_active_game(self, channel: GuildChannel | Thread) -> Optional[Game]:
        """
        Retrieves the active game, if one exists.
        """
        channel_id = self.get_channel_id(channel)
        in_channel = await ActiveGame.objects.select_related(ActiveGame.game).get_or_none(id=channel_id)
        game = in_channel.game if in_channel else None
        return game

    def get_channel_id(self, channel: GuildChannel | Thread):
        """
        Gets the root-channel id (either the id of the channel, or the id of the thread's parent channel if the input is a thread).
        """
        if isinstance(channel, GuildChannel):
            return channel.id
        elif isinstance(channel, Thread):
            thread: Thread = channel
            return thread.parent.id

    async def followup_ethereal(self, interaction: Interaction, **kwargs):
        """
        Sends an ethereal followup.
        """
        await interaction.followup.send(embed=embeds.make_embed(self, **kwargs), ephemeral=True)

    async def send_ethereal(self, interaction: Interaction, **kwargs):
        """
        Sends an ethereal message, which is an autodeleting ephemeral.
        """
        await interaction.response.send_message(
            embed=embeds.make_embed(self, **kwargs), delete_after=5, ephemeral=True
        )
