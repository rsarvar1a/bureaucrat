from bureaucrat.models.configure import JSONable
from enum import Enum 
from typing import List, Set, Optional

from .moment import *
from .nominations import *
from .seating import *


class Mod(Enum):
    """
    Modifications to standard play that deserve their own feature.
    """
    CULT_LEADER = 1
    ORGAN_GRINDER = 2
    STORYTELLER_EXECUTION = 3


class State(JSONable):
    """
    The gamestate tied to a game.
    """
    def __init__(self, *, mods: List[Mod] = [], moment = {}, seating = {}, nominations = {}, script: Optional[dict] = None):
        self.mods = mods
        self.moment = Moment(**moment)
        self.seating = Seating(**seating)
        self.nominations = Nominations(**nominations)
        self.script = script
