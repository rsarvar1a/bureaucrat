
from datetime import datetime
from ormar import ReferentialAction

from .configure import CONFIG, DictType, JSONable, ormar
from .games import Game
from .reminders import Reminder


class Feedback(ormar.Model):
    """
    A piece of feedback given to a storyteller by a player in their game.
    """

    ormar_config = CONFIG.copy(tablename="feedback")

    id: int = ormar.Integer(primary_key=True, autoincrement=True)
    created: datetime = ormar.DateTime()
    game: Game = ormar.ForeignKey(Game, ondelete=ReferentialAction.CASCADE, onupdate=ReferentialAction.CASCADE)
    storyteller: int = ormar.BigInteger()
    submitter: int = ormar.BigInteger()
    anonymous: bool = ormar.Boolean()
    
    enjoyability: int = ormar.Integer()
    organization: int = ormar.Integer()
    pacing: int = ormar.Integer()
    attentiveness: int = ormar.Integer()
    feedback: str = ormar.String(max_length=600, nullable=True)
    comments: str = ormar.String(max_length=600, nullable=True)