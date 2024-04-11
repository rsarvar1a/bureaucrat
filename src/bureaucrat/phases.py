
from bureaucrat.models import CONFIG
from bureaucrat.models.games import ActiveGame, Game, Participant, RoleType
from bureaucrat.models.state import Marker, Phase, State, Seat, Status, Type
from bureaucrat.utility import checks, embeds
from datetime import datetime, timedelta
from discord import app_commands as apc, Interaction, Member, TextChannel, Thread
from discord.ext import commands, tasks
from discord.ext.commands import Context
from typing import TYPE_CHECKING, Optional, List, Dict

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


async def setup(bot):
    await bot.add_cog(Phases(bot))


class Phases(commands.GroupCog, group_name="phases"):

    def __init__(self, bot: "Bureaucrat") -> None:
        self.bot = bot

    async def send_ethereal(self, interaction: Interaction, **kwargs):
        await self.bot.send_ethereal(interaction, title="Phases", **kwargs)

    @apc.command()
    async def show(self, interaction: Interaction):
        """
        Show the current day and phase.
        """
        if not await checks.in_guild(self.bot, interaction):
            return
    
        game = await self.bot.ensure_active(interaction)
        if game is None:
            return

        await self._show(interaction, game)

    async def _show(self, interaction: Interaction, game: Game):
        """
        Show the current day and phase.
        """
        state = State.load(game.state)
        description = f"It is {state.moment.phase.name} {state.moment.day}."

        await interaction.response.send_message(embed=embeds.make_embed(self.bot, title="Phases", description=description), ephemeral=True)

    nights = apc.Group(name="nights", description="Generate your night orders inside of Discord.")

    @nights.command()
    @apc.describe(filter="If you are a Storyteller, display only roles that are in-play.")
    async def first(self, interaction: Interaction, filter: Optional[bool]):
        """
        Generate the nightorder for the first night, including any apparent roles.
        """
        if not await checks.in_guild(self.bot, interaction):
            return
    
        game = await self.bot.ensure_active(interaction)
        if game is None:
            return
        
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        participant = await Participant.objects.get_or_none(game=game, member=user_id)
        
        private = (user_id in self.bot.owner_ids or game.owner == user_id or (participant and participant.role == RoleType.STORYTELLER))
        filter = (filter if filter is not None else True) and private

        state = State.load(game.state)
        page = state.make_nightorder(bot=self.bot, night="first", filter=filter, private=private)

        await interaction.followup.send(embed=embeds.make_embed(self.bot, title="First Night", description=page), ephemeral=True)
    
    @nights.command()
    @apc.describe(filter="If you are a Storyteller, display only roles that are in-play.")
    async def other(self, interaction: Interaction, filter: bool):
        """
        Generate the nightorder for the next nights, including any apparent roles.
        """
        if not await checks.in_guild(self.bot, interaction):
            return
    
        game = await self.bot.ensure_active(interaction)
        if game is None:
            return
        
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        participant = await Participant.objects.get_or_none(game=game, member=user_id)

        private = (user_id in self.bot.owner_ids or game.owner == user_id or (participant and participant.role == RoleType.STORYTELLER))
        filter = (filter if filter is not None else True) and private

        state = State.load(game.state)
        page = state.make_nightorder(bot=self.bot, night="other", filter=filter, private=private)

        await interaction.followup.send(embed=embeds.make_embed(self.bot, title="Other Nights", description=page), ephemeral=True)

    go = apc.Group(name="go", description="Switch between day and night phase.")

    @go.command()
    async def dusk(self, interaction: Interaction):
        """
        Advance to next dusk.
        """
        if not await checks.in_guild(self.bot, interaction):
            return
    
        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return
            
            if not await self.bot.ensure_privileged(interaction, game):
                return
        
            state = State.load(game.state)
            if state.moment.phase != Phase.Day:
                return await self.send_ethereal(interaction, description="It is already nighttime.")

            state.moment.go_to_dusk()
            game.state = state.dump()
            await game.update()
        
        await self._show(interaction, game)
    
    @go.command()
    async def dawn(self, interaction: Interaction):
        """
        Advance to next dawn.
        """
        if not await checks.in_guild(self.bot, interaction):
            return
    
        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return
            
            if not await self.bot.ensure_privileged(interaction, game):
                return
        
            state = State.load(game.state)
            if state.moment.phase != Phase.Night:
                return await self.send_ethereal(interaction, description="It is already daytime.")

            state.moment.go_to_dawn()
            game.state = state.dump()
            await game.update()
        
        await self._show(interaction, game)
