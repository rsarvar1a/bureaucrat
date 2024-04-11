from bureaucrat.models.configure import JSONable


from typing import Optional


class Config(JSONable):
    """
    The configuration of a game.
    """

    def __init__(self, *, name: Optional[str], script: Optional[str], seats: int):
        self.name = name if name else "new-game"
        self.script = script
        self.seats = seats if seats else 12

    def __repr__(self):
        return "\n".join([
            f"script: `{self.script}`",
            f"{self.seats} players"
        ])
