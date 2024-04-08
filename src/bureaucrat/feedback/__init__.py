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
        await self.bot.send_ethereal(interaction, title="Feedback", **kwargs)

    @apc.command()
    @apc.describe(game="Submit feedback for a game that has already ended.")
    @apc.describe(anonymous="Whether the storyteller can see your username on the feedback.")
    async def submit(self, interaction: Interaction, game: Optional[str], anonymous: bool):
        """
        Submit feedback for the current game's storyteller.
        """
        if not await checks.in_guild(bot=self.bot, interaction=interaction):
            return

        if game is None:
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return
        else:
            game = await Game.objects.get(id=game)
            if game is None:
                return await self.send_ethereal(interaction, description="Could not find that game.")

        participant = await Participant.objects.get_or_none(game=game, member=interaction.user.id)
        if not participant or participant.role != RoleType.PLAYER:
            await self.send_ethereal(interaction, description="You must be a player in this game to submit feedback.")
        
        await NewFeedbackView.create(parent=self, interaction=interaction, game=game, anonymous=anonymous)

    @apc.command()
    @apc.describe(game="The id of the game to filter on.")
    async def list(self, interaction: Interaction, game: Optional[str]):
        """
        List feedback you have received as a storyteller.
        """
        if game:
            game = await Game.objects.get_or_none(id=game)
            if game is None:
                return await self.send_ethereal(interaction, description="That game does not exist.")

        await FeedbackListView.create(parent=self, interaction=interaction, game=game)
