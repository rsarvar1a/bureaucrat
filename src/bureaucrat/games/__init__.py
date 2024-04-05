import pydantic

from bureaucrat.models.games import ActiveCategory, ActiveGame, Game, Participant
from bureaucrat.utility import checks, embeds
from discord import app_commands as apc, CategoryChannel, Member, Interaction, Thread
from discord.abc import GuildChannel
from discord.ext import commands
from typing import Optional, TYPE_CHECKING, Coroutine, Any

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat

from .categories import Categories
from .configure import Configure
from .kibitz import Kibitzers
from .roles import Roles, RoleType
from .toplevel import TopLevel


async def setup(bot):
    await bot.add_cog(Games(bot))


class Games(commands.GroupCog, group_name="game", description="Commands for managing and running text games."):

    def __init__(self, bot: "Bureaucrat") -> None:
        super().__init__()
        self.bot = bot
        self._toplevel = TopLevel(self)
        self._categories = Categories(self)
        self._configure = Configure(self)
        self._kibitz = Kibitzers(self)
        self._roles = Roles(self)

    # HELPERS

    async def ensure_active(self, interaction: Interaction) -> Optional[Game]:
        """
        Ensures that this channel has an active game.
        """
        in_channel: Optional[Game] = await self.get_active_game(interaction.channel)
        if in_channel is None:
            await interaction.response.send_message(
                embed=embeds.make_error(self.bot, message="There is no active game in this channel."), delete_after=5, ephemeral=True
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
                embed=embeds.make_error(self.bot, message="Text games are not enabled in this category."), delete_after=5, ephemeral=True
            )
            return False
        return True

    async def ensure_owner(self, interaction, game: Game):
        """
        Ensures the invoker is the owner of the current game.
        """
        if interaction.user.id != game.owner:
            await interaction.response.send_message(
                embeds.unauthorized(self.bot, message=f"You are not the owner of this game, <@{game.owner}> is."),
                delete_after=5, ephemeral=True,
            )
            return False
        return True

    async def ensure_privileged(self, interaction: Interaction, game: Game):
        """
        Ensures the invoker is the owner of the game or a storyteller.
        """
        as_member = await interaction.guild.fetch_member(interaction.user.id)
        participant = await Participant.objects.get_or_none(game=game, member=as_member.id)
        if game.owner != as_member.id and participant.role != RoleType.STORYTELLER:
            await interaction.response.send_message(
                embed=embeds.unauthorized(self.bot, message="You must be a storyteller or game owner."), delete_after=5, ephemeral=True
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
        await interaction.response.send_message(embed=embeds.make_embed(self.bot, **kwargs), delete_after=5, ephemeral=True)

    # TOP LEVEL

    @apc.command()
    async def end(self, interaction: Interaction):
        """
        End the running game in this channel, provided you are its owner.
        """
        await self._toplevel.end(interaction)

    @apc.command()
    @apc.choices(
        role=[
            apc.Choice(name="Player", value=1),
            apc.Choice(name="Storyteller", value=2),
        ]
    )
    @apc.describe(role="The role to ping.")
    @apc.describe(message="What you'd like to say.")
    async def mention(self, interaction: Interaction, role: Optional[apc.Choice[int]], message: str):
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

    @apc.command()
    @apc.describe(name="The name of the new game's channel.")
    @apc.describe(script="The id of an existing script.")
    async def new(self, interaction: Interaction, name: Optional[str], script: Optional[str]):
        """
        Create a new game in an empty channel.
        """
        await self._toplevel.new(interaction, name=name, script=script)

    @apc.command()
    async def script(self, interaction: Interaction):
        """
        Opens a script details view, if a script exists.
        """
        await self._toplevel.script(interaction)

    @apc.command()
    @apc.describe(user="A server member.")
    async def transfer(self, interaction: Interaction, user: Member):
        """
        Transfer ownership of this game to the given user.
        """
        await self._toplevel.transfer(interaction, user)

    # CATEGORY MANAGEMENT

    categories = apc.Group(name="categories", description="Configure which categories in your server allow text games.")

    @categories.command()
    async def active(self, interaction: Interaction):
        """
        List categories that support text games.
        """
        await self._categories.active(interaction)

    @categories.command()
    @apc.checks.has_permissions(manage_guild=True)
    @apc.describe(category="The category to activate.")
    async def add(self, interaction: Interaction, category: CategoryChannel):
        """
        Enable text games in a category.
        """
        await self._categories.add(interaction, category)

    @categories.command()
    @apc.checks.has_permissions(manage_guild=True)
    @apc.describe(category="The category to deactivate.")
    async def remove(self, interaction: Interaction, category: CategoryChannel):
        """
        Disable text games in a category.
        """
        await self._categories.add(interaction, category)

    # GAME CONFIGURATION

    configure = apc.Group(name="config", description="Configure one of your games.")

    @configure.command()
    async def show(self, interaction: Interaction):
        """
        Show the game's configuration.
        """
        await self._configure.show(interaction)

    @configure.command()
    async def edit(self, interaction: Interaction, name: Optional[str], script: Optional[str]):
        """
        Edit the game's configuration.
        """
        await self._configure.edit(interaction, name=name, script=script)

    # KIBITZ MANAGEMENT

    kibitz = apc.Group(name="kibitz", description="Control spectator access.")

    @kibitz.command()
    async def init(self, interaction: Interaction):
        """
        Create a kibitz thread and role.
        """
        await self._kibitz.init(interaction)
    
    @kibitz.command()
    async def cleanup(self, interaction: Interaction):
        """
        Clean up a kibitz thread's role. This does not delete the thread or its contents.
        """
        await self._kibitz.cleanup(interaction)

    @kibitz.command()
    async def add(self, interaction: Interaction, user: Member):
        """
        Add a server member into the kibitz thread.
        """
        await self._kibitz.add(interaction, user)

    @kibitz.command()
    async def remove(self, interaction: Interaction, user: Member):
        """
        Remove a member from kibitz.
        """
        await self._kibitz.remove(interaction, user)

    # ROLE MANAGEMENT

    roles = apc.Group(name="roles", description="Set permissions for players and storytellers.")

    @roles.command()
    @apc.choices(
        role=[
            apc.Choice(name="Player", value=1),
            apc.Choice(name="Storyteller", value=2),
        ]
    )
    @apc.describe(role="Filter users by a specific role.")
    async def list(self, interaction: Interaction, role: Optional[apc.Choice[int]]):
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

    @roles.command()
    @apc.describe(user="A server member.")
    async def remove(self, interaction: Interaction, user: Member):
        """
        Removes a user from the game.
        """
        await self._roles.remove(interaction, user)

    @roles.command()
    @apc.choices(
        role=[
            apc.Choice(name="Player", value=1),
            apc.Choice(name="Storyteller", value=2),
        ]
    )
    @apc.describe(role="The role to assign to this user.")
    @apc.describe(user="A server member.")
    async def set(self, interaction: Interaction, user: Member, role: apc.Choice[int]):
        """
        Set a user's role in the game.
        """
        match role.value:
            case 1:
                r = RoleType.PLAYER
            case 2:
                r = RoleType.STORYTELLER
            
        await self._roles.set(interaction, user, r)
