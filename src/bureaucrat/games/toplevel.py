from bureaucrat.models.config import Config
from bureaucrat.models.state import State
from bureaucrat.models.configure import ormar
from bureaucrat.models import games
from bureaucrat.models.games import ActiveCategory, ActiveGame, Game, Participant, Signup, ManagedThread, ThreadType
from bureaucrat.models.scripts import Script
from bureaucrat.scripts.details import ScriptDetailsView
from bureaucrat.utility import checks, embeds
from datetime import datetime
from discord import Interaction, Member, Thread, CategoryChannel
from sqids.sqids import Sqids
from typing import TYPE_CHECKING, Optional

from .roles import RoleType

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat
    from bureaucrat.games import Games


class TopLevel:

    def __init__(self, parent: "Games") -> None:
        self.bot: "Bureaucrat" = parent.bot
        self.parent = parent

    async def followup_ethereal(self, interaction: Interaction, **kwargs):
        await self.bot.followup_ethereal(interaction, title="Games", **kwargs)

    async def send_ethereal(self, interaction: Interaction, **kwargs):
        await self.bot.send_ethereal(interaction, title="Games", **kwargs)

    async def end(self, interaction: Interaction):
        """
        Ends the active game in this channel, freeing it up.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return

        if not await self.bot.ensure_owner(interaction, game):
            return

        await ActiveGame.objects.filter(game=game).delete()
        await self.parent._roles.cleanup(interaction.guild, game.player_role, game.st_role)
        await self.parent._kibitz._cleanup(interaction, game)

        await self.send_ethereal(interaction, description="This channel has been freed up.")

    async def new(self, interaction: Interaction, *, category: Optional[CategoryChannel], name: Optional[str], script: Optional[str], seats: Optional[int]):
        """
        Creates a new game in the given channel.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        if category is None:
            if await self.bot.get_active_game(interaction.channel):
                return await self.send_ethereal(interaction, description="There is already an active game here.")

            if not await self.bot.ensure_active_category(interaction):
                return

            channel_id = self.bot.get_channel_id(interaction.channel)
            channel = await interaction.guild.fetch_channel(channel_id)

        else:
            cat = await ActiveCategory.objects.get_or_none(id=category.id)
            if cat is None:
                return await self.send_ethereal(interaction, description="Text games are not enabled in that category.")
            channel = await category.create_text_channel(name=f"new-channel-for-{interaction.user.name}")

        await interaction.response.defer(ephemeral=True)
        
        state = State()
        config = Config(name=name, script=script, seats=seats)
        name = config.name
        
        player_role, st_role = await self.parent._roles.prepare_channel(interaction.guild, channel)
        channel = await channel.edit(name=name)

        created = datetime.now()
        id = Sqids(min_length=8).encode([int(interaction.guild.id), int(created.timestamp())])

        game = await Game.objects.create(
            id=id,
            created=created,
            guild=interaction.guild.id,
            channel=channel.id,
            owner=interaction.user.id,
            player_role=player_role.id,
            st_role=st_role.id,
            config=config.dump(),
            state=state.dump(),
        )
        in_channel = await ActiveGame.objects.create(id=channel.id, game=game)

        as_member = await interaction.guild.fetch_member(interaction.user.id)
        await self.parent._roles.set_role(game, as_member, RoleType.STORYTELLER)

        if script:
            await self.parent.add_script_to_game(game, script)
            await game.update()

        await self.followup_ethereal(interaction, description=f"Created game '{name}' in {channel.mention}.")

    async def mention(self, interaction: Interaction, role: Optional[RoleType], message: str):
        """
        Mentions a role in this game with the given message.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return

        if role is None:
            ping = ""
        else:
            match role:
                case RoleType.PLAYER:
                    if not await self.bot.ensure_privileged(interaction, game):
                        return
                    ping = f"(<@&{game.player_role}>) "
                case RoleType.STORYTELLER:
                    ping = f"(<@&{game.st_role}>) "

        description = f"{ping}{interaction.user.mention} sent the following message:\n>>> {message}"

        thread = await ManagedThread.objects.get_or_none(game=game, type=ThreadType.Announcements)
        if not thread:
            return await self.send_ethereal("There is no announcements thread yet.")

        thread = self.bot.get_channel(thread.id) or await self.bot.fetch_channel(thread.id)
        await thread.send(content=description)

        await self.send_ethereal(interaction, description="Sent an announcement.")

    async def script(self, interaction: Interaction):
        """
        Returns the script details view for the configured script, if any.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return

        config = Config.load(game.config)
        if config.script is not None:
            await ScriptDetailsView.create(interaction=interaction, bot=self.bot, id=config.script, followup=False)
        else:
            await self.send_ethereal(interaction, description="No script has been set.")

    async def signup(self, interaction: Interaction):
        """
        Signs up for the game in this channel.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return
        
        this_signup = await Signup.objects.get_or_none(game=game, member=interaction.user.id)
        if this_signup:
            return await self.send_ethereal(interaction, description=f"You are already signed up for this game!")

        this_user = await Participant.objects.get_or_none(game=game, member=interaction.user.id)
        if this_user:
            return await self.send_ethereal(interaction, description=f"You are already a {this_user.role.value} in this game.")

        signups = await Signup.objects.all(game=game)
        l = len(signups) + 1
        await Signup.objects.create(game=game, member=interaction.user.id)

        def ordinal(i):
            if 11 <= (i % 100) <= 13:
                suf = "th"
            else:
                suf = ["th", "st", "nd", "rd", "th"][min(i % 10, 4)]
            return str(i) + suf
    
        await self.send_ethereal(interaction, description=f"You are the {ordinal(l)} signup!")

    async def transfer(self, interaction: Interaction, user: Member):
        """
        Transfers ownership of this game.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return

        if not await self.bot.ensure_owner(interaction, game):
            return

        owner = await interaction.guild.fetch_member(game.owner)
        await self.parent._roles.set_role(game, owner, RoleType.NONE)
        await self.parent._roles.set_role(game, user, RoleType.STORYTELLER)
        await game.update(owner=user.id)

        game_channel = await self.bot.fetch_channel(game.channel)
        await self.send_ethereal(interaction, description=f"{user.mention} is now the owner of this game.")

        try:
            await user.create_dm()
            await user.dm_channel.send(
                embed=embeds.make_embed(
                    self.bot,
                    title=game_channel.name,
                    description=f"You are now the owner of the game in {game_channel.mention}.",
                )
            )
        except:
            pass

    async def unregister(self, interaction: Interaction):
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return
        
        this_signup = await Signup.objects.get_or_none(game=game, member=interaction.user.id)
        if this_signup is None:
            return await self.send_ethereal(interaction, description="You were not signed up for this game.")
        
        await this_signup.delete()
        await self.send_ethereal(interaction, description="Successfully cancelled your signup.")