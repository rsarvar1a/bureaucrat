import os

from bureaucrat.utility import embeds
from discord.ext import commands
from discord.ext.commands import Context
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


async def setup(bot):
    await bot.add_cog(Administrative(bot))


class Administrative(commands.GroupCog, group_name="administrative"):

    def __init__(self, bot: "Bureaucrat") -> None:
        super().__init__()
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def list_extensions(self, ctx: Context):
        """
        Lists the enabled extensions.
        """
        cogs = "\n".join(f"Bureaucrat.{c}" for c in self.bot.cogs)
        await ctx.reply(
            embed=embeds.make_embed(
                self.bot,
                title="Extensions",
                description=f"The following extensions are currently active: ```py\n{cogs}\n```",
            ),
            ephemeral=True,
        )

    @commands.command()
    @commands.is_owner()
    async def register(self, ctx: Context):
        """
        Registers application commands in the home guild.
        """
        home_guild = await self.bot.fetch_guild(int(os.getenv("HOME_GUILD")))
        self.bot.tree.copy_global_to(guild=home_guild)
        cmds = await self.bot.tree.sync(guild=home_guild)
        await ctx.reply(
            embed=embeds.make_embed(
                self.bot,
                title="Registration",
                description=f"Synced {len(cmds)} commands into home guild {home_guild.name}.",
            ),
            ephemeral=True,
        )

    @commands.command()
    @commands.is_owner()
    async def register_global(self, ctx: Context):
        """
        Registers application commands globally.
        """
        cmds = await self.bot.tree.sync()
        await ctx.reply(
            embed=embeds.make_embed(
                self.bot, title="Registration", description=f"Synced {len(cmds)} commands into the global namespace."
            ),
            ephemeral=True,
        )
