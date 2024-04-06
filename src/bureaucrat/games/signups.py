from bureaucrat.models.games import Signup
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
