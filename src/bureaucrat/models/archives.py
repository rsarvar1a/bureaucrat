from .configure import CONFIG, DictType, JSONable, ormar


class ArchiveCategory(ormar.Model):
    """
    Tracks the category to archive into.
    """

    ormar_config = CONFIG.copy(tablename="archive_categories")

    id: int = ormar.BigInteger(primary_key=True)
    category: int = ormar.BigInteger()
