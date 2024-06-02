import os

from bureaucrat.models.configure import ormar
from bureaucrat.models.scripts import *
from bureaucrat.utility import embeds
from discord import ButtonStyle, File, ui, Interaction
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from typing import TYPE_CHECKING, List
from urllib.request import urlretrieve
from urllib.parse import urlparse
from zipfile import ZipFile

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


class ScriptDetailsView(ui.View):

    def __init__(
        self, *, bot: "Bureaucrat", id: str, pages: List[Document], script: Script, timeout: float | None = 180
    ):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.id = id
        self.workspace = None
        self.pages = pages
        self.script = script
        self.page = 1
        self.max_page = len(pages)

    @ui.button(label="Download .zip", style=ButtonStyle.green)
    async def send_zip(self, interaction: Interaction, button: ui.Button):
        # Load all documents associated with the script.
        try:
            script = await Script.objects.select_related(Script.documents).get(id=self.id)
            docs = script.documents
        except ormar.NoMatch as e:
            await interaction.response.send_message(
                embed=embeds.make_error(self.bot, message=f"Could not find the script with id {self.id}."),
                ephemeral=True,
            )
            self.stop()
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        # Multithreaded downloads from S3.
        self._workspace = TemporaryDirectory()
        self.workspace = self._workspace.name
        os.mkdir(Path(self.workspace, "pdf"))
        os.mkdir(Path(self.workspace, "pages"))
        self.populate_workspace(docs)

        # Add each file into the zipfile, preserving structure.
        files = set(Path(self.workspace).rglob("*"))
        zip_path = Path(self.workspace, "render.zip")
        with ZipFile(zip_path, "w") as zipfile:
            for file in files:
                zipfile.write(file, arcname=file.relative_to(self.workspace))

        file = File(zip_path, filename="render.zip")
        if os.stat(zip_path).st_size >= interaction.guild.file_limit:
            await interaction.followup.send(
                embed=embeds.make_error(self.bot, message=f"The render is too big to send."),
                ephemeral=True,
            )
        else:   
            await interaction.followup.send(
                content="Here's your render!",
                ephemeral=True,
                file=file,
            )

    def enable(self, button):
        button.disabled = False
        button.style = ButtonStyle.blurple

    def disable(self, button):
        button.disabled = True
        button.style = ButtonStyle.grey

    @ui.button(label="<", style=ButtonStyle.grey, disabled=True)
    async def prev(self, interaction: Interaction, button: ui.Button):
        self.page -= 1
        self.enable(self.next)
        if self.page == 1:
            self.disable(self.prev)
        await self.update(interaction)

    @ui.button(label=">", style=ButtonStyle.grey, disabled=True)
    async def next(self, interaction: Interaction, button: ui.Button):
        self.page += 1
        self.enable(self.prev)
        if self.page == self.max_page:
            self.disable(self.next)
        await self.update(interaction)

    async def update(self, interaction):
        embed = await self.make_page(self.page)
        await interaction.response.defer()
        await interaction.edit_original_response(embed=embed, view=self)

    @classmethod
    def get_stem(cls, doc):
        url = doc.url
        path = urlparse(url).path
        basename = os.path.basename(path)
        stem = os.path.splitext(basename)[0]
        return stem

    @classmethod
    def order_by_resource(cls, doc: Document):
        stem = cls.get_stem(doc)
        for option in ("script", "nights-simple", "nights-full"):
            if option in stem:
                return option
        return ""

    @classmethod
    def order_by_number(cls, doc: Document):
        stem = cls.get_stem(doc)
        parts = str(stem).split("-")
        return int(parts[-1])

    @classmethod
    async def create(cls, *, interaction: Interaction, bot: "Bureaucrat", id: str, followup: bool = False):
        try:
            script = await Script.objects.get(id=id)
        except ormar.NoMatch:
            if followup:
                return await bot.followup_ethereal(interaction, title="Script", description=f"Could not find the script with id `{id}`.")
            else:
                return await bot.send_ethereal(interaction, title="Script", description=f"Could not find the script with id `{id}`.")

        pages = await Document.objects.filter(script=script, doctype=".png").order_by("-url").all()
        pages = sorted(
            sorted(pages, key=ScriptDetailsView.order_by_number), key=ScriptDetailsView.order_by_resource, reverse=True
        )
        view = ScriptDetailsView(bot=bot, id=id, script=script, pages=pages)
        embed = await view.make_page(1)

        if len(pages) > 1:
            view.enable(view.next)

        if followup:
            await interaction.followup.send(embed=embed, ephemeral=True, view=view)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True, view=view)

    async def make_page(self, page):
        author = await self.bot.fetch_user(self.script.author)
        brief = f"by {author.mention}\ncreated on <t:{int(self.script.created.timestamp())}:f>\nid: `{self.script.id}`"
        return embeds.make_embed(
            self.bot, title=self.script.name, description=brief, image=self.pages[page - 1].url, thumb=self.script.logo
        )

    def populate_workspace(self, docs):
        threads: list[Thread] = []

        for document in docs:
            document: Document = document
            url = document.url
            basename = os.path.basename(urlparse(url).path)
            if document.doctype in [".pdf", ".png"]:
                intermediate = "pdf" if document.doctype == ".pdf" else "pages"
                filepath = Path(self.workspace, intermediate, basename)
            else:
                filepath = Path(self.workspace, basename)
            self.bot.logger.debug(f"Fetching {url} into {filepath}.")
            t = Thread(target=urlretrieve, args=(url, filepath))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()
