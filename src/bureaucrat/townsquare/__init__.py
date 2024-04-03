from discord import app_commands as apc, Interaction, Member
from discord.ext import commands
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


async def setup(bot):
    await bot.add_cog(TownSquare(bot))


class TownSquare(commands.GroupCog):

    def __init__(self, bot: "Bureaucrat") -> None:
        self.bot = bot
