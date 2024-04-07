from bureaucrat.models.feedback import Feedback
from bureaucrat.models.games import Game
from bureaucrat.utility import embeds
from datetime import datetime
from discord import Attachment, ButtonStyle, Interaction, SelectOption, TextStyle, ui 
from sqids.sqids import Sqids
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat
 

class FeedbackCommentsModal(ui.Modal, title="Input your comments!"):
    """
    A Discord modal for comments submission, as a part of feedback creation.
    """
    
    feedback = ui.TextInput(label="Feedback", placeholder="Do you have any specific and constructive feedback for the Storyteller?", style=TextStyle.paragraph, max_length=500, required=False)
    comments = ui.TextInput(label="Other Comments", placeholder="Do you have any other comments?", style=TextStyle.paragraph, max_length=500, required=False)

    def with_parent(self, parent):
        self.parent = parent
        return self

    async def on_submit(self, interaction: Interaction) -> None:
        self.parent.feedback.feedback = self.feedback.value if self.feedback.value else None
        self.parent.feedback.comments = self.comments.value if self.comments.value else None
        await self.parent.update(interaction)
        self.stop()

class NewFeedbackView(ui.View):
    """
    A Discord view for feedback creation.
    It allows the user to submit paragraph-style comments and improvements.
    It also allows the user to score the game.
    """

    OPTIONS = [
        {
            "label": "Enjoyability",
            "description": "Was the game fun regardless of if you won or lost?"
        },
        {
            "label": "Organization",
            "description": "Was this game well-organized?"
        },
        {
            "label": "Pacing",
            "description": "Did the game's phases run smoothly, or were they rushed?"
        },
        {
            "label": "Attentiveness",
            "description": "Was the ST's decision making reasonable?"
        }
    ]

    def __init__(self, *, parent, game: Game, interaction: Interaction, anonymous: bool, timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.parent = parent
        self.bot = parent.bot

        created = datetime.now()
        storyteller = game.owner 
        submitter = interaction.user.id

        self.feedback = Feedback(
            created=created, 
            storyteller=storyteller, 
            submitter=submitter, 
            game=game,
            anonymous=anonymous,
            enjoyability=0,
            organization=0,
            pacing=0,
            attentiveness=0,
            feedback=None,
            comments=None
        )

        self.buttons = [self.stars1, self.stars2, self.stars3, self.stars4, self.stars5]
        self.select_measure.options = [SelectOption(**l) for l in NewFeedbackView.OPTIONS]
        self.target = None
    
    def make_embed(self):
        """
        Refreshes the embed to match the current contents.
        """
        title = "Create Feedback"
        header = f"You are creating {'anonymous ' if self.feedback.anonymous else ''}feedback for <#{self.feedback.game.channel}>."
        description = self.parent.make_embed(self.feedback, header=header)
        return embeds.make_embed(self.bot, title=title, description=description)

    def apply_value(self, value: int, button: ui.Button):
        """
        Set the current target's value to the given value.
        """
        if not self.target:
            return
        
        self.feedback.__dict__[self.target.lower()] = value
        button.disabled = True
        for other_button in self.buttons:
            if other_button == button:
                continue
            other_button.disabled = False

    async def update(self, interaction: Interaction):
        """
        Update the view after making a change to its contents.
        """
        if self.feedback.enjoyability > 0 and self.feedback.organization > 0 and self.feedback.pacing > 0 and self.feedback.attentiveness > 0:
            self.submit.disabled = False
        
        embed = self.make_embed()
        await interaction.response.defer()
        await interaction.edit_original_response(embed=embed, view=self)

    @classmethod
    async def create(cls, *, parent, game: Game, interaction: Interaction, anonymous: bool):
        view = NewFeedbackView(parent=parent, game=game, interaction=interaction, anonymous=anonymous)
        embed = view.make_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True, view=view)
    
    @ui.button(label="Submit", style=ButtonStyle.green, disabled=True, row=1)
    async def submit(self, interaction: Interaction, button: ui.Button):
        await self.feedback.upsert()
        await self.parent.send_ethereal(interaction, description="Sent feedback!")

    @ui.button(label="Add Comments", style=ButtonStyle.grey, row=1)
    async def comment(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_modal(FeedbackCommentsModal().with_parent(self))

    @ui.button(label="No measure selected...", style=ButtonStyle.grey, disabled=True, row=1)
    async def selected(self, interaction: Interaction, button: ui.Button):
        pass

    @ui.select(cls=ui.Select, placeholder="Choose a measure.", min_values=1, max_values=1, row=2)
    async def select_measure(self, interaction: Interaction, select: ui.Select):
        self.target = select.values[0]
        if not self.target:
            return
        
        self.selected.label = f"Set a score for {self.target.lower()}."
        self.selected.style = ButtonStyle.red

        cur_value = self.feedback.__dict__[self.target.lower()]
        for (i, button) in enumerate(self.buttons):
            button.disabled = (cur_value == i + 1)
        await self.update(interaction)

    @ui.button(label="⭐", style=ButtonStyle.blurple, row=3)
    async def stars1(self, interaction: Interaction, button: ui.Button):
        self.apply_value(1, button)
        await self.update(interaction)

    @ui.button(label="⭐⭐", style=ButtonStyle.blurple, row=3)
    async def stars2(self, interaction: Interaction, button: ui.Button):
        self.apply_value(2, button)
        await self.update(interaction)

    @ui.button(label="⭐⭐⭐", style=ButtonStyle.blurple, row=3)
    async def stars3(self, interaction: Interaction, button: ui.Button):
        self.apply_value(3, button)
        await self.update(interaction)

    @ui.button(label="⭐⭐⭐⭐", style=ButtonStyle.blurple, row=3)
    async def stars4(self, interaction: Interaction, button: ui.Button):
        self.apply_value(4, button)
        await self.update(interaction)

    @ui.button(label="⭐⭐⭐⭐⭐", style=ButtonStyle.blurple, row=3)
    async def stars5(self, interaction: Interaction, button: ui.Button):
        self.apply_value(5, button)
        await self.update(interaction)