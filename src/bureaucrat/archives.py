from bureaucrat.models.archives import ArchiveCategory
from bureaucrat.models.games import ActiveGame
from bureaucrat.utility import checks, embeds
from datetime import datetime
from discord import app_commands as apc, Interaction, CategoryChannel
from discord.ext import commands
from discord.ext.commands import Context
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


async def setup(bot):
    await bot.add_cog(Archives(bot))


class Archives(commands.GroupCog, group_name="archives"):

    def __init__(self, bot: "Bureaucrat") -> None:
        self.bot = bot

    async def send_ethereal(self, interaction: Interaction, **kwargs):
        await self.bot.send_ethereal(interaction, title="Archives", **kwargs)

    @apc.command()
    async def add(self, interaction: Interaction):
        """
        Adds the current channel to the archive.
        """
        if not await checks.in_guild(self.bot, interaction):
            return
        
        game = await self.bot.ensure_active(interaction)
        if game is None:
            return
        
        archive = await ArchiveCategory.objects.get_or_none(id=interaction.guild.id)
        if archive is None:
            return await self.send_ethereal(interaction, description="Archives are not enabled in this server.")
        
        category = self.bot.get_channel(archive.category) or await self.bot.fetch_channel(archive.category)
        channel = self.bot.get_channel(game.channel) or await self.bot.fetch_channel(game.channel)
        timestamp = datetime.now()
        date = f"{timestamp.year:04}{timestamp.month:02}{timestamp.day:02}"

        await channel.edit(name=f"{date}-{channel.name}", category=category, position=0)
        await self.send_ethereal(interaction, description=f"Archived as {channel.mention}.")

    @apc.command()
    @apc.checks.has_permissions(manage_guild=True)
    @apc.describe(category="The category to move archived games into.")
    async def set(self, interaction: Interaction, category: CategoryChannel):
        """
        Sets the archive category in this server.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        archive = await ArchiveCategory.objects.get_or_create({"category": category.id}, id=interaction.guild.id)
        archive = archive[0]
        archive.category = category.id
        await archive.update()

        await self.send_ethereal(interaction, description=f"{category.mention} is now the archive category in this server.")
    
    @apc.command()
    async def where(self, interaction: Interaction):
        """
        Retrieves the archive category in this server, if one is set.
        """
        if not await checks.in_guild(self.bot, interaction):
            return

        archive = await ArchiveCategory.objects.get_or_none(id=interaction.guild.id)
        if archive is None:
            await self.send_ethereal(interaction, description="An archive has not been enabled in this server.")
        else:
            await self.send_ethereal(interaction, description=f"This server's archive is currently in <#{archive.category}>.")
