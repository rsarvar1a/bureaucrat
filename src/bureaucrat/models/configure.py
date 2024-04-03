import databases
import ormar
import os
import sqlalchemy

DATABASE_URL = os.getenv("DATABASE_URL")

CONFIG = ormar.OrmarConfig(
    database=databases.Database(DATABASE_URL),
    metadata=sqlalchemy.MetaData(),
    engine=sqlalchemy.create_engine(DATABASE_URL),
)
