import asyncio
import json
import os
import shutil

from bureaucrat.models import CONFIG
from bureaucrat.models.scripts import Script, Document
from bureaucrat.utility import embeds
from datetime import datetime
from discord import Attachment, ButtonStyle, Interaction, TextStyle, ui
from functools import partial
from io import BytesIO
from pathlib import Path
from scriptmaker import Datastore, Renderer, PDFTools
from sqids import Sqids
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from urllib.request import urlretrieve

from .details import ScriptDetailsView

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


class NewScript:
    """
    Represents a rendered script and its corresponding night orders.
    When a user wishes to download a script package, the info gathers all of the JSONs, PDFs and PNGs in the workspace and zips them.
    """

    def __init__(self, *, bot: "Bureaucrat", paths: set[Path], interaction: Interaction, logo, name, workspace):
        self.bot = bot

        self.created = datetime.now()
        self.id = NewScript.make_script_uuid(interaction, self.created)
        self.author = interaction.user.id
        self.logo = logo
        self.name = name
        self.paths = paths
        self.workspace = workspace

    def cleanup(self):
        shutil.rmtree(self.workspace)

    @classmethod
    def make_script_uuid(cls, interaction: Interaction, timestamp):
        user_id = interaction.user.id
        discrim = timestamp.timestamp()
        return Sqids(min_length=8).encode([int(user_id), int(discrim)])

    @CONFIG.database.transaction()
    async def persist(self):
        script = await Script.objects.create(
            id=self.id, author=self.author, created=self.created, logo=self.logo, name=self.name
        )
        for path in self.paths:
            if path.is_dir():
                continue

            relative_path = path.relative_to(self.workspace)
            s3_key = "/".join([self.id, str(relative_path)])
            self.bot.logger.debug(f"Creating {s3_key}.")

            url = await self.bot.aws.s3_create(bucket="scripts", key=s3_key, file=path)
            doctype = os.path.splitext(urlparse(url).path)[1]
            await Document.objects.create(doctype=doctype, script=script, url=url)


class NewScriptModal(ui.Modal, title="Create a script!"):
    """
    A Discord modal that collects script and night order JSON inputs.
    Ths view also verifies that they are well-formed, but leaves content verification to scriptmaker.
    """

    def with_parent(self, *, parent):
        self.parent = parent
        return self

    def handle_rich_form(self) -> None:
        splits = [
            self.parent.good_characters_input.value.split(','),
            self.parent.evil_characters_input.value.split(','),
            self.parent.extras_input.value.split(',')
        ]
        characters = [x for xs in splits for x in xs]
        
        meta = {
            'id': '_meta',
            'name': self.parent.name_input.value,
            "author": self.parent.author_input.value
        }
        
        self.parent.script_json = [meta] + characters
        self.parent.nights_json = None

    def handle_json_form(self) -> None:
        self.parent.script_json = json.loads(self.parent.script_input.value)
        self.parent.nights_json = (
            json.loads(self.parent.nights_input.value) if self.parent.nights_input.value != "" else None
        )

    def handle_url_form(self) -> None:
        with NamedTemporaryFile() as f:
            urlretrieve(self.parent.script_url_input.value, f.name)
            self.parent.script_json = json.load(f)
            if self.parent.nights_url_input.value != "":
                urlretrieve(self.parent.nights_url_input.value, f.name)
                self.parent.nights_json = json.load(f)
            else:
                self.parent.nights_json = None

    async def on_submit(self, interaction: Interaction) -> None:
        match self.parent.mode:
            case NewScriptView.MODE_RICH:
                self.handle_rich_form()
            case NewScriptView.MODE_JSON:
                self.handle_json_form()
            case NewScriptView.MODE_URL:
                self.handle_url_form()

        await interaction.response.defer()
        self.parent.enable_generation()
        await interaction.edit_original_response(view=self.parent)
        self.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        await interaction.response.send_message(
            None, embed=embeds.make_error(self.parent.bot, message="Invalid inputs:", error=error), ephemeral=True
        )
        self.parent.bot.logger.error(error)
        self.stop()


class NewScriptView(ui.View):
    """
    A Discord view for script creation.
    It allows the user to input the script and night order as JSON blocks.
    It also allows the user to select the desired night order modes.
    """

    MODE_ATTACHMENT = 0
    MODE_URL = 1
    MODE_JSON = 2
    MODE_RICH = 3

    def __init__(self, *, attachment: Attachment | None, bot: "Bureaucrat", timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.bot = bot

        self.script_json = {}
        self.nights_json = {}
        self.full = False
        self.simple = False

        self.script_input = ui.TextInput(label="Script JSON", style=TextStyle.paragraph)
        self.nights_input = ui.TextInput(label="Nightorder JSON", style=TextStyle.paragraph, required=False)
        
        self.script_url_input = ui.TextInput(label="Script URL", style=TextStyle.short)
        self.nights_url_input = ui.TextInput(label="Nightorder URL", style=TextStyle.short, required=False)
        
        self.name_input = ui.TextInput(label="Name", style=TextStyle.short)
        self.author_input = ui.TextInput(label="Author", style=TextStyle.short)
        self.good_characters_input = ui.TextInput(label="Townsfolk & Outsiders", style=TextStyle.paragraph)
        self.evil_characters_input = ui.TextInput(label="Minions & Demon(s)", style=TextStyle.paragraph)
        self.extras_input = ui.TextInput(label="Travelers & Fabled", style=TextStyle.paragraph, required=False)
        
        self.attachment = attachment
        if self.attachment:
            self.mode = NewScriptView.MODE_ATTACHMENT
        else:
            self.mode = NewScriptView.MODE_RICH
            self.next_mode = NewScriptView.MODE_JSON

    @ui.button(label="toggle", style=ButtonStyle.red)
    async def toggle(self, interaction: Interaction, button: ui.Button):
        self.mode = self.next_mode
        match self.mode:
            case NewScriptView.MODE_RICH:
                self.toggle.label = "Switch to JSON"
                self.get_jsons.label = "Choose characters"
                self.next_mode = NewScriptView.MODE_JSON
            case NewScriptView.MODE_URL:
                self.toggle.label = "Switch to Easy Mode"
                self.get_jsons.label = "Enter URL"
                self.next_mode = NewScriptView.MODE_RICH
            case NewScriptView.MODE_JSON:
                self.toggle.label = "Switch to URL"
                self.get_jsons.label = "Enter JSON"
                self.next_mode = NewScriptView.MODE_URL

        await interaction.response.defer()
        await interaction.edit_original_response(view=self)

    async def setup(self):
        if self.attachment:
            try:
                content = await self.attachment.read()
                self.script_json = json.load(BytesIO(content))
                self.nights_json = {}
            except Exception as e:
                self.bot.logger.warn(f"Failed to use attachment: {e}")
                self.mode = NewScriptView.MODE_JSON

        match self.mode:
            case NewScriptView.MODE_ATTACHMENT:
                self.toggle.label = "Attachment Mode"
                self.toggle.disabled = True
                self.enable_generation()
                self.remove_item(self.get_jsons)
            case NewScriptView.MODE_JSON:
                self.toggle.label = "Switch to URL"
                self.toggle.disabled = False
            case NewScriptView.MODE_RICH:
                self.toggle.label = "Switch to JSON"
                self.toggle.disabled = False
            case NewScriptView.MODE_URL:
                self.toggle.label = "Switch to Easy Mode"
                self.toggle.disabled = False

    def enable_generation(self):
        self.generate.disabled = False
        self.generate.style = ButtonStyle.green

    @classmethod
    async def create(
        cls,
        *,
        attachment: Attachment | None = None,
        interaction: Interaction,
        bot: "Bureaucrat",
        timeout: float | None = 180,
    ):
        view = NewScriptView(bot=bot, attachment=attachment)
        await view.setup()

        embed = embeds.make_embed(
            bot=bot,
            title="Create a script",
            description="",
        )

        await interaction.response.send_message(embed=embed, ephemeral=True, view=view)

    @ui.button(label="Choose Characters", style=ButtonStyle.blurple)
    async def get_jsons(self, interaction: Interaction, button: ui.Button):
        match self.mode:
            case NewScriptView.MODE_JSON:
                scripts_modal = (
                    NewScriptModal().with_parent(parent=self).add_item(self.script_input).add_item(self.nights_input)
                )
            case NewScriptView.MODE_URL:
                scripts_modal = (
                    NewScriptModal()
                    .with_parent(parent=self)
                    .add_item(self.script_url_input)
                    .add_item(self.nights_url_input)
                )
            case NewScriptView.MODE_RICH:
                scripts_modal = (
                    NewScriptModal()
                    .with_parent(parent=self)
                    .add_item(self.name_input)
                    .add_item(self.author_input)
                    .add_item(self.good_characters_input)
                    .add_item(self.evil_characters_input)
                    .add_item(self.extras_input)              
                )

        await interaction.response.send_modal(scripts_modal)
        await interaction.edit_original_response(view=self)

    @ui.button(label="Simple Nights")
    async def toggle_simple(self, interaction: Interaction, button: ui.Button):
        self.simple = not self.simple
        button.style = ButtonStyle.blurple if button.style == ButtonStyle.grey else ButtonStyle.grey
        await interaction.response.defer()
        await interaction.edit_original_response(view=self)

    @ui.button(label="Full Nights")
    async def toggle_full(self, interaction: Interaction, button: ui.Button):
        self.full = not self.full
        button.style = ButtonStyle.blurple if button.style == ButtonStyle.grey else ButtonStyle.grey
        await interaction.response.defer()
        await interaction.edit_original_response(view=self)

    @ui.button(label="Generate", style=ButtonStyle.grey, disabled=True)
    async def generate(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        await interaction.response.defer(ephemeral=True, thinking=True)

        scriptinfo: NewScript = await self.create_script(interaction=interaction)
        await scriptinfo.persist()
        await ScriptDetailsView.create(interaction=interaction, bot=self.bot, id=scriptinfo.id, followup=True)
        scriptinfo.cleanup()

        self.stop()

    async def on_error(self, interaction: Interaction, error: Exception, item: ui.Item) -> None:
        await interaction.followup.send(None, embed=embeds.make_error(self.bot, error=error), ephemeral=True)
        self.bot.logger.error(error)

    async def create_script(self, *, interaction: Interaction):
        workspace = TemporaryDirectory().name
        datastore = Datastore(workspace)
        datastore.add_official_characters()

        script = datastore.load_script(self.script_json, nights_json=self.nights_json)
        script.meta.author = interaction.user.name if script.meta.author is None else script.meta.author
        scriptinfo = NewScript(
            bot=self.bot,
            interaction=interaction,
            paths=set(),
            logo=script.meta.logo,
            name=script.meta.name,
            workspace=workspace,
        )

        await asyncio.get_event_loop().run_in_executor(None, partial(self.render_docs, script=script))
        self.populate_paths(workspace=workspace, scriptinfo=scriptinfo)
        return scriptinfo

    def populate_paths(self, *, workspace, scriptinfo):
        with open(Path(workspace, "script.json"), "w") as json_file:
            json.dump(self.script_json, json_file)

        if self.nights_json is not None:
            with open(Path(workspace, "nights.json"), "w") as json_file:
                json.dump(self.nights_json, json_file)

        shutil.rmtree(Path(workspace, "build"))
        scriptinfo.paths = set(Path(workspace).rglob("*"))

    def render_docs(self, *, script) -> set[Path]:
        paths = set()
        renderer = Renderer()
        paths.add(renderer.render_script(script))

        if self.full:
            script.options.simple_nightorder = False
            paths.add(renderer.render_nightorder(script))

        if self.simple:
            script.options.simple_nightorder = True
            paths.add(renderer.render_nightorder(script))

        for path in paths:
            PDFTools.compress(path)
            PDFTools.pngify(path)
