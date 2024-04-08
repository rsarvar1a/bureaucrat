import re

from bureaucrat.models.reminders import Reminder, Interval
from bureaucrat.utility import embeds
from datetime import datetime, timedelta
from discord import app_commands as apc, Interaction, Member, TextChannel, Thread
from discord.ext import commands, tasks
from discord.ext.commands import Context
from sqids.sqids import Sqids
from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


async def setup(bot):
    await bot.add_cog(Reminders(bot))


class Reminders(commands.GroupCog, group_name="reminders"):

    time_regex = re.compile(
        r"^((?P<days>[\.\d]+?)d)?((?P<hours>[\.\d]+?)h)?((?P<minutes>[\.\d]+?)m)?((?P<seconds>[\.\d]+?)s)?$"
    )

    def __init__(self, bot: "Bureaucrat") -> None:
        self.bot = bot
        self.fire.start()

    async def send_ethereal(self, interaction: Interaction, **kwargs):
        await self.bot.send_ethereal(interaction, title="Reminders", **kwargs)

    @classmethod
    def parse_time(cls, time_str) -> timedelta | None:
        """
        Parses a time string of the form XdYhZmAs, with all components optional. We don't accept 0-valued times, though.
        """
        parts = cls.time_regex.match(time_str)
        if parts is None:
            return None
        time_params = {name: float(param) for name, param in parts.groupdict().items() if param}
        return timedelta(**time_params)

    @apc.command()
    @apc.describe(id="The reminder id.")
    async def delete(self, interaction: Interaction, id: str):
        """
        Delete an active reminder.
        """
        reminder = await Reminder.objects.get_or_none(id=id)
        if reminder is None:
            return await self.send_ethereal(interaction, description=f"There is no reminder with id `{id}`.")

        if reminder.author != interaction.user.id:
            return await self.send_ethereal(
                interaction, description=f"This reminder belongs to <@{reminder.author}>, not you."
            )

        await self._delete(interaction, reminder)

    async def _delete(self, interaction: Interaction, reminder: Reminder):
        """
        Deletes a reminder, bypassing the author check.
        """
        await reminder.delete()
        await self.send_ethereal(interaction, description=f"Deleted reminder `{id}`.")

    @apc.command()
    async def list(self, interaction: Interaction):
        """
        List your active reminders and their intervals.
        """
        reminders = await Reminder.objects.select_related(Reminder.intervals).all(author=interaction.user.id)

        if reminders == []:
            return await self.send_ethereal(interaction, description="You have no reminders.")

        await self._list(interaction, reminders)

    async def _list(self, interaction: Interaction, reminders: List[Reminder]):
        """
        Constructs a list view on a set of reminders, rather than drawing from interaction context.
        """
        timestamp = datetime.now()
        segments = []
        for reminder in reminders:
            # Construct a list of intervals, where each achieved interval is crossed out.
            interval_list = []
            for interval in reminder.intervals:
                duration = interval.duration
                expired = interval.expires <= timestamp
                interval_str = f"~~{duration}~~" if expired else duration
                interval_list.append(interval_str)
            interval_list = f'({", ".join(interval_list)})'

            # Construct the segment with the primary reminder.
            message = reminder.message
            expires = int(reminder.expires.timestamp())
            segment = f"id: `{reminder.id}`\n<t:{expires}:R> {interval_list}\n{reminder.message}"
            segments.append(segment)
        description = "\n\n".join(s for s in segments)
        await interaction.response.send_message(
            embed=embeds.make_embed(self.bot, title="Reminders", description=description), ephemeral=True
        )

    @apc.command()
    @apc.describe(message="The reminder message.")
    @apc.describe(duration="The duration this reminder should last for, in 99d23h59m59s format.")
    @apc.describe(intervals="A list of times from expiry to ping this reminder at.")
    async def new(self, interaction: Interaction, message: str, duration: str, intervals: Optional[str]):
        """
        Set a new reminder with a given expiry duration.
        """
        await self._new(interaction, interaction.user, interaction.channel, message, duration, intervals)

    async def _new(
        self,
        interaction: Interaction,
        author: Member,
        channel: TextChannel | Thread,
        message: str,
        duration: str,
        intervals: Optional[str],
    ):
        """
        Sets a new reminder with the given author and channel, rather than drawing from interaction context.
        """
        delta = Reminders.parse_time(duration)
        if delta is None:
            return await self.send_ethereal(interaction, description=f"{duration} is an invalid duration.")

        # Setup the main reminder.
        timestamp = datetime.now()
        id = Sqids(min_length=8).encode([author.id, int(timestamp.timestamp())])
        expires = timestamp + delta
        reminder = await Reminder.objects.create(
            id=id, author=author.id, channel=channel.id, message=message, expires=expires
        )

        # Setup the interval reminders.
        intervals = (intervals.split(" ") if intervals else []) + ["0s"]
        for interval in intervals:
            interval_delta = Reminders.parse_time(interval)
            if interval_delta is None:
                continue
            interval_expires = expires - interval_delta
            await Interval.objects.create(reminder=reminder, duration=interval, expires=interval_expires, fired=False)

        # Downstream modules might define their own reminder system, so we should always return reminders back.
        await self.send_ethereal(
            interaction, description=f"Created new reminder that expires <t:{int(expires.timestamp())}:R>."
        )
        return reminder

    @apc.command()
    @apc.describe(id="The id of the reminder.")
    @apc.describe(duration="The new expiry duration of the reminder.")
    async def push(self, interaction: Interaction, id: str, duration: str):
        """
        Push back a reminder that you own, refreshing the expiry date and rearming the reminder's ping intervals.
        """
        reminder = await Reminder.objects.select_related(Reminder.intervals).get_or_none(id=id)
        if reminder is None:
            return await self.send_ethereal(interaction, description=f"There is no reminder with id {id}.")

        if reminder.author != interaction.user.id:
            return await self.send_ethereal(
                interaction, description=f"This reminder belongs to <@{reminder.author}>, not you."
            )

        await self._push(interaction, reminder, duration)

    async def _push(self, interaction: Interaction, reminder: Reminder, duration: str):
        """
        Push back a reminder, bypassing author checks.
        """
        delta = Reminders.parse_time(duration)
        if delta is None:
            return await self.send_ethereal(interaction, description=f"{duration} is an invalid duration.")

        # Update the main reminder with a new expiry date.
        timestamp = datetime.now()
        expires = timestamp + delta
        await reminder.update(expires=expires)

        # Recalculate the interval expiry dates from the new overall ending date.
        # If any of these new times are in the future, reactivate those alarms.
        for interval in reminder.intervals:
            interval: Interval = interval
            interval_delta = Reminders.parse_time(interval.duration)
            interval_expires = expires - interval_delta
            if interval_expires > timestamp:
                await interval.update(expires=interval_expires, fired=False)

        await self.send_ethereal(
            interaction, description=f"Updated reminder to expire <t:{int(expires.timestamp())}:R>."
        )
        return reminder

    @tasks.loop(seconds=10)
    async def fire(self):
        """
        Checks all intervals for any that have expired, and sends their corresponding reminder.
        If their parent reminder has also expired, then we delete the parent and all of its ping intervals.
        """
        timestamp = datetime.now()
        expired_intervals = await Interval.objects.select_related(Interval.reminder).all(
            expires__lte=timestamp, fired=False
        )

        expired = []
        for interval in expired_intervals:
            self.bot.logger.debug(f"Fire: interval {interval.id} on reminder {interval.reminder.id} expired.")

            channel_id = interval.reminder.channel
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
            stamp = int(interval.reminder.expires.timestamp())
            description = f"Reminder `{interval.reminder.id}` for <@{interval.reminder.author}>:\n{interval.reminder.message} <t:{stamp}:R> (<t:{stamp}:t>)"

            # Insert interval reminders back into the table, but don't refire them unless explicitly rearmed.
            await channel.send(content=description)
            await interval.update(fired=True)

            # Fully discard reminders that have reached their expiry date.
            if interval.reminder.expires < timestamp:
                expired.append(interval.reminder)

        for reminder in expired:
            await reminder.delete()
