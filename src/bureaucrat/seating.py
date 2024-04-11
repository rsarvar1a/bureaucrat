from bureaucrat.models import CONFIG
from bureaucrat.models.games import ActiveGame, Game, Participant, RoleType
from bureaucrat.models.state import Marker, State, Seat, Status, Type
from bureaucrat.utility import checks, embeds
from datetime import datetime, timedelta
from discord import app_commands as apc, Interaction, Member, TextChannel, Thread
from discord.ext import commands, tasks
from discord.ext.commands import Context
from typing import TYPE_CHECKING, Optional, List, Dict

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


async def setup(bot):
    await bot.add_cog(Seating(bot))


class Seating(commands.GroupCog, group_name="seating"):

    def __init__(self, bot: "Bureaucrat") -> None:
        self.bot = bot

    async def send_ethereal(self, interaction: Interaction, **kwargs):
        await self.bot.send_ethereal(interaction, title="Seating", **kwargs)

    async def autocomplete(self, interaction: Interaction, current: str):
        """
        Returns a list of players in the game.
        """
        channel_id = self.bot.get_channel_id(interaction.channel)
        in_channel = await ActiveGame.objects.select_related(ActiveGame.game).get_or_none(id=channel_id)
        if in_channel is None:
            return []
        game = in_channel.game
        state = State.load(game.state)
        return [apc.Choice(name=seat.alias, value=seat.id) for seat in state.seating.seats if current.lower() in seat.alias.lower()]

    @apc.command()
    async def show(self, interaction: Interaction):
        """
        Shows the seating in the current game. If you are a Storyteller, also shows private information.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return
        
        await self._show(interaction, game, followup=False)
    
    async def _show(self, interaction: Interaction, game: Game, followup: bool = False):
        participant = await Participant.objects.get_or_none(game=game, member=interaction.user.id)
        
        user_id = interaction.user.id
        show_private = user_id in self.bot.owner_ids or game.owner == user_id or (participant and participant.role == RoleType.STORYTELLER)
        
        state = State.load(game.state)
        description = state.seating.make_page(bot=self.bot, private=show_private)

        if followup:
            await interaction.followup.send(embed=embeds.make_embed(self.bot, title="Seating", description=description), ephemeral=True)
        else:
            await interaction.response.send_message(embed=embeds.make_embed(self.bot, title="Seating", description=description), ephemeral=True)


    @apc.command()
    async def init(self, interaction: Interaction):
        """
        Initializes seating by drawing from the players in the game.
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
            if state.seating.already_init:
                return await self.send_ethereal(interaction, description="Seating has already been initialized.")
            state.seating.already_init = True

            await interaction.response.defer()

            players = await Participant.objects.all(game=game, role=RoleType.PLAYER)
            for player in players:
                as_member = interaction.guild.get_member(player.member) or await interaction.guild.fetch_member(player.member)
                state.seating.add_player(user=as_member, kind=Type.Player, role=None, apparent=None)
            
            game.state = state.dump()
            await game.update()
        
        await self._show(interaction, game, followup=True)

    @apc.command()
    @apc.describe(user="The player to add to the seating. This also adds them as a participant.")
    @apc.describe(kind="Whether the player is a traveller or not.")
    @apc.describe(true_role="The true character of this player, as its id in the script.")
    @apc.describe(apparent_role="The character this player believes they are, if not the same as the true role.")
    async def add(self, interaction: Interaction, user: Member, kind: Type, true_role: Optional[str], apparent_role: Optional[str]):
        """
        Adds a player to the seating.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return
            
            if not await self.bot.ensure_privileged(interaction, game):
                return
            
            await interaction.response.defer(ephemeral=True)

            state = State.load(game.state)

            state.seating.add_player(user=user, kind=kind, role=true_role, apparent=apparent_role)

            p = await Participant.objects.get_or_create({"role": RoleType.PLAYER}, game=game, member=user.id)
            await p[0].update(role=RoleType.PLAYER)

            game.state = state.dump()
            await game.update()
        
        await self._show(interaction, game, followup=True)

    @apc.command()
    @apc.autocomplete(player=autocomplete)
    @apc.describe(player="The player to remove from seating.")
    async def remove(self, interaction: Interaction, player: str):
        """
        Removes a player from the seating.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return
            
            if not await self.bot.ensure_privileged(interaction, game):
                return
            
            await interaction.response.defer(ephemeral=True)

            state = State.load(game.state)

            seat = state.seating.remove_player(id=player)
            user = await interaction.guild.fetch_member(seat.member)
            await self.bot.get_cog('Games')._roles.set_role(game, user, RoleType.NONE)

            game.state = state.dump()
            await game.update()
        
        await self._show(interaction, game, followup=True)

    @apc.command()
    @apc.autocomplete(player=autocomplete)
    @apc.describe(player="The player to substitute out.")
    @apc.describe(substitute="The user to substitute in.")
    async def substitute(self, interaction: Interaction, player: str, substitute: Member):
        """
        Substitutes a player out of the game.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return
            
            if not await self.bot.ensure_privileged(interaction, game):
                return
            
            await interaction.response.defer(ephemeral=True)

            state = State.load(game.state)

            prev_id = state.seating.substitute_player(id=player, user=substitute)
            games = self.bot.get_cog("Games")

            if prev_id:
                as_member = await interaction.guild.fetch_member(prev_id)
                await games._roles.set_role(game, as_member, RoleType.NONE)
            await games._roles.set_role(game, substitute, RoleType.PLAYER)

            game.state = state.dump()
            await game.update()
        
        await self._show(interaction, game, followup=True)

    @apc.command()
    @apc.autocomplete(first=autocomplete, other=autocomplete)
    @apc.describe(first="The first player in the pair to swap.")
    @apc.describe(other="The other player in the pair to swap.")
    async def swap(self, interaction: Interaction, first: str, other: str):
        """
        Swaps two players in the seating order.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return
            
            if not await self.bot.ensure_privileged(interaction, game):
                return
            
            await interaction.response.defer(ephemeral=True)

            state = State.load(game.state)

            state.seating.swap_seats(lhs=first, rhs=other)

            game.state = state.dump()
            await game.update()
        
        await self._show(interaction, game, followup=True)

    @apc.command()
    @apc.autocomplete(player=autocomplete)
    @apc.describe(player="The player to edit.")
    @apc.describe(status="The player's status as it would appear on their life token.")
    @apc.describe(true_role="The true character of this player, as its id in the script.")
    @apc.describe(apparent_role="The character this player believes they are, if not the same as the true role.")
    async def edit(self, interaction: Interaction, player: str, status: Optional[Status], true_role: Optional[str], apparent_role: Optional[str]):
        """
        Edits a player's info in the seating order.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return
            
            if not await self.bot.ensure_privileged(interaction, game):
                return
            
            await interaction.response.defer(ephemeral=True)

            state = State.load(game.state)

            state.seating.set_role(id=player, true=true_role, apparent=apparent_role)
            state.seating.set_status(id=player, status=status)

            game.state = state.dump()
            await game.update()
        
        await self._show(interaction, game, followup=True)

    move = apc.Group(name="move", description="Move players around in the seating order using a rich positional interface.")

    @move.command()
    @apc.autocomplete(player=autocomplete)
    @apc.describe(player="The player to move.")
    async def beginning(self, interaction: Interaction, player: str):
        """
        Move a player to the first seat.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return
            
            if not await self.bot.ensure_privileged(interaction, game):
                return
            
            await interaction.response.defer(ephemeral=True)

            state = State.load(game.state)

            state.seating.move_seats(lhs=player, mode = Marker.Beginning)

            game.state = state.dump()
            await game.update()
        
        await self._show(interaction, game, followup=True)
    
    @move.command()
    @apc.autocomplete(player=autocomplete, before=autocomplete)
    @apc.describe(player="The player to move.")
    @apc.describe(before="The player to move before.")
    async def before(self, interaction: Interaction, player: str, before: str):
        """
        Move a player right before another player.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return
            
            if not await self.bot.ensure_privileged(interaction, game):
                return
            
            await interaction.response.defer(ephemeral=True)

            state = State.load(game.state)

            state.seating.move_seats(lhs=player, rhs=before, mode=Marker.Before)

            game.state = state.dump()
            await game.update()
        
        await self._show(interaction, game, followup=True)

    @move.command()
    @apc.autocomplete(player=autocomplete, after=autocomplete)
    @apc.describe(player="The player to move.")
    @apc.describe(after="The player to move after.")
    async def after(self, interaction: Interaction, player: str, after: str):
        """
        Move a player right after another player.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return
            
            if not await self.bot.ensure_privileged(interaction, game):
                return
            
            await interaction.response.defer(ephemeral=True)

            state = State.load(game.state)

            state.seating.move_seats(lhs=player, rhs=after, mode=Marker.After)

            game.state = state.dump()
            await game.update()
        
        await self._show(interaction, game, followup=True)

    @move.command()
    @apc.autocomplete(player=autocomplete)
    @apc.describe(player="The player to move.")
    async def end(self, interaction: Interaction, player: str):
        """
        Move a player to the last seat.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return
            
            if not await self.bot.ensure_privileged(interaction, game):
                return
            
            await interaction.response.defer(ephemeral=True)

            state = State.load(game.state)

            state.seating.move_seats(lhs=player, mode = Marker.End)

            game.state = state.dump()
            await game.update()
        
        await self._show(interaction, game, followup=True)

    nights = apc.Group(name="nights", description="Generate your night orders inside of Discord.")

    @nights.command()
    @apc.describe(filter="If you are a Storyteller, display only roles that are in-play.")
    async def first(self, interaction: Interaction, filter: Optional[bool]):
        """
        Returns the nightorder for the first night, including any apparent roles.
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
        Returns the nightorder for the next nights, including any apparent roles.
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
