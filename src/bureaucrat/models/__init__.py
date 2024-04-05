# Create the Ormar config.

from .configure import CONFIG


async def setup():
    if not CONFIG.database.is_connected:
        await CONFIG.database.connect()


from . import games
from . import scripts
