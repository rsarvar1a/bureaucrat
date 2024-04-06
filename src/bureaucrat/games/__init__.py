import pydantic

from bureaucrat.models.games import ActiveCategory, ActiveGame, Game, Participant
from bureaucrat.utility import checks, embeds
from discord import app_commands as apc, CategoryChannel, Member, Interaction, Thread
from discord.abc import GuildChannel
from discord.ext import commands
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat

from .categories import Categories
from .configure import Configure
from .kibitz import Kibitzers
from .reminders import Reminders
from .roles import Roles, RoleType
from .signups import Signups
from .toplevel import TopLevel


async def setup(bot):
    await bot.add_cog(Games(bot))


class Games(commands.GroupCog, group_name="game", description="Commands for managing and running text games."):

    def __init__(self, bot: "Bureaucrat") -> None:
        self.bot = bot

        self._toplevel = TopLevel(self)
        self._categories = Categories(self)
        self._configure = Configure(self)
        self._kibitz = Kibitzers(self)
        self._reminders = Reminders(self)
        self._roles = Roles(self)
        self._signups = Signups(self)

    # HELPERS

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

    async def ensure_active_category(self, interaction: Interaction):
        """
        Ensures the category allows text games.
        """
        category = interaction.channel.category
        if category is None:
            await interaction.response.send_message(
                embed=embeds.make_error(self.bot, message="You must be in a category."), delete_after=5, ephemeral=True
            )
            return False
        elif await ActiveCategory.objects.get_or_none(id=category.id) is None:
            await interaction.response.send_message(
                embed=embeds.make_error(self.bot, message="Text games are not enabled in this category."),
                delete_after=5,
                ephemeral=True,
            )
            return False
        return True

    async def ensure_owner(self, interaction, game: Game):
        """
        Ensures the invoker is the owner of the current game.
        """
        if interaction.user.id in self.bot.owner_ids:
            return True
        
        if interaction.user.id != game.owner:
            await interaction.response.send_message(
                embed=embeds.unauthorized(self.bot, message=f"You are not the owner of this game, <@{game.owner}> is."),
                delete_after=5,
                ephemeral=True,
            )
            return False
        return True

    async def ensure_privileged(self, interaction: Interaction, game: Game):
        """
        Ensures the invoker is the owner of the game or a storyteller.
        """
        if interaction.user.id in self.bot.owner_ids:
            return True
        
        as_member = await interaction.guild.fetch_member(interaction.user.id)
        participant = await Participant.objects.get_or_none(game=game, member=as_member.id)
        if game.owner != as_member.id and participant.role != RoleType.STORYTELLER:
            await interaction.response.send_message(
                embed=embeds.unauthorized(self.bot, message="You must be a storyteller or game owner."),
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
        await interaction.followup.send(embed=embeds.make_embed(self.bot, **kwargs), ephemeral=True)

    async def send_ethereal(self, interaction: Interaction, **kwargs):
        """
        Sends an ethereal message, which is an autodeleting ephemeral.
        """
        await interaction.response.send_message(
            embed=embeds.make_embed(self.bot, **kwargs), delete_after=5, ephemeral=True
        )

    # TOP LEVEL

    @apc.command(name="end")
    async def toplevel_end(self, interaction: Interaction):
        """
        End the running game in this channel, provided you are its owner.
        """
        await self._toplevel.end(interaction)

    @apc.command(name="mention")
    @apc.choices(
        role=[
            apc.Choice(name="Player", value=1),
            apc.Choice(name="Storyteller", value=2),
        ]
    )
    @apc.describe(role="The role to ping.")
    @apc.describe(message="What you'd like to say.")
    async def toplevel_mention(self, interaction: Interaction, role: Optional[apc.Choice[int]], message: str):
        """
        Make an announcement that pings the given role.
        """
        if role is None:
            r = None
        else:
            match role.value:
                case 1:
                    r = RoleType.PLAYER
                case 2:
                    r = RoleType.STORYTELLER
                case _:
                    r = None

        await self._toplevel.mention(interaction, r, message)

    @apc.command(name="new")
    @apc.describe(name="The name of the new game's channel.")
    @apc.describe(script="The id of an existing script.")
    async def toplevel_new(self, interaction: Interaction, name: Optional[str], script: Optional[str], seats: Optional[int]):
        """
        Create a new game in an empty channel.
        """
        await self._toplevel.new(interaction, name=name, script=script, seats=seats)

    @apc.command(name="signup")
    async def toplevel_signup(self, interaction: Interaction):
        """
        Sign up for the game in this channel.
        """
        await self._toplevel.signup(interaction)

    @apc.command(name="script")
    async def toplevel_script(self, interaction: Interaction):
        """
        Opens a script details view, if a script exists.
        """
        await self._toplevel.script(interaction)

    @apc.command(name="transfer")
    @apc.describe(user="A server member.")
    async def toplevel_transfer(self, interaction: Interaction, user: Member):
        """
        Transfer ownership of this game to the given user.
        """
        await self._toplevel.transfer(interaction, user)

    @apc.command(name="unregister")
    async def toplevel_unregister(self, interaction: Interaction):
        """
        Remove your signup from this game.
        """
        await self._toplevel.unregister(interaction)

    # CATEGORY MANAGEMENT

    categories = apc.Group(name="categories", description="Configure which categories in your server allow text games.")

    @categories.command(name="active")
    async def categories_active(self, interaction: Interaction):
        """
        List categories that support text games.
        """
        await self._categories.active(interaction)

    @categories.command(name="add")
    @apc.checks.has_permissions(manage_guild=True)
    @apc.describe(category="The category to activate.")
    async def categories_add(self, interaction: Interaction, category: CategoryChannel):
        """
        Enable text games in a category.
        """
        await self._categories.add(interaction, category)

    @categories.command(name="remove")
    @apc.checks.has_permissions(manage_guild=True)
    @apc.describe(category="The category to deactivate.")
    async def categories_remove(self, interaction: Interaction, category: CategoryChannel):
        """
        Disable text games in a category.
        """
        await self._categories.add(interaction, category)

    # GAME CONFIGURATION

    configure = apc.Group(name="config", description="Configure one of your games.")

    @configure.command(name="show")
    async def configure_show(self, interaction: Interaction):
        """
        Show the game's configuration.
        """
        await self._configure.show(interaction)

    @configure.command(name="edit")
    async def configure_edit(self, interaction: Interaction, name: Optional[str], script: Optional[str], seats: Optional[int]):
        """
        Edit the game's configuration.
        """
        await self._configure.edit(interaction, name=name, script=script, seats=seats)

    # KIBITZ MANAGEMENT

    kibitz = apc.Group(name="kibitz", description="Control spectator access.")

    @kibitz.command(name="init")
    async def kibitz_init(self, interaction: Interaction):
        """
        Create a kibitz thread and role.
        """
        await self._kibitz.init(interaction)

    @kibitz.command(name="cleanup")
    async def kibitz_cleanup(self, interaction: Interaction):
        """
        Clean up a kibitz thread's role. This does not delete the thread or its contents.
        """
        await self._kibitz.cleanup(interaction)

    @kibitz.command(name="add")
    async def kibitz_add(self, interaction: Interaction, user: Member):
        """
        Add a server member into the kibitz thread.
        """
        await self._kibitz.add(interaction, user)

    @kibitz.command(name="remove")
    async def kibitz_remove(self, interaction: Interaction, user: Member):
        """
        Remove a member from kibitz.
        """
        await self._kibitz.remove(interaction, user)

    # REMINDERS

    reminders = apc.Group(name="reminders", description="Manage reminders on a game.")

    @reminders.command(name="delete")
    @apc.describe(id="The reminder id.")
    async def reminders_delete(self, interaction: Interaction, id: str):
        """
        Delete an active reminder.
        """
        await self._reminders.delete(interaction, id)

    @reminders.command(name="list")
    async def reminders_list(self, interaction: Interaction):
        """
        List all reminders on the active game.
        """
        await self._reminders.list(interaction)

    @reminders.command(name="new")
    @apc.describe(message="The reminder message.")
    @apc.describe(duration="The duration this reminder should last for, in 99d23h59m59s format.")
    @apc.describe(intervals="A list of times from expiry to ping this reminder at.")
    async def reminders_new(self, interaction: Interaction, message: str, duration: str, intervals: Optional[str]):
        """
        Set a new reminder with a given expiry duration.
        """
        await self._reminders.new(interaction, message, duration, intervals)

    @reminders.command(name="push")
    @apc.describe(id="The id of the reminder.")
    @apc.describe(duration="The new expiry duration of the reminder.")
    async def reminders_push(self, interaction: Interaction, id: str, duration: str):
        """
        Push back a reminder, refreshing the expiry date and rearming the reminder's ping intervals.
        """
        await self._reminders.push(interaction, id, duration)

    # ROLE MANAGEMENT

    roles = apc.Group(name="roles", description="Set permissions for players and storytellers.")

    @roles.command(name="list")
    @apc.choices(
        role=[
            apc.Choice(name="Player", value=1),
            apc.Choice(name="Storyteller", value=2),
        ]
    )
    @apc.describe(role="Filter users by a specific role.")
    async def roles_list(self, interaction: Interaction, role: Optional[apc.Choice[int]]):
        """
        List all users in the game.
        """
        if role is None:
            r = None
        else:
            match role.value:
                case 1:
                    r = RoleType.PLAYER
                case 2:
                    r = RoleType.STORYTELLER
                case _:
                    r = None

        await self._roles.list(interaction, r)

    @roles.command(name="remove")
    @apc.describe(user="A server member.")
    async def roles_remove(self, interaction: Interaction, user: Member):
        """
        Removes a user from the game.
        """
        await self._roles.remove(interaction, user)

    @roles.command(name="set")
    @apc.choices(
        role=[
            apc.Choice(name="Player", value=1),
            apc.Choice(name="Storyteller", value=2),
        ]
    )
    @apc.describe(role="The role to assign to this user.")
    @apc.describe(user="A server member.")
    async def roles_set(self, interaction: Interaction, user: Member, role: apc.Choice[int]):
        """
        Set a user's role in the game.
        """
        match role.value:
            case 1:
                r = RoleType.PLAYER
            case 2:
                r = RoleType.STORYTELLER

        await self._roles.set(interaction, user, r)

    # SIGNUPS

    signups = apc.Group(name="signups", description="Track signups for your game.")

    @signups.command(name="clear")
    async def signups_clear(self, interaction: Interaction):
        """
        Clear signups.
        """
        await self._signups.clear(interaction)

    @signups.command(name="list")
    async def signups_list(self, interaction: Interaction):
        """
        See all signups for your game.
        """
        await self._signups.list(interaction)

    @signups.command(name="take")
    @apc.describe(number="The number of signups to take.")
    async def signups_take(self, interaction: Interaction, number: Optional[int]):
        """
        Take the first n signups and turn them into players.
        """
        await self._signups.take(interaction, number)
