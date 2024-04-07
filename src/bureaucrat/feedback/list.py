from bureaucrat.models.feedback import Feedback
from bureaucrat.models.games import Game
from bureaucrat.utility import ormar, embeds
from datetime import datetime
from discord import Attachment, ButtonStyle, Interaction, TextStyle, ui
from typing import Optional, TYPE_CHECKING, List

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat
 

class FeedbackListView(ui.View):

    def __init__(self, *, parent, query: dict, max_page: int, timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.parent = parent
        self.bot = parent.bot
        self.query = query
        self.page = 1
        self.max = max_page
    
    @ui.button(label="<", disabled=True, style=ButtonStyle.gray)
    async def prev(self, interaction: Interaction, button: ui.Button):
        self.page -= 1
        self.enable(self.next)
        if self.page == 1:
            self.disable(self.prev)
        await self.update(interaction)

    @ui.button(label=">", disabled=True, style=ButtonStyle.grey)
    async def next(self, interaction: Interaction, button: ui.Button):
        self.page += 1
        self.enable(self.prev)
        if self.page == self.max:
            self.disable(self.next)
        await self.update(interaction)
    
    def make_page(self, entry: Feedback):
        submitter = "anonymously" if entry.anonymous else f"by <@{entry.submitter}>"
        header = f"Feedback for <#{entry.game.channel}>\nSubmitted {submitter} <t:{int(entry.created.timestamp())}:R>"
        description = self.parent.make_embed(entry, header)
        return embeds.make_embed(self.bot, title=f"Feedback (page {self.page} of {self.max})", description=description)

    async def paginate(self):
        return await Feedback.objects.select_related(Feedback.game).filter(**self.query).order_by("-created").paginate(self.page, page_size=1).get()

    async def update_meta(self):
        self.max = await Feedback.objects.filter(**self.query).count()

    async def update(self, interaction):
        await self.update_meta()
        result = await self.paginate()
        embed = self.make_page(result=result)
        await interaction.response.defer()
        await interaction.edit_original_response(embed=embed, view=self)

    @classmethod
    async def create(self, *, parent, interaction: Interaction, game: Optional[Game], followup: bool = False):

        query = {k: v for k, v in {"game": game, "storyteller": interaction.user.id}.items() if v}
        count = await Feedback.objects.filter(**query).count()
        view = FeedbackListView(parent=parent, query=query, max_page=count)

        try:
            page_1 = await view.paginate()
            embed = view.make_page(page_1)
            if view.max > 1:
                view.enable(view.next)

            if followup:
                await interaction.followup.send(embed=embed, ephemeral=True, view=view)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True, view=view)
        
        except ormar.NoMatch:    
            embed = embeds.make_embed(bot=parent.bot, title="Feedback", description="There were no results.")
            if followup:
                await interaction.followup.send(embed=embed, ephemeral=True, view=view)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True, view=view)
        