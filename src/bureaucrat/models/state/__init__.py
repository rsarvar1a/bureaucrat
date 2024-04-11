from bureaucrat.models.configure import JSONable
from enum import Enum 
from typing import List, Literal, Set, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


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
    def __init__(self, *, mods: List[int] = [], moment = {}, seating = {}, nominations = {}, script: Optional[dict] = None, nights: Optional[dict] = None):
        self.mods = [Mod(m) for m in mods]
        self.moment = Moment(**moment)
        self.seating = Seating(**seating)
        self.nominations = Nominations(**nominations)
        self.script = script
        self.nights = nights

    def make_nightorder(self, *, bot: "Bureaucrat", night: Literal["first", "other"], filter: bool = False, private: bool = False):
        """
        Creates a nightorder page for the given night, if a script is loaded.
        """
        if not self.script:
            return "There is no script loaded on this game."
        
        if not self.nights:
            return "There is a script, but no loaded nightorder..."

        special = ["DUSK", "DEMON", "MINION", "DAWN"]

        night = self.nights[night]
        night = [
            [
                (id, seat) for seat in self.seating.seats + [None] 
                if (seat is None and (id in special or not filter)) or (seat and (seat.roles.true == id or seat.roles.apparent == id))
            ] 
            for id in night
        ]
        night: List[Tuple[str, Seat]] = [pair for lst in night for pair in lst]
        nights = [pair for pair in night if pair[1] or not any(p[1] and (p[1].roles.true == pair[0] or p[1].roles.apparent == pair[0]) for p in night)]

        segments = []
        for i, pair in enumerate(nights):
            role_string = Roles(true=pair[0]).make_description(bot=bot)
            target = f" for {pair[1].status.emojify(bot=bot)} {pair[1].alias} (<@{pair[1].member}>)" if private and pair[1] else ""
            segments.append(f"{i + 1}. {role_string}{target}")
        
        description = "\n".join(s for s in segments)
        return description