from datetime import datetime
from ormar import ReferentialAction

from .configure import CONFIG, ormar


class Script(ormar.Model):
    """
    A model representing a rendered script.
    It owns many documents, which are the JSON inputs and PDF or PNG outputs of the rendering step.
    """

    ormar_config = CONFIG.copy(tablename="scripts")

    id: str = ormar.String(primary_key=True, max_length=64)
    author: int = ormar.BigInteger()
    created: datetime = ormar.DateTime(timezone=True)
    logo: str = ormar.String(max_length=500, nullable=True)
    name: str = ormar.String(max_length=250)


class Document(ormar.Model):
    """
    A model representing a script's rendering inputs and outputs.
    A document is a JSON file, or a PDF or PNG produced by scriptmaker.
    it is stored in AWS S3.
    """

    ormar_config = CONFIG.copy(tablename="documents")

    id: int = ormar.Integer(primary_key=True)
    doctype: str = ormar.String(max_length=10)
    script: Script = ormar.ForeignKey(Script, ondelete=ReferentialAction.CASCADE, onupdate=ReferentialAction.CASCADE)
    url: str = ormar.String(max_length=500)
