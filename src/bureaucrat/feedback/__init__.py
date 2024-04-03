from bureaucrat.utility import embeds
from discord import app_commands as apc, Interaction, Member
from discord.ext import commands
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


async def setup(bot):
    await bot.add_cog(Feedback(bot))


class Feedback(commands.GroupCog):
    pass
