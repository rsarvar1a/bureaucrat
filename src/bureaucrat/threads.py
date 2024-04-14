from bureaucrat.models import CONFIG
from bureaucrat.models.games import ManagedThread, Participant, ThreadMember, ThreadType, RoleType, Game
from bureaucrat.utility import checks, embeds
from datetime import datetime, timedelta
from discord import app_commands as apc, Interaction, Member, ChannelType, TextChannel, Thread
from discord.ext import commands
from typing import TYPE_CHECKING, Optional, List, Dict

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


async def setup(bot):
    await bot.add_cog(Threads(bot))


class Threads(commands.GroupCog, group_name="threads"):

    LAYOUT_REVERSED = [
        {"name": "ST PRIVATE", "type": ThreadType.Private},
        {"name": "Seating", "type": ThreadType.Layout},
        {"name": "Rules", "type": ThreadType.Layout},
        {"name": "Nominations", "type": ThreadType.Nomination},
        {"name": "Claims", "type": ThreadType.Layout},
        {"name": "Announcements", "type": ThreadType.Announcements}
    ]

    def __init__(self, bot: "Bureaucrat") -> None:
        self.bot = bot

    async def followup_ethereal(self, interaction: Interaction, **kwargs):
        await self.bot.followup_ethereal(interaction, title="Threads", **kwargs)

    async def send_ethereal(self, interaction: Interaction, **kwargs):
        await self.bot.send_ethereal(interaction, title="Threads", **kwargs)
    
    async def create_thread(self, channel: TextChannel, name: str, type: ThreadType):
        """
        Create a thread with the given type.
        """
        thread_type = ChannelType.private_thread if type in [ThreadType.Private, ThreadType.Whisper] else ChannelType.public_thread
        thread = await channel.create_thread(name=name, type=thread_type, auto_archive_duration=10080)
        return thread

    async def create_managed_thread(self, game: Game, name: str, kind: ThreadType):
        """
        Create a managed thread.
        """
        channel = self.bot.get_channel(game.channel) or await self.bot.fetch_channel(game.channel)
        participants = await Participant.objects.filter(game=game).all()

        thread = await self.create_thread(channel, name, kind)
        managed_thread = await ManagedThread.objects.create(id=thread.id, game=game, type=kind)

        if kind in [ThreadType.Private, ThreadType.Whisper]:
            await thread.send(content=f"<@&{game.st_role}>", delete_after=5)
            for member in [p.member for p in participants if p.role == RoleType.STORYTELLER]:
                await ThreadMember.objects.create(game=game, thread=managed_thread, member=member)

        else:
            await thread.send(content=f"<@&{game.player_role}> <@&{game.st_role}>", delete_after=5)
            for member in [p.member for p in participants]:
                await ThreadMember.objects.create(game=game, thread=managed_thread, member=member)
        
        return thread, managed_thread

    async def create_st_thread(self, game: Game, player: Member):
        """
        Create a private ST thread.
        """
        channel = self.bot.get_channel(game.channel) or await self.bot.fetch_channel(game.channel)
        storytellers = await Participant.objects.filter(game=game, role=RoleType.STORYTELLER).all()

        thread = await self.create_thread(channel, f"ST Thread - {player.display_name}", ThreadType.Private)
        managed_thread = await ManagedThread.objects.create(id=thread.id, game=game, type=ThreadType.Private)
        await thread.send(content=f"{player.mention} <@&{game.st_role}>", delete_after=5)

        for thread_member in [player.id] + [st.member for st in storytellers]:
            await ThreadMember.objects.create(game=game, thread=managed_thread, member=thread_member)
        
        return thread, managed_thread

    @apc.command()
    async def init(self, interaction: Interaction):
        """
        Create the default threads for this game: ST Threads for each player; an ST PRIVATE thread; and threads for Announcements, Claims, Nominations, Rules, and Seating.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return
        
        if not await self.bot.ensure_privileged(interaction, game):
            return

        if await ManagedThread.objects.filter(game=game).count() > 0:
            return await self.send_ethereal(interaction, description="You have already initialized threads in this game.")
        
        await interaction.response.defer(ephemeral=True)

        async with CONFIG.database.transaction():
            players = await Participant.objects.filter(game=game, role=RoleType.PLAYER).all()
            player_members = [interaction.guild.get_member(player.member) or await interaction.guild.fetch_member(player.member) for player in players]

            for data in Threads.LAYOUT_REVERSED:
                await self.create_managed_thread(game, data['name'], data['type'])

            for player in sorted(player_members, key=lambda player: player.display_name, reverse=True):
                await self.create_st_thread(game, player)
        
        await self._list(interaction, game, whispers=False, followup=True)

    @apc.command()
    @apc.describe(player="The user to start a whisper with.")
    @apc.describe(title="The title of your whisper.")
    async def whisper(self, interaction: Interaction, player: Member, title: Optional[str]):
        """
        Whisper another player privately.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return

        you = await Participant.objects.get_or_none(game=game, member=interaction.user.id, role=RoleType.PLAYER)
        if not you:
            return await self.send_ethereal(interaction, description="You are not a player in this game.")
        
        them = await Participant.objects.get_or_none(game=game, member=player.id, role=RoleType.PLAYER)
        if not them:
            return await self.send_ethereal(interaction, description=f"{player.mention} is not a player in this game.")
        
        if not title:
            title = f"whisper: {interaction.user.display_name} & {player.display_name}"
        
        thread, managed_thread = await self.create_managed_thread(game, title, ThreadType.Whisper)
        for user in [interaction.user, player]:
            await thread.add_user(user)
            await ThreadMember.objects.create(game=game, thread=managed_thread, member=user.id)

        await self._list(interaction, game, whispers=True, followup=False)

    @apc.command()
    @apc.describe(whispers="Whether or not to show whisper threads. Defaults to true.")
    async def list(self, interaction: Interaction, whispers: Optional[bool]):
        """
        List all of the threads that you are a part of. If you are a Storyteller, list all of them instead.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return

        await self._list(interaction, game, whispers=whispers if whispers is not None else True, followup=False)

    async def _list(self, interaction: Interaction, game: Game, whispers: bool, followup: bool = False):
        """
        List all of the threads that you are a part of. If you are a Storyteller, list all of them instead.
        """
        this_user = await Participant.objects.get_or_none(game=game, member=interaction.user.id)
        if this_user is None:
            if followup:
                return await self.followup_ethereal(interaction, description="You do not have a role in this game.")
            else:
                return await self.send_ethereal(interaction, description="You do not have a role in this game.")
        
        st_view = this_user.role == RoleType.STORYTELLER

        if st_view:
            managed_threads = await ManagedThread.objects.filter(game=game).all()
        else:
            in_threads = await ThreadMember.objects.select_related(ThreadMember.thread).filter(game=game, member=interaction.user.id).all()
            managed_threads = [i.thread for i in in_threads]

        def whispers_afterwards(pair):
            if pair[0].type == ThreadType.Whisper:
                return 2
            if pair[0].type == ThreadType.Private:
                return 1
            return 0

        threads = [(t, self.bot.get_channel(t.id) or await self.bot.fetch_channel(t.id)) for t in managed_threads if whispers or t.type != ThreadType.Whisper]
        threads = sorted(sorted(threads, key=lambda thread: thread[1].name), key=whispers_afterwards)

        are_whispers = [pair for pair in threads if pair[0].type == ThreadType.Whisper]
        not_whispers = [pair for pair in threads if pair[0].type != ThreadType.Whisper]

        description = "\n".join([f"{i + 1}. {thread[1].mention}" for i, thread in enumerate(not_whispers)])
        if whispers:
            if len(are_whispers) > 0:
                description += "\n\n**Whispers**\n" + "\n".join(f"- {thread[1].mention}" for thread in are_whispers)
            else:
                description += "\n\nThere are no whispers."

        if followup:
            await interaction.followup.send(embed=embeds.make_embed(self.bot, title="Threads", description=description), ephemeral=True)
        else:
            await interaction.response.send_message(embed=embeds.make_embed(self.bot, title="Threads", description=description), ephemeral=True)
