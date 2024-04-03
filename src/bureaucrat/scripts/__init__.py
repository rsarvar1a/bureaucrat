from bureaucrat.models.configure import CONFIG, ormar
from bureaucrat.models.scripts import Script, Document
from bureaucrat.utility import embeds
from discord import app_commands as apc, Attachment, Interaction, Member
from discord.ext import commands
from typing import TYPE_CHECKING, Optional

from .details import ScriptDetailsView
from .listing import ScriptListView
from .new import NewScriptView

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


async def setup(bot):
    await bot.add_cog(Scripts(bot))


class Scripts(commands.GroupCog, group_name="scripts"):

    def __init__(self, bot: "Bureaucrat") -> None:
        super().__init__()
        self.bot = bot

    @apc.command()
    @CONFIG.database.transaction()
    async def delete(self, interaction: Interaction, id: str) -> None:
        """
        Delete one of your scripts.
        """
        try:
            script = await Script.objects.get(id=id)
            if script.author != interaction.user.id:
                user = await self.bot.fetch_user(script.author)
                return await interaction.response.send_message(
                    embed=embeds.unauthorized(self.bot, f"You are not the owner of this script, {user.mention} is."),
                    ephemeral=True,
                )
            await self.bot.aws.s3_delete(bucket="scripts", prefix=script.id)
            await Document.objects.delete(script=script)
            await Script.objects.delete(id=id)
        except ormar.NoMatch as e:
            pass

        await interaction.response.send_message(
            embed=embeds.make_embed(self.bot, title="Script Management", description=f"Deleted script `{id}`."),
            ephemeral=True,
        )

    @apc.command()
    async def details(self, interaction: Interaction, id: str) -> None:
        """
        Get information about a script, or download it.
        """
        await ScriptDetailsView.create(interaction=interaction, bot=self.bot, id=id, followup=False)

    @apc.command()
    @apc.describe(user="Search by script author.")
    @apc.describe(name="Search by script title.")
    @apc.describe(page_size="Number of scripts per page (default 10).")
    async def list(self, interaction: Interaction, user: Optional[Member], name: Optional[str], page_size: Optional[int]) -> None:
        """
        Search for scripts by author or name.
        """
        user_id = user.id if user else None
        await ScriptListView.create(interaction=interaction, bot=self.bot, author=user_id, name=name, page_size=page_size, followup=False)

    @apc.command()
    async def new(self, interaction: Interaction, attachment: Optional[Attachment]) -> None:
        """
        Create a new script from a script.json file.
        """
        await NewScriptView.create(attachment=attachment, interaction=interaction, bot=self.bot)
