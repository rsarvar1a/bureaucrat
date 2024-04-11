from bureaucrat.models.configure import dotdict
from enum import Enum
from typing import List, Set, Optional, TYPE_CHECKING

from .seating import Seat

if TYPE_CHECKING:
    from bureaucrat.models.state import State


class Nominations (dotdict):
    """
    A manager for nomination and voting contexts.
    """
    pass