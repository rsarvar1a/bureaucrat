from bureaucrat.models.configure import dotdict
from bureaucrat.models.state.seating import Seat
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


class Vote(dotdict):
    """
    A single voting entry.
    """
    def __init__(self, *, id: str, vote: Optional[str] = None, private_vote: Optional[str] = None, locked: Optional[bool] = None):
        self.id = id 
        self.vote = vote
        self.private_vote = private_vote
        self.locked = locked

    def emojify(self):
        match self.locked:
            case True:
                return ":white_check_mark:"
            case False:
                return ":x:"
            case None:
                return ""

    def make_description(self, *, indent: str = "  ", bot: "Bureaucrat", seat: Seat, nomination: "Nomination", private: bool = False, count: int, required: int):
        """
        Make the description for this vote.
        """
        status = f"{self.emojify()} ({count: >2}/{required: >2}) " if self.locked is not None else ""
        segments = [
            f"{status}{seat.make_description(bot=bot, private=private)}",
        ]
        if seat.status != Status.Spent:
            if private:
                segments += [
                    f"  - display: {self.vote if self.vote else 'n/a'}",
                    f"  - private: {self.private_vote if self.private_vote else 'n/a'}"
                ]
            else:
                segments.append(f"  - vote: '{self.vote if self.vote else 'unset'}")
        else:
            segments.append("  - *ghost vote already spent*")
        return f"\n{indent}".join(s for s in segments)

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


class Nomination (dotdict):
    """
    A single nomination.
    """
    def __init__(self, *, nominator: str, nominee: str, kind: int = NominationType.Execution.value, required: int, voters: List[dict] = []):
        self.nominator = nominator
        self.nominee = nominee
        self.kind = NominationType(kind)
        self.required = required
        self.voters = [Vote(**data) for data in voters]

    def make_description(self, *, indent: str = "", bot: "Bureaucrat", state: "State", private: bool = False, show_votes: bool = True):
        nominator = state.seating.seats[state.seating.index(self.nominator)]            
        nominee = state.seating.seats[state.seating.index(self.nominee)]
        
        subsegments = [
            f"Call for {self.kind.name.lower()}: {nominator.alias} ⟶ {nominee.alias}",
            f"- `plaintiff`: {nominator.make_description(bot=bot, private=private)}",
            f"- `defendant`: {nominee.make_description(bot=bot, private=private)}",
            f"- {self.required} vote{'s' if self.required != 1 else ''} required"
        ]
        if show_votes:
            subsegments.append(self.make_voting_log(state=state, indent=indent, bot=bot, private=private))

        description = f"\n{indent}".join(s for s in subsegments)
        return description

    def make_voting_log(self, *, indent: str = "", bot: "Bureaucrat", state: "State", private: bool = False):
        """
        Lists out the voters in this nomination, as well as their voting attributes.
        """
        count = 0
        required = self.required
        segments = []
        for i, vote in enumerate(self.voters):
            seat = state.seating.seats[state.seating.index(vote.id)]
            if vote.locked == True:
                count += 1
            segments.append(f"{indent}{i + 1}. {vote.make_description(indent=indent, bot=bot, seat=seat, nomination=self, private=private, count=count, required=required)}")
        return f"{indent}Votes:\n" + f"\n{indent}".join(s for s in segments)

    def set_vote(self, *, state: "State", voter: str, vote: Optional[str], private: bool):
        """
        Sets the vote, or returns an error.
        """
        votes = [v for v in self.voters if v.id == voter]
        if len(votes) == 0:
            return "You are not seated in this game."
        
        seat = state.seating.seats[state.seating.index(voter)]
        return votes[0].set_vote(seat=seat, kind=self.kind, vote=vote, private=private)


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

        if self.get_specific_nomination(day, nominee):
            return f"<@{seat.member}> has already been nominated today."
        
        if any(nom.nominator == nominator for nom in self.get_nominations(day)):
            return "You have already nominated today."
        
        nominator_index = state.seating.index(nominator)
        if nominator_index is None:
            return "You are not seated in this game."
        
        nom_seat = state.seating.seats[nominator_index]
        if nom_seat.status != Status.Alive:
            return "You cannot nominate because you are dead."

        kind = NominationType.Execution if seat.kind == Type.Player else NominationType.Exile
        required = state.seating.get_required_votes_for(seat.kind)
        
        nomination = Nomination(nominator=nominator, nominee=nominee, kind=kind, required=required, voters = [])
        nomination.voters = [Vote(id=seat.id, vote=None, private_vote=None, locked=None) for seat in rotate(state.seating.seats, state.seating.index(nominator))]
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

    def make_page(self, *, bot: "Bureaucrat", day: Optional[int], state: "State", private: bool = False):
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
            description = f"{i + 1}. {nomination.make_description(indent='  ', bot=bot, state=state, private=False, show_votes=False)}"
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
