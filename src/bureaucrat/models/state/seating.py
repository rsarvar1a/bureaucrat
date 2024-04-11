from bureaucrat.models.configure import dotdict
from datetime import datetime
from difflib import SequenceMatcher
from discord import Member, PartialEmoji, SelectOption
from enum import IntEnum
from sqids.sqids import Sqids
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


class Status(IntEnum):
    """
    The status of the player as it would appear on the town square's life token.
    """
    Alive = 1
    Dead = 2
    Spent = 3

    def emojify(self, *, bot: "Bureaucrat"):
        """
        Turns the life state into the emoji configured on this bot.
        """
        match self:
            case Status.Alive:
                s = bot.config.emoji.alive
            case Status.Dead:
                s = bot.config.emoji.dead 
            case Status.Spent:
                s = bot.config.emoji.spent
        return PartialEmoji.from_str(s)


class Marker(IntEnum):
    """
    Kinds of seat motions.
    """
    Beginning = 0
    Before = 1
    After = 2
    End = 3


class Type(IntEnum):
    """
    Whether a player is a player or traveller.
    """
    Player = 1
    Traveller = 2


class Seat(dotdict):
    """
    A player in the game.
    """
    def __init__(self, *, id: Optional[str] = None, member: int, alias: str, kind: Type = Type.Player, role: Optional[str] = None, status: int = Status.Alive.value):
        self.id = id if id else Sqids(min_length=8).encode([member, int(datetime.now().timestamp())])
        self.member = member
        self.alias = alias
        self.kind = kind
        self.role = role
        self.status = Status(status)

    def emojify(self, *, bot: "Bureaucrat"):
        """
        Determines if there is a suitable emoji representing this role.
        """
        # Try standards first.
        emojis = [emoji for emoji in bot.emojis if emoji.name == self.role and emoji.guild.id in bot.config.emoji.guilds]
        if len(emojis) > 0:
            return emojis[0]
        
        emojis = [emoji for emoji in bot.emojis if emoji.name == self.role]
        return emojis[0] if len(emojis) > 0 else None


class Seating(dotdict):
    """
    Manages seating in this game.
    """
    def __init__(self, *, seats: List[dict] = [], already_init: bool = False):
        self.seats = [Seat(**opts) for opts in seats]
        self.already_init = already_init

    def index(self, id: str):
        """
        Gets the index of the seat corresponding to the given alias.
        """
        indices = [i for i, seat in enumerate(self.seats) if seat.id == id]
        return indices[0] if len(indices) > 0 else None

    def move_seats(self, *, lhs: str, rhs: Optional[str] = None, mode: Marker) -> bool:
        """
        Moves a seat to a relative position, and returns whether or not the move was successful.
        """
        l = self.index(lhs)
        if l is None:
            return False

        match mode:
            case Marker.Beginning:
                seat = self.seats.pop(l)
                self.seats.insert(0, seat)

            case Marker.Before:
                r = self.index(rhs)
                if r is None:
                    return False
                r = r - 1 if r > l else r
                seat = self.seats.pop(l)
                self.seats.insert(r, seat)

            case Marker.After:
                r = self.index(rhs)
                if r is None:
                    return False
                r = r if r > l else r + 1
                seat = self.seats.pop(l)
                self.seats.insert(r, seat)

            case Marker.End:
                seat = self.seats.pop(l)       
                self.seats.append(seat)
        return True   

    def swap_seats(self, *, lhs: str, rhs: str) -> bool:
        """
        Swaps two players, and returns whether or not the swap was successful.
        """
        if lhs == rhs:
            return False

        l, r = self.index(lhs), self.index(rhs)
        if l is None or r is None:
            return False
        
        self.seats[l], self.seats[r] = self.seats[r], self.seats[l]
        return True

    def set_alias(self, *, id: str, alias: str):
        """
        Sets the alias of the given player.
        """
        l = self.index(id)
        if l is None:
            return False
        
        self.seats[l].alias = alias
        return True

    def set_role(self, *, id: str, role: Optional[str]):
        """
        Sets the role of the given player.
        """
        l = self.index(id)
        if l is None:
            return False
        
        self.seats[l].role = role
        return True

    def set_status(self, *, id: str, status: Status):
        """
        Sets the life/death status of a seat.
        """
        l = self.index(id)
        if l is None:
            return False
        
        self.seats[l].status = status
        return True
    
    def add_player(self, *, user: Member, kind: Type, role: Optional[str]):
        """
        Adds a player to the seating, provided they are not already in a seat.
        """
        if any(seat.member == user.id for seat in self.seats):
            return False
        
        seat = Seat(member=user.id, alias=user.display_name, kind=kind, role=role)
        self.seats.append(seat)
        return True

    def remove_player(self, *, id: str):
        """
        Removes a player, provided they are in a seat.
        """
        l = self.index(id)
        if l is None:
            return None
        
        return self.seats.pop(l)

    def substitute_player(self, *, id: str, user: Member):
        """
        Swaps the backing member on a seat and updates the alias.
        """
        l = self.index(id)
        if l is None:
            return False
        
        prev_id = self.seats[l].member
        self.seats[l].member = user.id
        self.seats[l].alias = user.display_name
        return prev_id

    def make_page(self, *, bot: "Bureaucrat", private: bool):
        """
        Create the embed text for a game.
        """
        if len(self.seats) == 0:
            return "There are no players."
        
        segments = []
        for i, seat in enumerate(self.seats):
            role_emoji = seat.emojify(bot=bot)
            private_text = (f" the {str(role_emoji)}" if role_emoji else f" the `{seat.role}`") if seat.role else ": no role"
            segments.append(f"{i + 1}. {str(seat.status.emojify(bot=bot))} {seat.alias} (<@{seat.member}>){private_text if private else ''}")
        return "\n".join(s for s in segments)
