from bureaucrat.models.games import ActiveGame, Game, Participant, RoleType
from bureaucrat.utility import checks, embeds
from discord import Interaction, Member, Guild, Permissions, PermissionOverwrite, Role, TextChannel
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat
    from bureaucrat.games import Games


class Roles:

    PLAYER_PERMISSIONS = PermissionOverwrite(
        create_public_threads=False, create_private_threads=True, manage_threads=False
    )

    ST_PERMISSIONS = PermissionOverwrite.from_pair(Permissions.all_channel(), Permissions.none())

    def __init__(self, parent: "Games") -> None:
        self.bot: "Bureaucrat" = parent.bot
        self.parent = parent

    # HELPERS

    async def cleanup(self, guild: Guild, player: int, st: int):
        """
        Deletes game-specific roles from the server.
        """
        await guild.fetch_roles()
        for r in (player, st):
            role = guild.get_role(r)
            if role:
                await role.delete()

    async def make_roles(self, guild: Guild, channel: TextChannel):
        """
        Creates a role pair for a new game.
        """
        player_role = await guild.create_role(name=f"pl:{channel.id}", mentionable=True)
        st_role = await guild.create_role(name=f"st:{channel.id}", mentionable=True)
        return player_role, st_role

    async def prepare_channel(self, guild: Guild, channel: TextChannel):
        """
        Syncs channel permissions with a pair of newly-created roles.
        """
        player, st = await self.make_roles(guild, channel)
        await channel.set_permissions(player, overwrite=Roles.PLAYER_PERMISSIONS)
        await channel.set_permissions(st, overwrite=Roles.ST_PERMISSIONS)
        return player, st

    async def set_role(self, game: Game, user: Member, role: RoleType):
        """
        Sets a single role on a participant, or removes all roles.
        """
        participant = await Participant.objects.get_or_create({"role": RoleType.NONE}, game=game, member=user.id)
        participant = participant[0]
        await participant.update(role=role)

        await user.guild.fetch_roles()
        player = user.guild.get_role(game.player_role)
        st = user.guild.get_role(game.st_role)

        match role:
            case RoleType.PLAYER:
                await user.remove_roles(st)
                await user.add_roles(player)
            case RoleType.STORYTELLER:
                await user.remove_roles(player)
                await user.add_roles(st)
            case RoleType.NONE:
                await user.remove_roles(player, st)
                await participant.delete()

    # APP COMMANDS

    async def list(self, interaction: Interaction, role: Optional[RoleType]):
        """
        Lists all members of a game, optionally filtering by role.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        if not await self.parent.ensure_active(interaction):
            return

        channel_id = self.parent.get_channel_id(interaction.channel)
        in_channel = await ActiveGame.objects.select_related(ActiveGame.game.participants).get(id=channel_id)
        members = [(await interaction.guild.fetch_member(p.member), p.role) for p in in_channel.game.participants]

        segments = []
        for cur_role in [RoleType.STORYTELLER, RoleType.PLAYER]:
            if role is not None and role != cur_role:
                continue
            filtered = [m[0] for m in members if cur_role == m[1]]
            member_list = "\n".join(
                f"{i + 1}. {member.mention}" for i, member in enumerate(sorted(filtered, key=lambda u: u.display_name))
            )
            member_list = "none" if member_list == "" else f"\n{member_list}"
            header = f"**{cur_role.value}s**"
            segments.append(f"{header}: {member_list}")
        listing = "\n".join(segments)

        title = "Participants"
        description = listing

        await interaction.response.send_message(
            embed=embeds.make_embed(self.bot, title=title, description=description), ephemeral=True
        )

    async def remove(self, interaction: Interaction, user: Member):
        """
        Removes a member from the game.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.parent.ensure_active(interaction)
        if game is None:
            return

        if not await self.parent.ensure_privileged(interaction, game):
            return

        role = await Participant.objects.get_or_none(game=game, member=user.id)
        if role:
            await self.set_role(game, user, RoleType.NONE)
            await interaction.response.send_message(
                embed=embeds.make_embed(
                    self.bot, title="Participants", description=f"{user.mention} has been removed from the game."
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embeds=embeds.make_embed(
                    self.bot, title="Participants", description=f"{user.mention} is not registered for this game."
                )
            )

    async def set(self, interaction: Interaction, user: Member, role: RoleType):
        """
        Adds or edits a member in the game.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.parent.ensure_active(interaction)
        if game is None:
            return

        if not await self.parent.ensure_privileged(interaction, game):
            return

        participant = await Participant.objects.get_or_none(game=game, member=user.id)
        if participant and participant.role == role:
            await interaction.response.send_message(
                embed=embeds.make_embed(
                    self.bot, title="Participants", description=f"{user.mention} is already a {role.value}."
                ),
                ephemeral=True,
            )
        else:
            await self.set_role(game, user, role)
            await interaction.response.send_message(
                embed=embeds.make_embed(
                    self.bot, title="Participants", description=f"{user.mention} is now a {role.value}."
                ),
                ephemeral=True,
            )
