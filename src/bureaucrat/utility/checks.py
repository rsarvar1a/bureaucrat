from discord import Interaction
from . import embeds


async def in_guild(bot, interaction: Interaction, silent=False):
    if interaction.guild is None:
        if not silent:
            await interaction.response.send_message(embed=embeds.guild_only(bot), ephemeral=True)
        return False
    return True
