import tomllib

from bureaucrat import admin, feedback, games, models, reminders, scripts
from bureaucrat.utility import aws, logging
from discord import AllowedMentions, Intents
from discord.ext.commands import DefaultHelpCommand
from discord.ext.commands.bot import Bot


class Config:

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)

    @classmethod 
    def load(cls, path):
        with open(path, "rb") as toml_file:
            obj = tomllib.load(toml_file)
        return Config(**obj)


class Bureaucrat(Bot):

    COG_MODULES = (admin, feedback, games, reminders, scripts)

    def __init__(self, *, config: Config):

        # Save the config.
        self.config = config

        # Create a handle to AWS for S3 operations.
        # It authenticates by checking the environment for AWS access variables.
        self.aws = aws.AWSClient(self)

        # Create Bureaucrat's logging handle, so that all Bureaucrat-level modules use the same label.
        severity = logging.severity(config.log_level)
        self.logger = logging.make_logger(name="Bureaucrat", severity=severity)
        self.logger.debug("Debug mode enabled.")

        # Initialize the underlying client.
        options = {
            "allowed_mentions": AllowedMentions(everyone=False),
            "case_insensitive": True,
            "help_command": DefaultHelpCommand(dm_help=None, dm_help_threshold=500, sort_commands=True),
            "intents": Intents.all(),
            "log_level": severity,
        }
        super().__init__(config.prefix, **options)
        self.owner_ids = config.owners

        self.logger.debug(f"Owned by {', '.join(str(i) for i in self.owner_ids)}.")

    async def setup_hook(self) -> None:

        await models.setup()

        # Initialize the cogs.
        # Each module should expose a setup function.
        self.logger.info(f"Loading extensions: {', '.join(m.__name__ for m in Bureaucrat.COG_MODULES)}.")
        for module in Bureaucrat.COG_MODULES:
            await module.setup(self)
