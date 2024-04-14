
from bureaucrat.models import CONFIG
from bureaucrat.models.games import ActiveGame, Game, ManagedThread, Participant, RoleType, ThreadType
from bureaucrat.models.state import NominationType, VoteResult, Marker, Phase, State, Seat, Status, Type
from bureaucrat.utility import checks, embeds
from datetime import datetime, timedelta
from discord import app_commands as apc, Interaction, Member, TextChannel, Thread
from discord.ext import commands, tasks
from discord.ext.commands import Context
from typing import TYPE_CHECKING, Optional, List, Dict

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


async def setup(bot):
    await bot.add_cog(Nominations(bot))


class Nominations(commands.GroupCog, group_name="nominations"):

    def __init__(self, bot: "Bureaucrat") -> None:
        self.bot = bot

    async def followup_ethereal(self, interaction: Interaction, **kwargs):
        await self.bot.followup_ethereal(interaction, title="Nominations", **kwargs)

    async def send_ethereal(self, interaction: Interaction, **kwargs):
        await self.bot.send_ethereal(interaction, title="Nominations", **kwargs)

    # AUTOCOMPLETES

    async def autocomplete(self, interaction: Interaction, current: str):
        """
        Returns a list of all players, for contexts where the day is unclear.
        """
        channel_id = self.bot.get_channel_id(interaction.channel)
        in_channel = await ActiveGame.objects.select_related(ActiveGame.game).get_or_none(id=channel_id)
        if in_channel is None:
            return []
        game = in_channel.game
        state = State.load(game.state)
        return [apc.Choice(name=seat.alias, value=seat.id) for seat in state.seating.seats if current.lower() in seat.alias.lower()]        

    async def valid_nominators(self, interaction: Interaction, current: str):
        """
        Returns a list of players that can still nominate today.
        """
        channel_id = self.bot.get_channel_id(interaction.channel)
        in_channel = await ActiveGame.objects.select_related(ActiveGame.game).get_or_none(id=channel_id)
        if in_channel is None:
            return []
        game = in_channel.game
        state = State.load(game.state)
        return [apc.Choice(name=seat.alias, value=seat.id) for seat in state.seating.seats if current.lower() in seat.alias.lower()]

    async def valid_nominees(self, interaction: Interaction, current: str):
        """
        Returns a list of players that can still be nominated today.
        """
        channel_id = self.bot.get_channel_id(interaction.channel)
        in_channel = await ActiveGame.objects.select_related(ActiveGame.game).get_or_none(id=channel_id)
        if in_channel is None:
            return []
        game = in_channel.game
        state = State.load(game.state)

        unnominated = [seat for seat in state.seating.seats if not any(nom.nominee == seat.id for nom in state.nominations.get_nominations(state.moment.day))]
        return [apc.Choice(name=seat.alias, value=seat.id) for seat in unnominated if current.lower() in seat.alias.lower()]
    
    async def existing_nominees(self, interaction: Interaction, current: str):
        """
        Returns a list of players that have already been nominated today.
        """
        channel_id = self.bot.get_channel_id(interaction.channel)
        in_channel = await ActiveGame.objects.select_related(ActiveGame.game).get_or_none(id=channel_id)
        if in_channel is None:
            return []
        game = in_channel.game
        state = State.load(game.state)

        nominated = [seat for seat in state.seating.seats if any(nom.nominee == seat.id for nom in state.nominations.get_nominations(state.moment.day))]
        return [apc.Choice(name=seat.alias, value=seat.id) for seat in nominated if current.lower() in seat.alias.lower()]

    # COMMANDS

    @apc.command()
    @apc.describe(day="Show all nominations that occurred on a particular day. Defaults to the current day.")
    async def list(self, interaction: Interaction, day: Optional[int]):
        """
        Show all nominations occurring on a particular day.
        """
        if not await checks.in_guild(self.bot, interaction):
            return
    
        game = await self.bot.ensure_active(interaction)
        if game is None:
            return

        await self._list(interaction, game, day)

    async def _list(self, interaction: Interaction, game: Game, day: Optional[int] = None):
        state = State.load(game.state)

        user_id = interaction.user.id
        participant = await Participant.objects.get_or_none(game=game, member=user_id)        
        private = (user_id in self.bot.owner_ids or game.owner == user_id or (participant and participant.role == RoleType.STORYTELLER))

        description = state.nominations.make_page(bot=self.bot, day=day, state=state, private=private, viewer=None)
        await interaction.response.send_message(embed=embeds.make_embed(self.bot, title="Nominations", description=description), ephemeral=True)

    @apc.command()
    @apc.autocomplete(nominee=autocomplete)
    @apc.describe(nominee="The player that was nominated.")
    @apc.describe(day="The day on which to search for nominations. Defaults to the current day.")
    async def show(self, interaction: Interaction, nominee: str, day: Optional[int]):
        """
        Show information on a specific nomination.
        """
        if not await checks.in_guild(self.bot, interaction):
            return
    
        game = await self.bot.ensure_active(interaction)
        if game is None:
            return
        
        await self._show(interaction, game, nominee, day)
    
    async def _show(self, interaction: Interaction, game: Game, nominee: str, day: Optional[int], *, followup: bool = False):
        state = State.load(game.state)

        user_id = interaction.user.id
        participant = await Participant.objects.get_or_none(game=game, member=user_id)        
        private = (user_id in self.bot.owner_ids or game.owner == user_id or (participant and participant.role == RoleType.STORYTELLER))

        day = day if day is not None else state.moment.day
        nomination = state.nominations.get_specific_nomination(day, nominee)
     
        if nomination is None:
            description = "There is no such nomination."
        else:
            viewer = state.seating.member_to_id(interaction.user.id)
            description = nomination.make_description(indent="", bot=self.bot, state=state, private=private, show_votes=True, viewer=viewer)

        if followup:
            await interaction.followup.send(embed=embeds.make_embed(self.bot, title="Nominations", description=description), ephemeral=True)
        else:
            await interaction.response.send_message(embed=embeds.make_embed(self.bot, title="Nominations", description=description), ephemeral=True)

    # NOMINATION

    @apc.command()
    @apc.autocomplete(nominee=valid_nominees)
    @apc.describe(nominee="The player you wish to nominate.")
    async def nominate(self, interaction: Interaction, nominee: str):
        """
        Nominate a player.
        """
        if not await checks.in_guild(self.bot, interaction):
            return
    
        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return

            thread = await ManagedThread.objects.get_or_none(game=game, type=ThreadType.Nomination)
            if not thread:
                return await self.send_ethereal(interaction, description="There is no nomination thread yet.")

            await interaction.response.defer(ephemeral=True)

            state = State.load(game.state)

            nominator = state.seating.member_to_id(interaction.user.id)
            error = state.nominations.create(state=state, nominator=nominator, nominee=nominee)
            if error:
                return await self.followup_ethereal(interaction, description=error)    

            nominee_seat = state.seating.seats[state.seating.index(nominee)]

            game.state = state.dump()
            await game.update()            

        thread = self.bot.get_channel(thread.id) or await interaction.guild.fetch_channel(thread.id)
        await thread.send(content=f"<@&{game.player_role}> <@&{game.st_role}>\n{interaction.user.mention} has nominated <@{nominee_seat.member}>.")

        await self._show(interaction, game, nominee, None, followup=True)

    @apc.command()
    @apc.autocomplete(nominator=valid_nominators, nominee=valid_nominees)
    @apc.describe(nominator="The nominating player.")
    @apc.describe(nominee="The nominated player.")
    async def create(self, interaction: Interaction, nominator: str, nominee: str):
        """
        Manually create a nomination as the ST.
        """
        if not await checks.in_guild(self.bot, interaction):
            return
    
        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return
            
            thread = await ManagedThread.objects.get_or_none(game=game, type=ThreadType.Nomination)
            if not thread:
                return await self.send_ethereal(interaction, description="There is no nomination thread yet.")

            await interaction.response.defer(ephemeral=True)

            state = State.load(game.state)

            error = state.nominations.create(state=state, nominator=nominator, nominee=nominee)
            if error:
                return await self.followup_ethereal(interaction, description=f"Proxy nomination failed: `{error}`.")    

            nominator_seat = state.seating.seats[state.seating.index(nominator)]
            nominee_seat = state.seating.seats[state.seating.index(nominee)]

            game.state = state.dump()
            await game.update()            

        thread = self.bot.get_channel(thread.id) or await interaction.guild.fetch_channel(thread.id)
        await thread.send(content=f"<@&{game.player_role}> <@&{game.st_role}>\n<@{nominator_seat.member}> has nominated <@{nominee_seat.member}>.")

        await self._show(interaction, game, nominee, None, followup=True)

    @apc.command()
    @apc.autocomplete(nominee=existing_nominees)
    @apc.describe(nominee="The nomination to edit.")
    @apc.describe(required="The number of yes votes required to pass this nomination.")
    @apc.describe(accusation="A new accusation message.")
    @apc.describe(defense="A new defense message.")
    async def edit(self, interaction: Interaction, nominee: str, required: Optional[int], accusation: Optional[str], defense: Optional[str]):
        """
        Edit an existing nomination.
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
            nomination = state.nominations.get_specific_nomination(state.moment.day, nominee)
            if not nomination:
                return await self.send_ethereal(interaction, description="There is no such nomination.")

            if accusation:
                nomination.accusation = accusation
            if defense:
                nomination.defense = defense
            if required:
                nomination.required = required

            game.state = state.dump()
            await game.update()
        
        await self._show(interaction, game, nominee, None)

    @apc.command()
    @apc.autocomplete(nominee=existing_nominees)
    @apc.describe(nominee="The nomination to mark for death.")
    async def mark(self, interaction: Interaction, nominee: str):
        """
        Mark one of today's nominees for death.
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

            err = state.nominations.mark(state=state, nominee=nominee, mark=True)
            if err:
                return await self.send_ethereal(interaction, description=err)

            game.state = state.dump()
            await game.update()
        
        await self._show(interaction, game, nominee, None)

    @apc.command()
    @apc.autocomplete(nominee=existing_nominees)
    @apc.describe(nominee="The nomination to remove a mark from.")
    async def unmark(self, interaction: Interaction, nominee: str):
        """
        Remove a mark from an existing nomination.
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

            err = state.nominations.mark(state=state, nominee=nominee, mark=False)
            if err:
                return await self.send_ethereal(interaction, description=err)

            game.state = state.dump()
            await game.update()
        
        await self._show(interaction, game, nominee, None)

    # PLAYER VOTES

    votes = apc.Group(name="vote", description="Vote on open nominations.")

    @votes.command()
    @apc.autocomplete(nominee=existing_nominees)
    @apc.describe(nominee="The nominee you wish to vote on.")
    @apc.describe(vote="Your vote or conditional.")
    @apc.describe(private="Whether this vote is private or public. Defaults to public.")
    async def set(self, interaction: Interaction, nominee: str, vote: str, private: Optional[bool]):
        """
        Vote on one of today's existing nominations.
        """
        if not await checks.in_guild(self.bot, interaction):
            return
    
        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return

            state = State.load(game.state)

            voter = state.seating.member_to_id(interaction.user.id)
            if voter is None:
                return await self.send_ethereal(interaction, description="You are not seated in this game.")

            error = state.nominations.set_vote(state=state, voter=voter, nominee=nominee, vote=vote, private=private if private is not None else False)  
            if error:
                return await self.send_ethereal(interaction, description=error)    

            game.state = state.dump()
            await game.update()            

        await self._show(interaction, game, nominee, None)

    @votes.command()
    @apc.autocomplete(nominee=existing_nominees)
    @apc.describe(nominee="The nominee you wish to remove your vote from.")
    @apc.describe(private="Whether you want to remove your private or public vote. Defaults to public.")
    async def remove(self, interaction: Interaction, nominee: str, private: Optional[bool]):
        """
        Unvote on one of today's existing nominations.
        """
        if not await checks.in_guild(self.bot, interaction):
            return
    
        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return

            state = State.load(game.state)

            voter = state.seating.member_to_id(interaction.user.id)
            if voter is None:
                return await self.send_ethereal(interaction, description="You are not seated in this game.")

            error = state.nominations.set_vote(state=state, voter=voter, nominee=nominee, vote=None, private=private if private is not None else False)  
            if error:
                return await self.send_ethereal(interaction, description=error)    

            game.state = state.dump()
            await game.update()            

        await self._show(interaction, game, nominee, None)

    @votes.command()
    @apc.autocomplete(nominee=existing_nominees, voter=autocomplete)
    @apc.describe(nominee="The nominated player.")
    @apc.describe(voter="The player to lock the vote on.")
    @apc.describe(result="The value of the player's vote.")
    async def lock(self, interaction: Interaction, nominee: str, voter: str, result: VoteResult):
        """
        Lock a player's vote.
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

            error = state.nominations.lock_vote(state=state, nominee=nominee, voter=voter, result=result)
            if error:
                return await self.send_ethereal(interaction, description=f"Failed to lock: `{error}`.")

            game.state = state.dump()
            await game.update()            

        await self._show(interaction, game, nominee, None)

    @votes.command()
    @apc.autocomplete(nominee=existing_nominees, voter=autocomplete)
    @apc.describe(nominee="The nominated player.")
    @apc.describe(voter="The player to unlock.")
    async def unlock(self, interaction: Interaction, nominee: str, voter: str):
        """
        Unlock a player's vote.
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

            error = state.nominations.lock_vote(state=state, nominee=nominee, voter=voter, result=None)
            if error:
                return await self.send_ethereal(interaction, description=f"Failed to unlock: `{error}`.")

            game.state = state.dump()
            await game.update()            

        await self._show(interaction, game, nominee, None)

    add = apc.Group(name="add", description="Add trial statements to open nominations.")

    @add.command()
    @apc.autocomplete(nominee=existing_nominees)
    @apc.describe(nominee="The nominee to accuse. You must have nominated this player.")
    @apc.describe(accusation="Your accusation message.")
    async def accusation(self, interaction: Interaction, nominee: str, accusation: str):
        """
        Add an accusation to a nomination that you created.
        """
        if not await checks.in_guild(self.bot, interaction):
            return
    
        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return

            state = State.load(game.state)

            nominator = state.seating.member_to_id(interaction.user.id)
            if nominator is None:
                return await self.send_ethereal(interaction, description="You are not seated in this game.")

            error = state.nominations.accuse(state=state, nominator=nominator, nominee=nominee, accusation=accusation)  
            if error:
                return await self.send_ethereal(interaction, description=error)    

            game.state = state.dump()
            await game.update()            

        await self._show(interaction, game, nominee, None)

    @add.command()
    @apc.describe(defense="Your defense message.")
    async def defense(self, interaction: Interaction, defense: str):
        """
        Add a defense to a nomination where you're a nominee.
        """
        if not await checks.in_guild(self.bot, interaction):
            return
    
        async with CONFIG.database.transaction():
            game = await self.bot.ensure_active(interaction)
            if game is None:
                return

            state = State.load(game.state)

            nominee = state.seating.member_to_id(interaction.user.id)
            if nominee is None:
                return await self.send_ethereal(interaction, description="You are not seated in this game.")

            error = state.nominations.defend(state=state, nominee=nominee, defense=defense)  
            if error:
                return await self.send_ethereal(interaction, description=error)    

            game.state = state.dump()
            await game.update()            

        await self._show(interaction, game, nominee, None)
