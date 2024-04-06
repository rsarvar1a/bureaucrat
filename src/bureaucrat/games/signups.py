from bureaucrat.models.games import Signup, Config, Participant, RoleType
from bureaucrat.utility import checks, embeds
from discord import Interaction
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat
    from bureaucrat.games import Games


class Signups:

    def __init__(self, parent: "Games") -> None:
        self.bot: "Bureaucrat" = parent.bot
        self.parent = parent
    
    async def send_ethereal(self, interaction: Interaction, **kwargs):
        await self.parent.send_ethereal(interaction, title="Signups", **kwargs)

    async def list(self, interaction: Interaction):
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.parent.ensure_active(interaction)
        if game is None:
            return
        
        signups = await Signup.objects.order_by("id").all(game=game)
        description = "\n".join(f"{i + 1}. <@{s.member}>" for i, s in enumerate(signups))
        description = description if description != "" else "There are no signups."

        await interaction.response.send_message(embed=embeds.make_embed(self.bot, title="Signups", description=description), ephemeral=True)

    async def clear(self, interaction: Interaction):
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.parent.ensure_active(interaction)
        if game is None:
            return
        
        if not await self.parent.ensure_privileged(interaction, game):
            return
        
        await Signup.objects.filter(game=game).delete()
        await self.send_ethereal(interaction, description="Cleared signups.")

    async def take(self, interaction: Interaction, number: Optional[int]):
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.parent.ensure_active(interaction)
        if game is None:
            return
        
        if not await self.parent.ensure_privileged(interaction, game):
            return

        config = Config.load(game.config)
        
        filled = await Participant.objects.filter(game=game, role=RoleType.PLAYER).count()
        available = max(config.seats - filled, 0)
        to_take = number if number else available

        if to_take > available:
            return await self.send_ethereal(interaction, description="You are trying to take more signups than there are seats.")
        
        signups = await Signup.objects.filter(game=game).order_by("id").limit(to_take).all()
        for signup in signups:
            guild = interaction.guild
            member = guild.get_member(signup.member) or await guild.fetch_member(signup.member)
            await self.parent._roles.set_role(game, member, RoleType.PLAYER)
            await signup.delete()
        
        await self.send_ethereal(interaction, description=f"Took {len(signups)} signups.")
