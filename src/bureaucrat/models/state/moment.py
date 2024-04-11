from bureaucrat.models.configure import dotdict
from enum import IntEnum


class Phase(IntEnum):
    """
    Which phase the game is in.
    """
    Day = 0
    Night = 1


class Moment(dotdict):
    """
    The current "day" of the game, as well as its phase.
    """
    def __init__(self, *, day: int = 1, phase: int = Phase.Night.value):
        self.day = day
        self.phase = Phase(phase)
