from bureaucrat import admin, feedback, models, scripts, townsquare
from bureaucrat.utility import aws, logging
from discord import AllowedMentions, Intents
from discord.ext.commands import DefaultHelpCommand
from discord.ext.commands.bot import Bot


class Bureaucrat(Bot):

    COG_MODULES = (admin, feedback, scripts, townsquare)
    DEFAULT_PREFIX = ">"
    NACL = 84045472511033344

    def __init__(self, *, log_level="info", owner_id=NACL, prefix=DEFAULT_PREFIX):

        # Create a handle to AWS for S3 operations.
        # It authenticates by checking the environment for AWS access variables.
        self.aws = aws.AWSClient(self)

        # Create Bureaucrat's logging handle, so that all Bureaucrat-level modules use the same label.
        severity = logging.severity(log_level)
        self.logger = logging.make_logger(name="Bureaucrat", severity=severity)

        # Initialize the underlying client.
        options = {
            "allowed_mentions": AllowedMentions(everyone=False),
            "case_insensitive": True,
            "help_command": DefaultHelpCommand(dm_help=None, dm_help_threshold=500, sort_commands=True),
            "intents": Intents.all(),
            "log_level": severity,
            "owner_id": owner_id,
        }
        super().__init__(prefix, **options)

    async def setup_hook(self) -> None:

        await models.setup()

        # Initialize the cogs.
        # Each module should expose a setup function.
        self.logger.info(f"Loading extensions: {', '.join(m.__name__ for m in Bureaucrat.COG_MODULES)}")
        for module in Bureaucrat.COG_MODULES:
            await module.setup(self)
