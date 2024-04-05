from bureaucrat.models.games import Game, Kibitz, Participant, RoleType
from bureaucrat.utility import checks, embeds
from discord import ChannelType, Interaction, Member, Guild, Permissions, PermissionOverwrite, Role, TextChannel
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat
    from bureaucrat.games import Games


class Kibitzers:

    def __init__(self, parent: "Games") -> None:
        self.bot: "Bureaucrat" = parent.bot
        self.parent = parent

    async def send_ethereal(self, interaction: Interaction, **kwargs):
        await self.parent.send_ethereal(interaction, title="Kibitz", **kwargs)
    
    async def ensure_kibitz(self, interaction: Interaction, game: Game, silent=False):
        """
        Ensures a kibitz thread exists in this game.
        """
        kibitz = await Kibitz.objects.get_or_none(game=game)
        if kibitz is None:
            if not silent:
                await self.send_ethereal(interaction, description="There is no Kibitz thread in this game.")
            return None
        return kibitz

    async def init(self, interaction: Interaction):
        """
        Initializes Kibitz for the active game.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.parent.ensure_active(interaction)
        if game is None:
            return
        
        if not await self.parent.ensure_privileged(interaction, game):
            return
    
        if await Kibitz.objects.get_or_none(game=game) is not None:
            await self.send_ethereal(interaction, description="There is already an active kibitz thread.")
            return

        channel_id = game.channel
        channel: TextChannel = await interaction.guild.fetch_channel(channel_id)
        thread = await channel.create_thread(name="KIBITZ", type=ChannelType.private_thread)
        role = await interaction.guild.create_role(name=f"kb:{channel.id}", mentionable=False)
        await channel.set_permissions(role, overwrite=PermissionOverwrite(manage_threads=True))

        kibitz = await Kibitz.objects.create(id=thread.id, game=game, role=role.id)
        for st in await Participant.objects.all(game=game, role=RoleType.STORYTELLER):
            user = await interaction.guild.fetch_member(st.member)
            await self._add(game, user)
        
        await self.send_ethereal(interaction, description="Successfully initialized Kibitz.")

    async def _cleanup(self, interaction, game, silent = True):
        """
        Cleans up Kibitz for a given game.
        """
        kibitz = await self.ensure_kibitz(interaction, game, silent)
    
        await interaction.guild.fetch_roles()
        role = interaction.guild.get_role(kibitz.role)
        if role is not None:
            await role.delete()

    async def cleanup(self, interaction: Interaction):
        """
        Cleans up Kibitz for the active game.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.parent.ensure_active(interaction)
        if game is None:
            return
        
        if not await self.parent.ensure_privileged(interaction, game):
            return
    
        await self._cleanup(interaction, game, silent=False)

        await self.send_ethereal(interaction, description="Cleaned up this Kibitz's role.")

    async def _add(self, game: Game, user: Member):
        """
        Adds a user to the kibitz of the given game.
        """
        kibitz = await Kibitz.objects.get_or_none(game=game)
        if kibitz is None:
            return

        guild = user.guild

        await guild.fetch_roles()
        role = guild.get_role(kibitz.role)
        await user.add_roles(role)

        thread = await guild.fetch_channel(kibitz.id)
        await thread.add_user(user)

    async def add(self, interaction: Interaction, user: Member):
        """
        Adds a user to kibitz.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.parent.ensure_active(interaction)
        if game is None:
            return
        
        if not await self.parent.ensure_privileged(interaction, game):
            return
        
        kibitz = await self.ensure_kibitz(interaction, game, silent=False)
        if kibitz is None:
            return
        
        await self._add(game, user)
        await self.send_ethereal(interaction, description=f"Added {user.mention} to Kibitz.")

    async def _remove(self, game: Game, user: Member):
        """
        Removes a user from the kibitz of the given game.
        """
        kibitz = await Kibitz.objects.get_or_none(game=game)
        if kibitz is None:
            return

        guild = user.guild

        await guild.fetch_roles()
        role = guild.get_role(kibitz.role)
        await user.remove_roles(role)

        thread = await guild.fetch_channel(kibitz.id)
        await thread.remove_user(user)

    async def remove(self, interaction: Interaction, user: Member):
        """
        Removes a user from kibitz.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.parent.ensure_active(interaction)
        if game is None:
            return
        
        if not await self.parent.ensure_privileged(interaction, game):
            return
        
        kibitz = await self.ensure_kibitz(interaction, game, silent=False)
        if kibitz is None:
            return
        
        await self._remove(game, user)
        await self.send_ethereal(interaction, description=f"Removed {user.mention} from Kibitz.")
