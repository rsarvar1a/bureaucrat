from bureaucrat.models.configure import ormar
from bureaucrat.models.scripts import Script, Document
from bureaucrat.utility import embeds
from discord import ButtonStyle, Interaction, TextStyle, ui
from math import ceil
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


class ScriptListView(ui.View):

    PAGE_SIZE = 10

    def __init__(self, *, bot: "Bureaucrat", query: dict, max_page: int, page_size: int, timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.query = query
        self.page = 1
        self.max = max_page
        self.page_size = page_size

    @ui.button(label="<", disabled=True, style=ButtonStyle.grey)
    async def backwards(self, interaction: Interaction, button: ui.Button):
        self.page -= 1
        self.enable(self.forwards)
        if self.page == 1:
            self.disable(self.backwards)
        await self.update(interaction)

    @ui.button(label=">", disabled=True, style=ButtonStyle.grey)
    async def forwards(self, interaction: Interaction, button: ui.Button):
        self.page += 1
        self.enable(self.backwards)
        if self.page == self.max:
            self.disable(self.forwards)
        await self.update(interaction)

    async def update(self, interaction: Interaction):
        result = await ScriptListView.paginate(self.query, self.page, self.page_size)
        page = await ScriptListView.make_page(bot=self.bot, result=result)
        embed = ScriptListView.make_embed(bot=self.bot, num=self.page, page=page)

        await interaction.response.defer()
        await interaction.edit_original_response(embed=embed, view=self)

    def enable(self, button):
        button.disabled = False
        button.style = ButtonStyle.blurple

    def disable(self, button):
        button.disabled = True
        button.style = ButtonStyle.grey

    @classmethod
    async def create(
        cls,
        *,
        interaction: Interaction,
        bot: "Bureaucrat",
        author: Optional[int] = None,
        name: Optional[str] = None,
        page_size: Optional[int] = None,
        followup: bool = False,
    ):
        if page_size is None:
            page_size = ScriptListView.PAGE_SIZE

        query = {k: v for k, v in {"author": author, "name__contains": name}.items() if v}
        count = await Script.objects.filter(**query).count()
        max_page = int(ceil(float(count) / float(page_size)))

        try:
            page_1_result = await ScriptListView.paginate(query, 1, page_size)
            page = await ScriptListView.make_page(bot=bot, result=page_1_result)
            embed = ScriptListView.make_embed(bot=bot, num=1, page=page)

            view = ScriptListView(bot=bot, query=query, max_page=max_page, page_size=page_size)
            if view.max > 1:
                view.enable(view.forwards)

            if followup:
                await interaction.followup.send(embed=embed, ephemeral=True, view=view)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True, view=view)

        except ormar.NoMatch:
            embed = ScriptListView.make_embed(bot=bot, num=1, page="There were no results.")

            if followup:
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)

    @classmethod
    def make_embed(cls, *, bot, num, page):
        return embeds.make_embed(bot=bot, title=f"Search results (page {num})", description=page)

    @classmethod
    async def make_page(cls, *, bot, result):
        rows = []
        for row in result:
            row: Script = row
            user = await bot.fetch_user(row.author)
            rows.append(
                f"**{row.name}**\n  id `{row.id}`\n  created by {user.mention} on <t:{int(row.created.timestamp())}:f>\n"
            )
        return "\n".join(rows)

    @classmethod
    async def paginate(cls, query, page, page_size):
        rows = await Script.objects.filter(**query).order_by("-created").paginate(page, page_size=page_size).all()
        return rows
