from bureaucrat.models.configure import dotdict
from bureaucrat.models.state.seating import Seat
from discord import PartialEmoji
from enum import IntEnum
from typing import List, Set, Optional, TYPE_CHECKING

from .seating import Seat, Status, Type

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat
    from bureaucrat.models.state import State


def rotate(l, n):
    return l[n:] + l[:n]


class NominationType(IntEnum):
    """
    What kind of vote this is: standard, or exlie.
    """
    Execution = 1
    Exile = 2


class VoteResult(IntEnum):
    """
    Represents a type of voting modifier.
    """
    Yes = 1
    Thief = -1
    Bureaucrat = 3
    No = 0


class Vote(dotdict):
    """
    A single voting entry.
    """
    def __init__(self, *, id: str, vote: Optional[str] = None, private_vote: Optional[str] = None, locked: Optional[int] = None):
        self.id = id 
        self.vote = vote
        self.private_vote = private_vote
        self.locked = VoteResult(locked) if locked is not None else None

    def emojify(self, *, bot: "Bureaucrat"):
        if self.locked is None:
            return ""

        match self.locked:
            case VoteResult.Yes:
                s = ":white_check_mark:"
            case VoteResult.Thief:
                s = bot.config.emoji.thief
            case VoteResult.Bureaucrat:
                s = bot.config.emoji.bureaucrat
            case VoteResult.No:
                s = ":x:"
        return PartialEmoji.from_str(s)

    def make_description(self, *, indent: str = "  ", bot: "Bureaucrat", seat: Seat, kind: NominationType, nomination: "Nomination", private: bool = False, viewer: Optional[str], count: int, required: int, active: bool):
        """
        Make the description for this vote.
        """
        status = f"{':arrow_right: ' if active else ''}{str(self.emojify(bot=bot))}  (`{count: >2}`/`{required: >2}`)  " if self.locked is not None else ""
        segments = [
            f"{status}{seat.make_description(bot=bot, private=private) if seat else '(removed player)'}",
        ]
        if kind == NominationType.Exile or seat.status != Status.Spent:
            if private or self.id == viewer:
                segments += [
                    f"  - display: {self.vote if self.vote else 'n/a'}",
                    f"  - private: {self.private_vote if self.private_vote else 'n/a'}"
                ]
            else:
                segments.append(f"  - vote: {self.vote if self.vote else 'n/a'}")
        else:
            segments.append("  - *ghost vote already spent*")
        description = f"\n{indent}".join(s for s in segments)
        return f"**{description}**" if active else description

    def set_vote(self, *, kind: NominationType, seat: Seat, vote: Optional[str], private: bool):
        """
        Sets a vote, or returns an error if the vote is spent or locked.
        """
        if self.locked:
            return "Your vote is locked."
        if seat.status == Status.Spent and kind == NominationType.Execution:
            return "Your ghost vote is already spent."
        
        if private:
            self.private_vote = vote
        else:
            self.vote = vote
        return None
    
    def lock_vote(self, *, kind: NominationType, seat: Seat, vote: Optional[VoteResult]):
        """
        Locks a vote.
        """
        if seat.status == Status.Spent and kind == NominationType.Execution and vote and vote != VoteResult.No:
            return f"Their ghost vote is already spent."
        
        self.locked = vote

class Nomination (dotdict):
    """
    A single nomination.
    """
    def __init__(self, *, nominator: str, nominee: str, accusation: Optional[str] = None, defense: Optional[str] = None, kind: int = NominationType.Execution.value, required: int, voters: List[dict] = [], marked: bool = False):
        self.nominator = nominator
        self.nominee = nominee
        self.accusation = accusation
        self.defense = defense
        self.kind = NominationType(kind)
        self.required = required
        self.voters = [Vote(**data) for data in voters]
        self.marked = marked

    def emojify(self, *, bot: "Bureaucrat"):
        if self.marked:
            s = bot.config.emoji.marked
        else:
            s = ""
        return PartialEmoji.from_str(s)

    def make_description(self, *, indent: str = "", bot: "Bureaucrat", state: "State", private: bool = False, show_votes: bool = True, viewer: Optional[str], active: Optional[str] = None):
        nominator = state.seating.seats[state.seating.index(self.nominator)]            
        nominee = state.seating.seats[state.seating.index(self.nominee)]
        collected = sum(vote.locked.value if vote.locked is not None else 0 for vote in self.voters)

        subsegments = [
            f"Call for {self.kind.name.lower()}: {nominator.alias} ⟶ {nominee.alias}",
            f"- `plaintiff`: {nominator.make_description(bot=bot, private=private)}",
            f"- `defendant`: {nominee.make_description(bot=bot, private=private)}",
            f"- {f'{self.emojify(bot=bot)} ' if self.marked else ''}{collected} vote{'s' if collected != 1 else ''} (of {self.required} required)"
        ]
        if show_votes:
            subsegments.append(f"\nAccusation: \n> {'n/a' if self.accusation is None else f'\"{self.accusation}\"'}")
            subsegments.append(f"\nDefense: \n> {'n/a' if self.defense is None else f'\"{self.defense}\"'}")
            subsegments.append(self.make_voting_log(state=state, indent=indent, bot=bot, private=private, viewer=viewer, active=active))

        description = f"\n{indent}".join(s for s in subsegments)
        return description

    def make_voting_log(self, *, indent: str = "", bot: "Bureaucrat", state: "State", private: bool = False, viewer: Optional[str], active: Optional[str] = None):
        """
        Lists out the voters in this nomination, as well as their voting attributes.
        """
        count = 0
        required = self.required
        segments = []
        for i, vote in enumerate(self.voters):
            seat = state.seating.seats[state.seating.index(vote.id)]
            if vote.locked is not None:
                count += vote.locked.value
            is_active = vote.id == active
            segments.append(f"{indent}{i + 1}. {vote.make_description(indent=indent, kind=self.kind, bot=bot, seat=seat, nomination=self, private=private, viewer=viewer, count=count, required=required, active=is_active)}")
        return f"\n{indent}Votes:\n" + f"\n{indent}".join(s for s in segments)

    def set_vote(self, *, state: "State", voter: str, vote: Optional[str], private: bool):
        """
        Sets the vote, or returns an error.
        """
        votes = [v for v in self.voters if v.id == voter]
        if len(votes) == 0:
            return "You are not seated in this game."
        
        seat = state.seating.seats[state.seating.index(voter)]
        return votes[0].set_vote(seat=seat, kind=self.kind, vote=vote, private=private)
    
    def lock_vote(self, *, state: "State", voter: str, vote: Optional[VoteResult]):
        """
        Locks the vote, or returns an error.
        """
        votes = [v for v in self.voters if v.id == voter]
        if len(votes) == 0:
            return f"`{voter}` is not seated in this game."
        
        seat = state.seating.seats[state.seating.index(voter)]
        return votes[0].lock_vote(kind=self.kind, seat=seat, vote=vote)

class Nominations (dotdict):
    """
    A manager for nomination and voting contexts.
    """
    def __init__(self, *, days = {}):
        self.days = {int(k): [Nomination(**data) for data in v] for k, v in days.items()}

    def create(self, *, state: "State", nominator: str, nominee: str):
        """
        Creates a new nomination, or determines the point of failure.
        """
        day = state.moment.day
        seat = state.seating.seats[state.seating.index(nominee)]
        kind = NominationType.Execution if seat.kind == Type.Player else NominationType.Exile

        if self.get_specific_nomination(day, nominee):
            return f"<@{seat.member}> has already been nominated today."
        
        if kind == NominationType.Execution and any(nom.nominator == nominator and nom.kind == NominationType.Execution for nom in self.get_nominations(day)):
            return "You have already nominated today."
        
        nominator_index = state.seating.index(nominator)
        if nominator_index is None:
            return "You are not seated in this game."
        
        nom_seat = state.seating.seats[nominator_index]
        if nom_seat.status != Status.Alive:
            return "You cannot nominate because you are dead."

        required = state.seating.get_required_votes_for(seat.kind)
        
        nomination = Nomination(nominator=nominator, nominee=nominee, kind=kind, required=required, voters = [])
        active_seats = [seat for seat in rotate(state.seating.seats, state.seating.index(nominator)) if not seat.removed]
        nomination.voters = [Vote(id=seat.id, vote=None, private_vote=None, locked=None) for seat in active_seats]
        self.days[day].append(nomination)
        
        return None

    def get_nominations(self, day: int):
        """
        Gets all nominations (in order) in this day.
        """
        if day not in self.days:
            self.days[day] = []
        
        return self.days[day]

    def get_specific_nomination(self, day: int, nominee: str):
        """
        Gets the nomination.
        """
        nominations = self.get_nominations(day)
        noms = [nom for nom in nominations if nom.nominee == nominee]
        return noms[0] if len(noms) > 0 else None

    def make_page(self, *, bot: "Bureaucrat", day: Optional[int], state: "State", private: bool = False, viewer: Optional[str]):
        """
        Lists all of the active nominations today.
        """
        day = state.moment.day if day is None else day
        
        if day not in self.days:
            self.days[day] = []
        
        if len(self.days[day]) == 0:
            return f"There are no nominations on day {day}."
        
        segments = []
        for i, nomination in enumerate(self.days[day]):
            description = f"{i + 1}. {nomination.make_description(indent='  ', bot=bot, state=state, private=False, viewer=viewer, show_votes=False)}"
            segments.append(description)
        
        return "\n\n".join(s for s in segments)

    def set_vote(self, *, state: "State", voter: str, nominee: str, vote: Optional[str], private: bool):
        """
        Sets the vote on the corresponding nomination, or returns an error.
        """
        nomination = self.get_specific_nomination(state.moment.day, nominee)
        if not nomination:
            return "There is no such nomination."
        
        return nomination.set_vote(state=state, voter=voter, vote=vote, private=private)

    def lock_vote(self, *, state: "State", voter: str, nominee: str, result: Optional[VoteResult]):
        """
        Locks the vote on the corresponding nomination, or returns an error.
        """
        nomination = self.get_specific_nomination(state.moment.day, nominee)
        if not nomination:
            return "There is no such nomination."
        
        return nomination.lock_vote(state=state, voter=voter, vote=result)

    def mark(self, *, state: "State", nominee: str, mark: bool):
        """
        Sets the marked state on the corresponding nomination.
        """
        nomination = self.get_specific_nomination(state.moment.day, nominee)
        if not nomination:
            return "There is no such nomination."
        
        nomination.marked = mark
        return None

    def accuse(self, *, state: "State", nominator: str, nominee: str, accusation: str):
        """
        Sets the accusation message on the corresponding nomination.
        """
        nomination = self.get_specific_nomination(state.moment.day, nominee)
        if not nomination:
            return "There is no such nomination."
        
        if nomination.nominator != nominator:
            return "You did not make this nomination."
        
        nomination.accusation = accusation
        return None

    def defend(self, *, state: "State", nominee: str, defense: str):
        """
        Sets the defense message on the corresponding nomination.
        """
        nomination = self.get_specific_nomination(state.moment.day, nominee)
        if not nomination:
            return "There is no such nomination."
        
        nomination.defense = defense
        return None
