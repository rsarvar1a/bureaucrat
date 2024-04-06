from bureaucrat.models.games import Game, GameReminder
from bureaucrat.models.reminders import Reminder, Interval
from bureaucrat.utility import checks, embeds
from discord import Interaction, Member, TextChannel
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat
    from bureaucrat.games import Games


class Reminders:

    def __init__(self, parent: "Games") -> None:
        self.bot: "Bureaucrat" = parent.bot
        self.parent = parent

    def _reminders(self):
        return self.bot.get_cog("Reminders")

    async def send_ethereal(self, interaction: Interaction, **kwargs):
        await self.parent.send_ethereal(interaction, title="Reminders", **kwargs)

    async def delete(self, interaction: Interaction, id: str):
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.parent.ensure_active(interaction)
        if game is None:
            return

        if not await self.parent.ensure_privileged(interaction, game):
            return

        reminder = await Reminder.objects.get_or_none(id=id)
        if reminder is None:
            return await self.send_ethereal(interaction, description=f"There is no reminder with id `{id}`.")

        await self._reminders()._delete(interaction, reminder)

    async def list(self, interaction: Interaction):
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.parent.ensure_active(interaction)
        if game is None:
            return

        gamereminders = await GameReminder.objects.select_related([GameReminder.reminder, GameReminder.reminder.intervals]).all(game=game)
        reminders = [r.reminder for r in gamereminders]

        await self._reminders()._list(interaction, reminders)

    async def new(self, interaction: Interaction, message: str, duration: str, intervals: Optional[str]):
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.parent.ensure_active(interaction)
        if game is None:
            return

        if not await self.parent.ensure_privileged(interaction, game):
            return

        pinged_message = f"<@&{game.player_role}> {message}"
        channel = self.bot.get_channel(game.channel) or await self.bot.fetch_channel(game.channel)
        reminder = await self._reminders()._new(interaction, interaction.user, channel, pinged_message, duration, intervals)
        await GameReminder.objects.create(game=game, reminder=reminder)

    async def push(self, interaction: Interaction, id: str, duration: str):
        if not await checks.in_guild(self.bot, interaction):
            return

        game = await self.parent.ensure_active(interaction)
        if game is None:
            return

        if not await self.parent.ensure_privileged(interaction, game):
            return

        reminder = await Reminder.objects.get_or_none(id=id)
        if reminder is None:
            return await self.send_ethereal(interaction, description=f"There is no reminder with id `{id}`.")

        gamereminder = await GameReminder.objects.get_or_none(game=game, reminder=reminder)
        if gamereminder is None:
            return await self.send_ethereal(interaction, description="This reminder does not belong to this game.")

        await self._reminders()._push(interaction, reminder, duration)
