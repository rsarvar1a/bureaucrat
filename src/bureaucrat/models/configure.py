import databases
import ormar
import os
import pydantic
import sqlalchemy
import typing

DATABASE_URL = os.getenv("DATABASE_URL")

CONFIG = ormar.OrmarConfig(
    database=databases.Database(DATABASE_URL),
    metadata=sqlalchemy.MetaData(),
    engine=sqlalchemy.create_engine(DATABASE_URL),
)

DictType = pydantic.Json[typing.Dict[str, pydantic.JsonValue]]


class JSONable:
    """
    A base class for a model that is stored as a JSON column.
    """

    def dump(self):
        return self.__dict__

    @classmethod
    def load(cls, json_value):
        return cls(**json_value)

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
