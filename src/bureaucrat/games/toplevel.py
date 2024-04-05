from bureaucrat.models.configure import ormar
from bureaucrat.models import games
from bureaucrat.models.games import ActiveGame, Game, Config, State
from bureaucrat.models.scripts import Script
from bureaucrat.scripts.details import ScriptDetailsView
from bureaucrat.utility import checks, embeds
from discord import Interaction, Member
from typing import TYPE_CHECKING, Optional

from .roles import RoleType

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat
    from bureaucrat.games import Games


class TopLevel:

    def __init__(self, parent: "Games") -> None:
        self.bot: "Bureaucrat" = parent.bot
        self.parent = parent

    async def end(self, interaction: Interaction):
        """
        Ends the active game in this channel, freeing it up.
        """
        if not await checks.in_guild(self.bot, interaction):
            return
        
        game = await self.parent.ensure_active(interaction)
        if game is None:
            return
        
        if not await self.parent.ensure_owner(interaction, game):
            return
        
        await ActiveGame.objects.filter(game=game).delete()
        await self.parent._roles.cleanup(interaction.guild, game.player_role, game.st_role)

        await interaction.response.send_message(embed=embeds.make_embed(self.bot, title="Deleted Game", description="This channel has been freed up."), ephemeral=True)

    async def new(self, interaction: Interaction, *, name: Optional[str], script: Optional[str]):
        """
        Creates a new game in the given channel.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        if await self.parent.get_active_game(interaction.channel):
            return await interaction.response.send_message(
                embed=embeds.make_error(self.bot, message="There is already an active game here."), ephemeral=True
            )

        if not await self.parent.ensure_active_category(interaction):
            return

        channel_id = self.parent.get_channel_id(interaction.channel)
        channel = await interaction.guild.fetch_channel(channel_id)
        player_role, st_role = await self.parent._roles.prepare_channel(interaction.guild, channel)

        name = name if name else "new-game"
        channel = await channel.edit(name=name)

        config = Config(name=name, script=script)
        state = State()

        game = await Game.objects.create(
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

        await interaction.response.send_message(
            embed=embeds.make_embed(
                self.bot, title="New Game", description=f"Created game '{name}' in {channel.mention}."
            ),
            ephemeral=True,
        )

    async def script(self, interaction: Interaction):
        """
        Returns the script details view for the configured script, if any.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.parent.ensure_active(interaction)
        if game is None:
            return

        config = Config.load(game.config)
        if config.script is not None:
            await ScriptDetailsView.create(interaction=interaction, bot=self.bot, id=config.script, followup=False)
        else:
            await interaction.response.send_message(
                embed=embeds.make_error(self.bot, message="No script has been set."), ephemeral=True
            )

    async def transfer(self, interaction: Interaction, user: Member):
        """
        Transfers ownership of this game.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.parent.ensure_active(interaction)
        if game is None:
            return

        if not await self.parent.ensure_owner(interaction, game):
            return

        owner = await interaction.guild.fetch_member(game.owner)
        await self.parent._roles.set_role(game, owner, RoleType.NONE)
        await self.parent._roles.set_role(game, user, RoleType.STORYTELLER)
        await game.update(owner=user.id)

        game_channel = await self.bot.fetch_channel(game.channel)
        await interaction.response.send_message(
            embed=embeds.make_embed(
                self.bot, title=game_channel.name, description=f"{user.mention} is now the owner of this game."
            ),
            ephemeral=True,
        )
        await user.dm_channel.send(
            embed=embeds.make_embed(
                self.bot,
                title=game_channel.name,
                description=f"You are now the owner of the game in {game_channel.mention}.",
            )
        )
