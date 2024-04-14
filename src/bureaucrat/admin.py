import os

from bureaucrat.utility import embeds
from discord import app_commands as apc, Interaction
from discord.ext import commands
from discord.ext.commands import Context
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


async def setup(bot):
    await bot.add_cog(Administrative(bot))


class Administrative(commands.GroupCog, group_name="admin"):

    def __init__(self, bot: "Bureaucrat") -> None:
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def unregister(self, ctx: Context):
        self.bot.tree.clear_commands(guild=ctx.guild)
        await self.bot.tree.sync(guild=ctx.guild)
        await ctx.reply(
            embed=embeds.make_embed(
                self.bot, title="Registration", description=f"Unregistered commands from guild {ctx.guild.name}."
            ),
            ephemeral=True,
        )

    @commands.command()
    @commands.is_owner()
    async def register(self, ctx: Context):
        """
        Register application commands in the home guild.
        """
        home_guild = await self.bot.fetch_guild(int(self.bot.config.home_guild))
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
        Register application commands globally.
        """
        cmds = await self.bot.tree.sync()
        await ctx.reply(
            embed=embeds.make_embed(
                self.bot, title="Registration", description=f"Synced {len(cmds)} commands into the global namespace."
            ),
            ephemeral=True,
        )

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def register_here(self, ctx: Context):
        """
        Register application commands in a specific server.
        """
        self.bot.tree.copy_global_to(guild=ctx.guild)
        cmds = await self.bot.tree.sync(guild=ctx.guild)
        await ctx.reply(
            embed=embeds.make_embed(
                self.bot,
                title="Registration",
                description=f"Synced {len(cmds)} commands into home guild {ctx.guild.name}.",
            ),
            ephemeral=True,
        )

    @apc.command()
    async def owners(self, interaction: Interaction):
        """
        List Bureaucrat's owners.
        """
        description = "\n".join(f"- <@{o}>" for o in self.bot.owner_ids)
        await interaction.response.send_message(
            embed=embeds.make_embed(self.bot, title="Owners", description=description), ephemeral=True
        )

    @apc.command()
    async def extensions(self, interaction: Interaction):
        """
        List Bureaucrat's enabled extensions.
        """
        cogs = "\n".join(f"{i + 1}. `{c.lower()}`" for i, c in enumerate(self.bot.cogs))
        await interaction.response.send_message(
            embed=embeds.make_embed(
                self.bot,
                title="Extensions",
                description=f"The following extensions are currently active:\n{cogs}",
            ),
            ephemeral=True,
        )

    @apc.command()
    async def restart(self, interaction: Interaction):
        """
        Shut down Bureaucrat. If the bot is running in a supervisor, this should restart the process.
        """
        if interaction.user.id != self.bot.owner_id:
            return await interaction.response.send_message(
                bot=self.bot, embed=embeds.unauthorized("You must be a bot owner."), ephemeral=True
            )
        await interaction.response.send_message(
            embed=embeds.make_embed(bot=self.bot, description="Shutting down."), ephemeral=True
        )
        await self.bot.close()
        exit(0)
