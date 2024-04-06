from datetime import datetime
from ormar import ReferentialAction
from typing import Optional

from .configure import CONFIG, DictType, JSONable, ormar


class Reminder(ormar.Model):
    """
    Represents a timed reminder.
    """

    ormar_config = CONFIG.copy(tablename="reminders")

    id: str = ormar.String(primary_key=True, max_length=100)
    author: int = ormar.BigInteger()
    channel: int = ormar.BigInteger()
    message: str = ormar.String(max_length=1000)
    expires: datetime = ormar.DateTime()


class Interval(ormar.Model):
    """
    Represents a subreminder, which causes a reminder to, well, remind its user some number of hours before the deadline.
    """

    ormar_config = CONFIG.copy(tablename="intervals")

    id: int = ormar.Integer(primary_key=True, autoincrement=True)
    reminder: Reminder = ormar.ForeignKey(
        Reminder, ondelete=ReferentialAction.CASCADE, onupdate=ReferentialAction.CASCADE
    )
    duration: str = ormar.String(max_length=50)
    expires: datetime = ormar.DateTime()
    fired: bool = ormar.Boolean()
