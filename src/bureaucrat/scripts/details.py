import os

from bureaucrat.models.configure import ormar
from bureaucrat.models.scripts import *
from bureaucrat.utility import embeds
from discord import ButtonStyle, File, ui, Interaction
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from typing import TYPE_CHECKING
from urllib.request import urlretrieve
from urllib.parse import urlparse
from zipfile import ZipFile

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


class ScriptDetailsView(ui.View):

    def __init__(self, *, bot: "Bureaucrat", id: str, timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.id = id
        self.workspace = None

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
        await interaction.followup.send(
            content="Here's your render!",
            ephemeral=True,
            file=file,
        )

    @classmethod
    async def create(cls, *, interaction: Interaction, bot: "Bureaucrat", id: str, followup: bool = False):
        try:
            script = await Script.objects.get(id=id)
        except ormar.NoMatch:
            return await interaction.followup.send(
                embed=embeds.make_error(bot, message=f"Could not find the script with id {id}."), ephemeral=True
            )

        author = await bot.fetch_user(script.author)
        brief = f"by {author.mention}\ncreated on <t:{int(script.created.timestamp())}:f>\nid: `{script.id}`"
        first_page = await Document.objects.filter(script=script, url__contains="script-1.png").get()
        embed = embeds.make_embed(bot, title=script.name, description=brief, image=first_page.url, thumb=script.logo)
        view = ScriptDetailsView(bot=bot, id=id)

        if followup:
            await interaction.followup.send(embed=embed, ephemeral=True, view=view)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True, view=view)

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
