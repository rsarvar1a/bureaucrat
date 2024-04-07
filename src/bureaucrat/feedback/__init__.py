from bureaucrat.models.games import ActiveGame, Participant, RoleType, Game
from bureaucrat.utility import checks, embeds
from discord import app_commands as apc, Interaction, Member, Thread
from discord.abc import GuildChannel
from discord.ext import commands
from typing import TYPE_CHECKING, Optional

from .list import FeedbackListView
from .new import NewFeedbackView

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


async def setup(bot):
    await bot.add_cog(Feedback(bot))


class Feedback(commands.GroupCog, group_name="feedback"):
    
    def __init__(self, bot: "Bureaucrat") -> None:
        self.bot = bot
    
    async def ensure_active(self, interaction: Interaction) -> Optional[Game]:
        """
        Ensures that this channel has an active game.
        """
        in_channel: Optional[Game] = await self.get_active_game(interaction.channel)
        if in_channel is None:
            await interaction.response.send_message(
                embed=embeds.make_error(self.bot, message="There is no active game in this channel."),
                delete_after=5,
                ephemeral=True,
            )
            return None
        else:
            return in_channel

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

    def make_embed(self, feedback, header):
        segments = [header + "\n"]

        for opt in NewFeedbackView.OPTIONS:
            score = feedback.__dict__[opt['label'].lower()]
            score_str = "⭐" * score if score > 0 else "n/a"
            segments.append(f"{opt['label']}: {score_str}")

        for para in ["Feedback", "Comments"]:
            text = feedback.__dict__[para.lower()]
            segments.append(f"\n{para}:\n\n> {text}" if text else f"\n{para}: n/a")

        description = "\n".join(s for s in segments)
        return description

    async def send_ethereal(self, interaction: Interaction, **kwargs):
        await interaction.response.send_message(embed=embeds.make_embed(self.bot, **kwargs), delete_after=5, ephemeral=True)

    @apc.command()
    @apc.describe(anonymous="Whether the storyteller can see your username on the feedback.")
    async def submit(self, interaction: Interaction, anonymous: bool):
        """
        Submit feedback for the current game's storyteller.
        """
        if not await checks.in_guild(bot=self.bot, interaction=interaction):
            return

        game = await self.ensure_active(interaction)
        if game is None:
            return
        
        participant = await Participant.objects.get_or_none()
        if not participant or participant.role != RoleType.PLAYER:
            await self.send_ethereal(interaction, description="You must be a player in this game to submit feedback.")
        
        await NewFeedbackView.create(parent=self, interaction=interaction, game=game, anonymous=anonymous)

    @apc.command()
    @apc.describe(game="The id of the game to filter on.")
    async def list(self, interaction: Interaction, game: Optional[int]):
        """
        List feedback you have received as a storyteller.
        """
        if game:
            game = await Game.objects.get_or_none(id=game)
            if game is None:
                return await self.send_ethereal(interaction, description="That game does not exist.")

        await FeedbackListView.create(parent=self, interaction=interaction, game=game)
