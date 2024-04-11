from bureaucrat.models.config import Config
from bureaucrat.models.games import Signup, Participant, RoleType
from bureaucrat.utility import checks, embeds
from discord import Interaction, Member
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
        await self.bot.send_ethereal(interaction, title="Signups", **kwargs)

    async def list(self, interaction: Interaction):
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return
        
        signups = await Signup.objects.order_by("id").all(game=game)
        description = "\n".join(f"{i + 1}. <@{s.member}>" for i, s in enumerate(signups))
        description = description if description != "" else "There are no signups."
        await interaction.response.send_message(embed=embeds.make_embed(self.bot, title="Signups", description=description), ephemeral=True)

    async def clear(self, interaction: Interaction):
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return
        
        if not await self.bot.ensure_privileged(interaction, game):
            return
        
        await Signup.objects.filter(game=game).delete()
        await self.send_ethereal(interaction, description="Cleared signups.")

    async def take(self, interaction: Interaction, number: Optional[int]):
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return
        
        if not await self.bot.ensure_privileged(interaction, game):
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

    async def add(self, interaction: Interaction, user: Member):
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return
        
        if not await self.bot.ensure_privileged(interaction, game):
            return

        this_user = await Participant.objects.get_or_none(game=game, member=user.id)
        if this_user:
            return await self.send_ethereal(interaction, description=f"{user.mention} is already a {this_user.role.value} in this game.")
    
        signups = await Signup.objects.all(game=game)
        l = len(signups) + 1
        await Signup.objects.create(game=game, member=user.id)

        def ordinal(i):
            if 11 <= (i % 100) <= 13:
                suf = "th"
            else:
                suf = ["th", "st", "nd", "rd", "th"][min(i % 10, 4)]
            return str(i) + suf

        await self.send_ethereal(interaction, description=f"Added {user.mention} as the {ordinal(l)} signup.")
    
    async def remove(self, interaction: Interaction, user: Member):
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.bot.ensure_active(interaction)
        if game is None:
            return
        
        if not await self.bot.ensure_privileged(interaction, game):
            return
    
        this_signup = Signup.objects.get_or_none(game=game, member=user.id)
        if this_signup is None:
            return await self.send_ethereal(interaction, description=f"{user.mention} was not signed up.")

        await this_signup.delete()
        await self.send_ethereal(interaction, description=f"Removed {user.mention}'s signup.")
