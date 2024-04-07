# Create the Ormar config.

from .configure import CONFIG


async def setup():
    if not CONFIG.database.is_connected:
        await CONFIG.database.connect()


from . import feedback
from . import games
from . import reminders
from . import scripts
