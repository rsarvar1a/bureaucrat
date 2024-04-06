from enum import Enum
from ormar import ReferentialAction
from typing import Optional

from .configure import CONFIG, DictType, JSONable, ormar
from .reminders import Reminder


class ActiveCategory(ormar.Model):
    """
    A model indicating a category on a server configured to allow text games.
    The category alone is a unique snowflake, but the guild id is provided as a fetch hint.
    """

    ormar_config = CONFIG.copy(tablename="categories")

    id: int = ormar.BigInteger(primary_key=True)
    guild: int = ormar.BigInteger()


class Config(JSONable):
    """
    The configuration of a game.
    """

    def __init__(self, *, name: str | None = None, script: Optional[str] = None):
        self.name = name
        self.script = script

    def __repr__(self):
        return f"script: `{self.script}`"


class State(JSONable):
    """
    The gamestate tied to a game.
    """

    def __init__(self):
        pass


class Game(ormar.Model):
    """
    A model that represents a text game.
    """

    ormar_config = CONFIG.copy(tablename="games")

    id: int = ormar.Integer(primary_key=True, autoincrement=True)
    channel: int = ormar.BigInteger()
    owner: int = ormar.BigInteger()
    player_role: int = ormar.BigInteger()
    st_role: int = ormar.BigInteger()
    config: DictType = ormar.JSON()
    state: DictType = ormar.JSON()


class ActiveGame(ormar.Model):
    """
    A mapping from channel to active game.
    """

    ormar_config = CONFIG.copy(tablename="active_games")

    id: int = ormar.BigInteger(primary_key=True)
    game: Game = ormar.ForeignKey(
        Game, unique=True, ondelete=ReferentialAction.CASCADE, onupdate=ReferentialAction.CASCADE
    )


class RoleType(Enum):

    PLAYER = "Player"
    STORYTELLER = "Storyteller"
    NONE = "None"


class ManagedThread(ormar.Model):
    """
    A thread belonging to a game that was created by Bureaucrat.
    """

    ormar_config = CONFIG.copy(tablename="threads")

    id: int = ormar.BigInteger(primary_key=True)
    game: Game = ormar.ForeignKey(Game, ondelete=ReferentialAction.CASCADE, onupdate=ReferentialAction.CASCADE)


class Participant(ormar.Model):
    """
    A model that represents a user with a role assigned to them in a game.
    """

    ormar_config = CONFIG.copy(tablename="participants")

    id: int = ormar.Integer(primary_key=True, autoincrement=True)
    game: Game = ormar.ForeignKey(Game, ondelete=ReferentialAction.CASCADE, onupdate=ReferentialAction.CASCADE)
    member: int = ormar.BigInteger()
    role: RoleType = ormar.Enum(enum_class=RoleType)


class Kibitz(ormar.Model):
    """
    A model representing a special managed thread, the one for observers.
    """

    ormar_config = CONFIG.copy(tablename="kibitz")

    id: int = ormar.BigInteger(primary_key=True)
    game: Game = ormar.ForeignKey(Game, ondelete=ReferentialAction.CASCADE, onupdate=ReferentialAction.CASCADE)
    role: int = ormar.BigInteger()


class GameReminder(ormar.Model):
    """
    A reminder tied specifically to a game.
    """

    ormar_config = CONFIG.copy(tablename="game_reminders")

    id: int = ormar.Integer(primary_key=True, autoincrement=True)
    game: Game = ormar.ForeignKey(Game, ondelete=ReferentialAction.CASCADE, onupdate=ReferentialAction.CASCADE)
    reminder: Reminder = ormar.ForeignKey(Reminder, unique=True, ondelete=ReferentialAction.CASCADE, onupdate=ReferentialAction.CASCADE)
