from bureaucrat.models.games import ActiveCategory
from bureaucrat.utility import checks, embeds
from discord import CategoryChannel, Interaction
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat
    from bureaucrat.games import Games


class Categories:

    def __init__(self, parent: "Games") -> None:
        self.bot = parent.bot
        self.parent = parent

    async def active(self, interaction: Interaction):
        if not await checks.in_guild(self.bot, interaction):
            return

        categories = await ActiveCategory.objects.filter(guild=interaction.guild.id).all()
        categories = "\n".join(f"{i + 1}. <#{category.id}>" for i, category in enumerate(categories))
        description = (
            f"The following categories support text games:\n{categories}"
            if categories != ""
            else "Text games have not been enabled in any category."
        )
        await interaction.response.send_message(
            embed=embeds.make_embed(self.bot, title="Category Management", description=description), ephemeral=True
        )

    async def add(self, interaction: Interaction, category: CategoryChannel):
        if not await checks.in_guild(self.bot, interaction):
            return

        await ActiveCategory.objects.get_or_create(id=category.id, guild=interaction.guild.id)
        await interaction.response.send_message(
            embed=self.category_embed(category, "Enabled"), delete_after=5, ephemeral=True
        )

    def category_embed(self, category, state):
        return embeds.make_embed(
            self.bot, title="Category Management", description=f"{state} text games in category {category.name}."
        )

    async def remove(self, interaction: Interaction, category: CategoryChannel):
        if not await checks.in_guild(self.bot, interaction):
            return

        await ActiveCategory.objects.filter(id=category.id).delete()
        await interaction.response.send_message(
            embed=self.category_embed(category, "Disabled"), delete_after=5, ephemeral=True
        )
